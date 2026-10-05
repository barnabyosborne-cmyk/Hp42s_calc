#!/usr/bin/env python3
"""Put the cell and the panel (the LS027 + Azumo front light on this branch)
into the board's 3D view.

    python3 tools/mech_models.py            # write the models and the board
    python3 tools/mech_models.py --check    # print where they go, write nothing

The panel is Azumo's own STEP for the FLP 11103-06 front light on the Sharp
LS027B7DH01 (elec/footprints/vendor-3d/Azumo-FLP-11103-06-LS027B7DH01.step,
Barnaby's copy, 4 October 2026): glass and flat FPC, light guide, film
carrier, film roll, adhesive, and the light coupler with its LED flex. It is
turned into the board's frame here, the flat panel FPC is cut off past the
glass and drawn folded through the slot into J2 instead, and the LED flex
lies along the back as Azumo drew it. The pouch cell has no vendor model and
is a box.

KiCad has no board-level 3D models, so both hang off TP1 as extra models:
TP1 is on the front at 0 degrees, so a model's frame is simply the board's,
moved to TP1 and with y turned over. Nothing about TP1's copper changes. If
TP1 ever moves, re-run this and the models follow.

  - the cell, 50 x 40 x 6 mm (604050), board X 5.5..55.5, Y 10.5..50.5,
    on the back
  - the panel, glass X 6.6..69.4, Y 7.50..50.32 on 0.2 mm of adhesive, the
    coupler down through its cut-out, the LED flex on the back to Y 78.1
  - the panel FPC, 9.47 wide and 0.10 thick, down through the slot into J2
    on the back, back leg ending at Y 61.0

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

# ls027 branch: the Sharp LS027B7DH01 (LD-28305A page 24) under Azumo's
# FLP 11103-06, landscape, FPC off the bottom long edge, glass centred across
# the board at X 6.6..69.4, Y 7.50..50.32. Azumo's STEP is in its own frame;
# AZ_T takes it to the board's (x right, y = -board Y, z out of the front
# face): board X = 48.18 - z_az, -board Y = x_az + 0.87, z = -y_az - 12.61.
# That puts the glass's back on 0.20 mm of adhesive (ADHESIVE). Its LED flex
# was drawn for a 1.51 mm board, so that one solid drops a further 0.09 to
# lie on this 1.6 mm one. The cell is the 6 x 40 x 50 the bay takes.
AZUMO = ROOT / "elec" / "footprints" / "vendor-3d" / "Azumo-FLP-11103-06-LS027B7DH01.step"
AZ_T = ((0, 0, -1, 48.18), (1, 0, 0, 0.87), (0, -1, 0, -12.61))
AZ_PARTS = [  # solid index in Azumo's file, name, colour, extra z
    (0, "glass_fpc", (0.55, 0.60, 0.62), 0.0),
    (1, "light_guide", (0.80, 0.90, 0.95), 0.0),
    (2, "film_carrier", (0.75, 0.85, 0.90), 0.0),
    (3, "coupler_led_flex", (0.95, 0.95, 0.95), -(BOARD_T - 1.51)),
    (4, "film_roll", (0.85, 0.70, 0.30), 0.0),
    (5, "adhesive", (0.30, 0.30, 0.30), 0.0),
]
ADHESIVE = 0.20
GLASS = (6.60, 69.40, 7.50, 50.32)
FPC_CUT_Y = 50.92                              # flat FPC cut here, folded below
TAIL_X = (33.27, 42.74)
TAIL_Z = (1.008, 1.108)                        # the flat FPC in Azumo's STEP
SLOT_Y = 52.05                                 # centre of the FPC slot
TAIL_END_Y = 61.0                              # back leg ends in J2's mouth
CELL = (5.5, 55.5, 10.5, 50.5, 6.0)


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
    """The panel FPC: from where Azumo's flat one is cut, down through the
    slot and along the back into J2, as three flat pieces."""
    x0, x1 = TAIL_X
    z0, top = TAIL_Z
    t = top - z0
    bot = -BOARD_T
    front = box(ax, x0, x1, FPC_CUT_Y, SLOT_Y + t / 2, z0, top)
    down = box(ax, x0, x1, SLOT_Y - t / 2, SLOT_Y + t / 2, bot - t, top)
    back = box(ax, x0, x1, SLOT_Y - t / 2, TAIL_END_Y, bot - t, bot)
    return front.union(down).union(back)


def azumo(ax):
    """Azumo's solids in the anchor's frame, the flat FPC cut off."""
    from OCP.gp import gp_Trsf
    from OCP.TopLoc import TopLoc_Location
    fx, fy = ax
    solids = cq.importers.importStep(str(AZUMO)).solids().vals()
    out = []
    for i, name, colour, dz in AZ_PARTS:
        (a, b, c, d), (e, f, g, h), (k, m, n, o) = AZ_T
        t = gp_Trsf()
        t.SetValues(a, b, c, d - fx, e, f, g, h + fy, k, m, n, o + dz)
        s = cq.Shape.cast(solids[i].wrapped.Moved(TopLoc_Location(t)))
        if name == "glass_fpc":
            s = s.intersect(box(ax, -10, 90, 0, FPC_CUT_Y, -10, 10).val())
        out.append((name, s, colour))
    return out


def build(ax):
    cell = cq.Assembly(name="Mech_Cell")
    x0, x1, y0, y1, h = CELL
    cell.add(box(ax, x0, x1, y0, y1, -BOARD_T - h, -BOARD_T), name="cell",
             color=cq.Color(0.75, 0.75, 0.78))

    panel = cq.Assembly(name="Mech_Panel")
    for name, s, colour in azumo(ax):
        panel.add(s, name=name, color=cq.Color(*colour))
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
