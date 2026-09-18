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

## 3. Place the keypad

Tools → Scripting Console:

```python
exec(open('tools/place_keypad.py').read())
```

## One substitution to check before fab

`U5` uses `RF_Module:ESP32-S2-MINI-1`, because KiCad ships no
ESP32-S3-MINI-1 footprint. The MINI-1 module package is shared across the
family and it should be identical, but check the pad table in the S3-MINI-1
datasheet against it before you order boards. A module that does not fit its
land pattern is an expensive way to learn this.
