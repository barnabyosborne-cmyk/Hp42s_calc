// Minimal shell layer: enough to link and run the Plus42 core on the board.
// Display, keys, beeper and time are wired to the board layer. The
// accelerometer, GPS, compass and pop-up alpha keyboard are Android/iOS only:
// shell.h compiles them out for us, so there is nothing to supply.

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <sys/time.h>
#include "free42.h"
#include "shell.h"
#include "core_main.h"

extern "C" {
#include "esp_timer.h"
#include "esp_system.h"
#include "esp_random.h"
#include "epd.h"
}

const char *shell_platform() { return "1.3.15 ESP32-S3"; }

void shell_blitter(const char *bits, int bytesperline, int x, int y,
                   int width, int height) {
    for (int r = 0; r < height; r++)
        for (int c = 0; c < width; c++) {
            int sx = x + c, sy = y + r;
            int bit = (bits[sy * bytesperline + (sx >> 3)] >> (sx & 7)) & 1;
            epd_pixel(sx, sy, bit);
        }
}

void shell_beeper(int tone)                 { (void) tone; }
void shell_annunciators(int, int, int, int, int, int) { }
bool shell_wants_cpu()                      { return false; }
void shell_delay(int duration)              { (void) duration; }
void shell_request_timeout3(int delay)      { (void) delay; }
void shell_request_display_size(int r, int c) { (void) r; (void) c; }
uint8 shell_get_mem()                       { return 0; }
bool shell_low_battery()                    { return false; }
void shell_powerdown()                      { }
int8 shell_random_seed()                    { return (int8) esp_random(); }
uint4 shell_milliseconds()                  { return (uint4)(esp_timer_get_time() / 1000); }
const char *shell_number_format()           { return "..."; }
void shell_set_skin_mode(int mode)          { (void) mode; }
int shell_date_format()                     { return 1; }   // DMY
bool shell_clk24()                          { return true; }
void shell_print(const char *, int, const char *, int, int, int, int, int) { }

void shell_get_time_date(uint4 *time, uint4 *date, int *weekday) {
    if (time) *time = 0;
    if (date) *date = 20260101;
    if (weekday) *weekday = 4;
}

void shell_message(const char *message)     { printf("plus42: %s\n", message); }
void shell_log(const char *message)         { printf("plus42: %s\n", message); }

extern "C" void plus42_start(void) {
    int rows = 0, cols = 0;
    core_init(&rows, &cols, 0, NULL);
    printf("plus42 core up, display %d x %d\n", rows, cols);
    core_repaint_display(rows, cols, 3);
}
