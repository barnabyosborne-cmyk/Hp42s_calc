// main.c -- board bring-up for the HP-42S clone.
//
// This is NOT the calculator. It is the thing you flash onto the first board
// to find out whether the board works: it draws a test pattern on the panel,
// prints every key you press, and then proves the deep-sleep wake path by
// going to sleep and coming back on a keystroke.
//
// Plus42 goes on top of this. Its core is portable C++ that wants a shell
// underneath it, and the shell is what these files are: a panel to draw on, a
// keyboard to read, and a way to sleep. See firmware/README.md.

#include <stdio.h>

#include "board.h"
#include "epd.h"
#include "keypad.h"

#include "esp_log.h"
#include "esp_sleep.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "hp42s";

// Sleep after this long with nobody pressing anything. The real firmware will
// want a minute or two; ten seconds makes the wake path easy to test.
#define IDLE_SLEEP_MS 10000

static void draw_test_pattern(int last_key)
{
    epd_clear(true);

    // A frame, so it is obvious at a glance whether the whole panel is alive
    // and which way round it is.
    epd_fill_rect(0, 0, EPD_W, 2, true);
    epd_fill_rect(0, EPD_H - 2, EPD_W, 2, true);
    epd_fill_rect(0, 0, 2, EPD_H, true);
    epd_fill_rect(EPD_W - 2, 0, 2, EPD_H, true);

    // A solid block in the top left corner only. If the panel comes up
    // mirrored or rotated this is the thing that shows it.
    epd_fill_rect(8, 8, 24, 12, true);

    // A bar chart of the last key number, one bar per key, so a keypress is
    // visible on the glass without a font.
    for (int i = 0; i < KEY_MAX; i++) {
        int x = 8 + i * 7;
        int h = (i + 1 == last_key) ? 60 : 12;
        epd_fill_rect(x, EPD_H - 12 - h, 5, h, true);
    }
}

void app_main(void)
{
    // Read this before anything re-drives the matrix: it is latched by the
    // wake and the rows have to stay as sleep left them to decode it.
    int woke_on = keypad_wake_key();

    keypad_init();
    gpio_set_direction(PIN_LED_RED, GPIO_MODE_OUTPUT);
    gpio_set_direction(PIN_LED_GREEN, GPIO_MODE_OUTPUT);
    gpio_set_level(PIN_LED_RED, LED_OFF);
    gpio_set_level(PIN_LED_GREEN, LED_ON);

    ESP_ERROR_CHECK(epd_init());

    if (woke_on != KEY_NONE)
        ESP_LOGI(TAG, "woke on key %d", woke_on);
    else
        ESP_LOGI(TAG, "cold start");

    draw_test_pattern(woke_on);
    ESP_ERROR_CHECK(epd_update_full());

    int idle_ms = 0;
    int last_key = woke_on;

    while (1) {
        int k = keypad_scan();
        if (k != KEY_NONE) {
            ESP_LOGI(TAG, "key %d", k);
            gpio_set_level(PIN_LED_RED, LED_ON);
            last_key = k;
            draw_test_pattern(last_key);
            epd_update_partial();
            gpio_set_level(PIN_LED_RED, LED_OFF);
            keypad_wait_release();
            idle_ms = 0;
            continue;
        }

        vTaskDelay(pdMS_TO_TICKS(20));
        idle_ms += 20;

        if (idle_ms >= IDLE_SLEEP_MS) {
            ESP_LOGI(TAG, "idle, going to sleep -- press any key");
            gpio_set_level(PIN_LED_GREEN, LED_OFF);
            epd_sleep();
            keypad_arm_wake();
            esp_deep_sleep_start();
        }
    }
}
