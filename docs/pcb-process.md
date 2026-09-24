# Taking this board from a netlist to boards in your hand

Read this once end to end before starting anything. It is in the order you do
it, and each step says what "done" looks like.

You are at the end of step 1.

---

## 1. The wiring — atopile · DONE

`elec/src/*.ato` describes what connects to what. `ato build` compiles it to
`build/default.net`, a KiCad netlist, plus a BOM. atopile does not place and
does not route; it is the schematic, written as text.

**Everything is drawn and the netlist is complete.** Every footprint resolves
and every pin in the netlist lands on a real pad, checked mechanically against
the `.kicad_mod` files rather than by eye.

What is still open is in **`docs/before-layout.md`**, and as of 24 September
2026 it is short: measure the real panel's tail, check `FPC_ANGLE` in the
viewer, and read the MAX17048's DC table for its I²C thresholds. Every pin
number on the board is now confirmed against a datasheet table.

**Done looks like:** `ato build` ends in `Build complete!` and
`grep -c '"lib:' build/default.net` prints `0`.

---

## 2 to 7. The layout itself

**These six steps have their own document: `docs/layout-walkthrough.md`.** It
is the click-by-click version, written for a first layout, and it is where you
should be reading rather than here. Every menu path and keyboard shortcut in it
was checked against KiCad 10's own source.

What it covers, and roughly what each costs:

| Step | What | How long |
|---|---|---|
| 1 | The six KiCad keys and the layers panel | 5 minutes |
| 2 | Make the project at `elec/layout/default/` | 5 minutes |
| 3 | Add the `hp42s` footprint library | 5 minutes |
| 4 | Board Setup: 4 layers at 1.6 mm, constraints, net classes | 20 minutes |
| 5 | Import `build/default.net` — **link by unique ids, not designators** | 10 minutes |
| 6 | Run `tools/place_keypad.py` for the keypad, outline and panel | 10 minutes |
| 7 | Place the other ~60 parts, in the order the file gives | an evening |
| 8 | Pour the ground planes | an hour |
| 9 | Route, in the order the file gives | two or three evenings |
| 10 | The dome pads | reading only |
| 11 | DRC to zero errors and zero unconnected | an hour |
| 12 | Look at it in the 3D viewer | 10 minutes |

Three things in there are specific to this board and are the ones that would
cost you a board if skipped:

- **Import by unique ids, not reference designators.** atopile renumbers
  downstream parts whenever one is added mid-file — tested 22 September 2026,
  one inserted resistor moved eleven others — while the unique ids never move.
  Designator linking would scramble a finished placement.
- **The module's antenna overhangs the board with no copper under it**, on any
  layer, and sits as far from the USB connector as the board allows.
- **`In1.Cu` is a solid ground plane and stays solid.** Every return current on
  the board uses it.

Come back here when DRC is clean.

---

## 8. Outputs

File → Fabrication Outputs:

- **Gerbers** — all copper, mask, silk, paste, Edge.Cuts. Protel extensions off,
  X2 on.
- **Drill files** — Excellon, PTH and NPTH in one file, absolute, mm.
- **Position file** — CSV, mm. **Every part the assembler places is on the BACK
  (`B.Cu`)**, since 24 September 2026: the front carries only the panel, the 38
  dome sites and the frontlight sliver's lands, and all of those go on afterwards
  by hand. Export both sides anyway, so the file is self-evidently complete, but
  expect the front side to be empty.
- **BOM** — `build/default.csv` from atopile is the starting point, but it does
  not carry manufacturer part numbers. You will fill those in by hand once,
  and it is worth doing properly because you will reorder.

Zip the gerbers and drills together. Open the zip in an online gerber viewer
before you upload it anywhere — five minutes that catches inverted masks and
missing outlines.

---

## 9. Ordering rev A

- **5 boards**, 1.6 mm, 4 layer, ENIG, black or white soldermask to taste.
  Roughly £40 for the batch.
- **A stencil for the BOTTOM side, not the top.** That is where every reflowed
  part is. The module, the WSON parts and the USON ESD array are not
  hand-solderable without one; the 0402s are not fun without one either. Order
  one stencil, not two — that is the point of putting everything on one side.
- **Assembly** is a real choice. The BQ25185, TPS63900, MAX17048 and the ESD
  array are all leadless packages with thermal pads. If you have not reflowed
  those before, having the fab place them and hand-soldering the rest is money
  well spent.
- **Not the domes.** Those go on last, by hand, with the Peel-N-Place array, on
  a clean board. Do not let an assembler near them.
- **The four USB-C shield legs are the one through-hole joint**, and they
  protrude through the front. They are a second operation whichever side the
  receptacle is on; a receptacle with SMD-only shell tabs would remove it
  entirely, and it is worth looking for one before rev B. See
  `docs/top-edge.md`.

---

## 10. Bring-up, in this order

Never power a new board fully populated and hope.

1. **Bare board** — continuity check 3.3 V to ground and BAT to ground. Should
   read open.
2. **Power section only** — charger, buck-boost, passives. Apply USB. Measure
   SYS and 3.3 V. Nothing else fitted, so nothing else can be damaged. There is
   no slider to check: `EN` is tied to `SYS`, so the rail should come up as soon
   as there is a cell or a USB cable.
3. **Module** — fit it, check it enumerates over USB, flash a blink.
4. **Panel** — fit the connector and the booster. Before running any graphics,
   measure VGH and VGL at the connector: about +22 V and −20 V. If those are
   wrong, nothing above them will work and you will waste a day on firmware.
5. **Keypad** — domes last. Test every key individually; a matrix hides
   single-key faults well.

---

## What this board will cost you in time

The wiring was the fast part. Placement and routing on a board this dense —
38 dome sites, a 1.6 mm gap between the numeric ones, two switching loops and
a module antenna — is a few evenings of real work, and the first one is the
slowest. Expect to redo the placement once after you see the ratsnest.
