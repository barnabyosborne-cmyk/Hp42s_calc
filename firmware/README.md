# Firmware — porting Plus42

The **board layer is written and building**: pin map, SSD1680 panel driver,
6 x 7 keypad scan with deep-sleep wake, and a bring-up app that draws a test
pattern and echoes keys. The **Plus42 core is not here yet** — codeberg.org is
blocked by this session's network policy and there is no GitHub mirror, so the
source has to come from Barnaby.

## What is here

| File | What it does |
|---|---|
| `main/board.h` | Every pin number, in one place. The only file that changes for a different board. |
| `main/epd.c` | SSD1680 driver for the GDEY0266T90: init, full update, partial update, deep sleep. Landscape 296 x 152. |
| `main/keypad.c` | 6 x 7 diodeless scan, debounce, and `ext1` wake on any column going low. |
| `main/main.c` | Bring-up app. Draws a frame, a corner block and a 37-bar chart, then echoes key presses with partial updates and deep-sleeps after 10 s idle. |

## Building

```
. $IDF_PATH/export.sh
idf.py set-target esp32s3
idf.py build
idf.py -p /dev/ttyACM0 flash monitor
```

Built clean against ESP-IDF v5.5 on 2026-09-19: 245 KB, 77 % of the app
partition free.

For running any of this on a Seeed XIAO ESP32-S3 instead of the real board,
see `docs/breadboard.md` — the pin map in `board.h` does **not** transfer,
because the XIAO's octal PSRAM eats GPIO33-37.

Plus42 is Thomas Okken's extension of Free42: algebraic expressions, units,
directories, TVM, function plotting. Same GPLv2, same author, same repo
shape — a portable `common/` core plus a thin per-platform shell. Porting
means writing a new shell, not touching the core.

Source: <https://codeberg.org/thomasokken/plus42desktop>. The GTK shell is the
closest reference for a bare-metal port; the iOS and Android shells carry
platform baggage that does not help.

## The shell API

About 22 functions the platform has to supply. The ones that carry real work:

- `shell_blitter` — the whole display. **Must not assume a fixed size.**
  Plus42 resizes the display at runtime (`ROW±`, `COL±`, `SETDS`, `WIDTH`,
  `HEIGHT` in the DISP menu), 2–99 rows and 22–999 columns. Cells are 6 × 8 px.
  It also scales **anisotropically**: 2× across, 3× down, so one logical pixel
  becomes a 2 × 3 block of panel pixels. That is not something to tidy up later
  — it is what makes the characters the size of a real 42S's, because the
  original's pixels were 0.42 × 0.65 mm and ours are square. Two constants
  stand between 24 × 6 and 24 × 9. See `../docs/character-size.md`.
- `shell_annunciators` — the status strip.
- `shell_request_timeout3`, `shell_delay`, `shell_milliseconds` — timing.
- `shell_read_saved_state` / `shell_write_saved_state` — state to flash.
- `shell_get_mem`, `shell_low_battery`, `shell_powerdown`.
- `shell_print`, `shell_write`, `shell_read` — printing and file transfer.
- `shell_get_acceleration` / `_location` / `_heading` — stub these out.

## Power state machine

Three states, and two rules that matter more than the rest:

| State | Trigger | Cell current |
|---|---|---|
| Active | key or timer | ~24 mA |
| Idle | 0.5 s quiet, light sleep (SRAM retained) | ~265 µA |
| Off | 5 min quiet, deep sleep, state flushed to flash | ~25 µA |

1. **Never deep-sleep with a core timeout pending.** `core_keytimeout1` fires
   at 0.25 s and `core_keytimeout2` 2 s later; losing them loses keystrokes.
2. **Light-sleep through the panel refresh, waking on BUSY.** Spinning through
   a 400 ms partial update instead costs about 5× the energy per keystroke —
   0.70 µAh becomes 3.8 µAh. This one decision is the difference between
   15 months and 3.

A naive always-active port gets about 40 hours.
