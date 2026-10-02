#!/usr/bin/env python3
"""Put the cell and the panel (the LS032 on this branch) into the board's 3D view.

    python3 tools/mech_models.py            # write the models and the board
    python3 tools/mech_models.py --check    # print where they go, write nothing

Neither part has a vendor STEP: a pouch cell and a glass panel are boxes, so
they are drawn here from the numbers in docs/display-mounting.md and
docs/top-edge.md. They exist so the board's STEP export carries them into the
case model, and so the 3D viewer shows what sits where.

KiCad has no board-level 3D models, so both hang off TP1 as extra models:
TP1 is on the front at 0 degrees, so a model's frame is simply the board's,
moved to TP1 and with y turned over. Nothing about TP1's copper changes. If
TP1 ever moves, re-run this and the models follow.

  - the cell, 55 x 45 x 6 mm, board X 14..69, Y 13..58, on the back
  - the panel glass, 71.82 x 36.30 x 1.0 on 0.1 mm of adhesive, X 0.55..72.37,
    Y 12.00..48.30, with the active area as a dark inlay on its face
  - the flex tail, 12.50 wide and 0.30 thick, folded round the left edge at a
    1.05 mm radius into J2 on the back, back leg ending at X 10.50

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

# MIP branch: the Sharp LS032B7DD02 (spec LD-2023X13 page 60), landscape,
# tail to the left. TFT glass 76.00 x 47.02 at X 0.00..76.00, flush with
# both long edges of the board (Barnaby, 1 October 2026), Y 7.50..54.52
# (9.5 mm top bezel in the 150 case, 2 October 2026). Stack, bottom up:
# bottom polariser 0.115, TFT glass 0.2, CF glass 0.2, top polariser 0.19,
# 0.705 in all. The CF glass and both polarisers are 73.2 x 46.02, 0.5 in
# from the far end and the long edges, leaving a 2.3 mm TFT-glass ledge at the
# tail end where the flex is bonded on top. (The bottom polariser's outline is
# not drawn by Sharp; taken as the top one's.) Active area 68.072 x 42.672,
# centred 39.784 from the tail-end edge and on the glass's height. Tail 9.47
# wide on Y 31.01, 0.3 thick, leaving the ledge at the TFT glass's top face;
# the half turn is centred on X -0.80, 0.8 beyond the glass (Sharp's nearest
# bend), so it stands out past the board edge and the case has a pocket for
# it. Back leg ends 2.9 inside J2's mouth at X 3.35. (main: the e-paper's.)
# ADHESIVE is the allowance for a contact adhesive film between the bottom
# polariser and the board's front face: 0.20 (tesa 4965 is 0.205).
GLASS = (0.00, 76.00, 7.50, 54.52)          # TFT glass: X0, X1, Y0, Y1, board mm
POL = (0.00 + 2.3, 76.00 - 0.5, 8.00, 54.02)   # 2.30..75.50
ACTIVE = (5.748, 73.820, 9.674, 52.346)
ADHESIVE = 0.20
BOT_POL_T, TFT_T, CF_T, TOP_POL_T = 0.115, 0.2, 0.2, 0.19
GLASS_T = BOT_POL_T + TFT_T + CF_T + TOP_POL_T   # 0.705
LEDGE_Z = ADHESIVE + BOT_POL_T + TFT_T           # top of the TFT glass
TAIL_Y = (26.275, 35.745)
TAIL_T = 0.30
TAIL_END_X = 6.25                             # back leg ends here, in J2
BEND_X = -0.80                                 # centre of the half turn
CELL = (14.0, 69.0, 13.0, 58.0, 6.0)


def anchor(text):
    """TP1's position, which must be on the front at 0 degrees."""
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


def tail(ax):
    """The flex: a stub out of the glass, a half turn round the board edge
    and the back leg into J2, as one bent sheet."""
    fx, fy = ax
    y0, y1 = TAIL_Y
    top = LEDGE_Z + TAIL_T                   # front leg, on the TFT glass ledge
    bot = -BOARD_T                           # back leg, against the back face
    zc = (top - TAIL_T + bot) / 2            # centre of the bend
    r_in = (top - TAIL_T - bot) / 2
    r_out = r_in + TAIL_T
    xc = BEND_X
    front = box(ax, xc, GLASS[0] + 1.5, y0, y1, top - TAIL_T, top)
    back = box(ax, xc, TAIL_END_X, y0, y1, bot - TAIL_T, bot)
    ring = cq.Workplane("XZ").circle(r_out).circle(r_in).extrude(-(y1 - y0))
    keep = cq.Workplane("XZ").rect(r_out, 2 * r_out, centered=(False, True)) \
        .extrude(-(y1 - y0)).translate((-r_out, 0, 0))
    bend = ring.intersect(keep).translate((xc - fx, -(y1 - fy), zc))
    return front.union(back).union(bend)


def build(ax):
    cell = cq.Assembly(name="Mech_Cell")
    x0, x1, y0, y1, h = CELL
    cell.add(box(ax, x0, x1, y0, y1, -BOARD_T - h, -BOARD_T), name="cell",
             color=cq.Color(0.75, 0.75, 0.78))

    panel = cq.Assembly(name="Mech_Panel")
    z = ADHESIVE
    panel.add(box(ax, *POL, z, z + BOT_POL_T), name="bottom_polariser",
              color=cq.Color(0.30, 0.30, 0.30))
    z += BOT_POL_T
    panel.add(box(ax, *GLASS, z, z + TFT_T), name="tft_glass",
              color=cq.Color(0.86, 0.86, 0.82))
    z += TFT_T
    panel.add(box(ax, *POL, z, z + CF_T + TOP_POL_T), name="cf_glass_top_polariser",
              color=cq.Color(0.80, 0.82, 0.80))
    panel.add(box(ax, *ACTIVE, ADHESIVE + GLASS_T, ADHESIVE + GLASS_T + 0.01),
              name="active_area", color=cq.Color(0.25, 0.25, 0.28))
    panel.add(tail(ax), name="flex_tail", color=cq.Color(0.85, 0.55, 0.15))
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
    args = ap.parse_args()
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
        build((0.0, 0.0))["Mech_Panel"].save(
            str(ROOT / "hardware" / "LS032B7DD02_on_board.step"))
    if args.check:
        print("--check: nothing written")
        return 0
    PCB.write_text(attach(text))
    print(f"wrote {', '.join(MODELS)} and attached them to {ANCHOR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
