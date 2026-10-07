# Ordering the 2.7" board from JLC (`ls027` branch)

Five files go to JLC: a zip of Gerbers and drill files for the bare board,
and the BOM and placement (CPL) files for assembly. The BOM and CPL are in
`fab/ls027/` and are regenerated with

    python3 tools/jlc_bom.py fab/ls027/hp42s-ls027-bom-jlc.csv fab/ls027/hp42s-ls027-cpl-jlc.csv

(`ato build` first: parts added straight into the board file take their
instance path from `build/default.net`). The Gerbers have to come from KiCad,
because only KiCad fills the pours.

## 1. Gerbers (KiCad 10)

1. Open `elec/layout/default/default.kicad_pcb`. Press `B` (Fill All Zones),
   then run DRC once more: expect the 12 vendor hole-clearance items only.
2. **File > Fabrication Outputs > Gerbers (.gbr)...**
3. Output directory: `gerbers/`.
4. Under Include Layers tick: F.Cu, In1.Cu, In2.Cu, B.Cu, F.Silkscreen,
   B.Silkscreen, F.Mask, B.Mask, F.Paste, B.Paste, Edge.Cuts. Nothing else.
5. Under General Options tick **Check zone fills before plotting**.
6. Under Gerber Options tick **Use Protel filename extensions** and
   **Subtract soldermask from silkscreen**; untick **Use extended X2 format
   (recommended)** (JLC's own KiCad guide asks for this).
7. Click **Plot**.

## 2. Drill files

1. In the same dialog click **Generate Drill Files...**
2. Format **Excellon**, untick **PTH and NPTH in single file**, tick **Use
   alternate drill mode for oval holes**.
3. Origin **Absolute**, Units **Millimeters**, Zeros **Decimal format
   (recommended)**.
4. Click **Generate**, then close both dialogs.
5. Zip the `gerbers/` folder.

## 3. Quote settings on jlcpcb.com

| Setting | Value | Why |
|---|---|---|
| Layers | 4 | |
| Size | 76 x 142 mm (read from the zip) | |
| Thickness | 1.6 mm | `docs/board-thickness.md` |
| Min track / spacing | 0.15 / 0.15 mm, JLC's standard | the board's minimum |
| Min via hole | 0.3 mm (0.6 pad) | 322 vias at 0.3, 50 at 0.4 |
| Surface finish | **ENIG** | the dome contacts are bare pads on the front: gold stays flat and does not tarnish; also flatter for U6's 0.4 mm ball grid |
| Via covering | Tented | |
| Outer / inner copper | 1 oz / 0.5 oz | |
| Stack-up | JLC's default for 4 layers | no impedance control needed |
| Mark on PCB | "Specify a location" if offered, else leave | |

The board has two internal cut-outs (the light coupler and the FPC slot) and
eleven unplated mounting holes, all on Edge.Cuts; JLC routes them as part of
the outline.

## 4. Assembly

- **PCB Assembly**: on. **Assembly side: Bottom** (every part is on the back).
- Upload `hp42s-ls027-bom-jlc.csv` and `hp42s-ls027-cpl-jlc.csv`.
- 66 parts on 43 lines; 23 lines are Extended parts (JLC adds a loading fee
  for each). Stock on 5 October 2026 was fine for 5 boards, but low on D1
  (VSMB2943, 25), U7 (RV-8263, 255) and D2 (XL-C4040, 397): check again on
  the day. On 7 October L1 became the SXN SMNR4020-2.2UH (C135262; the
  Coilcraft was $5.23 each with 31 left) and J1 the USB4105-GF-A-120
  (C5184243; the plain -GF-A was all reserved).
- **Edge rails**: the ESP32 module hangs 1.25 mm over the bottom edge. If JLC
  adds rails, ask for them on the two long sides only.
- If Economic assembly rejects a part (U6 is a 0.4 mm DSBGA, U2 a 0.4 mm
  WSON), switch to Standard.
- **Check every part in JLC's placement preview** and rotate where the body
  does not sit on its pads. Bottom-side rotations are the usual mistake.
  Look hardest at: U6 (pin A1), U9/U10 (pin 1 dots), U8, D2 (red pair on
  pads 1/3), J1, J2 and J3 (mouths facing up the board), Q1/Q2, BT1.
- The front carries no parts: domes, panel and front light are fitted by
  hand.

**Do not order until** J2's pin 1 has been checked against the real LS027
FPC (see `docs/ls027-display.md`).
