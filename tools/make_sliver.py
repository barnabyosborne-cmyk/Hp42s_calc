#!/usr/bin/env python3
"""Write the frontlight sliver: its own board, elec/layout/sliver/.

    python3 tools/make_sliver.py

The sliver is `FrontlightStrip` in elec/src/frontlight.ato: four Dialight
599-2Q01-147F white LEDs in series, on a 1.0 mm FR4 strip lying on the main
board between the panel and the keyboard, looking into the light guide's edge.

WHY IT IS ITS OWN BOARD. It is 1.0 mm thick with copper on one face; the main
board is 1.6 mm with four layers. A fab builds each order to one thickness and
one stack-up, so the two cannot share a panel. Order them separately.

THE GEOMETRY, all from docs/front-face.md:

  - 64 x 4 mm. The guide is about 60 mm across its injection edge, so the
    sliver overhangs it by 2 mm at each end, and the two wire pads go on that
    overhang (settled 27 September 2026, option 2).
  - Four LEDs on a 15 mm pitch at 7.5, 22.5, 37.5 and 52.5 mm across the 60 mm
    edge, which is 9.5, 24.5, 39.5 and 54.5 mm along the sliver.
  - The lens faces -y in the footprint, and it is placed flush with the
    sliver's top edge (y 0), which is the edge that faces the guide.
  - The string runs FL+ (TP1, `vled` on the main board) -> D1 -> D2 -> D3 ->
    D4 -> FL- (TP2, `fb`), on F.Cu alone. B.Cu is empty.

Nothing here is reflowed at the fab: the four LEDs and two wires are
hand-soldered, so the wire pads have no paste. The LEDs keep their paste
apertures in case a stencil is ever used.

Rewrites the board every time; there is nothing on it to preserve.
"""

import json
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "elec/layout/sliver"
NS = uuid.UUID("9a3c17be-0000-4000-8000-00000000511e")

LENGTH, DEPTH = 64.0, 4.0
LED_X = [9.5, 24.5, 39.5, 54.5]
LENS = 1.57          # footprint origin to the front of the lens, in -y
LED_Y = LENS         # so the lens sits on the top edge
TRACK_W = 0.4        # 20 mA at most; 0.4 because there is room
PAD_W, PAD_H = 1.5, 3.0
PAD_X = [1.0, LENGTH - 1.0]
PAD_Y = DEPTH / 2
THICKNESS = 1.0


def uid(*parts):
    return str(uuid.uuid5(NS, " ".join(str(p) for p in parts)))


def f(v):
    return f"{v:.4f}".rstrip("0").rstrip(".")


def prop(ref, name, value, at, layer, hide=False, size=0.8):
    return (f'\t\t(property "{name}" "{value}"\n'
            f'\t\t\t(at {f(at[0])} {f(at[1])} 0)\n'
            f'\t\t\t(layer "{layer}")\n'
            + ('\t\t\t(hide yes)\n' if hide else '')
            + f'\t\t\t(uuid "{uid(ref, name)}")\n'
            f'\t\t\t(effects (font (size {f(size)} {f(size)}) (thickness 0.12)))\n'
            '\t\t)\n')


def pad(ref, num, shape, at, size, layers, net, rratio=None):
    s = (f'\t\t(pad "{num}" smd {shape}\n'
         f'\t\t\t(at {f(at[0])} {f(at[1])})\n'
         f'\t\t\t(size {f(size[0])} {f(size[1])})\n'
         f'\t\t\t(layers {layers})\n')
    if rratio is not None:
        s += f'\t\t\t(roundrect_rratio {rratio})\n'
    if net:
        s += f'\t\t\t(net "{net}")\n'
    return s + f'\t\t\t(uuid "{uid(ref, "pad", num)}")\n\t\t)\n'


def graphic(ref, kind, a, b, layer, width, n):
    return (f'\t\t({kind} (start {f(a[0])} {f(a[1])}) (end {f(b[0])} {f(b[1])})\n'
            f'\t\t\t(stroke (width {width}) (type solid))\n'
            + ('\t\t\t(fill no)\n' if kind == "fp_rect" else '')
            + f'\t\t\t(layer "{layer}")\n'
            f'\t\t\t(uuid "{uid(ref, kind, n)}")\n\t\t)\n')


def led(ref, x, anode, cathode):
    """hp42s:Dialight_599_White_1208_RA: pad 2 anode (left), pad 1 cathode
    (right), pad 3 a mechanical anchor with nothing bonded to it."""
    s = (f'\t(footprint "hp42s:Dialight_599_White_1208_RA"\n'
         f'\t\t(layer "F.Cu")\n\t\t(uuid "{uid(ref)}")\n'
         f'\t\t(at {f(x)} {f(LED_Y)})\n'
         '\t\t(descr "Dialight 599 series MicroLED, single-colour 1208 right angle. '
         'Pad 2 anode, pad 1 cathode, pad 3 mechanical. Lens faces -y.")\n')
    s += prop(ref, "Reference", ref, (0, 2.3), "F.Fab")
    s += prop(ref, "Value", "599-2Q01-147F", (0, 3.2), "F.Fab", hide=True)
    s += '\t\t(attr smd)\n'
    s += graphic(ref, "fp_rect", (-1.5, -0.5), (1.5, 0.5), "F.Fab", 0.1, 1)
    s += graphic(ref, "fp_rect", (-2.25, -1.82), (2.25, 1.4), "F.CrtYd", 0.05, 2)
    # cathode mark, right of pad 1, as on the library footprint
    s += graphic(ref, "fp_line", (2.15, -0.75), (2.15, 0.75), "F.SilkS", 0.15, 3)
    s += pad(ref, 2, "roundrect", (-1.5, 0), (1.0, 1.5),
             '"F.Cu" "F.Paste" "F.Mask"', anode, 0.15)
    s += pad(ref, 1, "roundrect", (1.5, 0), (1.0, 1.5),
             '"F.Cu" "F.Paste" "F.Mask"', cathode, 0.15)
    s += pad(ref, 3, "roundrect", (0, 0.815), (0.9, 0.65),
             '"F.Cu" "F.Paste" "F.Mask"', None, 0.15)
    s += ('\t\t(model "${KIPRJMOD}/../../footprints/hp42s.3dshapes/'
          'Dialight_599_White_1208_RA.step"\n'
          '\t\t\t(offset (xyz 0 0 0))\n\t\t\t(scale (xyz 1 1 1))\n'
          '\t\t\t(rotate (xyz 0 0 0))\n\t\t)\n')
    return s + '\t\t(embedded_fonts no)\n\t)\n'


def wire_pad(ref, x, net, label):
    s = (f'\t(footprint "hp42s:Frontlight_SliverWirePad"\n'
         f'\t\t(layer "F.Cu")\n\t\t(uuid "{uid(ref)}")\n'
         f'\t\t(at {f(x)} {f(PAD_Y)})\n'
         '\t\t(descr "Where a 30 AWG wire from the main board lands. On the '
         '2 mm of sliver that overhangs the light guide, so the joint is '
         'clear of it. Hand soldered: no paste.")\n')
    s += prop(ref, "Reference", ref, (0, -2.4), "F.Fab")
    s += prop(ref, "Value", label, (0, 2.4), "F.Fab", hide=True)
    s += '\t\t(attr smd)\n'
    s += graphic(ref, "fp_rect", (-0.85, -1.6), (0.85, 1.6), "F.CrtYd", 0.05, 1)
    s += pad(ref, 1, "rect", (0, 0), (PAD_W, PAD_H), '"F.Cu" "F.Mask"', net)
    return s + '\t\t(embedded_fonts no)\n\t)\n'


def segment(net, a, b):
    return (f'\t(segment\n\t\t(start {f(a[0])} {f(a[1])})\n'
            f'\t\t(end {f(b[0])} {f(b[1])})\n\t\t(width {TRACK_W})\n'
            f'\t\t(layer "F.Cu")\n\t\t(net "{net}")\n'
            f'\t\t(uuid "{uid("seg", net, a, b)}")\n\t)\n')


def gr_line(a, b, layer, width, n):
    return (f'\t(gr_line\n\t\t(start {f(a[0])} {f(a[1])})\n'
            f'\t\t(end {f(b[0])} {f(b[1])})\n'
            f'\t\t(stroke (width {width}) (type solid))\n'
            f'\t\t(layer "{layer}")\n\t\t(uuid "{uid("gr", n)}")\n\t)\n')


def gr_text(text, at, n, size=0.8):
    return (f'\t(gr_text "{text}"\n\t\t(at {f(at[0])} {f(at[1])} 0)\n'
            f'\t\t(layer "F.SilkS")\n\t\t(uuid "{uid("txt", n)}")\n'
            f'\t\t(effects (font (size {f(size)} {f(size)}) (thickness 0.12)))\n\t)\n')


HEADER = f'''(kicad_pcb
\t(version 20260206)
\t(generator "make_sliver.py")
\t(generator_version "10.0")
\t(general
\t\t(thickness {THICKNESS})
\t\t(legacy_teardrops no)
\t)
\t(paper "A4")
\t(layers
\t\t(0 "F.Cu" signal)
\t\t(2 "B.Cu" signal)
\t\t(9 "F.Adhes" user "F.Adhesive")
\t\t(11 "B.Adhes" user "B.Adhesive")
\t\t(13 "F.Paste" user)
\t\t(15 "B.Paste" user)
\t\t(5 "F.SilkS" user "F.Silkscreen")
\t\t(7 "B.SilkS" user "B.Silkscreen")
\t\t(1 "F.Mask" user)
\t\t(3 "B.Mask" user)
\t\t(17 "Dwgs.User" user "User.Drawings")
\t\t(19 "Cmts.User" user "User.Comments")
\t\t(25 "Edge.Cuts" user)
\t\t(27 "Margin" user)
\t\t(31 "F.CrtYd" user "F.Courtyard")
\t\t(29 "B.CrtYd" user "B.Courtyard")
\t\t(35 "F.Fab" user)
\t\t(33 "B.Fab" user)
\t)
\t(setup
\t\t(stackup
\t\t\t(layer "F.SilkS" (type "Top Silk Screen"))
\t\t\t(layer "F.Paste" (type "Top Solder Paste"))
\t\t\t(layer "F.Mask" (type "Top Solder Mask") (thickness 0.01))
\t\t\t(layer "F.Cu" (type "copper") (thickness 0.035))
\t\t\t(layer "dielectric 1" (type "core") (thickness 0.91) (material "FR4")
\t\t\t\t(epsilon_r 4.5) (loss_tangent 0.02))
\t\t\t(layer "B.Cu" (type "copper") (thickness 0.035))
\t\t\t(layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.01))
\t\t\t(layer "B.Paste" (type "Bottom Solder Paste"))
\t\t\t(layer "B.SilkS" (type "Bottom Silk Screen"))
\t\t\t(copper_finish "None")
\t\t\t(dielectric_constraints no)
\t\t)
\t\t(pad_to_mask_clearance 0)
\t\t(allow_soldermask_bridges_in_footprints no)
\t)
'''


def board():
    nets = ["vled", "n1", "n2", "n3", "fb"]
    body = [HEADER]
    body.append(wire_pad("TP1", PAD_X[0], "vled", "FL+"))
    for k, x in enumerate(LED_X):
        body.append(led(f"D{k + 1}", x, nets[k], nets[k + 1]))
    body.append(wire_pad("TP2", PAD_X[1], "fb", "FL-"))

    # The string, along the LEDs' own pad line. Each hop goes from one LED's
    # cathode (x + 1.5) to the next one's anode (x - 1.5).
    ends = [PAD_X[0]] + [c for x in LED_X for c in (x - 1.5, x + 1.5)] + [PAD_X[1]]
    for k in range(5):
        body.append(segment(nets[k], (ends[2 * k], LED_Y), (ends[2 * k + 1], LED_Y)))

    corners = [(0, 0), (LENGTH, 0), (LENGTH, DEPTH), (0, DEPTH)]
    for k in range(4):
        body.append(gr_line(corners[k], corners[(k + 1) % 4], "Edge.Cuts", 0.05, k))

    body.append(gr_text("FL+", (4.5, 3.1), 1))
    body.append(gr_text("FL-", (LENGTH - 4.5, 3.1), 2))
    body.append(gr_text("LED EDGE ^", (17.0, 3.1), 3))
    body.append(gr_text("HP42S FL A", (47.0, 3.1), 4))
    return "".join(body) + "\t(embedded_fonts no)\n)\n"


def project():
    src = json.loads((ROOT / "elec/layout/default/default.kicad_pro").read_text())
    src["meta"]["filename"] = "sliver.kicad_pro"
    src["boards"] = []
    src["sheets"] = []
    return json.dumps(src, indent=2) + "\n"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "sliver.kicad_pcb").write_text(board())
    (OUT / "sliver.kicad_pro").write_text(project())
    (OUT / "fp-lib-table").write_text(
        (ROOT / "elec/layout/default/fp-lib-table").read_text())
    print(f"wrote {OUT.relative_to(ROOT)}/sliver.kicad_pcb, "
          f"{LENGTH:g} x {DEPTH:g} mm, {THICKNESS} mm thick")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
