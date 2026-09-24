# What is outstanding before layout

Written 21 September 2026, when Barnaby asked whether anything was still open
on the design side, and largely struck through on the 22nd when he answered
the questions and sent the two missing datasheets. **Short answer: nothing
blocks starting, and the parts questions are now closed.** The netlist is
complete, every footprint resolves, and every pin in the netlist matches a real
pad in its footprint. That last one is checked mechanically rather than by eye,
by `tools/check_netlist.py`, against the actual `.kicad_mod` files including the
ones pulled from KiCad's upstream library. Run it after every `ato build`:

```
python3 tools/check_netlist.py
```

It exists because KiCad matches a netlist pin to a pad **by name**, and a pin
whose name matches no pad imports silently unconnected — no error, just a
ratsnest line that is not there. This repo has been caught by that twice.

What follows is everything still open, sorted by whether it stops you.

## 1. Decide before you place copper

**All four of these closed on 22 September 2026.** Kept here with what they
turned into, because each one changed a part.

**The slide switch → C&K JS102011SAQN.** Barnaby's call. KiCad's Shouhan land
put the three pads at an uneven 3.0 / 1.5 mm spacing for a part sold as 1.5 mm
pitch, and the vendor drawing was unreachable; the C&K land is a clean 2.5 mm
pitch drawn from C&K's own document, and it is the better switch. It costs
board area — a 10.00 × 8.75 mm courtyard against 8.90 × 5.95 — which is only
affordable because the bezel went to 14 mm. Its placement moved from y 2.30 to
y 3.00 so the knob still lands 0.80 mm proud of the board edge. It has **no
shield pad**; `power.ato` lost its `sw_power.shield` connection with the swap.

**The USB-C receptacle → GCT USB4105-GF-A.** Not for the reason we were
looking. **Every** 16-pin Type-C receptacle in KiCad's library has four
through-hole shell legs, and that is not an oversight: the legs are what stops
a yanked cable lifting the pads off a board that gets charged daily. A
fully-SMD receptacle would trade a solved case problem for an unsolved
mechanical one. So the legs stay, the cell stays clear of board Y 0 to 5, and
the fillets are a case problem — give the cell a printed rib to rest on across
the top 6 mm and it never touches them.

What did change is the land pattern. The Same Sky UJ20's footprint was
hand-generated in `tools/gen_ic_footprints.py`; GCT's is in KiCad drawn from
GCT's own document. That is one fewer hand-made land pattern on the one part
that gets mechanically abused. The pad names are identical (A1…B12, SH) so
nothing in the netlist changed, and GCT's mouth sits at the same 3.675 mm from
the footprint origin, so the placement constant did not change either. Its
courtyard reaches 8.44 mm in rather than 8.83.

A **Same Sky UJC-HP-G-5-SMT-TR** was put up against it on 24 September 2026 and
turned down. Six contacts, `CC`/`VBUS`/`GND` only, no `D+`/`D-`: a charge-only
receptacle. It is smaller and it is fully SMD, which is genuinely attractive
after the paragraph above, but this board transfers files over USB and, with no
USB-UART bridge on it, the S3's own USB is the only way a bricked board ever
gets reflashed. See `docs/top-edge.md`.

**`L2`, the panel's 47 µH → Bourns SRN4018-470M.** 47 µH ±20%, 600 mA,
semi-shielded, 4.0 × 4.0 × 1.8 mm, on KiCad's `L_Bourns-SRN4018` drawn from
Bourns' own drawing. This closes the oldest open item on the board. It beats
Solomon Systech's requirement (600 mA against 500), it is stocked with a real
datasheet, and at 1.8 mm it is 0.2 mm **shorter** than the Sumida CDRH2D18 we
were chasing — worth having, because it lives on the back where the cell now
does. It costs 0.8 mm in each direction inside the panel's switching loop; a
correct land that is 0.8 mm bigger beats a wrong one that is 0.2 mm smaller.

**`U4`'s exposed pad — nothing to fix.** The answer was not the drawing. The
EP on a 3 µA part is a ground and mechanical anchor, not a heatsink, so there
is no thermal size to hit. The error is asymmetric: a land *larger* than the
package's pad risks bridging to the pins, a land *smaller* just solders fine.
KiCad's 0.8 × 1.2 mm is conservative for a 2 × 2 mm TDFN-8, so it already errs
the safe way — and it windows the paste into four apertures, which is what
stops the part floating on excess solder. That is the failure this land is
actually exposed to and it is already handled.

## 2. Pin numbering — all confirmed

Nothing left here. The last two closed on 22 September 2026 from the PDFs
Barnaby supplied.

| | source |
|---|---|
| `U2` BQ25185 | SLUSF65B table 4-1 |
| `U1` TPD4E05U06 | SLVSBO7O rev. August 2024, table 4-2 |
| `U3` TPS63900 | **SLVSET3D rev. October 2020, figure 5-1 and table 5-1.** All ten match. The thermal pad is not optional — TI's words are "connect this pin to ground for correct operation" |
| `U4` MAX17048 | pin/bump description table, page 6 |
| `U6` TPS61165 | **SLVS790E rev. April 2019, section 6.** The table gives WSON and SOT-23 numbering side by side; ours is the SOT-23 column, and all six match |
| `J1` USB-C | the connector standard; the pads really are called A1, B5, SH |
| `U5` ESP32-S3-MINI-1 | module pin table. KiCad has no S3-MINI-1 footprint, but its `RF_Module:ESP32-S2-MINI-1` cites the **S3**-MINI-1 datasheet in its own description |

**The fuel gauge's I²C levels** is the one electrical check left in this
section. `U4` runs off the cell rather than the 3.3 V rail, so its SDA/SCL sit
on a 4.2 V part with 3.3 V pull-ups. Its input thresholds are fixed rather than
VDD-referenced, so this should be fine — read the DC table and confirm.

## 3. Things only you can measure

**The panel's tail.** This is the highest-risk item on the page and it is not
close. The drawing gives 14.30 mm ± 0.3, the fold eats 3.30, and the
connector's pad row has to land inside the last 3 mm of what is left. There is
no slack at all: 0.3 mm short and the flex does not reach the contacts. Measure
a real panel before you commit the board.

**~~Which leg of the power slider is the wiper.~~ CLOSED 2026-09-24 by deleting
the slider.** On/off is the `EXIT/ON` key now, the way it is on a real 42S, so
there is no switch to buzz out and no 4 µA of agnostic wiring to pay for. See
`docs/power-control.md`.

**The C&K's knob protrusion.** KiCad's Fab outline puts the actuator tip
3.80 mm from the footprint origin and its courtyard 4.25 mm, and those two
cannot both be the knob. The placement assumes 3.80, which lands the tip
0.80 mm proud of the board edge. Check it against C&K's drawing.

**`FPC_ANGLE` in `tools/place_keypad.py`.** Set to 90° so the connector's mouth
faces the notched left edge. Never verified, because there is no KiCad in this
session. Look at it in the viewer after the script runs; if the mouth points at
the middle of the board, change it to 270.

## 4. Not board work, but not done

**The frontlight sliver.** The four LEDs live on a 1.0 mm FR4 strip about
60 × 4 mm that lies on the main board, not on the main board itself. It is its
own little PCB and it is not drawn. It does not block the main board — the main
board's side of it is two solder pads, which are in the netlist — but it has to
exist before you can light anything.

**The firmware.** Keys are not yet fed to `core_keydown()`, the annunciator
strip is a stub, nothing saves state, and the blitter has never driven real
glass. None of it changes the board.

**The licence.** Plus42 is GPLv2, so anyone given or sold a unit has to be able
to get the source.
