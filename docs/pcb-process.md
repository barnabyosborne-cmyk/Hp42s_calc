# Taking this board from a netlist to boards in your hand

Read this once end to end before starting anything. It is in the order you do
it, and each step says what "done" looks like.

You are at the end of step 1.

---

## 1. The wiring — atopile · DONE, with four holes

`elec/src/*.ato` describes what connects to what. `ato build` compiles it to
`build/default.net`, a KiCad netlist, plus a BOM. atopile does not place and
does not route; it is the schematic, written as text.

**Four parts are still incomplete**, and they are mine to finish:

| | what is missing | blocked on |
|---|---|---|
| `U2` BQ25185 | pin numbers | TI's datasheet, which this session cannot fetch |
| `U3` TPS63900 | footprint *and* pin numbers | TI's land pattern |
| `U4` MAX17048 | footprint *and* pin numbers | Analog's land pattern |
| `U6` TPS61165 | pin numbers to confirm | TI's package drawing — ti.com is blocked from this session, and the numbers in `parts.ato` came out of a text extraction of the pin-functions table, not off the drawing |

If you can download those four datasheets and drop them in the thread the way
you did the panel spec, all four close in one go. Everything else on the
board — the MCU, the panel, its booster, USB, the keypad, the top-edge parts,
every passive — is complete and routable now.

**Done looks like:** `ato build` ends in `Build complete!` and
`grep -c '"lib:' build/default.net` prints `0`.

---

## 2. Make the KiCad project

KiCad needs a project to import into. It does not exist yet.

1. KiCad → File → New Project, save it as `elec/layout/default/default.kicad_pro`
   inside this repo. Let it create the folder.
2. Open the PCB editor (the second icon). You will not use the schematic editor
   at all — atopile is the schematic.
3. Tell KiCad where this repo's own footprints live. Preferences → Manage
   Footprint Libraries → Project tab → Add:

   | Field | Value |
   |---|---|
   | Nickname | `hp42s` |
   | Library Path | `${KIPRJMOD}/../../footprints/hp42s.pretty` |
   | Format | KiCad |

**Done looks like:** the footprint browser lists two entries under `hp42s`,
the two dome sites.

---

## 3. Import the netlist

PCB editor → File → Import → Netlist → `build/default.net`.

Leave the defaults except: match by **reference designator**, and tick "update
footprints". Import it again after every `ato build`; it is not a one-time
operation and it does not disturb placement or routing you have already done.

All 100 footprints should land in a heap at the origin. Expect errors only for
`U3` and `U4`, whose footprints do not exist yet.

**Done looks like:** 100 footprints on the board, and the ratsnest shows the
keypad matrix as a regular grid of lines rather than a tangle.

---

## 4. Outline and placement

Run the placement script — PCB editor → Tools → Scripting Console:

```python
exec(open('../../../tools/place_keypad.py').read())
```

(the path is relative to the KiCad project folder; adjust if you put it
elsewhere.)

That draws the 76 × 144 mm outline and places the 38 dome sites on the
measured grid plus the six top-edge parts, which now go on the **front**.
Everything else is still in a heap, and placing it is the first real judgement
call of the job.

Two things settled on 21 September 2026 changed the shape of this step. The
**cell goes at the top of the back**, which evicts the electronics bay to
behind the keyboard; and the **top bezel is 14 mm**, which moved the six
top-edge parts to the front and the whole panel 6 mm down the board. See
`docs/top-edge.md` and `docs/display-mounting.md`.

Place in this order, because each constrains the next:

1. **The panel's FPC connector** — already placed by `tools/place_keypad.py`,
   back side, origin at board X 9.00, Y 30.15, mouth facing the notched left
   edge. Do not move it: the 14.30 mm tail has no slack. See
   `docs/display-mounting.md`. Measure the real panel's tail before you commit
   the board, because the drawing gives it to ±0.3 mm.
2. **The module**, back side, behind the keyboard — the top of the back is the
   cell's now. The antenna end must overhang the board outline with all copper
   cleared beneath it, and sit as far from the USB-C shield and the cell as you
   can manage. The board's bottom edge does that as well as the top did, and it
   is diagonally opposite the USB connector, which is what you want.
3. **The panel's booster** — L1, Q1, C3, D1–D3 — as one tight cluster next to
   the FPC connector. This is a switching loop; every millimetre of it is
   inductance you do not want. It and the FPC connector are the only two
   things still pinned to the top left of the back, because the tail length
   gives them no choice; the cell has to come down past them.
4. **The buck-boost** and its inductor, likewise tight, and away from (3),
   behind the keyboard.
5. **The charger**, near USB-C, with the cell connection running away from
   the signal side. USB-C is on the front now, so this is the one part that
   gained from the move: the charge current no longer runs the length of the
   board to reach a cell at the top.
6. **The fuel gauge**, anywhere convenient on the cell net.
7. **The frontlight driver**, if the unit is getting one — U6 and its
   inductor, diode and caps — on the front, at the right-hand end of the strip
   between the panel and the keyboard (board Y 48.3 to 59.0), as far from the
   FPC connector and the panel's booster at X 7–20 as the board allows. It is
   a second switching node and it wants to be nowhere near the panel's SPI.
8. **Decoupling capacitors**, each hard against the pin it serves. Do this
   last and do it deliberately; a 100 nF placed 10 mm from its pin is
   decoration.

**Done looks like:** nothing overlaps, the ratsnest has no lines crossing the
whole board, and the battery bay at the top of the back is clear from about
board Y 5 to Y 59. Y 5 rather than Y 0 because the USB-C receptacle's
through-hole shield legs leave their fillets there now.

---

## 5. Stack-up

File → Board Setup → Physical Stackup: **4 layers, 1.0 mm**.

| Layer | Use |
|---|---|
| F.Cu | dome pads, panel, short signal runs |
| In1.Cu | **solid ground**. Do not cut it up |
| In2.Cu | 3.3 V pour, plus the keypad column and row nets |
| B.Cu | everything else, and the second ground pour |

The keypad matrix runs on an inner layer because nothing can route between the
numeric domes on the front — they clear each other by 1.6 mm and their
courtyards by 0.6 mm. Each dome ring is reached by a via placed outside its
courtyard.

Net classes worth setting up now: `default` 0.2 mm track, `power` 0.5 mm,
`keypad` 0.2 mm. Clearance 0.2 mm throughout, which every cheap fab meets.

---

## 6. Route, in this order

1. **The two switching loops first** — the panel booster and the buck-boost.
   Short, fat, and returning to ground directly beneath themselves. If these
   end up long you will hear it through the buzzer and see it on the panel.
2. **Power distribution** — SYS, BAT, 3.3 V.
3. **The panel's SPI**, kept away from both switch nodes.
4. **USB D+/D−** as a pair, same length, no stubs, straight from the
   connector through the ESD array to the module.
5. **The keypad matrix**, last and on inner layers. It is slow, it is
   forgiving, and it is most of the copper.

**Done looks like:** DRC clean with zero unrouted nets.

---

## 7. The dome pads

This is the part that is specific to this board and gets it wrong quietly.

- Solder mask must be **open over the whole contact area** of every dome pad,
  ring and centre both.
- Each dome site needs a **vent** — a via or a channel in the dome array — or
  trapped air mushes the click.
- **Plating:** ENIG for rev A is fine. For the final board, specify selective
  hard gold on the 37 dome sites: 0.38–0.76 µm gold over 1.27–5.0 µm nickel.
  ENIG typically fails before 200,000 cycles and a flaky `0` key ruins the
  object. Get a quote before you design around it — it costs more than the
  rest of the board.

---

## 8. Outputs

File → Fabrication Outputs:

- **Gerbers** — all copper, mask, silk, paste, Edge.Cuts. Protel extensions off,
  X2 on.
- **Drill files** — Excellon, PTH and NPTH in one file, absolute, mm.
- **Position file** — CSV, mm, both sides. This is the assembly file.
- **BOM** — `build/default.csv` from atopile is the starting point, but it does
  not carry manufacturer part numbers. You will fill those in by hand once,
  and it is worth doing properly because you will reorder.

Zip the gerbers and drills together. Open the zip in an online gerber viewer
before you upload it anywhere — five minutes that catches inverted masks and
missing outlines.

---

## 9. Ordering rev A

- **5 boards**, 1.0 mm, 4 layer, ENIG, black or white soldermask to taste.
  Roughly £40 for the batch.
- **A stencil** for the top side. The module, the WSON parts and the USON ESD
  array are not hand-solderable without one; the 0402s are not fun without one
  either.
- **Assembly** is a real choice. The BQ25185, TPS63900, MAX17048 and the ESD
  array are all leadless packages with thermal pads. If you have not reflowed
  those before, having the fab place them and hand-soldering the rest is money
  well spent.
- **Not the domes.** Those go on last, by hand, with the Peel-N-Place array, on
  a clean board. Do not let an assembler near them.

---

## 10. Bring-up, in this order

Never power a new board fully populated and hope.

1. **Bare board** — continuity check 3.3 V to ground and BAT to ground. Should
   read open.
2. **Power section only** — charger, buck-boost, passives. Apply USB. Measure
   SYS and 3.3 V. Nothing else fitted, so nothing else can be damaged. Check
   the slider actually switches the rail.
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
