# The MIP variant: Sharp LS032B7DD02

This is the **`mip` branch**, started 30 September 2026 from `main` at
`1f6fb35`. `main` stays the e-paper design (GDEY0266T90) and keeps moving on
its own; this branch swaps the panel for Sharp's LS032B7DD02 memory-in-pixel
LCD. Fixes that apply to both, such as a footprint or a tool, go on `main`
first and are merged into this branch, never the other way round.

Barnaby's reasons: the LS032's active area is wider than the 2.66" e-paper's,
closer to the original HP-42S display, and he accepts a taller board and case
to get it.

## The panel, from Sharp's datasheet

Confirmed against Sharp's LS032B7DD02 specification (Barnaby's copy,
30 September 2026). Page numbers are the PDF's.

| | value | page |
|---|---|---|
| Type | reflective memory-in-pixel LCD, 1 bit, normally white | 15 |
| Resolution | 336 (H) × 536 (V), native portrait, 0.127 mm pitch | 15 |
| Active area | 42.672 × 68.072 mm | 15 |
| Glass outline | 47.02 × 76.00 × 0.705 mm, 5.5 g max | 60 |
| Active-area centre | 39.784 mm from the FPC-end glass edge | 60 |
| Reflectivity | 14 % typical, 10 % minimum (e-paper is about 35-40 %) | 45 |
| Viewing angle | 60° typical, all four directions, at CR ≥ 2 | 45 |
| Interface | SCLK, SI, SCS (active **high**), DISP, EXTCOMIN, EXTMODE | 16 |
| VDD, VDDA | **4.8-5.5 V**, 5.0 typical, VDD ≥ VDDA | 25 |
| Logic inputs | VIH 2.7 V to VDD, so 3.3 V logic drives it directly | 25 |
| EXTCOMIN | 1-10 Hz, edges under 50 ns; EXTMODE tied to VDD | 25 |
| Power | hold 30 µW typical (330 max); 1 Hz update 250 µW typical | 26 |
| Sequencing | on: VDD before or with VDDA; off: VDDA first; no floating inputs | 26 |

FPC, pages 51-52 and 60: 10 pins at 0.5 mm, 9.47 mm wide, leaving the
centre of a **short** (47.02 mm) edge, tail 13.63 ± 0.5 mm beyond the glass
with a 3.5 mm stiffener. It bends to the rear only, at most three bends,
between 0.8 and 6.0 mm from the glass edge, inner radius 0.45 mm minimum.

| pin | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| | SCLK | SI | SCS | EXTCOMIN | DISP | VDDA | VDD | EXTMODE | VSS | VSSA |

Sharp's recommended connectors are all stocked at JLC: **Hirose
FH34SRJ-10S-0.5SH (C324723)**, the choice here, dual contact and 53k in
stock; Molex 503480-1000 (C127355); Panasonic AYF531035 (C425133).

## Width: the case wants to be 82 mm

In landscape the glass is 76.00 mm wide and the FPC leaves one end of it.
The fold beyond the glass is the 0.8 mm straight run, about 0.95 mm of bend
and the 0.3 mm FPC, so about 2.05 mm. Fold apex to far glass edge is
**78.1-78.25 mm**. The 80 mm case has 77.6 mm inside, which does not fit;
**82 mm** does, with room for the 1.2 mm wall beside the fold that Barnaby
already accepted.

The board stays 76 mm wide. **The glass is flush with it, X 0.00 to 76.00**
(Barnaby, 1 October 2026), which gives the most viewing area; the case masks
the right-hand side so the window matches visually. The tail wraps the left
edge to J2 on the back. Its half turn is centred 0.8 mm beyond the glass, so
its outside stands at **X -2.16**, past the board edge: the case has a
special cut-out for it.

Visible region: polarisers 73.2 x 46.02 at X 2.30 to 75.50, Y 12.50 to
58.52; active area 68.072 x 42.672 at **X 5.748 to 73.820, Y 14.174 to
56.846**. It is centred on the glass's height and 39.784 from the tail end.

Stack above the board's front face: 0.20 mm contact adhesive film (tesa
4965 is 0.205), then the 0.705 mm panel, so the front face is at
**0.905 mm**. The flex is bonded on top of the TFT glass's 2.3 mm ledge.
`hardware/LS032B7DD02_on_board.step` has all of it in the board's frame.

## Height: board 155 mm, case 159 mm

The glass is 47.02 mm tall against the e-paper's 36.30, 10.72 mm more.
Everything from the display's lower edge down moves by **11.0 mm** as one
block: keypad, domes, mounting holes F and G, the cell and the bottom
chamfers. **Board 144 → 155 mm; case 148 → 159 mm.** The keypad geometry is
untouched.

## What changes on the board

Done on 30 September 2026, in `elec/src/display.ato` and `parts.ato`:

1. **The e-paper booster is gone.** Q1, L2, D1-D3 and the ±20 V capacitors.
2. **5 V from a TPS610997YFFR** (C2072359), off SYS: 2.2 µH Murata
   DFE201612P (C79317), 10 µF in, 2 × 10 µF out (C19702, Basic), as TI's
   SLVSD88M asks. VDD and VDDA are one net: Sharp allows them to rise and
   fall together (spec page 23), so there is no sequencing circuit. EN has a
   1 M pulldown, so the panel is off while the ESP32 is in reset. The boost
   disconnects its output when off.
3. **J2 is the Hirose FH34SRJ-10S** (C324723), land from the FH34 catalogue.
   Connector pin n is panel pin n; the reasoning is in `parts.ato`
   (MIPConnector). J2 sits on the back at (7.05, 35.51), 90°, mouth at
   X 3.35, which leaves the tail 2 mm of slack like the e-paper's.
4. **EXTCOMIN from an RV-8263-C7** (C5137460, the C7 package so its land is
   Micro Crystal's own drawing) on the gauge's I2C bus. CLKOUT is EXTCOMIN;
   CLKOE comes from IO36 with a 1 M pulldown, because the RTC wakes up
   giving 32.768 kHz and CLKOE low holds CLKOUT low until firmware has set
   1 Hz. INT is not connected.
5. **GPIOs**: the e-paper's six, reused. IO33 SCS, IO34 DISP, IO35 5 V
   enable, IO36 CLKOE, IO37 SCLK, IO38 SI. DISP, the enable and CLKOE are
   held through deep sleep with `gpio_hold_en`, because the picture stays up
   while the calculator is off.
6. **The board is 155 mm.** `tools/variant.py` moves everything below
   Y 48.3 down 11.0 mm; `tools/mip_drop_board.py` did it once to the board
   file, and the FPC notch is now Y 29.01..42.01. The battery bay grows with
   it, to Y 13..69 on the back, so a 56 mm cell would fit where the 45 mm one
   is.

Designators moved with the change (atopile numbers in source order):
D4, D5, D6 are now D1, D2, D3; Q2 is Q1; U6 (frontlight) is U8; C20, C21,
C22 are C15, C16, C17. The placement table on this branch uses the new names.

## The frontlight: six LEDs

A memory LCD is reflective, like e-paper, so it keeps the edge-lit guide in
`docs/front-face.md` and the Dialight 599-2Q01-147F LEDs on the sliver.

The lit area is 68 × 42.7 mm against 60 × 30.7, 1.57 times larger. The
Dialight part's rated maximum is 20 mA, which the e-paper design already
runs at, so the extra light has to come from more LEDs, not more current:
**six at 20 mA**, about 11.3 mm apart. The string is about 20.4 V, well
inside the TPS61165's 37 V open-LED limit, and the set resistor stays 10 Ω.
(An earlier draft of this note said five at 24 mA; that would overdrive the
LED.)

The LS032 reflects about 14 % against e-paper's 35-40 %, so under the same
light it looks darker, and the bench may call for seven or eight. The sliver
is its own board, so that costs nothing on the main board.

## Battery

`tools/battery_life.py` with the panel's figures
(`--set panel_sleep_uA=16 --set partial_s=0.03 --set full_s=0.03 --set
panel_refresh_mA=1`): the 16 µA is the panel holding its image, the 5 V
boost and the RTC together. Unlike e-paper, the MIP needs power to keep its
picture, so "off" costs twice as much, while each keystroke costs half.

| profile | e-paper | MIP |
|---|---|---|
| drawer | 30.0 months | 24.5 months |
| light | 26.7 | 23.3 |
| daily | 20.2 | 20.2 |
| heavy | 14.1 | 16.5 |
| exam day | 9.2 | 12.4 |

If the display is blanked when switched off (DISP low, 5 V off), the drawer
figure goes back to the e-paper's, at the cost of a blank screen when off.

## Firmware

A new panel driver replaces `epd.c`: the MIP line-write command over SPI, and
EXTCOMIN. It is much simpler and much faster. A full frame is 336 × 536 / 8 =
22.5 KB and writes in tens of milliseconds, against the e-paper's 0.4 s
partial refresh, so the per-keystroke delay goes away. The panel's lines run
along its 42.67 mm side, so in landscape the framebuffer is written rotated.

The HP-42S screen is 131 × 16 pixels. 536 / 131 is 4.09, so **Plus42 scales
by exactly 4 across the width**: 524 pixels, leaving 6 either side. That
leaves plenty of height for Plus42's taller layouts.

## Order of work

1. ~~Get the datasheet and fill in the table above.~~ Done 30 September.
2. ~~Rewrite `display.ato` without the booster, with the FH34SRJ, the
   TPS610997 and the RV-8263; rebuild.~~ Done. **Re-import in KiCad is
   Barnaby's step.**
3. ~~Extend the outline to 155 mm, move the keypad block down 11 mm,
   lengthen the frontlight sliver to six LEDs.~~ Done. Then, after the
   re-import: place the new parts, reroute with the same tools.
4. Firmware: the MIP driver and the ×4 Plus42 blitter, in `sim/host` first.

## Shelved 1 October, resumed 2 October 2026

Barnaby tried the Displaytech 64128M (branch `dt`) and then a 2.9" frontlit
e-paper (GDEY029T94-FL03, which needed an 83 mm case and left the image 3 mm
off centre), and came back to this one.

On resuming, main was merged in (L1 to XFL4020-222MEB; routers hold copper
0.25 mm off bare holes) and the board was stripped and routed from scratch
with the glass flush left and J2 at X 7.05: 96 nets, 0 failed, audit clean,
`check_ends`, `check_pour`, `check_placement` clean, every NPTH cleared by
0.25 mm. The via that stopped the last attempt is gone.
