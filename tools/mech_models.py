#!/usr/bin/env python3
"""Put the cell and the panel (the Displaytech 64128M on this branch) into the
board's 3D view.

    python3 tools/mech_models.py            # write the models and the board
    python3 tools/mech_models.py --check    # print where they go, write nothing
    python3 tools/mech_models.py --panel-only   # just hardware/64128M_on_board.step

Neither part has a vendor STEP: a pouch cell and a glass panel are boxes, so
they are drawn here from the numbers in docs/displaytech-display.md and
docs/top-edge.md. They exist so the board's STEP export carries them into the
case model, and so the 3D viewer shows what sits where.

KiCad has no board-level 3D models, so both hang off TP1 (the faceplate
bond, TP3 on main) as extra models: it is on the front at 0 degrees, so a
model's frame is simply the board's, moved to TP1 and with y turned over.
Nothing about TP1's copper changes. If TP1 ever moves, re-run this and the
models follow.

  - the cell, 55 x 45 x 6 mm, board X 14..69, Y 13..58, on the back
  - the 64128M, upright: glass 75 x 50 at X 0.5..75.5, Y 10.5..60.5 on
    0.2 mm of adhesive, the driver ledge at the bottom, 28 clip pins whose
    legs run 8.0 mm back from the glass, through the board

Needs cadquery.
"""

import argparse
import math
import re
import sys
from pathlib import Path

import cadquery as cq

ROOT = Path(__file__).resolve().parent.parent
PCB = ROOT / "elec" / "layout" / "default" / "default.kicad_pcb"
SHAPES = ROOT / "elec" / "footprints" / "hp42s.3dshapes"
ANCHOR = "TP1"
BOARD_T = 1.6
MODELS = ("Mech_Cell", "Mech_Panel")

# dt branch: the Displaytech 64128M COG (spec v1.0, page 7), upright, pins at
# the bottom. Two 1.1 mm glasses: the back one is 75 x 50 and carries the
# 7 mm ledge at the pin end, with the ST7565R bonded on its front face; the
# front one is 75 x 43. Polarisers fill the rest of the 2.95 max (Displaytech
# does not split it; taken as 0.40 behind, reflector included, and 0.35 in
# front) and stop 0.5 short of the glass edges and 1.3 short of the front
# glass's lower edge, as the drawing shows. Clip pins: a 0.9 wide clip over
# the ledge edge, then a 0.4 x 0.4 leg 0.25 outside it, 8.0 back from the
# back glass's rear face. Seal bump 10 x 1.0 on the left edge.
# ADHESIVE is the allowance for a contact adhesive film between the back
# polariser and the board's front face: 0.20 (tesa 4965 is 0.205).
GLASS = (0.50, 75.50, 10.50, 60.50)          # back glass: X0, X1, Y0, Y1, board mm
FRONT_GLASS = (0.50, 75.50, 10.50, 53.50)
POL = (1.00, 75.00, 11.00, 52.20)
VIEW = (3.00, 73.00, 12.00, 52.00)
ACTIVE = (4.74, 71.26, 15.38, 48.62)
CHIP = (33.20, 42.80, 55.00, 56.40, 0.35)    # ST7565R on the ledge, centred
BUMP = (-0.50, 0.50, 27.00, 37.00)
ADHESIVE = 0.20
BACK_POL_T, GLASS_T1, FRONT_POL_T = 0.40, 1.10, 0.35
PIN_X = [54.645 - 1.27 * k for k in range(28)]   # pin 1 first, at the right
PIN_Y = 60.75
LEG = 0.40
LEG_BACK = 8.0
CELL = (14.0, 69.0, 13.0, 58.0, 6.0)


def anchor(text):
    """TP3's position, which must be on the front at 0 degrees."""
    for f in re.split(r"\n\t\(footprint ", text)[1:]:
        if f'"Reference" "{ANCHOR}"' in f:
            layer = re.search(r'\(layer "([^"]+)"\)', f)[1]
            at = re.search(r"\n\t\t\(at ([^)]+)\)", f)[1].split()
            if layer != "F.Cu" or (len(at) > 2 and float(at[2]) != 0):
                sys.exit(f"{ANCHOR} must be on F.Cu at 0 degrees; it is {layer} {at}")
            return float(at[0]), float(at[1])
    sys.exit(f"no {ANCHOR} on the board")


def box(ax, x0, x1, y0, y1, z0, z1):
    """A box given in BOARD X/Y and model z, placed in the anchor's frame
    (model y is minus footprint y)."""
    fx, fy = ax
    return (cq.Workplane("XY")
            .box(x1 - x0, y1 - y0, z1 - z0, centered=False)
            .translate((x0 - fx, -(y1 - fy), z0)))


def build_panel(ax):
    z0 = ADHESIVE
    z1 = z0 + BACK_POL_T                     # back glass
    z2 = z1 + GLASS_T1                       # front glass, ledge face
    z3 = z2 + GLASS_T1                       # front polariser
    z4 = z3 + FRONT_POL_T
    p = cq.Assembly(name="Mech_Panel")
    p.add(box(ax, *POL, z0, z1), name="back_polariser",
          color=cq.Color(0.55, 0.55, 0.52))
    p.add(box(ax, *GLASS, z1, z2), name="back_glass",
          color=cq.Color(0.86, 0.88, 0.84, 0.6))
    p.add(box(ax, *FRONT_GLASS, z2, z3), name="front_glass",
          color=cq.Color(0.86, 0.88, 0.84, 0.6))
    p.add(box(ax, *POL, z3, z4), name="front_polariser",
          color=cq.Color(0.70, 0.73, 0.65))
    p.add(box(ax, *ACTIVE, z4, z4 + 0.01), name="active_area",
          color=cq.Color(0.45, 0.48, 0.42))
    p.add(box(ax, *VIEW, z4 + 0.005, z4 + 0.008), name="view_area",
          color=cq.Color(0.62, 0.65, 0.58))
    p.add(box(ax, *CHIP[:4], z2, z2 + CHIP[4]), name="st7565r",
          color=cq.Color(0.15, 0.15, 0.17))
    p.add(box(ax, *BUMP, z1 + 0.6, z2 + 0.5), name="seal_bump",
          color=cq.Color(0.9, 0.9, 0.85))
    pins = None
    edge = GLASS[3]
    for x in PIN_X:
        clip = (box(ax, x - 0.45, x + 0.45, edge - 2.40, edge + 0.45, z2, z2 + 0.20)
                .union(box(ax, x - 0.45, x + 0.45, edge - 1.20, edge + 0.45, z1 - 0.20, z1))
                .union(box(ax, x - 0.45, x + 0.45, edge + 0.05, edge + 0.45, z1 - 0.20, z2 + 0.20)))
        leg = box(ax, x - LEG / 2, x + LEG / 2, PIN_Y - LEG / 2, PIN_Y + LEG / 2,
                  z1 - LEG_BACK, z1)
        one = clip.union(leg)
        pins = one if pins is None else pins.union(one)
    p.add(pins, name="clip_pins", color=cq.Color(0.80, 0.80, 0.82))
    return p


def build(ax):
    cell = cq.Assembly(name="Mech_Cell")
    x0, x1, y0, y1, h = CELL
    cell.add(box(ax, x0, x1, y0, y1, -BOARD_T - h, -BOARD_T), name="cell",
             color=cq.Color(0.75, 0.75, 0.78))

    panel = build_panel(ax)
    return {"Mech_Cell": cell, "Mech_Panel": panel}


MODEL_BLOCK = """\t\t(model "${{KIPRJMOD}}/../../footprints/hp42s.3dshapes/{name}.step"
\t\t\t(offset
\t\t\t\t(xyz 0 0 0)
\t\t\t)
\t\t\t(scale
\t\t\t\t(xyz 1 1 1)
\t\t\t)
\t\t\t(rotate
\t\t\t\t(xyz 0 0 0)
\t\t\t)
\t\t)
"""


def attach(text):
    """Add (or refresh) the two model entries on the anchor footprint."""
    parts = re.split(r"(\n\t\(footprint )", text)
    for i in range(2, len(parts), 2):
        f = parts[i]
        if f'"Reference" "{ANCHOR}"' not in f:
            continue
        for name in MODELS:
            f = re.sub(r'\t\t\(model "[^"]*/' + name + r'\.step"[\s\S]*?\n\t\t\)\n', "", f)
        end = f.rindex("\n\t)")
        f = f[:end + 1] + "".join(MODEL_BLOCK.format(name=n) for n in MODELS) + f[end + 1:]
        parts[i] = f
        return "".join(parts)
    sys.exit(f"no {ANCHOR} on the board")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--panel-only", action="store_true")
    args = ap.parse_args()
    if args.panel_only:
        build_panel((0.0, 0.0)).save(str(ROOT / "hardware" / "64128M_on_board.step"))
        print("wrote hardware/64128M_on_board.step")
        return 0
    text = PCB.read_text()
    ax = anchor(text)
    for name, asm in build(ax).items():
        bb = asm.toCompound().BoundingBox()
        print(f"{name:11s} board X {bb.xmin + ax[0]:7.2f}..{bb.xmax + ax[0]:7.2f}  "
              f"Y {ax[1] - bb.ymax:7.2f}..{ax[1] - bb.ymin:7.2f}  "
              f"z {bb.zmin:6.2f}..{bb.zmax:6.2f}")
        if not args.check:
            asm.save(str(SHAPES / f"{name}.step"))
    if not args.check:
        # The same panel in the board's own frame, for the case model: origin
        # at the board's top-left corner on its front face, X right, Y up
        # (so board Y 35 is model Y -35), Z out of the front.
        build_panel((0.0, 0.0)).save(
            str(ROOT / "hardware" / "64128M_on_board.step"))
    if args.check:
        print("--check: nothing written")
        return 0
    PCB.write_text(attach(text))
    print(f"wrote {', '.join(MODELS)} and attached them to {ANCHOR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
