#include "keypad.h"
#include "board.h"

#include "driver/rtc_io.h"
#include "esp_log.h"
#include "esp_sleep.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_rom_sys.h"

static const char *TAG = "keypad";

// Row-major, in the core's key order. A 0 is a position with no key: row 2
// column 1 is the right-hand half of ENTER, whose second dome is wired in
// parallel with the first, and rows 3 to 6 are five keys wide because the
// numeric block uses a coarser column pitch than the function rows.
static const uint8_t s_map[KP_ROWS][KP_COLS] = {
    {  1,  2,  3,  4,  5,  6 },   // SUM+  1/x   sqrt  LOG  LN   XEQ
    {  7,  8,  9, 10, 11, 12 },   // STO   RCL   Rv    SIN  COS  TAN
    { 13,  0, 14, 15, 16, 17 },   // ENTER ----- x<>y  +/-  E    <--
    { 18, 19, 20, 21, 22,  0 },   // up    7     8     9    div
    { 23, 24, 25, 26, 27,  0 },   // down  4     5     6    mul
    { 28, 29, 30, 31, 32,  0 },   // SHIFT 1     2     3    minus
    { 33, 34, 35, 36, 37,  0 },   // EXIT  0     .     R/S  plus
};

// A metal dome settles in a couple of milliseconds. Ten is comfortable and
// still far below the time a finger spends on a key.
#define DEBOUNCE_MS 10

static uint64_t col_mask(void)
{
    uint64_t m = 0;
    for (int c = 0; c < KP_COLS; c++) m |= 1ULL << kp_col[c];
    return m;
}

void keypad_init(void)
{
    for (int r = 0; r < KP_ROWS; r++) {
        gpio_reset_pin(kp_row[r]);
        gpio_set_direction(kp_row[r], GPIO_MODE_OUTPUT);
        gpio_set_level(kp_row[r], 1);
    }
    for (int c = 0; c < KP_COLS; c++) {
        gpio_reset_pin(kp_col[c]);
        gpio_set_direction(kp_col[c], GPIO_MODE_INPUT);
        gpio_set_pull_mode(kp_col[c], GPIO_PULLUP_ONLY);
    }
}

// One pass over the matrix. Drives each row low in turn and looks for a column
// that follows it down.
static int scan_once(void)
{
    for (int r = 0; r < KP_ROWS; r++) {
        gpio_set_level(kp_row[r], 0);
        esp_rom_delay_us(20);       // let the column's pull-up settle
        for (int c = 0; c < KP_COLS; c++) {
            if (gpio_get_level(kp_col[c]) == 0 && s_map[r][c] != 0) {
                gpio_set_level(kp_row[r], 1);
                return s_map[r][c];
            }
        }
        gpio_set_level(kp_row[r], 1);
    }
    return KEY_NONE;
}

int keypad_scan(void)
{
    int first = scan_once();
    if (first == KEY_NONE) return KEY_NONE;
    vTaskDelay(pdMS_TO_TICKS(DEBOUNCE_MS));
    return (scan_once() == first) ? first : KEY_NONE;
}

void keypad_wait_release(void)
{
    while (scan_once() != KEY_NONE) vTaskDelay(pdMS_TO_TICKS(DEBOUNCE_MS));
    vTaskDelay(pdMS_TO_TICKS(DEBOUNCE_MS));
}

void keypad_arm_wake(void)
{
    // Every row low, and held there through sleep. Without the hold the pads
    // revert when the digital domain powers down and nothing can pull a column
    // low, so the calculator never wakes.
    for (int r = 0; r < KP_ROWS; r++) {
        rtc_gpio_init(kp_row[r]);
        rtc_gpio_set_direction(kp_row[r], RTC_GPIO_MODE_OUTPUT_ONLY);
        rtc_gpio_set_level(kp_row[r], 0);
        rtc_gpio_hold_en(kp_row[r]);
    }
    for (int c = 0; c < KP_COLS; c++) {
        rtc_gpio_init(kp_col[c]);
        rtc_gpio_set_direction(kp_col[c], RTC_GPIO_MODE_INPUT_ONLY);
        rtc_gpio_pulldown_dis(kp_col[c]);
        rtc_gpio_pullup_en(kp_col[c]);
    }
    ESP_ERROR_CHECK(
        esp_sleep_enable_ext1_wakeup_io(col_mask(), ESP_EXT1_WAKEUP_ANY_LOW));
    ESP_LOGI(TAG, "matrix armed, %d columns watched", KP_COLS);
}

void keypad_release_wake(void)
{
    for (int r = 0; r < KP_ROWS; r++) {
        rtc_gpio_hold_dis(kp_row[r]);
        rtc_gpio_deinit(kp_row[r]);
    }
    for (int c = 0; c < KP_COLS; c++) rtc_gpio_deinit(kp_col[c]);
}

// ext1 tells us which column went low, not which key. Every row was low during
// sleep, so the row is still unknown: drive them one at a time and find the
// one the finger is bridging. The key is almost certainly still down, because
// the chip wakes in a few milliseconds and people do not press keys that fast.
int keypad_wake_key(void)
{
    if (esp_sleep_get_wakeup_cause() != ESP_SLEEP_WAKEUP_EXT1) return KEY_NONE;
    uint64_t woke = esp_sleep_get_ext1_wakeup_status();
    if (woke == 0) return KEY_NONE;

    keypad_release_wake();
    keypad_init();

    for (int c = 0; c < KP_COLS; c++) {
        if (!(woke & (1ULL << kp_col[c]))) continue;
        for (int r = 0; r < KP_ROWS; r++) {
            gpio_set_level(kp_row[r], 0);
            esp_rom_delay_us(20);
            int down = (gpio_get_level(kp_col[c]) == 0);
            gpio_set_level(kp_row[r], 1);
            if (down && s_map[r][c] != 0) return s_map[r][c];
        }
    }
    return KEY_NONE;
}
