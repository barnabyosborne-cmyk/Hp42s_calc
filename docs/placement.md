# Where everything goes, and why

First pass, 23 September 2026, in `tools/place_board.py` as `FIRST_PASS`.
Nothing here is routed, and routing will move some of it.

## What was already spoken for

Three areas were fixed before this started, and between them they take most
of the board:

| | |
|---|---|
| FRONT Y 0–5 | the six top-edge parts, pushed out towards the case wall |
| FRONT Y 12–48.3 | the panel's glass |
| FRONT Y 59–137 | the keyboard, on Barnaby's measured grid |
| BACK Y 5–59 | the battery bay, full width but for the FPC in the left 10 mm |

The battery bay is the hard one. `docs/display-mounting.md` settled the cell
on the back at the top, which evicted the electronics to **behind the
keyboard**, and nothing may go under a pouch cell — it grows over its life and
its case is soft aluminium laminate.

So there were three places left: the back below Y 59, and two slivers of front
that nothing else wanted.

## The two front slivers

**Y 5–12, between the top-edge parts and the glass.** The USB front end lives
here — the ESD array, the two CC resistors and the VBUS capacitor — directly
behind J1, because the alternative is 60 mm of unprotected D+/D− running the
length of the board to the only other free space. The IR transistor and its
two resistors are here too, next to the emitter they drive, and so are the
status LED's two ballast resistors.

The band is a single row at Y 9.60, not two rows starting at Y 5, because the
USB-C receptacle's body reaches Y 6.8 and the slider's Y 5.9. That collision
is the reason for the row.

**Y 48.3–59, between the glass and the keys.** `TP1` and `TP2` are the
frontlight sliver's two ends, 60 mm apart at the active area's edges, with the
sliver spanning between them along the guide's injection edge. `TP3` bonds the
metal faceplate to ground and has to be on the front, under the plate.

## The back, below Y 59

**Top left — the panel's boost.** As near J2 as the bay allows. The ten rail
capacitors sit with the boost rather than at the connector, which is a
compromise the bay forces: decoupling belongs at the load, but the load's
connector is surrounded by cell.

**Top right — the frontlight driver.** `elec/src/frontlight.ato` asks for this
explicitly: a second fast switching node, kept as far from the FPC and the
panel's own converter as the board allows. FL+ and FL− climb through vias to
`TP1` and `TP2`; both are DC once past the output capacitor, so the 60 mm run
to the far land costs nothing.

**Centre, just below the bay — the cell connector**, so the cell's leads drop
straight down into it.

**Middle — charger, regulator, fuel gauge** and their passives.

**Bottom — the module.** Rotated 180° so the antenna faces the board's bottom
edge and radiates off it. Its keepout then covers Y 138.75–144 from X 15 to
61, which is the chin — where `docs/front-face.md` already keeps the metal
faceplate out for the same reason. **No copper, no pour and no parts in that
rectangle.**

**Bottom left — the buzzer**, which needs a hole through the case back, clear
of the antenna keepout.

## What is checked

`tools/place_board.py` writes positions into the `.kicad_pcb` directly, so the
result is reviewable in `git diff`. The placement was checked for courtyard
overlaps on each layer, for parts crossing the board outline, and for anything
straying into the battery bay or the antenna keepout. All four are clean.

## What is not settled

- **The cell connector's height.** `JST_PH_B2B-PH-K` is the vertical variant,
  about 6 mm tall, on the back. The cell beside it is 5 mm. Worth measuring
  against the case before this is fixed; the side-entry variant is the same
  land pattern turned on its side if it does not fit.
- **Support corridors.** `docs/board-thickness.md` wants the case to bear on
  the board inside the keyboard area, in the gaps between key columns. The
  back is now populated there. Three or four bearing points still need to be
  agreed, and parts moved out of their way.
- **The antenna and the bottom key row.** The 10 mm domes on the bottom row
  reach Y 139.0; the keepout starts at Y 138.75. A 0.25 mm sliver of dome pad
  is not going to detune a 2.4 GHz antenna, but the ground pour must stop at
  the keepout regardless.
- Nothing is routed. Expect the switchers' loops in particular to want
  rearranging once their current paths are real.
