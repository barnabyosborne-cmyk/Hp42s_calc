// sim_main.c -- the Wokwi test app for the keypad and the panel.
//
// Prints one line per key, in a form the scenario in keypad.test.yaml can
// check: "key 19 7". Each key also redraws the panel with a partial update, so
// a run exercises epd.c against the SSD1680 chip on every keystroke, the same
// way the calculator will.

#include <stdio.h>

#include "board.h"
#include "epd.h"
#include "keypad.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

// The legend on each key, by the core's key number (1-based).
static const char *const s_names[KEY_MAX + 1] = {
    "none",
    "SUM+", "1/x", "SQRT", "LOG", "LN", "XEQ",
    "STO", "RCL", "RDN", "SIN", "COS", "TAN",
    "ENTER", "X<>Y", "+/-", "E", "BKSP",
    "UP", "7", "8", "9", "DIV",
    "DOWN", "4", "5", "6", "MUL",
    "SHIFT", "1", "2", "3", "SUB",
    "EXIT", "0", ".", "R/S", "ADD",
};

static void draw(int last_key)
{
    epd_clear(true);

    // The part of the glass the case aperture shows, outlined, so it is plain
    // in the simulator which columns the case will hide.
    epd_fill_rect(EPD_VIEW_X, 0, EPD_VIEW_W, 2, true);
    epd_fill_rect(EPD_VIEW_X, EPD_H - 2, EPD_VIEW_W, 2, true);
    epd_fill_rect(EPD_VIEW_X, 0, 2, EPD_H, true);
    epd_fill_rect(EPD_VIEW_X + EPD_VIEW_W - 2, 0, 2, EPD_H, true);

    // Top-left block: shows at a glance if the image is mirrored or rotated.
    epd_fill_rect(EPD_VIEW_X + 6, 6, 24, 12, true);

    // One bar per key, the pressed one tall.
    for (int i = 0; i < KEY_MAX; i++) {
        int x = EPD_VIEW_X + 8 + i * 7;
        int h = (i + 1 == last_key) ? 80 : 12;
        epd_fill_rect(x, EPD_H - 10 - h, 5, h, true);
    }
}

void app_main(void)
{
    keypad_init();
    ESP_ERROR_CHECK(epd_init());
    draw(KEY_NONE);
    epd_update_full();

    printf("hp42s sim ready\n");

    int presses = 0;
    while (1) {
        int k = keypad_scan();
        if (k == KEY_NONE) {
            vTaskDelay(pdMS_TO_TICKS(10));
            continue;
        }
        printf("key %d %s\n", k, s_names[k]);
        draw(k);
        epd_update_partial();
        keypad_wait_release();
        printf("up %d\n", k);

        // Every tenth partial is followed by a full refresh on the real
        // panel, to clear ghosting; do the same here so both paths run.
        if (++presses % 10 == 0) epd_update_full();
    }
}
