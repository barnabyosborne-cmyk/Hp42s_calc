# Firmware — porting Plus42

The **board layer and the Plus42 core both build for the ESP32-S3.** Plus42
1.3.15 (Thomas Okken, GPLv2) is vendored in `components/plus42core/`, its
decimal arithmetic comes from Intel's BID library in `components/libbid/`, and
`main/shell.cc` is the platform layer that joins them to the board. What is
**not** done yet is the interesting half of the shell: the display blitter is
written but unverified, keys are not yet fed to the core, and nothing saves
state.

## What is here

| File | What it does |
|---|---|
| `main/board.h` | Every pin number, in one place. The only file that changes for a different board. |
| `main/epd.c` | SSD1680 driver for the GDEY0266T90: init, full update, partial update, deep sleep. Landscape 296 x 152. |
| `main/keypad.c` | 6 x 7 diodeless scan, debounce, and `ext1` wake on any column going low. |
| `main/shell.cc` | The 22 shell functions Plus42 asks the platform for. Real: display, milliseconds, random seed, log. Stubbed: beeper, printer, clock, power-down. |
| `main/main.c` | Bring-up app. Draws a test pattern, starts the core, echoes key presses, deep-sleeps after 10 s idle. |
| `components/plus42core/` | Plus42's portable core, unmodified, plus a CMakeLists. |
| `components/libbid/` | Intel's decimal library. Sources are laid out by `vendor/setup.sh`, not committed. |

## Building

```
cd firmware
./vendor/setup.sh
. $IDF_PATH/export.sh
idf.py set-target esp32s3
idf.py build
idf.py -p /dev/ttyACM0 flash monitor
```

Built against ESP-IDF v5.5 on 2026-09-19.

## What it costs

Measured, at `-Os`, with the whole core linked in:

| | Flash | RAM |
|---|---|---|
| Intel decimal library | 2.20 MB (2.06 MB of it lookup tables) | 34 KB |
| Plus42 core | 414 KB | 6.7 KB |
| Board layer | 3 KB | 11 KB |
| **Whole image** | **2.85 MB** | **113 KB of 334 KB** |

So the `-N8` module's 8 MB of flash is comfortable but not generous: the app
gets a 4 MB partition (`partitions.csv`), leaving 3 MB of FAT for programs and
state. 221 KB of RAM is left for Plus42's heap, which is where user programs,
variables and the stack live.

**The decimal tables are the whole story on flash.** Free42 and Plus42 also
build in a "binary" flavour that uses the hardware double instead, which would
drop about 2 MB. It would also stop the calculator rounding the way a real 42S
rounds, so it is not on the table unless flash becomes the binding constraint.

## Three things that had to be worked out

1. **Exceptions.** The core throws in three places (`core_equations.cc`,
   `core_display.cc`, `core_commands9.cc`), so `CONFIG_COMPILER_CXX_EXCEPTIONS`
   has to be on. That costs 39 KB of unwind tables.
2. **`fexcept_t`.** Intel's header defines it as `unsigned short` unless a
   `fenv.h` guard macro is already set, while newlib's is `unsigned long`; the
   two collide. Both components are compiled with `-include fenv.h` so
   newlib's definition wins everywhere.
3. **`shell_always_on()` and `shell_alpha_keyboard_enabled()`** look like
   shell functions but are not: the core defines the first itself off Android
   and iOS, and `shell.h` macro-defines the second. Supplying either is a
   link error.

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
