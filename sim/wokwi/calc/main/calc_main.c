// calc_main.c -- the calculator in Wokwi.
//
// Plus42 on the real shell, keypad and panel code, the way the board will run
// it, minus sleep. After every key it prints the X register, so a scenario can
// check the arithmetic ("x 5"), and the SSD1680 chip dumps each frame it
// shows, so frames.py can turn a run into pictures.

#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>

#include "board.h"
#include "epd.h"
#include "keypad.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

void plus42_start(void);
void plus42_keydown(int key);
void plus42_keyup(void);
bool plus42_running(void);
void plus42_step(void);
bool plus42_take_dirty(void);
char *plus42_x(void);

static void show(void)
{
    if (plus42_take_dirty())
        epd_update_partial();
}

static void print_x(void)
{
    char *x = plus42_x();
    printf("x %s\n", x ? x : "?");
    free(x);
}

void app_main(void)
{
    keypad_init();
    ESP_ERROR_CHECK(epd_init());
    plus42_start();
    plus42_take_dirty();
    epd_update_full();
    printf("hp42s calc ready\n");
    print_x();

    int presses = 0;
    while (1) {
        int k = keypad_scan();
        if (k == KEY_NONE) {
            if (plus42_running()) {
                plus42_step();
                show();
            } else {
                vTaskDelay(pdMS_TO_TICKS(10));
            }
            continue;
        }
        printf("key %d\n", k);
        plus42_keydown(k);
        show();
        keypad_wait_release();
        plus42_keyup();
        show();
        printf("up %d\n", k);
        print_x();

        // A full refresh every tenth key clears ghosting on the real panel.
        if (++presses % 10 == 0) epd_update_full();
    }
}
