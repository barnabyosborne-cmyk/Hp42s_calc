# Where everything goes, and why

23 September 2026. The table is `FIRST_PASS` in `tools/place_board.py`, which
writes it into `elec/layout/default/default.kicad_pcb`. Nothing here is
routed, and routing will move some of it.

## The rules this follows

Barnaby sent a placement checklist on 23 September; these are the parts of it
that bite on a board this size.

| Rule | How it is applied here |
|---|---|
| Fixed parts first | The keys, the five top-edge parts, the FPC, the sliver lands and the ESP32 were placed by the case, the panel and the antenna before anything else moved. None of them is on a grid, and none of them should be. |
| Then the ICs, then the passives | Each supply is a block built outwards from its own IC. |
| Decoupling at the pin | Every bypass capacitor is beside the pin it serves, and the comment beside it in `place_board.py` names that pin. |
| Zoning | The two boosts are at opposite corners. The fuel gauge, the only analogue part, is 14 mm from the display inductor and 45 mm from the frontlight's. |
| Signal flow | Power runs down the back: charger Y 72, regulator Y 89, module Y 133. USB runs J1 → U1 → down. |
| Grid | ICs and connectors on 1.27 mm (50 mil), passives on 0.635 mm (25 mil). |
| Clearance | At least 1.0 mm between courtyards — near enough the 40 mil asked for, and the courtyards already carry the manufacturer's own handling allowance. |
| Uniform orientation | Every two-terminal passive is at 0°, so the board is one pick-and-place orientation. |
| One side if possible | **Met, since 24 September 2026.** Everything the fab house solders is on the back. See below. |

Two rules cannot be met and are not:

- **100 mil to the board edge.** The board is 76 × 144 mm with a keyboard over
  half of it and a cell over a third. The top-edge parts are *meant* to
  overhang the outline, and the back components sit 0.5–5 mm from it. This is
  a sealed resin case with no edge rails or board guides, so the reason for
  the rule — handling damage and depanelling — is weaker here than the space
  is scarce.
- ~~**All on one side.**~~ **Met on 24 September 2026, at the cost of a
  millimetre of cell thickness.** Barnaby asked for it, because a single-sided
  assembly is the cheaper build: one stencil, one paste print, one reflow. The
  last nine parts on the front — the USB front end, the IR driver and the status
  LED's ballasts — crossed to the back at exactly the same x and y, and the
  battery bay gave up the 4.5 mm they needed. A 6 × 45 × 55 cell is the same
  1600 mAh as the 5 × 50 × 60 it replaces.

  What is still on the front is the panel, the 38 dome sites and the frontlight
  sliver's lands, none of which the fab house solders. The one blemish is the
  USB-C's four through-hole shield legs, which are a second operation whichever
  side they protrude from; a receptacle with SMD-only shell tabs would remove it.
  See `docs/top-edge.md`.

## What was already spoken for

| | |
|---|---|
| BACK Y 0–8 | the five top-edge parts, pushed out towards the case wall |
| BACK Y 4–11.7 | the nine parts that serve them, interleaved with those |
| BACK Y 13–58, X 14–69 | the battery bay |
| FRONT Y 0–5 | nothing but the USB-C's four through-hole shield fillets |
| FRONT Y 12–48.3 | the panel's glass |
| FRONT Y 48.3–57 | the frontlight sliver's two lands and a ground point |
| FRONT Y 57–137 | the keyboard, on Barnaby's measured grid |

The battery bay is the hard one. `docs/display-mounting.md` settled the cell
on the back at the top, which evicted the electronics to **behind the
keyboard**, and nothing may go under a pouch cell — it grows over its life and
its case is soft aluminium laminate.

## The band that serves the top edge

**BACK Y 4–11.7, between the top-edge parts and the battery bay.** The USB front
end lives here — the ESD array behind J1's own D+/D− pins, the two CC resistors
at U1's CC pins, the VBUS capacitor at the connector where the current enters.
The alternative is 60 mm of unprotected D+/D− running the length of the board to
the only other free space. The IR transistor and its two resistors are here too,
behind the emitter they drive, and so are the status LED's two ballast resistors,
behind it.

**This band was on the FRONT until 24 September 2026**, at exactly these x and y.
Moving it over cost the battery bay 4.5 mm and gained a single-sided assembly and
a USB pair that reaches its ESD array without crossing the board.

Nothing in the band can go past Y 11.7: the bay starts at 13. And the nine parts
have to thread between the five above them, none of which can move — J1's body
reaches Y 7.24, the two buttons 3.85, and the two LEDs about 2.4.

## The one remaining front sliver

**Y 48.3–57, between the glass and the keys.** `TP1` and `TP2` are the
frontlight sliver's two solder lands, 60 mm apart because that is the sliver's
length, with the sliver spanning between them along the guide's injection
edge. `TP3` is a ground point to clip a scope to while the frontlight is being
set up; it is on the front because that is where the frontlight is.

All three go on after the board comes back from the fab, along with the panel and
the domes, which is what lets the front carry nothing the fab house solders.

## The back, below Y 59

**Rows 1 and 2, left — the panel's own rail capacitors.** C10 (3V3), C11
(VDD), C12 (VSH1), C13 (VSH2), C14 (VSL), C15 (VCOM). These belong at J2's
pins and they cannot get there: the bay is in the way. They sit in the first
two rows below it, directly under the connector, which is as close as the
geometry allows. The run is about 33 mm. That is the price of the cell being
where it is, and it was paid the moment the cell went on the back.

**Left, Y 65–81 — the display boost.** The noisiest block on the board. Q1
switches L2 against the 3V3 rail; D1 rectifies PREVGH into C17; D2, D3 and C18
are the inverting charge pump that makes PREVGL into C19. The inductor is hard
against Q1's drain so the switching loop stays small.

**Right, Y 59.5–72 — the frontlight boost.** U6 sits at the sliver's FB end,
so the high-impedance feedback trace is short and it is the 38 V rail that
takes the long way to TP1 — a rail is far happier running 60 mm than a
feedback node is. L3, D6 and C20 close the switching loop in that order.

**Centre, Y 60–79 — the cell and the charger.** BT1 is hard against the bottom
edge of the bay so the cell's tails drop straight into it. U2 is directly
below, C2 at its BAT pin, C3 at its SYS pin, the four programming resistors on
the right-hand side where their pins are.

**Centre, Y 86–96 — the 3V3 regulator.** L1 straddles the TPS63900's two
switch pins. C4 and C5 are at the VOUT pin, R11 and the three CFG resistors on
the left where theirs are.

**Left, Y 87–91 — the fuel gauge**, kept away from both switchers, with its
BAT bypass at pin 3 and the two I²C pull-ups at pins 7 and 8.

**Right, Y 108–125 — the sounder**, which needs a hole through the case back,
clear of the antenna keepout.

**Bottom, Y 123–138 — the module.** Rotated 180° so the antenna faces the
board's bottom edge and radiates off it. Its keepout covers Y 138.75–144 from
X 15.3 to 60.7, which is the chin — where `docs/front-face.md` already keeps
the metal faceplate out for the same reason. **No copper, no pour and no parts
in that rectangle.** C8 and C9 bypass 3V3 at pin 3, C7 and R14 hold EN at pin
45, and the four signal test points sit at the pins they probe.

**Right, Y 85–90 — the four power test points**: BAT, SYS, 3V3, GND.

## What is checked

`tools/check_placement.py` reads the board file and reports courtyards closer
than 1.0 mm on the same side, anything crossing the outline, anything on the
back inside the battery bay, anything inside the antenna keepout, anything on
the front under the glass or the keys, and anything off its grid. It is clean
apart from the five top-edge parts, which are meant to overhang.

`tools/fix_pads.py --check` is the other half: it compares every pad on the
board against the library footprint it came from — mirrored in y for the
parts on the back, and with the footprint's rotation folded into each pad's
angle — and reports any that have drifted. Run it after any KiCad session
that moved things; without `--check` it puts them back.

Both sides are set by `place_board.py` too. A flipped footprint is not the
same footprint with B.* layer names: every coordinate inside it is mirrored
in y. All 75 footprints that come from KiCad's own libraries were checked
graphic by graphic against those libraries, mirrored where they should be.

## What is not settled

- ~~The cell connector's height.~~ **Settled 23 September 2026.** It was
  `JST_PH_B2B-PH-K`, the vertical variant, and Barnaby made two objections
  that were both right: the plug and its leads need more headroom above it
  than the 5 mm cell beside it is tall, and its through-holes went straight
  through the board into the SW3 dome site on the front. It is now
  **`S2B-PH-SM4-TB`** — side entry and fully surface mount, so nothing
  pierces the board and the leads leave it flat. It is turned 180° so its
  mouth faces the bay, and it moved right to (50.8, 64.77) because its
  courtyard is 9.2 × 10.2 mm against the old 6.9 × 5.5. Nearest neighbour is
  L3, 3.1 mm away. **This needs `ato build` and a netlist re-import** before
  the board carries the new land pattern.
- **Support corridors.** `docs/board-thickness.md` wants the case to bear on
  the board inside the keyboard area, in the gaps between key columns. Y
  96–108 and Y 125–144 to the left and right of the module are the clearest
  bands on the back. Three or four bearing points still need to be agreed.
- **The antenna and the bottom key row.** The 10 mm domes on the bottom row
  reach Y 139.0; the keepout starts at Y 138.75. A 0.25 mm sliver of dome pad
  is not going to detune a 2.4 GHz antenna, but the ground pour must stop at
  the keepout regardless.
- Nothing is routed. Expect the switchers' loops in particular to want
  rearranging once their current paths are real.
