# Getting the board into KiCad

**Start at `docs/layout-walkthrough.md` instead.** That file is the step-by-step
procedure — make the project, add the library, set the stackup, import the
netlist, run the placement script, place, route, check — and it supersedes the
three steps this file used to carry. `docs/pcb-process.md` is the map around it,
from netlist to boards in your hand.

What is left here is the part that is not a procedure: why the pin numbers on
this board are the way they are, and what reading the datasheets properly
turned up.

## Pin numbers: all of them are real now

KiCad matches a netlist pin to a footprint pad **by name**. Declaring a pin as
`IO33` against a footprint whose pads are called `1` to `65` matches nothing,
and the net imports silently unconnected -- no error, just missing ratsnest.
Every part on this board was once in that state. None is now.

The numbering came from the parts' own datasheets, except the ESP32's, which
came from KiCad's own `ESP32-S3-MINI-1` symbol. That symbol settles the
footprint question too: it points at `RF_Module:ESP32-S2-MINI-1` itself,
because the MINI-1 package is shared across the family.

Reading those datasheets properly turned up five things that were wrong rather
than merely unmapped, and any one of them would have cost a board:

- The **TPS63900 has no feedback divider**. Output voltage is set by resistors
  on CFG1/CFG2/CFG3, none of which may be left open. It is also a 2.5 x 2.5 mm
  WSON-10, not the VQFN-12 this repo claimed.
- The **BQ25185 has no CHG pin**. Status is two open-drain pins, and ILIM and
  VSET are one pin programmed by one resistor.
- The BQ25185's **TS/MR pin cannot float**. Left open, the internal clamp reads
  as a temperature fault and the charger refuses to charge. It needs 10k to
  ground, or a real NTC.
- On the **MAX17048, CELL is not internally connected** -- VDD is the sense
  input. CELL belongs to the 2-cell MAX17049.
- The **ESD array is a USON-10**, not a SOT-23-6.

## Things to check before fab

The full list lives in **`docs/before-layout.md`**. As of 22 September 2026
every parts question on it is closed: the slide switch is a C&K JS102011SAQN,
the USB-C receptacle a GCT USB4105-GF-A, `L2` a Bourns SRN4018-470M, and `U4`'s
exposed pad turned out not to need the drawing. What is left is three things
only a meter and a real panel can settle, and one DC-table read on the fuel
gauge's I²C levels.
