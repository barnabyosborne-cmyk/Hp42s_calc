# What is outstanding before layout

Written 21 September 2026, when Barnaby asked whether anything was still open
on the design side. **Short answer: nothing blocks starting.** The netlist is
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

These change a footprint's shape or its presence on the board, so finding out
afterwards means moving things.

**The slide switch.** `SW39` is a Shouhan MSK-12C02 on KiCad's
`SW_SPDT_Shouhan_MSK12C02`, and that land pattern is doubtful: KiCad puts the
three pads at x = −2.25, +0.75, +2.25, an uneven 3.0 / 1.5 mm spacing that
looks wrong for a 1.5 mm-pitch part, and the vendor drawing is behind a host
this session cannot reach. **The 14 mm bezel makes the C&K JS102011SAQN an
option** — its 8.75 mm courtyard did not fit in 6 mm of board and fits easily
in 12 — and it is the better part: a real detent on the switch you touch every
day, and a land pattern that is not in question. Switching is a one-line change
in `parts.ato` plus a new footprint. Decide now.

**The USB-C receptacle.** The Same Sky UJ20 anchors with through-hole shield
legs. With the receptacle on the front those fillets are on the back, in the
battery bay, which is why the cell has to stay clear of board Y 0 to 5 and why
the bay is 54 mm rather than 57. A receptacle with SMD-only shell tabs removes
the question and gives the cell the whole bay. Different part, different
footprint — so it is a before-layout decision, not an after one.

**`L2`, the panel's 47 µH inductor.** Still on a 3.0 × 3.0 × 1.5 mm stand-in.
The part Solomon Systech name is a Sumida CDRH2D18, which is 3.2 × 3.2 × 2.0.
Not a big difference, but it is inside the panel booster's switching loop,
which is the one cluster on this board where a millimetre matters. Either find
the drawing or leave that cluster 0.5 mm of slack on every side.

**`U4`'s exposed pad.** The MAX17048 datasheet points at Maxim land pattern
90-0065 rather than drawing it, and that document is not in the PDF. KiCad's
generic TDFN-8 2 × 2 mm is almost certainly right — the package code T822 says
8 pins, 2 × 2 mm — but the exposed pad size is the part that varies between
vendors.

## 2. Check before you order boards, not before you place

These are net correctness. They do not change where anything sits.

**Pin numbering that has been confirmed against a datasheet table**, and does
not need looking at again:

| | source |
|---|---|
| `U2` BQ25185 | SLUSF65B table 4-1, from the PDF Barnaby supplied |
| `U1` TPD4E05U06 | SLVSBO7O rev. August 2024, table 4-2 |
| `J1` USB-C | the connector standard; the footprint's pads really are called A1, B5, SH |
| `U5` ESP32-S3-MINI-1 | module pin table. KiCad has no S3-MINI-1 footprint, but its `RF_Module:ESP32-S2-MINI-1` cites the **S3**-MINI-1 datasheet in its own description, so the two share a land pattern |

**Pin numbering that has not:**

| | what is missing |
|---|---|
| `U3` TPS63900 | the footprint is generated from TI's own land pattern, so the pads are right. The assignment of EN / SEL / CFG1-3 / VOUT / LX1 / LX2 / GND / VIN to pin numbers 1-10 has never been read off a drawing |
| `U6` TPS61165 | pin numbers came out of a text extraction of the pin-functions table, not the package drawing |

`ti.com`, `analog.com`, `mouser.com` and Espressif are all blocked from this
session's network policy, and the HTML datasheet mirrors that do work do not
carry the pinout pages. So these two close the moment you drop the PDFs in the
thread, the way you did with the panel spec and the BQ25185, and not before.

**The fuel gauge's I²C levels.** `U4` runs off the cell rather than the 3.3 V
rail, so its SDA/SCL sit on a 4.2 V part with 3.3 V pull-ups. Its input
thresholds are fixed rather than VDD-referenced, so this should be fine — read
the DC table and confirm.

## 3. Things only you can measure

**The panel's tail.** This is the highest-risk item on the page and it is not
close. The drawing gives 14.30 mm ± 0.3, the fold eats 3.30, and the
connector's pad row has to land inside the last 3 mm of what is left. There is
no slack at all: 0.3 mm short and the flex does not reach the contacts. Measure
a real panel before you commit the board.

**Which leg of the power slider is the wiper.** Needs a meter. The netlist
assumes pin 2 is common.

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
