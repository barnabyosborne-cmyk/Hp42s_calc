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

Expect **two errors**, and only two:

| Reference | Footprint | Why |
|---|---|---|
| U3 | `hp42s:TPS63900_VQFN-12_2.5x3mm` | KiCad's only VQFN-12 is 4 × 4 mm |
| U4 | `hp42s:MAX17048_WLP-8_1.2x0.9mm` | Package_BGA has Maxim's WLP-9 and WLP-12, not WLP-8 |

Both land patterns exist in the vendor datasheets. Drop them into
`elec/footprints/hp42s.pretty/` under exactly those names and the errors go.

Everything else resolves against KiCad's standard libraries.

## 3. Place the keypad and the top-edge parts

Tools → Scripting Console:

```python
exec(open('tools/place_keypad.py').read())
```

See `docs/pcb-process.md` for the whole route from here to boards in your hand.

That puts the 38 dome sites on the measured grid, flips USB-C, the power
slider and the reset button onto the back at the top edge, and draws the
76 × 144 outline if Edge.Cuts is empty. See `docs/top-edge.md`.

## Before you route: three parts have no pin numbers yet

This is the thing to know before you start pulling ratsnest lines.

KiCad matches a netlist pin to a footprint pad **by name**. Declaring a pin as
`IO33` against a footprint whose pads are called `1` to `65` matches nothing,
and the net imports silently unconnected — no error, just missing ratsnest.

Everything on the board is now numbered correctly **except three parts**:

| | what is missing |
|---|---|
| `U2` BQ25185 | pin numbers — needs TI's datasheet |
| `U3` TPS63900 | footprint *and* pin numbers — needs TI's land pattern |
| `U4` MAX17048 | footprint *and* pin numbers — needs Analog's land pattern |

So the ratsnest after import is the MCU, the panel, its booster, USB, the
keypad, the top-edge parts and every passive — real and routable — plus those
three floating free. Route everything else first; they sit in the power
corner and do not constrain the rest.

The ESP32's numbering came from KiCad's own `ESP32-S3-MINI-1` symbol rather
than from anyone's memory, and that symbol settles the footprint question too:
it points at `RF_Module:ESP32-S2-MINI-1` itself, because the MINI-1 package is
shared across the family. Two other things that check fixed on the way: the
ESD array is a USON-10, not the SOT-23-6 it had been given, and the IR LED's
pads are numbered like a diode's rather than named A and K.

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
