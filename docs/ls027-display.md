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
| Cell bay | X 5..55, Y 12.5..50.5: a **6 x 38 x 50 mm** cell (about 1250 mAh) |

The 6 x 45 x 55 mm cell of the other boards clashes with the panel FPC fold,
so this board takes the smaller cell. `tools/battery_life.py` now uses
1250 mAh: about 16 months of daily use instead of 20.

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

## Display connector J2

FH34SRJ-10S on the back at (38.0, 59.9), mouth facing up the board, contact 1
at the +X end. **LS027 pin 1 is not yet checked against a real panel.** Look
at your panel's FPC: if pin 1 is on the left as you look at the back of the
board, the pin map in `elec/src/hp42s.ato` must be mirrored before ordering.

## Front light (fit or leave off)

The Azumo LED flex's contacts face away from the board, so it is wired to J3,
two 1.4 mm pads on the back at (69.85, 76.74), beside the flex end.

    v5 (5.0 V) -> R23 100R -> J3.1 (+) LED J3.2 (-) -> Q2 Si1308EDL -> gnd
    Q2 gate = IO46, R24 100k pull-down (light off at reset and in sleep)

Hand calculation: Vf 3.0 V typical, so (5.0 - 3.0) / 100 = 20 mA; over Vf
2.8..3.2 V it is 18..22 mA, under the 25 mA absolute maximum. R23 dissipates
40 mW (0603 rated 100 mW). Q2's on-resistance at 3.3 V gate drive is a few
hundred milliohms, a few mV. From the cell that is about 32 mA while lit.
PWM on IO46 dims it.

Without the front light, leave J3 empty; R23, Q2 and R24 can stay fitted.

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
