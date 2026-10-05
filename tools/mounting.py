#!/usr/bin/env python3
"""The case's screw holes.

    python3 tools/mounting.py            # write them into the board
    python3 tools/mounting.py --check    # list them and what they would hit

Barnaby's choice, 27 September 2026: screws at the four corners and one in
the middle of the numeric block, where the board would otherwise flex most
under a keypress. G was first drawn at (38.25, 80), but the cell's `bat`
line crosses the keyboard on F.Cu along y 80.5, so it moved to (45.75, 116),
the same kind of four-key gap. POSTS is kept for pads a case post bears on
without a screw; there are none now.

  - A hole is a circle on Edge.Cuts, which the fab mills as an unplated
    hole, inside a rule area on every layer: no tracks, no vias, no pour, so
    the head and the boss sit on bare laminate and the hole cuts no plane.
  - A post pad is a rule area on both outer layers with no tracks and no
    vias, keeping its ground pour.

Every one is a board-level item, not a footprint, so a netlist re-import
never deletes it. Re-running replaces them, found by name. Run the routers
after this: every one of them honours rule areas.
"""

import argparse
import math
import re
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from variant import drop    # noqa: E402  the MIP branch's taller board
import variant              # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PCB = ROOT / "elec" / "layout" / "default" / "default.kicad_pcb"
NS = uuid.UUID("5c1e4a9e-8d37-4f0b-9a55-2b1d0a7c6e42")

# name: (x, y, hole diameter, clear diameter). M2 is a 2.2 mm hole and wants
# 4.5 mm clear for a 3.8 mm head; G sits where four keys meet, which is only
# 4.1 mm across, so it is an M1.6 (1.7 mm hole, 3.0 mm head).
#
# The corner pairs mirror about the board's centreline, x = 38, which is the
# case's too (case x = board x + 2 on an 80 mm case). Barnaby asked for that on
# 27 September 2026 so rubber feet in the rear case line up. RESET sets B's
# y and the antenna keepout and bottom-row domes set D's x; A and C follow.
HOLES = {
    # Up to Y 3.5 (dt 1 October, mip 2 October 2026) so the glass can start
    # high. B sits in the 5 mm between the two side buttons, so both take C
    # and D's 4.5 mm ring, and A mirrors it.
    "A": (10.0, 3.5, 2.2, 4.5),      # top left, level with B
    "B": (66.0, 3.5, 2.2, 4.5),      # top right, between RESET and BOOT
    "C": (6.0, 141.5, 2.2, 4.5),     # bottom left, D mirrored
    "D": (70.0, 141.5, 2.2, 4.5),    # bottom right, the tightest corner
    "G": (38.25, 80.0, 1.7, 4.0),    # centre of the keypad, where four keys meet
    # ls027, 5 October 2026: Barnaby's board-to-front-shell screws, so the
    # PCB is held to the front first and the corners only join the shells.
    # Mirrored about x = 38. E/F beside the glass's top corners (M2, room
    # to spare). H/I in the four-key gaps of the top two rows, whose centres
    # mirror exactly (13.0 / 63.0). J/K between the bottom two rows, where
    # the gaps are at 14.875 and 60.5 and do not mirror, so each is 0.31
    # off its gap's centre. All y here are e-paper y (board y + 2 below 48.3).
    "E": (3.3, 9.0, 2.2, 4.5),       # left of the glass's top corner
    "F": (72.7, 9.0, 2.2, 4.5),      # right of it
    "H": (13.0, 68.0, 1.7, 4.0),     # SW1 / SW2 / SW7 / SW8
    "I": (63.0, 68.0, 1.7, 4.0),     # SW5 / SW6 / SW11 / SW12
    "J": (15.19, 128.0, 1.7, 4.0),   # SW28 / SW29 / SW33 / SW34
    "K": (60.81, 128.0, 1.7, 4.0),   # SW31 / SW32 / SW36 / SW37
}
HOLES = {k: (x, drop(y), d, keep) for k, (x, y, d, keep) in HOLES.items()}
POSTS = {}
POST_D = 4.0


def circle(x, y, d, n=16):
    r = d / 2 / math.cos(math.pi / n)     # the polygon contains the circle
    return [(round(x + r * math.cos(2 * math.pi * (k + .5) / n), 4),
             round(y + r * math.sin(2 * math.pi * (k + .5) / n), 4)) for k in range(n)]


def zone(name, pts, layers, pour):
    xy = " ".join(f"(xy {a} {b})" for a, b in pts)
    lay = " ".join(f'"{l}"' for l in layers)
    return f"""\t(zone
\t\t(layers {lay})
\t\t(uuid "{uuid.uuid5(NS, name)}")
\t\t(name "{name}")
\t\t(hatch edge 0.5)
\t\t(connect_pads
\t\t\t(clearance 0)
\t\t)
\t\t(min_thickness 0.25)
\t\t(keepout
\t\t\t(tracks not_allowed)
\t\t\t(vias not_allowed)
\t\t\t(pads allowed)
\t\t\t(copperpour {"allowed" if pour else "not_allowed"})
\t\t\t(footprints allowed)
\t\t)
\t\t(placement
\t\t\t(enabled no)
\t\t\t(sheetname "")
\t\t)
\t\t(fill
\t\t\t(thermal_gap 0.5)
\t\t\t(thermal_bridge_width 0.5)
\t\t\t(island_removal_mode 0)
\t\t)
\t\t(polygon
\t\t\t(pts
\t\t\t\t{xy}
\t\t\t)
\t\t)
\t)
"""


def hole(name, x, y, d):
    return f"""\t(gr_circle
\t\t(center {x} {y})
\t\t(end {x + d / 2} {y})
\t\t(stroke
\t\t\t(width 0.05)
\t\t\t(type solid)
\t\t)
\t\t(fill no)
\t\t(layer "Edge.Cuts")
\t\t(uuid "{uuid.uuid5(NS, name)}")
\t)
"""


def items():
    out = []
    for k, (x, y, d, keep) in HOLES.items():
        out.append(hole(f"mounting hole {k}", x, y, d))
        out.append(zone(f"mounting hole {k} keepout", circle(x, y, keep),
                        ["F.Cu", "B.Cu", "In1.Cu", "In2.Cu"], pour=False))
    for k, (x, y) in POSTS.items():
        out.append(zone(f"case post {k}", circle(x, y, POST_D),
                        ["F.Cu", "B.Cu"], pour=True))
    # Board cut-outs (ls027: the light coupler and the FPC slot) are milled
    # holes like these, so copper keeps the same 0.5 mm off their edges.
    for k, (x0, y0, x1, y1) in enumerate(getattr(variant, "CUTOUTS", [])):
        g = 0.5
        out.append(zone(f"cutout {k} keepout",
                        [(x0 - g, y0 - g), (x1 + g, y0 - g), (x1 + g, y1 + g), (x0 - g, y1 + g)],
                        ["F.Cu", "B.Cu", "In1.Cu", "In2.Cu"], pour=False))
    return out


def strip(text):
    # Every letter ever used, so a hole or post taken out of the tables
    # above is removed from the board too. (It stopped at H until 5 October
    # 2026, so I, J and K were written again on every run: DRC saw the
    # doubled Edge.Cuts circles as a self-intersecting outline.)
    ours = {str(uuid.uuid5(NS, n)) for k in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" for n in
            (f"mounting hole {k}", f"mounting hole {k} keepout", f"case post {k}")}
    ours |= {str(uuid.uuid5(NS, f"cutout {k} keepout")) for k in range(8)}
    out, i = [], 0
    for m in re.finditer(r"\n\t\((?:zone|gr_circle)\n", text):
        if m.start() + 1 < i:          # inside a block already removed
            continue
        end = text.index("\n\t)\n", m.start()) + 4
        blk = text[m.start():end]
        u = re.search(r'\(uuid "([^"]+)"\)', blk)
        if u and u.group(1) in ours:
            out.append(text[i:m.start() + 1])
            i = end
    out.append(text[i:])
    return "".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    text = strip(PCB.read_text())
    for k, (x, y, d, keep) in HOLES.items():
        print(f"hole {k}  ({x}, {y})  {d} mm, {keep} mm clear")
    for k, (x, y) in POSTS.items():
        print(f"post {k}  ({x}, {y})  {POST_D} mm pad")
    if args.check:
        print("--check: nothing written")
        return 0
    end = text.rindex("\n)")
    text = text[:end + 1] + "".join(items()) + text[end + 1:]
    PCB.write_text(text)
    print("written; now re-run route_power.py, stitch_zones.py and route_signals.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
