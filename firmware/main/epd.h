// epd.h -- GDEY0266T90 e-paper panel on an SSD1680 controller.
//
// The panel is 152(H) x 296(V) in its own coordinates: 152 source lines and
// 296 gate lines. We use it on its side, so the calculator sees a landscape
// 296 x 152 display and this file does the swap.
//
// Everything here follows Solomon Systech's own operation flow, figure 9-1 of
// the SSD1680 datasheet rev 0.14, which Good Display reprints unchanged on
// page 30 of the GDEY0266T90 specification.
#pragma once

#include <stdbool.h>
#include <stdint.h>
#include "esp_err.h"

#define EPD_W 296   // what the calculator sees, across
#define EPD_H 152   // and down

// The panel's own geometry, which is the framebuffer's shape.
#define EPD_SRC_BYTES (EPD_H / 8)          // 19 bytes of source per gate line
#define EPD_GATES     EPD_W                // 296 gate lines
#define EPD_FB_BYTES  (EPD_SRC_BYTES * EPD_GATES)

esp_err_t epd_init(void);

// 1 is white and 0 is black, which is the SSD1680's own convention for the
// black/white RAM, not an inversion introduced here.
void epd_clear(bool white);
void epd_pixel(int x, int y, bool black);
void epd_fill_rect(int x, int y, int w, int h, bool black);

// A full update rewrites every pixel with the panel's mode 1 waveform. Slow,
// a couple of seconds, and the only thing that clears ghosting.
esp_err_t epd_update_full(void);

// A partial update uses mode 2 against the previous frame. This is the one
// that runs on a keystroke.
esp_err_t epd_update_partial(void);

// Deep sleep draws essentially nothing but needs a hardware reset to leave,
// which epd_init() does. The image stays on the glass either way.
esp_err_t epd_sleep(void);

uint8_t *epd_framebuffer(void);
