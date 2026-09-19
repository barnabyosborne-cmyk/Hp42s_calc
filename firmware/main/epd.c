#include <string.h>

#include "epd.h"
#include "board.h"

#include "driver/spi_master.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "epd";

// SSD1680 commands. Only the ones this driver uses; hex values and semantics
// are from the command table, datasheet sections 8 and 9.
#define CMD_DRIVER_OUTPUT   0x01
#define CMD_SOFT_START      0x0C
#define CMD_DEEP_SLEEP      0x10
#define CMD_DATA_ENTRY      0x11
#define CMD_SW_RESET        0x12
#define CMD_TEMP_SENSOR     0x18
#define CMD_MASTER_ACTIVATE 0x20
#define CMD_UPDATE_CTRL2    0x22
#define CMD_WRITE_RAM_BW    0x24
#define CMD_WRITE_RAM_RED   0x26
#define CMD_BORDER_WAVEFORM 0x3C
#define CMD_SET_RAM_X       0x44
#define CMD_SET_RAM_Y       0x45
#define CMD_SET_RAM_X_AC    0x4E
#define CMD_SET_RAM_Y_AC    0x4F

// 0x22 sequences, straight out of the datasheet's own table for that register.
#define SEQ_LOAD_LUT_MODE1  0xB1   // clock on, load temperature, load LUT 1
#define SEQ_DISPLAY_MODE1   0xF7   // analog on, load temperature, display, off
#define SEQ_DISPLAY_MODE2   0xFF   // the same with the mode 2 (partial) LUT

static spi_device_handle_t s_spi;
static uint8_t s_fb[EPD_FB_BYTES];
static uint8_t s_prev[EPD_FB_BYTES];

uint8_t *epd_framebuffer(void) { return s_fb; }

// BUSY is HIGH while the controller is working -- datasheet wording, "BUSY pad
// will output high during operation". Getting this polarity backwards is the
// classic way to make a panel that never updates.
static void wait_busy(const char *what)
{
    int waited = 0;
    while (gpio_get_level(EPD_BUSY)) {
        vTaskDelay(pdMS_TO_TICKS(10));
        waited += 10;
        if (waited > 20000) {
            ESP_LOGE(TAG, "BUSY stuck high for 20 s during %s", what);
            return;
        }
    }
}

static void tx(bool is_data, const uint8_t *buf, size_t len)
{
    gpio_set_level(EPD_DC, is_data ? 1 : 0);
    spi_transaction_t t = {
        .length = len * 8,
        .tx_buffer = buf,
    };
    ESP_ERROR_CHECK(spi_device_polling_transmit(s_spi, &t));
}

static void cmd(uint8_t c) { tx(false, &c, 1); }
static void dat(uint8_t d) { tx(true, &d, 1); }
static void dat_n(const uint8_t *d, size_t n) { tx(true, d, n); }

static void hw_reset(void)
{
    gpio_set_level(EPD_RST, 1);
    vTaskDelay(pdMS_TO_TICKS(10));
    gpio_set_level(EPD_RST, 0);
    vTaskDelay(pdMS_TO_TICKS(10));   // datasheet asks for at least 200 us
    gpio_set_level(EPD_RST, 1);
    vTaskDelay(pdMS_TO_TICKS(10));
    wait_busy("hw reset");
}

// Step 3 of the operation flow: gate driver output, RAM size, border.
static void send_init_code(uint8_t border)
{
    cmd(CMD_SW_RESET);
    vTaskDelay(pdMS_TO_TICKS(10));
    wait_busy("sw reset");

    // 296 gate lines, so MUX = 296 - 1 = 0x127. Third byte 0x00 leaves the
    // scan direction at its power-on default.
    cmd(CMD_DRIVER_OUTPUT);
    dat((EPD_GATES - 1) & 0xFF);
    dat(((EPD_GATES - 1) >> 8) & 0x01);
    dat(0x00);

    // 0x03 = Y increment, X increment, counter walks in X. With the X window
    // 19 bytes wide that means one gate line per 19 bytes written, in order,
    // which is exactly how the framebuffer is laid out.
    cmd(CMD_DATA_ENTRY);
    dat(0x03);

    cmd(CMD_SET_RAM_X);
    dat(0x00);
    dat(EPD_SRC_BYTES - 1);

    cmd(CMD_SET_RAM_Y);
    dat(0x00);
    dat(0x00);
    dat((EPD_GATES - 1) & 0xFF);
    dat(((EPD_GATES - 1) >> 8) & 0x01);

    cmd(CMD_BORDER_WAVEFORM);
    dat(border);

    // 0x80 selects the on-chip temperature sensor, which is what makes the
    // OTP waveform load pick the right LUT for the room.
    cmd(CMD_TEMP_SENSOR);
    dat(0x80);

    // Display Update Control 1 (0x21) is deliberately left at its power-on
    // value. Its B[7] bit narrows the available sources to S8..S167, which is
    // for 160-source glass; this panel has 152 sources starting at S0, so the
    // default is the correct setting and not an oversight.

    cmd(CMD_UPDATE_CTRL2);
    dat(SEQ_LOAD_LUT_MODE1);
    cmd(CMD_MASTER_ACTIVATE);
    wait_busy("load waveform");
}

esp_err_t epd_init(void)
{
    gpio_config_t out = {
        .pin_bit_mask = (1ULL << EPD_DC) | (1ULL << EPD_RST),
        .mode = GPIO_MODE_OUTPUT,
    };
    ESP_ERROR_CHECK(gpio_config(&out));

    gpio_config_t in = {
        .pin_bit_mask = (1ULL << EPD_BUSY),
        .mode = GPIO_MODE_INPUT,
    };
    ESP_ERROR_CHECK(gpio_config(&in));

    spi_bus_config_t bus = {
        .mosi_io_num = EPD_MOSI,
        .miso_io_num = -1,
        .sclk_io_num = EPD_SCK,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = EPD_FB_BYTES + 8,
    };
    ESP_ERROR_CHECK(spi_bus_initialize(SPI2_HOST, &bus, SPI_DMA_CH_AUTO));

    // The SSD1680 takes 20 MHz. 10 is plenty for 5.6 kB a frame and leaves
    // margin for whatever the FPC does to the edges.
    spi_device_interface_config_t dev = {
        .clock_speed_hz = 10 * 1000 * 1000,
        .mode = 0,
        .spics_io_num = EPD_CS,
        .queue_size = 1,
    };
    ESP_ERROR_CHECK(spi_bus_add_device(SPI2_HOST, &dev, &s_spi));

    hw_reset();
    send_init_code(0x05);
    epd_clear(true);
    memset(s_prev, 0xFF, sizeof(s_prev));
    ESP_LOGI(TAG, "panel up: %dx%d, %d byte framebuffer", EPD_W, EPD_H,
             (int)sizeof(s_fb));
    return ESP_OK;
}

void epd_clear(bool white) { memset(s_fb, white ? 0xFF : 0x00, sizeof(s_fb)); }

// The calculator's x runs along the panel's gate axis and its y along the
// source axis, which is the whole of the landscape rotation.
void epd_pixel(int x, int y, bool black)
{
    if (x < 0 || x >= EPD_W || y < 0 || y >= EPD_H) return;
    uint8_t *p = &s_fb[x * EPD_SRC_BYTES + (y >> 3)];
    uint8_t mask = 0x80 >> (y & 7);
    if (black) *p &= (uint8_t)~mask;   // 0 is black
    else       *p |= mask;
}

void epd_fill_rect(int x, int y, int w, int h, bool black)
{
    for (int j = y; j < y + h; j++)
        for (int i = x; i < x + w; i++)
            epd_pixel(i, j, black);
}

static void write_ram(uint8_t which, const uint8_t *src)
{
    cmd(CMD_SET_RAM_X_AC);
    dat(0x00);
    cmd(CMD_SET_RAM_Y_AC);
    dat(0x00);
    dat(0x00);
    cmd(which);
    dat_n(src, EPD_FB_BYTES);
}

esp_err_t epd_update_full(void)
{
    write_ram(CMD_WRITE_RAM_BW, s_fb);
    cmd(CMD_UPDATE_CTRL2);
    dat(SEQ_DISPLAY_MODE1);
    cmd(CMD_MASTER_ACTIVATE);
    wait_busy("full update");
    memcpy(s_prev, s_fb, sizeof(s_prev));
    return ESP_OK;
}

// Mode 2 drives only the pixels that changed, which is what makes a keystroke
// cost a few hundred milliseconds instead of a couple of seconds. The
// controller works it out from the two RAMs, so the previous frame goes into
// the red RAM and the new one into the black/white RAM.
//
// The mode 2 waveform comes from the panel's OTP. If ghosting builds up, the
// answer is a periodic full update -- every tenth partial is the usual rule --
// rather than a different waveform.
esp_err_t epd_update_partial(void)
{
    // A partial update needs the border held at VCOM rather than driven, or
    // the frame edge flashes on every keystroke.
    cmd(CMD_BORDER_WAVEFORM);
    dat(0x80);

    write_ram(CMD_WRITE_RAM_RED, s_prev);
    write_ram(CMD_WRITE_RAM_BW, s_fb);

    cmd(CMD_UPDATE_CTRL2);
    dat(SEQ_DISPLAY_MODE2);
    cmd(CMD_MASTER_ACTIVATE);
    wait_busy("partial update");

    memcpy(s_prev, s_fb, sizeof(s_prev));
    return ESP_OK;
}

esp_err_t epd_sleep(void)
{
    cmd(CMD_DEEP_SLEEP);
    dat(0x01);
    vTaskDelay(pdMS_TO_TICKS(10));
    return ESP_OK;
}
