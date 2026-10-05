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

  - the cell, 50 x 38 x 6 mm, board X 5..55, Y 12.5..50.5, on the back
  - the LS027 glass, 62.80 x 42.82 x 1.65 on 0.2 mm of adhesive, X 6.6..69.4,
    Y 7.50..50.32, with the active area as a dark inlay on its face
  - the FPC, 9.47 wide and 0.30 thick, down through the slot into J2 on the
    back, back leg ending at Y 61.0

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

# ls027 branch: the Sharp LS027B7DH01 (LD-28305A page 24), landscape, FPC
# off the bottom long edge. Glass 62.8 x 42.82 x 1.65, centred across the
# board at X 6.6..69.4, Y 7.50..50.32. Active area 58.8 x 35.28, centred
# along the length, 2.0 from the top edge and 5.54 from the FPC edge. FPC
# 9.47 wide, centred, folds through the slot at Y 51.2..52.9 to J2 on the
# back at Y 59.9. ADHESIVE as before. The cell is the 6 x 38 x 50 the bay
# takes. The Azumo front light is not drawn; its STEP is in the project
# files (outputs/display-options).
ADHESIVE = 0.20
GLASS = (6.60, 69.40, 7.50, 50.32)
GLASS_T = 1.65
ACTIVE = (8.60, 67.40, 9.50, 44.78)
TAIL_X = (33.265, 42.735)
TAIL_T = 0.30
SLOT_Y = 52.05                                 # centre of the FPC slot
TAIL_END_Y = 61.0                              # back leg ends in J2's mouth
CELL = (5.0, 55.0, 12.5, 50.5, 6.0)


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
    """The FPC: off the glass's bottom edge, down through the slot and along
    the back into J2, as three flat pieces."""
    x0, x1 = TAIL_X
    top = ADHESIVE + 0.7
    bot = -BOARD_T
    front = box(ax, x0, x1, GLASS[3] - 1.0, SLOT_Y + TAIL_T / 2, top - TAIL_T, top)
    down = box(ax, x0, x1, SLOT_Y - TAIL_T / 2, SLOT_Y + TAIL_T / 2, bot - TAIL_T, top)
    back = box(ax, x0, x1, SLOT_Y - TAIL_T / 2, TAIL_END_Y, bot - TAIL_T, bot)
    return front.union(down).union(back)


def build(ax):
    cell = cq.Assembly(name="Mech_Cell")
    x0, x1, y0, y1, h = CELL
    cell.add(box(ax, x0, x1, y0, y1, -BOARD_T - h, -BOARD_T), name="cell",
             color=cq.Color(0.75, 0.75, 0.78))

    panel = cq.Assembly(name="Mech_Panel")
    panel.add(box(ax, *GLASS, ADHESIVE, ADHESIVE + GLASS_T), name="glass",
              color=cq.Color(0.86, 0.86, 0.82))
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
            str(ROOT / "hardware" / "LS027B7DH01_on_board.step"))
    if args.check:
        print("--check: nothing written")
        return 0
    PCB.write_text(attach(text))
    print(f"wrote {', '.join(MODELS)} and attached them to {ANCHOR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
