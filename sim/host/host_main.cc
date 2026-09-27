// host_main.cc -- Plus42 and the real shell.cc on a PC, drawing into the same
// panel framebuffer layout as firmware/main/epd.c.
//
// It is the calculator half of the Wokwi simulation without the simulator:
// no ESP32, no SPI, no keypad scan, so it needs no Wokwi minutes and runs in a
// second. What it proves is what the core draws and where shell_blitter puts
// it on the panel; the keypad and the SSD1680 protocol are Wokwi's job.
//
//     ./hp42s_host OUTDIR KEY KEY ...     keys by legend, e.g. 2 ENTER 3 ADD
//
// Writes OUTDIR/frame-NN.pbm for every panel update (NN from 00, the boot
// screen) and prints the X register after each key.

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>

extern "C" {
#include "epd.h"
}

// --- the panel, as epd.c lays it out -----------------------------------------
static uint8_t s_fb[EPD_FB_BYTES];
static const char *s_out;
static int s_frame;

extern "C" {
uint8_t *epd_framebuffer(void) { return s_fb; }
esp_err_t epd_init(void) { return 0; }
void epd_clear(bool white) { memset(s_fb, white ? 0xFF : 0x00, sizeof s_fb); }
void epd_pixel(int x, int y, bool black) {
    if (x < 0 || x >= EPD_W || y < 0 || y >= EPD_H) return;
    uint8_t *p = &s_fb[x * EPD_SRC_BYTES + (y >> 3)];
    uint8_t mask = 0x80 >> (y & 7);
    if (black) *p &= (uint8_t)~mask;
    else       *p |= mask;
}
void epd_fill_rect(int x, int y, int w, int h, bool black) {
    for (int j = y; j < y + h; j++)
        for (int i = x; i < x + w; i++)
            epd_pixel(i, j, black);
}
static esp_err_t save(void) {
    char path[512];
    snprintf(path, sizeof path, "%s/frame-%02d.pbm", s_out, s_frame++);
    FILE *f = fopen(path, "wb");
    if (!f) { perror(path); exit(1); }
    fprintf(f, "P1\n%d %d\n", EPD_W, EPD_H);
    for (int y = 0; y < EPD_H; y++) {
        for (int x = 0; x < EPD_W; x++)
            fputs((s_fb[x * EPD_SRC_BYTES + (y >> 3)] & (0x80 >> (y & 7))) ? "0" : "1", f);
        fputc('\n', f);
    }
    fclose(f);
    return 0;
}
esp_err_t epd_update_full(void) { return save(); }
esp_err_t epd_update_partial(void) { return save(); }
esp_err_t epd_sleep(void) { return 0; }

int64_t esp_timer_get_time(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (int64_t)t.tv_sec * 1000000 + t.tv_nsec / 1000;
}
uint32_t esp_random(void) { return (uint32_t)rand(); }

void plus42_start(void);
void plus42_keydown(int key);
void plus42_keyup(void);
bool plus42_running(void);
void plus42_step(void);
bool plus42_take_dirty(void);
char *plus42_x(void);
}

// The legends, by core key number; the same table as sim_main.c.
static const char *const s_names[] = {
    "none",
    "SUM+", "1/x", "SQRT", "LOG", "LN", "XEQ",
    "STO", "RCL", "RDN", "SIN", "COS", "TAN",
    "ENTER", "X<>Y", "+/-", "E", "BKSP",
    "UP", "7", "8", "9", "DIV",
    "DOWN", "4", "5", "6", "MUL",
    "SHIFT", "1", "2", "3", "SUB",
    "EXIT", "0", ".", "R/S", "ADD",
};

static int key_of(const char *name) {
    for (int k = 1; k <= 37; k++)
        if (!strcasecmp(name, s_names[k])) return k;
    int n = atoi(name);
    if (n >= 1 && n <= 37 && strspn(name, "0123456789") == strlen(name)) return n;
    fprintf(stderr, "no key called %s\n", name);
    exit(2);
}

static void show(void) {
    if (plus42_take_dirty()) epd_update_partial();
}

static void print_x(void) {
    char *x = plus42_x();
    printf("x %s\n", x ? x : "?");
    free(x);
}

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: %s OUTDIR KEY...\n", argv[0]);
        return 2;
    }
    s_out = argv[1];
    epd_init();
    plus42_start();
    plus42_take_dirty();
    epd_update_full();
    print_x();
    for (int i = 2; i < argc; i++) {
        int k = key_of(argv[i]);
        printf("key %d %s -> frame %02d\n", k, s_names[k], s_frame);
        plus42_keydown(k);
        show();
        plus42_keyup();
        show();
        for (int n = 0; plus42_running() && n < 1000000; n++) {
            plus42_step();
            show();
        }
        print_x();
    }
    return 0;
}
