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
for all but eight, and this repo's `hp42s` library for the two dome sites, the
TPS63900's land pattern, the side-looking IR emitter's, the status LED's, the
ESD array's, the USB-C receptacle's and the two recovery buttons',
none of which KiCad carries. All of them are generated from the vendors' own
drawings, by `tools/gen_dome_footprints.py` and `tools/gen_ic_footprints.py`;
re-run both if you ever delete `elec/footprints/hp42s.pretty/`.

## 3. Place the keypad and the top-edge parts

Tools → Scripting Console:

```python
exec(open('tools/place_keypad.py').read())
```

See `docs/pcb-process.md` for the whole route from here to boards in your hand.

That puts the 38 dome sites on the measured grid, places the six top-edge
parts on the **front** at the top edge, places the panel's FPC connector on
the back, and draws the 76 × 144 outline with its notch if Edge.Cuts is empty.
See `docs/top-edge.md`. Nothing is flipped any more: the top-edge parts moved
to the front with the 14 mm bezel, so the 180° rotations in the script are the
whole of the orientation story.

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

The full list lives in **`docs/before-layout.md`**, sorted by whether it stops
you starting layout or only stops you ordering boards. The two that change a
footprint's shape, and so want deciding first, are the slide switch (KiCad's
Shouhan land pattern is doubtful, and the nicer C&K part fits now the bezel is
14 mm) and `L2`, the panel's 47 µH, which is still on a stand-in pattern inside
a switching loop.
