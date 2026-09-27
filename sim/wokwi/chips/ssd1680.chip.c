// ssd1680.chip.c -- a Wokwi custom chip for the SSD1680 e-paper controller,
// as fitted to the GDEY0266T90 panel (152 sources x 296 gates).
//
// It is not a model of the glass. It is a model of the controller's interface,
// good enough to prove that firmware/main/epd.c talks to it correctly: the
// command set epd.c uses, the RAM and its address counters, BUSY, reset and
// deep sleep. Waveforms, temperature, ghosting and the red RAM's part in a
// partial update are not modelled; the panel simply shows the black/white RAM
// once an update finishes.
//
// It also complains, on the simulator console, about the mistakes that make a
// real panel sit there blank: a command sent while BUSY is high, anything sent
// after deep sleep without a hardware reset, and a RAM write that runs off the
// end of the window. Those are the bugs the bench would otherwise find.
//
// The display is drawn landscape, 296 x 152, gate g at x = g and source s at
// y = s. That matches epd_pixel(), where the calculator's x runs along the
// gate axis. Whether the real glass reads the same way round is for the
// bench; the test pattern's corner block is there to show it.
//
// Attributes (set in diagram.json): fullUpdateMs (default 2000),
// partialUpdateMs (default 400), debug (default 0; 1 logs every command),
// dumpFrames (default 0; 1 prints every frame shown, for frames.py).

#include "wokwi-api.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define GATES      296
#define SOURCES    152
#define RAM_XBYTES 22          // the controller has 176 sources of RAM
#define RAM_BYTES  (RAM_XBYTES * GATES)

// The display's two colours, as RGBA. Grey paper and near-black ink rather
// than pure white and black, so it reads as e-paper at a glance.
static const uint8_t PAPER[4] = { 0xE4, 0xE2, 0xD8, 0xFF };
static const uint8_t INK[4]   = { 0x22, 0x22, 0x26, 0xFF };

typedef struct {
  pin_t cs, dc, rst, busy;
  spi_dev_t spi;
  uint8_t spi_byte;

  timer_t busy_timer;
  bool busy_on;
  bool pending_display;   // when BUSY drops, copy the RAM to the screen
  bool asleep;

  uint8_t cmd;
  int nparam;             // parameter bytes received for the current command
  uint8_t params[8];

  uint8_t data_entry;     // 0x11: bit0 X+, bit1 Y+, bit2 counter walks Y first
  int x_start, x_end;     // 0x44, in bytes
  int y_start, y_end;     // 0x45, in gates
  int x_ac, y_ac;         // 0x4E / 0x4F
  uint8_t ctrl2;          // 0x22
  bool overrun_logged;

  uint8_t bw[RAM_BYTES];
  uint8_t red[RAM_BYTES];

  buffer_t fb;
  uint32_t fb_w, fb_h;
  uint32_t full_ms, partial_ms;
  bool debug;
  bool dump;
  uint32_t updates;
} chip_t;

static void reset_registers(chip_t *c)
{
  c->cmd = 0;
  c->nparam = 0;
  c->data_entry = 0x03;
  c->x_start = 0;
  c->x_end = RAM_XBYTES - 1;
  c->y_start = 0;
  c->y_end = GATES - 1;
  c->x_ac = 0;
  c->y_ac = 0;
  c->ctrl2 = 0xFF;
  c->overrun_logged = false;
}

static void set_busy(chip_t *c, bool on, uint32_t micros)
{
  c->busy_on = on;
  pin_write(c->busy, on ? HIGH : LOW);
  if (on) timer_start(c->busy_timer, micros, false);
}

static void render(chip_t *c)
{
  uint8_t row[GATES * 4];
  for (uint32_t y = 0; y < c->fb_h && y < SOURCES; y++) {
    for (uint32_t x = 0; x < c->fb_w && x < GATES; x++) {
      uint8_t byte = c->bw[x * RAM_XBYTES + (y >> 3)];
      const uint8_t *px = (byte & (0x80 >> (y & 7))) ? PAPER : INK;
      memcpy(&row[x * 4], px, 4);
    }
    buffer_write(c->fb, y * c->fb_w * 4, row, c->fb_w * 4);
  }
}

// Prints the black/white RAM as it is shown, 8 gate lines to a console line:
// "EPDFRAME <update> <first gate> <hex>", each gate line being SOURCES/8
// bytes, bit 7 of the first byte at source 0, a set bit paper. Short lines,
// because the CLI interleaves chip output with the serial port and a long one
// is likelier to be split.
static void dump_frame(chip_t *c)
{
  static const char HEX[] = "0123456789abcdef";
  char line[40 + 8 * (SOURCES / 8) * 2];
  for (int g0 = 0; g0 < GATES; g0 += 8) {
    int n = snprintf(line, 40, "EPDFRAME %u %d ", (unsigned)c->updates, g0);
    for (int g = g0; g < g0 + 8 && g < GATES; g++)
      for (int b = 0; b < SOURCES / 8; b++) {
        uint8_t v = c->bw[g * RAM_XBYTES + b];
        line[n++] = HEX[v >> 4];
        line[n++] = HEX[v & 15];
      }
    line[n] = 0;
    printf("%s\n", line);
  }
}

static void busy_done(void *user_data)
{
  chip_t *c = user_data;
  if (c->pending_display) {
    render(c);
    c->pending_display = false;
    c->updates++;
    if (c->debug) printf("ssd1680: update %u shown\n", (unsigned)c->updates);
    if (c->dump) dump_frame(c);
  }
  set_busy(c, false, 0);
}

// Moves the RAM address counter on by one byte, the way 0x11 says to.
static void advance(chip_t *c)
{
  bool x_inc = c->data_entry & 0x01;
  bool y_inc = c->data_entry & 0x02;
  bool y_first = c->data_entry & 0x04;
  int xlo = c->x_start < c->x_end ? c->x_start : c->x_end;
  int xhi = c->x_start < c->x_end ? c->x_end : c->x_start;
  int ylo = c->y_start < c->y_end ? c->y_start : c->y_end;
  int yhi = c->y_start < c->y_end ? c->y_end : c->y_start;

  if (!y_first) {
    c->x_ac += x_inc ? 1 : -1;
    if (c->x_ac > xhi || c->x_ac < xlo) {
      c->x_ac = x_inc ? xlo : xhi;
      c->y_ac += y_inc ? 1 : -1;
    }
  } else {
    c->y_ac += y_inc ? 1 : -1;
    if (c->y_ac > yhi || c->y_ac < ylo) {
      c->y_ac = y_inc ? ylo : yhi;
      c->x_ac += x_inc ? 1 : -1;
    }
  }
}

static void ram_write(chip_t *c, uint8_t *ram, uint8_t value)
{
  if (c->x_ac < 0 || c->x_ac >= RAM_XBYTES || c->y_ac < 0 || c->y_ac >= GATES) {
    if (!c->overrun_logged) {
      printf("ssd1680: RAM write outside the panel at x=%d y=%d; check 0x44/0x45 "
             "and the byte count\n", c->x_ac, c->y_ac);
      c->overrun_logged = true;
    }
  } else {
    ram[c->y_ac * RAM_XBYTES + c->x_ac] = value;
  }
  advance(c);
}

static void master_activate(chip_t *c)
{
  uint8_t s = c->ctrl2;
  bool display = s & 0x04;
  bool mode2 = s & 0x08;
  uint32_t ms = display ? (mode2 ? c->partial_ms : c->full_ms) : 5;
  c->pending_display = display;
  if (c->debug)
    printf("ssd1680: activate 0x%02X, %s, BUSY for %u ms\n", s,
           display ? (mode2 ? "partial" : "full") : "no display", (unsigned)ms);
  set_busy(c, true, ms * 1000);
}

static void on_command(chip_t *c, uint8_t cmd)
{
  c->cmd = cmd;
  c->nparam = 0;
  if (c->debug) printf("ssd1680: cmd 0x%02X\n", cmd);

  switch (cmd) {
  case 0x12:   // software reset: registers to defaults, RAM kept
    reset_registers(c);
    set_busy(c, true, 2000);
    break;
  case 0x20:
    master_activate(c);
    break;
  case 0x24:
  case 0x26:
    c->overrun_logged = false;
    break;
  default:
    break;
  }
}

static void on_data(chip_t *c, uint8_t d)
{
  int n = c->nparam++;
  if (n < (int)sizeof(c->params)) c->params[n] = d;

  switch (c->cmd) {
  case 0x10:   // deep sleep; only a hardware reset brings it back
    if (d & 0x03) {
      c->asleep = true;
      if (c->debug) printf("ssd1680: deep sleep\n");
    }
    break;
  case 0x11:
    c->data_entry = d & 0x07;
    break;
  case 0x22:
    c->ctrl2 = d;
    break;
  case 0x24:
    ram_write(c, c->bw, d);
    break;
  case 0x26:
    ram_write(c, c->red, d);
    break;
  case 0x44:
    if (n == 0) c->x_start = c->x_ac = d & 0x3F;
    if (n == 1) c->x_end = d & 0x3F;
    break;
  case 0x45:
    if (n == 1) c->y_start = c->y_ac = c->params[0] | ((d & 0x01) << 8);
    if (n == 3) c->y_end = c->params[2] | ((d & 0x01) << 8);
    break;
  case 0x4E:
    if (n == 0) c->x_ac = d & 0x3F;
    break;
  case 0x4F:
    if (n == 1) c->y_ac = c->params[0] | ((d & 0x01) << 8);
    break;
  default:     // 0x01, 0x0C, 0x18, 0x21, 0x3C and the rest: accepted, not modelled
    break;
  }
}

static void on_spi_done(void *user_data, uint8_t *buffer, uint32_t count)
{
  chip_t *c = user_data;
  if (count > 0) {
    uint8_t b = buffer[0];
    bool is_data = pin_read(c->dc) == HIGH;
    if (c->asleep) {
      printf("ssd1680: 0x%02X sent during deep sleep and ignored; the panel "
             "needs a hardware reset first\n", b);
    } else {
      if (c->busy_on)
        printf("ssd1680: 0x%02X sent while BUSY was high; a real panel may "
               "drop it\n", b);
      if (is_data) on_data(c, b);
      else on_command(c, b);
    }
  }
  if (pin_read(c->cs) == LOW) spi_start(c->spi, &c->spi_byte, 1);
}

static void on_cs(void *user_data, pin_t pin, uint32_t value)
{
  chip_t *c = user_data;
  if (value == LOW) spi_start(c->spi, &c->spi_byte, 1);
  else spi_stop(c->spi);
}

static void on_rst(void *user_data, pin_t pin, uint32_t value)
{
  chip_t *c = user_data;
  if (value == LOW) {
    c->asleep = false;
    c->pending_display = false;
    timer_stop(c->busy_timer);
    reset_registers(c);
    set_busy(c, false, 0);
  } else {
    set_busy(c, true, 1000);   // a short BUSY pulse coming out of reset
  }
}

void chip_init(void)
{
  chip_t *c = calloc(1, sizeof(chip_t));

  c->cs = pin_init("CS", INPUT_PULLUP);
  c->dc = pin_init("DC", INPUT);
  c->rst = pin_init("RST", INPUT_PULLUP);
  c->busy = pin_init("BUSY", OUTPUT_LOW);

  c->full_ms = attr_read(attr_init("fullUpdateMs", 2000));
  c->partial_ms = attr_read(attr_init("partialUpdateMs", 400));
  c->debug = attr_read(attr_init("debug", 0)) != 0;
  c->dump = attr_read(attr_init("dumpFrames", 0)) != 0;

  memset(c->bw, 0xFF, sizeof(c->bw));
  memset(c->red, 0xFF, sizeof(c->red));
  reset_registers(c);

  const timer_config_t timer = { .user_data = c, .callback = busy_done };
  c->busy_timer = timer_init(&timer);

  const spi_config_t spi = {
    .sck = pin_init("SCK", INPUT),
    .mosi = pin_init("SDI", INPUT),
    .miso = NO_PIN,
    .mode = 0,
    .done = on_spi_done,
    .user_data = c,
  };
  c->spi = spi_init(&spi);

  const pin_watch_config_t cs_watch = { .user_data = c, .edge = BOTH, .pin_change = on_cs };
  pin_watch(c->cs, &cs_watch);
  const pin_watch_config_t rst_watch = { .user_data = c, .edge = BOTH, .pin_change = on_rst };
  pin_watch(c->rst, &rst_watch);

  c->fb = framebuffer_init(&c->fb_w, &c->fb_h);
  render(c);

  printf("ssd1680: ready, %ux%u\n", (unsigned)c->fb_w, (unsigned)c->fb_h);
}
