# The 2.7" board (`ls027` branch)

Sharp LS027B7DH01 memory-in-pixel panel (400 x 240), with or without an Azumo
FLP 11103-06 front light. Branched from `mip` (the 3.16" LS032 board) on
4 October 2026. `main` stays e-paper, `mip` stays 3.16".

## Size

| | |
|---|---|
| Board | 76 x 142 mm, 1.6 mm 4-layer, chamfers 2 mm top, 4 mm bottom |
| Case | 146 mm long (was 150 for the 3.16") |
| Glass | X 6.6..69.4, Y 7.5..50.32 (62.8 x 42.82), centred across |
| Cell bay | X 5.5..55.5, Y 10.5..50.5: a **6 x 40 x 50 mm** cell (604050, about 1300 mAh) |

The 6 x 45 x 55 mm cell of the other boards clashes with the panel FPC fold,
so this board takes a smaller cell. `tools/battery_life.py` uses 1300 mAh:
about 17 months of daily use instead of 20.

On 5 October 2026 the bay grew from 38 x 50 (Y 12.5) to 40 x 50 by moving
the top-band parts out of its way: the IR driver (Q1, R18, R19) up beside
D1, C1 right of J1, and U1, R1, R2 into one row just under J1 (Y 8.1..9.8),
which the cell could not use anyway since J1's body reaches Y 7.23. VBUS now
runs J1 to C1 along Y 7.75 and leaves C1 down x 45.58.

Everything below the glass moved up 4.2 mm from the mip board
(`tools/ls027_from_mip.py`, run once). `tools/variant.py` holds the geometry:
`DROP = -2.0` against the e-paper tables.

## Holes in the board

| Cut-out | X | Y | For |
|---|---|---|---|
| Light coupler | 59.85..67.25 | 7.75..46.45 | the Azumo coupler sits behind the glass |
| FPC slot | 32.75..43.25 | 51.2..52.9 | the panel FPC folds through to J2 on the back |

Each has a 0.5 mm copper keepout (`tools/mounting.py`). The LED flex lies flat
on the back from the coupler down to Y 79 (strip X 62.8..66.6 kept clear of
parts).

## 3D model

`tools/mech_models.py` builds the panel from Azumo's own STEP for the
FLP 11103-06 on the LS027B7DH01 (`elec/footprints/vendor-3d/`), turned into
the board's frame: glass, light guide, film carrier and roll, the coupler
down through its cut-out and the LED flex along the back. The flat panel
FPC is cut at Y 50.92 and drawn folded through the slot into J2. The cell is
a 6 x 40 x 50 box. Both hang off TP1; `hardware/LS027B7DH01_on_board.step`
is the same panel in the board's own frame for the case model.

## Display connector J2

FH34SRJ-10S on the back at (38.0, 59.9), mouth facing up the board, contact 1
at the +X end. **LS027 pin 1 is not yet checked against a real panel.** Look
at your panel's FPC: if pin 1 is on the left as you look at the back of the
board, the pin map in `elec/src/hp42s.ato` must be mirrored before ordering.

## Front light (fit or leave off)

The Azumo LED flex ends in a standard 1.0 mm ZIF tail: two contacts 0.8 wide
at 1.0 pitch on its last 3.32 mm, stiffened there to 0.30 mm, 2.49 wide
(Azumo drawing detail A; thickness from Azumo's STEP). Lying along the back
its contacts face away from the board, so J3 is a top-contact connector:
GUOCONN 1.0K-LS-2PWB-TW (LCSC C53145530), slide lock, 2.0 high, on the back
at (64.725, 76.7), mouth up the board at Y 74.5. The flex tip lands at
Y 78.09, 3.6 mm in. The slot is made for a 3.0 mm tail, so the 2.49 mm one
has 0.3 mm of side play; the 0.8 mm fingers still land. + is the contact
nearer the short glass edge the flex leaves beside, which is board +X: pad 1.

    v5 (5.0 V) -> R23 100R -> J3.1 (+) LED J3.2 (-) -> Q2 Si1308EDL -> gnd
    Q2 gate = IO46, R24 100k pull-down (light off at reset and in sleep)

Hand calculation: Vf 3.0 V typical, so (5.0 - 3.0) / 100 = 20 mA; over Vf
2.8..3.2 V it is 18..22 mA, under the 25 mA absolute maximum. R23 dissipates
40 mW (0603 rated 100 mW). Q2's on-resistance at 3.3 V gate drive is a few
hundred milliohms, a few mV. From the cell that is about 32 mA while lit.
PWM on IO46 dims it.

Without the front light, leave J3 empty or fitted; R23, Q2 and R24 can stay.

## IMU

U9 LSM6DSV16X (accelerometer + gyro, 0x6A, INT1 on IO3) and U10 LIS2MDL
(magnetometer, 0x1E) on the I2C bus with the gauge (0x36) and RTC (0x51).
Both in the via corridor at X 15.24, left of the numeric block. IO46 went to
the front light, so the module has no spare GPIO left.

## Tools, in order

    ato build && python3 tools/check_netlist.py
    python3 tools/place_board.py
    python3 tools/fix_pads.py
    python3 tools/fix_footprint_zones.py
    python3 tools/check_placement.py
    python3 tools/route_power.py
    python3 tools/stitch_zones.py
    python3 tools/route_signals.py
    python3 tools/straighten.py        # after every route_signals.py run
    python3 tools/check_ends.py && python3 tools/check_pour.py

`tools/straighten.py` replaces the router's stepped diagonals with straight
0/45/90 runs or single 45-degree doglegs wherever the clearance audit allows.

`tools/inject_parts.py` added the parts new since the mip import (R23, R24,
C16..C19, U9, U10, J3, Q2) straight into the board file; Update PCB from
Netlist in KiCad, linking by unique ids, picks them up without renumbering.

## Status LED (D2)

XINGLIGHT XL-C4040SURSYGC (LCSC C7545693) since 5 October 2026: lens centre
2.0 mm above the board, in line with the USB mouth (1.28) and the buttons
(1.65) against the wall centreline at 1.7. Its red and yellow-green dice are
back to back, so firmware drives IO16 high and IO39 low for red, the other
way for green, both high impedance for off (was: common anode, active low).

## Fixing holes

Corners A-D (M2) join the two shells. Six more hold the board to the front
shell first, mirrored about X 38 (board coordinates):

| | X | Y | screw |
|---|---|---|---|
| E / F | 3.3 / 72.7 | 9.0 | M2, beside the glass's top corners |
| H / I | 13.0 / 63.0 | 66.0 | M1.6, the top rows' four-key gaps |
| J / K | 15.19 / 60.81 | 126.0 | M1.6, between the bottom rows (0.31 off each gap's centre, since those gaps do not mirror) |
| G | 38.25 | 78.0 | M1.6, keypad centre (existing) |

L2 and C11 moved above the H hole, the buzzer 3.2 mm right of K.
