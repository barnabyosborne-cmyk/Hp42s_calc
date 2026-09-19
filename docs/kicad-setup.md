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

That puts the 38 dome sites on the measured grid, flips USB-C, the power
slider and the reset button onto the back at the top edge, and draws the
76 × 144 outline if Edge.Cuts is empty. See `docs/top-edge.md`.

## Before you route: five parts have no pin numbers yet

This is the thing to know before you start pulling ratsnest lines.

KiCad matches a netlist pin to a footprint pad **by name**. Most of this
board's parts declare their pins by the name the datasheet uses — `pin IN`,
`pin IO33` — which is deliberate, because inventing pin numbers from memory is
how you buy a board that does not work. The cost is that a pin called `IO33`
matches no pad on a footprint whose pads are called `1` to `65`. Those nets
import silently unconnected.

Right now these are **correct and fully connected**:

| | |
|---|---|
| all 38 dome sites | pads 1 and 2 |
| every resistor, capacitor, inductor | pads 1 and 2 |
| diodes, FETs | SOT-23 / SOD-123 numbering |
| the e-paper FPC connector `J2` | all 24 pins, from the panel spec |
| USB-C `J1` | A1…B12 and SH, the USB-C contact names, which are what this footprint calls its pads |
| both top-edge switches | pads 1/2/3, MP, SH |

These are **not**, and will show as unconnected:

| | |
|---|---|
| `U5` ESP32-S3-MINI-1 | needs the module's 1…65 pin table |
| `U2` BQ25185 | needs the WSON-10 numbering |
| `U3` TPS63900 | no footprint at all yet |
| `U4` MAX17048 | no footprint at all yet |
| `U1` TPD4E05U06 | needs the SOT-23-6 numbering |

So the ratsnest you see after import is the keypad, the panel, the panel's
booster, USB and the passives — real and routable — plus five parts floating
free. Do not start routing around `U5` until its numbering lands.

## Things to check before fab

**`U5` footprint.** It uses `RF_Module:ESP32-S2-MINI-1`, because KiCad ships no
ESP32-S3-MINI-1 footprint. The MINI-1 module package is shared across the
family and it should be identical, but check the pad table in the S3-MINI-1
datasheet against it before you order boards. A module that does not fit its
land pattern is an expensive way to learn this.

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
