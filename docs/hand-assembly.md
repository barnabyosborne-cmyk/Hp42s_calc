# Building the board by hand (`ls027-hand-assembly` branch)

On 25 October 2026 Barnaby decided to skip JLC's assembly service: bare
boards and a stencil from JLC, parts from LCSC, placed with tweezers and
reflowed at home. This branch, cut from `ls027` at `ecf5607`, is the 2.7"
board revised for that. `ls027` itself is unchanged.

## What changed

**Every resistor and capacitor is 0805.** There were 33 0402s and 9 0603s.
0805 is the smallest size that is easy to pick up, turn and rework without a
microscope, and that is where the line was drawn. The inductors, the
transistors and the ICs were already larger, or cannot change (below).

| Part | Was | Now | Why |
|---|---|---|---|
| All R, all C | 0402 / 0603 | 0805 | tweezers |
| C1, C7, C10 | 1 uF in two parts (25 V 0603, 10 V 0402) | one part, 1 uF 50 V X7R | one BOM line |
| C2, C11 | 10 uF in two parts (0805, 0603) | one part, 10 uF 25 V X5R | one BOM line |
| C12, C13 | 10 uF 10 V 0603 | 22 uF 25 V 0805, the part C3/C4/C8 already use | TI asks for 20 uF on the 5 V boost's output; 2 x 10 uF 0603 at 5 V of bias was nearer 8 |
| R8 + R22 | 15k + 1.2k in series | one 16.2k 1% (R8); R22 deleted | the pair only existed because 16.2k is not a JLC Basic part |
| R11, R12 | 4.7k | 5.1k, the CC pull-downs' part | one BOM line; rise time at 400 kHz still inside spec |
| Every resistor | 1% and 5% | 1% | same price, one part per value |

The BOM went from 44 lines and 66 parts to **39 lines and 65 parts**. The
passives alone went from 22 lines to 17.

## Files to order from

`fab/ls027-hand/` (the old `fab/ls027/` is left as it was, for the
JLC-assembled version):

- `hp42s-ls027-hand-gerbers.zip`: copper (4 layers), mask, silk, paste,
  outline and drill, exported by KiCad 10's own `kicad-cli` from the board
  after a zone refill. Upload it for the bare board and ask for a stencil for
  the **bottom** side only.
- `hp42s-ls027-hand-bom.csv`: every part with its LCSC number, for LCSC's
  BOM tool (multiply the quantities by the number of boards, and add spares
  of the small passives; they are sold by the strip anyway).
- `hp42s-ls027-hand-cpl.csv`: part positions, useful as a placement map.

Exporting from KiCad yourself (docs/jlc-order.md) gives the same files and is
worth doing once to check them against these.

R23 and R24 now have their designators pinned in `hp42s.ato`: deleting R22
would otherwise have renumbered them.

### On the board

The 0805s went back onto the same spots where they fit. Twenty moved to
make room, most by one or two grid steps (0.635 or 1.27 mm): R3, R4, R5,
R8, R10, R13, R14, R15, R16, R20, R21, R24, C5, C6, C7, C8, C9, C19 and
Q1, and R6 by 3.2 mm. R3/R4/R5 sit one step further from the charger U2 so
the 1.7 mm channel between U2's pins and the resistor pads is as wide as it
was with 0402s; the CFG resistors R9/R10/R8 are on a 3.175 mm pitch so each
ground pad keeps room for its via; the module's EN/3V3 stack (R13, C7, C8,
C9) moved up so C9 stays out of the antenna keepout. `check_placement.py` now asks for 0.5 mm between courtyards
rather than 1.0 (about 1 mm between part bodies, room for tweezer tips).
In `route_power.py`, VBUS down the charger moved (x 38.42 to 40.40) and past
R2 (y 7.75 to 7.70), SYS's loop round the CFG resistors moved (x 26.8 to
26.4), the 3V3 ties between C8, C9 and the module followed those parts, and
SW40's left mounting pad got a ground via of its own (the pour stopped
reaching it). Then the whole board was
rerouted with the repo's own tools and checked with KiCad 10's DRC.

## What could not get bigger

These stay fine-pitch because no larger package of the same part exists,
and a different part would mean a redesign:

| Ref | Part | Package | Pitch |
|---|---|---|---|
| U2 | BQ25185 charger | WSON-10 2 x 2 | **0.4 mm** |
| U6 | TPS610997 5 V boost | DSBGA-6 (6 balls) | **0.4 mm** |
| U3 | TPS63900 buck-boost | WSON-10 2.5 x 2.5 | 0.5 mm |
| U4 | MAX17048 gauge | TDFN-8 2 x 2 | 0.5 mm |
| U9 | LSM6DSV16X IMU | LGA-14 3 x 2.5 | 0.5 mm |
| U10 | LIS2MDL magnetometer | LGA-12 2 x 2 | 0.5 mm |
| U7 | RV-8263-C7 RTC | 3.2 x 1.5 | 4 pads |
| U1 | TPD4E05U06 USB ESD | USON-10 2.5 x 1 | 0.5 mm |
| J2 | FH34SRJ-10S panel FPC | 10 pins | 0.5 mm |

All of these reflow well from a stencil: surface tension pulls a
leadless part onto its pads if it is put down roughly right. The two
0.4 mm parts are the ones to take care over. Neither can be inspected by eye
afterwards (the DSBGA's joints are underneath it), so the test is the
power-up sequence on the bench.

Two that could change, not done here:

- **U1** could be an SRV05-4 in SOT-23-6 (4 channels, 3 pF, LCSC C85364):
  0.95 mm pitch instead of 0.5. It needs a new spot in the crowded strip
  under the USB socket and a reroute of the USB pair. Worth it only if
  0.5 mm turns out to be a problem, because U3, U4, U9 and U10 are 0.5 mm
  anyway.
- **U6** could become a TPS61222 (SC-70-6, 0.65 mm pitch, fixed 5 V) with
  its own inductor. That is a circuit change, not a footprint swap.

### Stencil and paste

Order the stencil for the **bottom** side only: every reflowed part is on
the back, the front only has the dome pads. Ask JLC for a 0.10 mm (not
0.12) stencil, electropolished, because of the two 0.4 mm parts; 0805s are
happy with 0.10. Use a type 4 or type 5 paste (finer powder) for the same
reason.

## Two layers instead of four?

**Possible, not recommended.** All the tracks are already on the two outer
layers; the inner two carry no tracks. In1.Cu is a solid ground plane and
In2.Cu is mostly ground with a 3.3 V plane. So a 2-layer board means
losing both planes, and on this board that hurts more than usual:

- **No layer is free to be a ground plane.** The front is the keypad: 38
  dome pads and the matrix between them. The back carries every part and
  about 850 track segments, so its ground pour is chopped into pieces. Today
  the 380 vias drop straight into In1.Cu and every return current has an
  unbroken plane under it; on 2 layers they would have to be joined by
  tracks.
- **3.3 V has no plane.** It feeds 19 pads through 26 vias into In2.Cu. Each
  would need a track instead, through a board that is already routed tight.
- **The ESP32 module** wants unbroken ground under it and round its ground
  pads for the radio; Espressif's 2-layer layouts give the whole area under
  the module to ground, which here is where the matrix and other tracks run.
- **The two switchers** (TPS63900 and the 5 V boost) and the charger keep
  their loops short on the back, which survives 2 layers, but their return
  currents and the panel's SPI clock running the length of the board would
  no longer have a plane next to them.
- **The panel FPC and the front-light ZIF** are single-sided connectors on
  the back and do not care about the layer count; nor does USB at 12 Mbit/s.

It would mean ripping up and rerouting the whole board, by hand or with the
tools reworked for it, then living with weaker ground. **Rough cost
difference** (JLC's usual pricing, not a quote): for 5 boards of 76 x 142 mm,
1.6 mm, the 4-layer board is in the region of $20 to $40 more than 2-layer.
The stencil and shipping are the same either way. Get JLC's own quote for
both before deciding; this could not be checked from here.

## Not verified here

- The 0805 swap was checked by `check_placement.py`, the routers' own
  clearance audits and KiCad 10's DRC (results in the commit message).
  It has not been looked at in KiCad's GUI or 3D viewer.
- LCSC stock was read from JLC's parts search on 25 October 2026. Stock moves.
- The TPS610997's largest allowed output capacitance was not re-read from
  TI's datasheet (www.ti.com is not reachable from here). 2 x 22 uF is well
  inside what boost converters of this kind usually accept, but check the
  output capacitor section of the datasheet before ordering.
- In KiCad no netlist re-import is needed: the 0805 footprints were written
  into the board from KiCad's own libraries with the netlist's ids. If you
  do re-import, link by unique ids as always.
