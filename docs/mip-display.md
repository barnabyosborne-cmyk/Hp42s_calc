# The MIP variant: Sharp LS032B7DD02

This is the **`mip` branch**, started 30 September 2026 from `main` at
`1f6fb35`. `main` stays the e-paper design (GDEY0266T90) and keeps moving on
its own; this branch swaps the panel for Sharp's LS032B7DD02 memory-in-pixel
LCD. Fixes that apply to both, such as a footprint or a tool, go on `main`
first and are merged into this branch, never the other way round.

Barnaby's reasons: the LS032's active area is wider than the 2.66" e-paper's,
closer to the original HP-42S display, and he accepts a taller board and case
to get it.

## What is known, and what is waiting on the datasheet

The datasheet could not be fetched from this environment (Sharp's site and
the distributors are outside its network policy), so everything below marked
**to confirm** is from memory and must be checked against it before any
footprint or outline is drawn.

| | value | status |
|---|---|---|
| Type | reflective memory-in-pixel LCD, monochrome, 1 bit per pixel | known |
| Resolution | 336 × 536 | to confirm |
| Interface | 3-wire SPI (SCLK, SI, SCS), plus DISP and EXTCOMIN | to confirm |
| Supply | VDD / VDDA, 3 V or 5 V class | **to confirm, it decides the power tree** |
| Glass outline and active area | roughly 67 × 42 mm active, landscape | **to confirm** |
| FPC | pitch, pin count, contact side, tail length | **to confirm** |

## What changes on the board

1. **The e-paper booster goes.** Q1, L2, D1–D3 and the ±20 V capacitors exist
   only to make the SSD1680's gate rails. A memory LCD needs none of that.
2. **J2 becomes the LS032's FPC connector**, with its own fold and slack
   worked out the way `docs/display-mounting.md` did for the e-paper tail.
3. **EXTCOMIN.** The panel needs its common electrode toggled, typically at
   about 1 Hz while static. That is one GPIO driven by the ESP32's RTC or LEDC
   so it keeps running in light sleep. Its cost is a few microamps, which goes
   into the battery estimate.
4. **The board and case get taller.** How much is set by the glass outline;
   the keyboard, its 12 mm row pitch and everything below it move down as one
   block, so the keypad geometry is untouched.
5. **The frontlight grows** (below).

Everything else carries over: the ESP32-S3 module, the power chain, the
gauge, the keypad and its scan, USB-C and the top-edge parts.

## The frontlight: five LEDs

A memory LCD is reflective, like e-paper, so it still needs the edge-lit
guide in `docs/front-face.md`, and the same Dialight 599-2Q01-147F LEDs on a
sliver under the guide's edge.

The e-paper design uses four LEDs on a 15 mm pitch across a 60 mm edge. On a
guide about 67 mm wide, keeping the pitch at or under 15 mm needs **five**,
at about 13.5 mm. The lit area also grows by about half (roughly 67 × 42
against 60 × 31), so to keep the same brightness the string needs about half
as much light again: five LEDs at about 24 mA instead of 20, or six at 20 mA.
The power is the same either way, about 0.4 W while lit, so **five** is the
recommendation: one fewer part and a tighter pitch than today. Five in series
is about 17 V, well inside the TPS61165, whose open-LED protection is 37 V.
Its set resistor goes from 10 Ω to 8.2 Ω for 24 mA.

This gets confirmed once the active area is known. MIP panels also reflect
somewhat less light than e-paper, so the current may want trimming on the
bench.

## Firmware

A new panel driver replaces `epd.c`: the MIP line-write command over SPI, and
EXTCOMIN. It is much simpler and much faster. A full frame is 336 × 536 / 8 =
22.5 KB and writes in tens of milliseconds, against the e-paper's 0.4 s
partial refresh, so the per-keystroke delay goes away.

The HP-42S screen is 131 × 16 pixels. 536 / 131 is 4.09, so **Plus42 scales
by exactly 4 across the width**: 524 pixels, leaving 6 either side. That
leaves plenty of height for Plus42's taller layouts.

## Order of work

1. Get the datasheet and fill in the table above.
2. Draw the panel's outline and FPC, and work out the fold and the new board
   height.
3. Rewrite `display.ato` without the booster, re-home J2, rebuild, re-import.
4. Re-place the display area, move the keypad block down, lengthen the
   frontlight sliver to five LEDs, reroute with the same tools.
5. Firmware: the MIP driver and the ×4 Plus42 blitter, in `sim/host` first.
