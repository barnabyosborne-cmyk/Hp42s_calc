# Displaytech 64128M COG (branch `dt`)

Started 1 October 2026, when the Sharp LS032B7DD02 work (`mip`) was shelved.
Barnaby's choices: reflective panel, **no backlight and no frontlight** (like
the original HP-42S), hand-solder the 28 clip pins after JLC assembly, and
shrink the board where possible.

## The part

64128M COG series spec v1.0, page 7 (drawing T653 rev D):

| | |
|---|---|
| Glass | 75.0 x 50.0 (±0.2), 2.95 max thick. 43 mm top glass plus a 7 mm ledge carrying the ST7565R on the pin side |
| View area | 70.0 x 40.0, 2.5 from each short edge, 1.5 from the edge away from the pins |
| Active area | 66.52 x 33.24, 128 x 64 dots at 0.52 mm |
| Pins | 28 clip pins at 1.27, row 34.29 long, centred on the 75 mm edge (pin 28 at 20.35 from the left). Legs 0.4 x 0.4, about 0.25 outside the ledge edge, **8.0 long behind the glass**. Page 3's "8.50 mm" module thickness includes them |
| Pin 1 | on the right, seen from the front with the pins at the bottom |
| Seal bump | 10 x 1.0 max, on the pin-28 short edge, 16.5 from the edge away from the pins |
| Drive | 3.0 V, ST7565R, 4-wire serial, 1/65 duty, 1/9 bias, internal x4 booster to about 9 V |

The pins stick out about 6 mm behind the board (8.0 less 0.2 adhesive and
1.6 board), so trim them after soldering.

## Mounting

**Upright** (pins at the bottom), the standard 6 o'clock part. Glass at board
Y 7.5..57.5, X 0.5..75.5, so the image is centred and the seal bump stands
0.5 mm past the left board edge. The pin row is at Y 57.75 and the first dome
sites start 2 mm under its pads. Everything below the e-paper glass's old
edge (Y 48.3) moves 3.0 (`tools/variant.py`), so the board is **76 x 147**.

Shortened on 1 October at Barnaby's suggestion (it was 76 x 150):
- Mounting holes A and B moved up to (10, 3.5) and (66, 3.5) with 4.5 mm
  rings, B between the two side buttons and A mirroring it.
- The glass's top edge is set by J1's shell-leg pads, which reach Y 6.63 on
  the front; 7.5 clears them.
- U1, R1, R2, C1, Q1 and R18 moved out of the band under J1 into the top
  band either side of it, so the cell bay starts at Y 8.5: **47 x 55 x 6**
  at Y 8.75..55.75, ending above the pins' back-side joints.

Turned 180° (pins at the top) was the first plan, but the pin row would hit
the USB ESD array and its resistors on the back (Y 8.9..10.2), which pushes
the glass down and the board to 152, and needs the 12 o'clock part.
Picture: `hp42s-display-options/displaytech-orientation.png` in the project
files.

The footprint (`Displaytech_64128M_1x28_P1.27mm`) is drawn for the panel
turned 180°, glass below the pins; `place_board.py` puts it in at 180.

## Board changes from `mip`

- `tools/dt_lift_board.py`: from mip, everything below Y 59.3 up 5 mm,
  outline to 150, the FPC notch closed; then `--from 6` and `--from 2` for
  the shortening, ending at 147.
- The faceplate bond pad (now TP1) moved from under the glass into the
  keypad (Barnaby's choice): board (14.75, 106.855) on the front, in the gap
  between the left column and the numeric block, between rows 5 and 6. Its
  ground via is in `route_power.py`.
- The ST7565R's ten 1 uF caps and the /RES pull-up sit in a row on the back
  under the pin row (board Y 61.42), in pin order.
- Removed: the MIP 5 V boost, the frontlight boost and their power routes.
- Designators after the re-import: `placement-ids.json` is re-recorded
  against the dt netlist (old U7 is U6, C14 is C20, R24 is R21, TP3..TP11
  are TP1..TP9).

## Still to do

Done: netlist imported, board placed and fully rerouted at 76 x 147
(`fd24ffc`); `check_ends`, `check_pour`, `check_placement` clean;
`mech_models.py` draws the 64128M (anchor TP1), and
`hardware/64128M_on_board.step` is the panel alone in the board frame.

1. Barnaby: KiCad DRC on `fd24ffc`. The 12 hole_clearance items inside the
   J1, SW39 and SW40 vendor footprints are the same as on `main`.
2. Regenerate the JLC BOM (`tools/jlc_bom.py`) for this branch.
3. Firmware: ST7565R driver and the Plus42 blitter at 1x, in `sim/host`
   first.
