# Getting the board into KiCad

## 1. Tell KiCad where this repo's own footprints live

The netlist references two libraries: KiCad's standard ones, which you already
have, and `hp42s`, which is this repo. Without the second, import fails on
every dome site.

Preferences → Manage Footprint Libraries → Global (or Project) → Add, then:

| Field | Value |
|---|---|
| Nickname | `hp42s` |
| Library Path | the full path to `elec/footprints/hp42s.pretty` |
| Library Format | KiCad |

If you would rather do it per project, the same thing in `fp-lib-table` next
to your `.kicad_pcb`:

```
(fp_lib_table
  (version 7)
  (lib (name "hp42s")(type "KiCad")(uri "${KIPRJMOD}/../../footprints/hp42s.pretty")(options "")(descr "HP-42S dome sites"))
)
```

That `${KIPRJMOD}` path assumes the project sits at `elec/layout/default/`.

## 2. Import the netlist

File → Import → Netlist, point it at `build/default.net`.

**Expect no errors.** Every footprint resolves — KiCad's standard libraries
for all but three, and this repo's `hp42s` library for the two dome sites and
the TPS63900's land pattern, which KiCad does not carry. That one is generated
from TI's own drawing by `tools/gen_ic_footprints.py`; re-run it if you ever
delete `elec/footprints/hp42s.pretty/`.

## 3. Place the keypad and the top-edge parts

Tools → Scripting Console:

```python
exec(open('tools/place_keypad.py').read())
```

See `docs/pcb-process.md` for the whole route from here to boards in your hand.

That puts the 38 dome sites on the measured grid, flips USB-C, the power
slider and the reset button onto the back at the top edge, and draws the
76 × 144 outline if Edge.Cuts is empty. See `docs/top-edge.md`.

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

**`Q1` package.** The panel's boost FET is a Si1308EDL in SC-75A, and
`Package_TO_SOT_SMD:SOT-416` is the matching land pattern. Check it against
Vishay's drawing — SC-75 and SOT-416 are the same 1.6 × 1.6 mm outline under
two naming schemes, but confirm rather than trust that sentence.

**The slide switch pads.** KiCad places the MSK-12C02's three pads at
x = −2.25, +0.75, +2.25 — an uneven 3.0 / 1.5 mm spacing that looks wrong for a
1.5 mm-pitch part. The vendor drawing is behind a host this session cannot
reach, so it has not been confirmed. The netlist is right either way; it is the
land pattern that wants a second look.

**The fuel gauge's I²C.** `U4` now runs off the cell rather than the 3.3 V
rail, so its SDA/SCL sit on a 4.2 V part with 3.3 V pull-ups. Its input
thresholds are fixed rather than VDD-referenced, so this should be fine — read
the DC table and confirm.
