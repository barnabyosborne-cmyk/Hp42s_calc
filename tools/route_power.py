#!/usr/bin/env python3
"""
Route steps 9.1 and 9.2 by writing tracks into default.kicad_pcb.

    python3 tools/route_power.py --check    # validate, write nothing
    python3 tools/route_power.py            # write the tracks

Run it with KiCad CLOSED, then open the board.

WHY A SCRIPT AND NOT THE MOUSE
------------------------------
Same reason as place_board.py: KiCad 10's scripting API misplaces things and
lies about it (docs/layout-walkthrough.md, and tools/place_board.py's header).
Writing the file directly means every co-ordinate is in `git diff` where it can
be read, and it means the routes can be re-derived after a part moves rather
than re-drawn.

This is a FIRST PASS for review. It routes all of step 9.1 -- the two switching
loops -- and all of step 9.2: `vbus`, `sys`, `bat` and `v3v3`. It does not touch
9.3 (the panel's SPI), 9.4 (USB) or 9.5 (the keypad matrix).

`gnd` needs no tracks: every pad on this board is on B.Cu and the B.Cu pour is
ground. `v3v3` needs no tracks either, because In2.Cu is a v3v3 plane -- each
v3v3 pad gets a short stub to a via that drops into it, and the plane does the
distributing. Those vias are placed by a search rather than by hand, because
each one has to miss 38 dome keepouts, every foreign pad and every track above.

THE ONE LAYER CHANGE, AND WHY
-----------------------------
`sys` runs north-south down the 1.62 mm corridor between C2/C3 and U2/U3, and
`bat` runs east-west from the cell at BT1 to the charger and the gauge. They
have to cross, and no amount of shuffling avoids it: `sys` goes west-to-east
across the board while `bat` goes east-to-west through the same rectangle. So
`bat` crosses on F.Cu, 2.6 mm of it, in the 3 mm gap between the dome rows at
y 74 and y 86 where F.Cu is empty and a via is legal. Two vias, and the keypad
loses a couple of millimetres of one row lane.

`vbus` has a second, unrelated hop for the same kind of reason. The USB
receptacle is a mid-mount part, so its four VBUS contacts land as two pads, at
x 35.6 and x 40.4, with CC1, CC2, D+, D- and SBU between them. Nothing can pass
between them on B.Cu, and the 2.15 mm below the connector is where D+ and D-
have to run to reach U1. So the two VBUS pads are joined on F.Cu.

WHAT IT CHECKS BEFORE IT WRITES
-------------------------------
Every route is validated and nothing is written if anything fails:

  - each path's ends land inside a pad of its own net, on its own layer, or
    meet another track of the same net
  - each leg starts where the last one finished
  - no track comes within CLEARANCE of a pad of a different net on its layer
  - no track comes within CLEARANCE of a track of a different net on its layer
  - no via lands inside a dome keepout, or off the board, or within CLEARANCE
    of a pad or a track of a different net on any layer

The clearance arithmetic is real 2D rectangle-to-capsule distance, not a
bounding-box guess, because most of these routes pass within half a millimetre
of something and a bounding box would either reject them all or miss a short.

It is idempotent: it removes the tracks it wrote last time first, so it can be
re-run after a part moves. It touches nothing else in the file -- tracks laid by
hand in KiCad have different uuids and are left alone.
"""

import math
import re
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PCB = ROOT / "elec/layout/default/default.kicad_pcb"

CLEARANCE = 0.2          # the Default net class, from default.kicad_pro
EPS = 1e-6               # 0.2 + 0.1 is not 0.3 in binary, and a rule that
                         # rejects an exactly-legal track is worse than no rule
POWER_W = 0.5            # the power net class
MID_W = 0.4              # down the C2/C3-to-U2 corridor, where 0.5 will not go
NECK_W = 0.25            # into a fine-pitch pad, where 0.5 would bridge two
# U2's pads are 0.2 mm tall on a 0.4 mm pitch, so the gap between neighbours is
# 0.2 mm and NOTHING wider than the pad itself can come in between them. A track
# exactly as wide as the pad, entering along the pad's own centreline, sits at
# exactly the 0.2 mm clearance from both neighbours. That is the only width that
# works, and it is why these entries run horizontally rather than diagonally.
FINE_W = 0.2
VIA_D, VIA_DRILL = 0.8, 0.4      # the power class via
EDGE_KEEP = 0.5                  # copper to board edge
# The searched v3v3 vias are held this much further off than the rule requires.
# Without it the search happily returns a via 9 microns outside a dome keepout's
# diagonal corner, or 21 microns clear of a test pad: legal, and no use to anyone
# who then nudges a part. The validator still tests the real rule.
MARGIN = 0.1

# Deterministic uuids so a re-run is byte-identical and git diff stays readable,
# and so the tracks this script wrote can be told from ones drawn by hand.
NS = uuid.UUID("9a3c17be-0000-4000-8000-000000000091")

REF_RE = re.compile(r'\(property "Reference" "([^"]+)"')
FP_AT = re.compile(r'\n\t\t\(at (-?[\d.]+) (-?[\d.]+)((?: -?[\d.]+)?)\)')


# --- the routes ---------------------------------------------------------------
#
# Each entry is one polyline. `path` is its corners; `widths` is one width per
# leg, so len(widths) == len(path) - 1. Co-ordinates are board millimetres and
# every one of them is a pad position read out of the board file, not a guess:
# run tools/netpads.py to print them.
#
# 9.1 -- THE TWO SWITCHING LOOPS
#
# The buck-boost first. L1 is turned 90 degrees from where it was, which is the
# whole reason these two are short: with L1's pads along x, `lx2` had to detour
# around the inductor's body to reach the far pad, about 12 mm for a node that
# should be 4. Turned, both of U3's switch pins face a pad of their own. The
# part is 4 x 4 mm so the courtyard does not change and the turn costs nothing.
#
# U3's pads are 0.6 x 0.25 mm on a 0.5 mm pitch, so a 0.5 mm track would bridge
# to the neighbour. Each leaves on a 0.25 mm neck until it is clear of the pad
# field at x 34.27, then widens.
ROUTES = [
    dict(net="lx1", layer="B.Cu",
         path=[(34.000, 89.400), (34.600, 89.400), (37.300, 89.400), (38.300, 90.085)],
         widths=[NECK_W, POWER_W, POWER_W],
         why="U3 pin 9 to L1 pad 1, the buck-boost's first switch node"),

    dict(net="lx2", layer="B.Cu",
         path=[(34.000, 88.400), (34.600, 88.400), (37.300, 88.400), (38.300, 87.715)],
         widths=[NECK_W, POWER_W, POWER_W],
         why="U3 pin 7 to L1 pad 2, the buck-boost's second switch node"),

    # The panel booster. THIS ONE IS COMPROMISED AND THE REASON IS PLACEMENT.
    # `display-sw` is the switch node and it has three pads: Q1's drain at
    # x 9.777, L2's output at x 15.495 and D1's anode at x 21.970. So the
    # inductor sits between the transistor and the diode, and the node that
    # wants to be shortest is forced to 12 mm and to detour around L2's own
    # input pad. In a boost converter the fast loop is drain to anode and back
    # through the output cap, so this is the worst place on the board to spend
    # 12 mm. Routed anyway, as one spine at y 68.5 clear of every pad in the
    # way, with a stub down into L2. It works and it is honest about the cost.
    dict(net="display-sw", layer="B.Cu",
         path=[(9.777, 71.120), (9.777, 68.500), (21.970, 68.500), (21.970, 69.600)],
         widths=[POWER_W, POWER_W, POWER_W],
         why="Q1 drain to D1 anode, the panel boost's switch node"),

    dict(net="display-sw", layer="B.Cu",
         path=[(15.495, 68.500), (15.495, 70.000)],
         widths=[POWER_W],
         why="the stub down into L2's output pad"),
]

# 9.2 -- POWER DISTRIBUTION, AND HOW THE CORRIDOR IS SHARED
#
# The whole of `sys` and `bat` comes down to one 1.62 mm gap. C2 and C3 end at
# x 30.025; U2's and U3's left-hand pad columns begin at x 31.645 and 31.870.
# Everything the charger and the buck-boost need has to pass between those two
# walls, and two 0.5 mm tracks will not both fit. So `sys` owns the corridor at
# x 31.200 and `bat` stays out of it, dropping in only at the top, at x 30.450,
# where `sys` has not started yet.
#
# The two leave U2 on adjacent pins -- pin 1 is `sys` at y 73.190 and pin 2 is
# `bat` at y 72.790 -- so for the first millimetre they run 0.400 mm apart, which
# on 0.2 mm tracks is exactly the 0.2 mm clearance and not a millimetre more.
# That is what a 0.4 mm pitch QFN costs and there is no way around it; it is
# also why `sys` turns south at x 31.200 and stays 0.2 mm wide until y 74.
#
# `vbus` runs the length of the board, from the USB connector at the top edge to
# the charger at y 73. 64 mm, which sounds alarming and is not: it is a DC rail
# at 500 mA, and the slot it cuts in the B.Cu pour is backed by the In1.Cu
# ground plane underneath, so nothing loses its return path. It descends at
# x 38.420, which is the middle of the 1.615 mm gap between R3/R5 and R6 -- the
# obvious x 38.000 is 0.39 mm from R5's ground pad and will not do.
ROUTES += [
    dict(net="vbus", layer="B.Cu",
         path=[(40.400, 6.400), (40.400, 8.000), (41.770, 9.800)],
         widths=[NECK_W, POWER_W],
         why="J1 pins A9/B4 down to C1, the USB bulk cap"),

    dict(net="vbus", layer="B.Cu",
         path=[(41.770, 10.160), (41.770, 14.000), (38.420, 20.000),
               (38.420, 74.500), (34.033, 74.500), (34.033, 73.250)],
         widths=[POWER_W, POWER_W, POWER_W, POWER_W, NECK_W],
         why="C1 down the board and up into U2 pin 10 from below"),

    dict(net="vbus", layer="B.Cu",
         path=[(35.600, 6.400), (35.600, 7.400)],
         widths=[NECK_W],
         why="J1 pins A4/B9 down to the F.Cu jumper"),

    dict(net="vbus", layer="F.Cu",
         path=[(35.600, 7.400), (40.400, 7.400)],
         widths=[POWER_W],
         why="the jumper joining J1's two VBUS pads under the connector"),
]

# `sys` is the battery-side rail: out of the charger at U2 pin 1, down the
# corridor to the buck-boost at U3, then east under U3 and L1, north past the
# cell to the test point, and on to the frontlight boost at x 59 to 65.
# U3's sys pins are its two bottom corners, pins 1 and 10, with the ground pad
# between them, so the rail runs beneath at y 91.400 and taps up into each
# corner rather than crossing the middle.
ROUTES += [
    dict(net="sys", layer="B.Cu",
         path=[(32.008, 73.190), (31.200, 73.190)],
         widths=[FINE_W],
         why="out of U2 pin 1, level with the pad because nothing wider fits"),

    dict(net="sys", layer="B.Cu",
         path=[(31.200, 73.190), (31.200, 74.000)],
         widths=[FINE_W],
         why="the turn south, still 0.2 mm while bat's exit is 0.4 mm away"),

    dict(net="sys", layer="B.Cu",
         path=[(31.200, 74.000), (31.200, 91.400)],
         widths=[POWER_W],
         why="down the corridor between C2/C3 and U2/U3 to beneath U3"),

    dict(net="sys", layer="B.Cu",
         path=[(31.200, 76.800), (27.625, 76.800), (27.625, 75.400)],
         widths=[POWER_W, POWER_W],
         why="round the underside of C3's ground pad into C3, the SYS bypass"),

    dict(net="sys", layer="B.Cu",
         path=[(31.200, 91.400), (56.000, 91.400)],
         widths=[POWER_W],
         why="east beneath U3 and L1, in the gap under the dome row at y 86"),

    dict(net="sys", layer="B.Cu",
         path=[(32.170, 91.400), (32.170, 89.950)],
         widths=[NECK_W],
         why="up into U3 pin 1"),

    dict(net="sys", layer="B.Cu",
         path=[(33.870, 91.400), (33.870, 89.950)],
         widths=[NECK_W],
         why="up into U3 pin 10"),

    dict(net="sys", layer="B.Cu",
         path=[(56.000, 91.400), (56.000, 68.500)],
         widths=[POWER_W],
         why="north up the free lane between the cell and the right dome column"),

    dict(net="sys", layer="B.Cu",
         path=[(56.000, 86.360), (53.500, 86.360)],
         widths=[POWER_W],
         why="the branch into TP5, the sys test point"),

    dict(net="sys", layer="B.Cu",
         path=[(56.000, 68.500), (64.900, 68.500)],
         widths=[POWER_W],
         why="east under the frontlight boost, below every part of it"),

    dict(net="sys", layer="B.Cu",
         path=[(64.900, 68.500), (64.900, 67.100)],
         widths=[POWER_W],
         why="up into U6 pin 1, the frontlight boost's supply"),

    dict(net="sys", layer="B.Cu",
         path=[(59.300, 68.500), (59.300, 61.700)],
         widths=[POWER_W],
         why="north through L3's pad to C21, the frontlight boost's input cap"),
]

# `bat` is the other side of the charger: the cell at BT1, the gauge at U4 with
# its own bypass C6, the charger's BAT bypass C2, a test point, and U2 pin 2.
# BT1 is at x 52 and the gauge is at x 6.6, so this net crosses the whole board.
# It goes down the free lane at x 52.070 -- the 1.04 mm gap between TP6 and TP7 --
# then west along y 80.500, which is the only y in that half of the board with
# nothing on it: C19 and D2/D3 reach y 79.975, and the dome courtyards begin
# again at y 81.500. It crosses `sys` once, on F.Cu, and that is the only layer
# change in step 9.2 that is not about the USB connector.
ROUTES += [
    dict(net="bat", layer="B.Cu",
         path=[(52.070, 63.000), (52.070, 86.360)],
         widths=[POWER_W],
         why="out of the cell at BT1 and down between the test points"),

    dict(net="bat", layer="B.Cu",
         path=[(52.070, 86.360), (51.000, 86.360)],
         widths=[POWER_W],
         why="the branch into TP4, the bat test point"),

    dict(net="bat", layer="B.Cu",
         path=[(52.070, 80.500), (32.500, 80.500)],
         widths=[POWER_W],
         why="west along the empty band at y 80.5 to the sys crossing"),

    dict(net="bat", layer="F.Cu",
         path=[(32.500, 80.500), (29.900, 80.500)],
         widths=[POWER_W],
         why="over sys on F.Cu, in the gap between the dome rows at 74 and 86"),

    dict(net="bat", layer="B.Cu",
         path=[(29.900, 80.500), (2.600, 80.500)],
         widths=[POWER_W],
         why="on west, under the keypad, to the gauge's end of the board"),

    dict(net="bat", layer="B.Cu",
         path=[(2.600, 80.500), (2.600, 89.535), (3.300, 89.535)],
         widths=[POWER_W, POWER_W],
         why="down the left edge into C6, the gauge's bypass"),

    dict(net="bat", layer="B.Cu",
         path=[(2.600, 87.800), (5.800, 87.800), (5.800, 88.650), (6.500, 88.650)],
         widths=[NECK_W, NECK_W, FINE_W],
         why="round U4's ground pads and in along pin 3's centreline"),

    dict(net="bat", layer="B.Cu",
         path=[(24.500, 80.500), (24.500, 70.000), (30.450, 70.000)],
         widths=[POWER_W, POWER_W],
         why="north clear of C17 and D1, then east above C2's ground pad"),

    dict(net="bat", layer="B.Cu",
         path=[(27.625, 70.000), (27.625, 71.500)],
         widths=[POWER_W],
         why="down into C2, the charger's BAT bypass"),

    dict(net="bat", layer="B.Cu",
         path=[(30.450, 70.000), (30.450, 72.790)],
         widths=[MID_W],
         why="down beside C2's ground pad, 0.425 mm off it, so 0.4 mm wide"),

    dict(net="bat", layer="B.Cu",
         path=[(30.450, 72.790), (32.000, 72.790)],
         widths=[FINE_W],
         why="into U2 pin 2, level with the pad and 0.4 mm under sys"),
]

# Vias placed by hand: the two ends of each F.Cu jumper above.
VIAS = [
    ("vbus", 35.600, 7.400),
    ("vbus", 40.400, 7.400),
    ("bat", 32.500, 80.500),
    ("bat", 29.900, 80.500),
]

# Every v3v3 pad gets a stub to a via that drops into the In2.Cu plane. The
# buck-boost's own output pin is the source, so it gets one too; the plane does
# the distributing. The positions are searched for, not written down, because a
# via has to miss 38 dome keepouts as well as every pad and track.
VIA_TO_PLANE = "v3v3"


# --- geometry -----------------------------------------------------------------

def rot(x, y, deg):
    a = math.radians(-deg)
    return x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)


def block_at(text, start):
    d = 0
    for i in range(start, len(text)):
        if text[i] == "(":
            d += 1
        elif text[i] == ")":
            d -= 1
            if d == 0:
                return text[start:i + 1]
    raise ValueError("unbalanced parentheses")


def read_pads(text):
    """Every pad on the board, as a dict with an absolute rectangle."""
    out = []
    for m in re.finditer(r'\n\t\(footprint "', text):
        blk = block_at(text, m.start() + 1)
        ref = REF_RE.search(blk).group(1)
        at = FP_AT.search(blk)
        fx, fy = float(at.group(1)), float(at.group(2))
        fr = float(at.group(3)) if at.group(3).strip() else 0.0
        for pm in re.finditer(r'\n\t\t\(pad "', blk):
            pad = block_at(blk, pm.start() + 2)
            pat = re.search(r'\(at (-?[\d.]+) (-?[\d.]+)(?: (-?[\d.]+))?\)', pad)
            siz = re.search(r'\(size ([\d.]+) ([\d.]+)\)', pad)
            if not (pat and siz):
                continue
            net = re.search(r'\(net "([^"]+)"\)', pad)
            lay = re.search(r'\(layers ([^)]*)\)', pad)
            px, py = float(pat.group(1)), float(pat.group(2))
            w, h = float(siz.group(1)), float(siz.group(2))
            # A pad's angle in the board file is ABSOLUTE -- it already
            # includes the footprint's rotation -- so the question of whether
            # this pad's width and height are swapped is answered by that angle
            # alone, NOT by its angle relative to the footprint. L1 is the part
            # that proves it: turned a quarter turn, its footprint is at 90 and
            # its pads are at 90, so the relative angle is 0 while the pad is
            # very much turned. check_placement.py subtracts the footprint's
            # rotation here; it gets away with it because it measures courtyards
            # from CrtYd lines rather than from pads.
            pr = float(pat.group(3) or 0.0) % 180
            if abs(pr - 90) < 1:
                w, h = h, w
            rx, ry = rot(px, py, fr)
            x, y = fx + rx, fy + ry
            out.append(dict(ref=ref, pad=pad.split('"')[1],
                            net=net.group(1) if net else None,
                            rect=(x - w / 2, y - h / 2, x + w / 2, y + h / 2),
                            layers=lay.group(1) if lay else ""))
    return out


def on_layer(pad, layer):
    ls = pad["layers"]
    return layer in ls or "*.Cu" in ls


def seg_rect_gap(p, q, rect):
    """Shortest distance from the segment p-q to an axis-aligned rectangle."""
    x0, y0, x1, y1 = rect

    def inside(pt):
        return x0 <= pt[0] <= x1 and y0 <= pt[1] <= y1
    if inside(p) or inside(q):
        return 0.0
    edges = [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)),
             ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]
    return min(seg_seg_gap(p, q, a, b) for a, b in edges)


def seg_seg_gap(p1, p2, p3, p4):
    """Shortest distance between two segments."""
    def sub(a, b):
        return (a[0] - b[0], a[1] - b[1])

    def cross(a, b):
        return a[0] * b[1] - a[1] * b[0]

    r, s = sub(p2, p1), sub(p4, p3)
    denom = cross(r, s)
    if abs(denom) > 1e-12:
        t = cross(sub(p3, p1), s) / denom
        u = cross(sub(p3, p1), r) / denom
        if 0 <= t <= 1 and 0 <= u <= 1:
            return 0.0
    return min(pt_seg_gap(p1, p3, p4), pt_seg_gap(p2, p3, p4),
               pt_seg_gap(p3, p1, p2), pt_seg_gap(p4, p1, p2))


def pt_seg_gap(pt, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.dist(pt, a)
    t = max(0.0, min(1.0, ((pt[0] - ax) * dx + (pt[1] - ay) * dy) / (dx * dx + dy * dy)))
    return math.dist(pt, (ax + t * dx, ay + t * dy))


def pt_in_rect(pt, rect):
    x0, y0, x1, y1 = rect
    return x0 <= pt[0] <= x1 and y0 <= pt[1] <= y1


# --- the dome keepouts, so a via is not put in one ----------------------------

def read_dome_keepouts(text):
    """(ref, centre_x, centre_y, half_width) for every dome via keepout."""
    out = []
    for m in re.finditer(r'\(name "dome via keepout ([^"]+)"\)', text):
        start = text.rfind("(zone", 0, m.start())
        blk = block_at(text, start)
        pts = [(float(a), float(b))
               for a, b in re.findall(r'\(xy (-?[\d.]+) (-?[\d.]+)\)', blk)]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        out.append((m.group(1), cx, cy, (max(xs) - min(xs)) / 2))
    return out


def in_dome_keepout(x, y, keepouts, margin=0.0):
    for ref, cx, cy, h in keepouts:
        dx, dy = abs(x - cx), abs(y - cy)
        h += margin
        if dx <= h and dy <= h and dx + dy <= h * 1.414216:
            return ref
    return None


def board_box(text):
    """The Edge.Cuts bounding box. The FPC notch is ignored -- it is 0.55 mm
    wide and nothing here goes near it."""
    xs, ys = [], []
    for m in re.finditer(r'\((?:gr_line|gr_rect)\n?\s*\(start (-?[\d.]+) (-?[\d.]+)\)'
                         r'\s*\(end (-?[\d.]+) (-?[\d.]+)\)(?:(?!\)\n\t\)).)*?'
                         r'\(layer "Edge\.Cuts"\)', text, re.S):
        xs += [float(m.group(1)), float(m.group(3))]
        ys += [float(m.group(2)), float(m.group(4))]
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


# --- validation ---------------------------------------------------------------

def legs(routes=None):
    """Flatten routes into (net, layer, p, q, width, why)."""
    out = []
    for r in (ROUTES if routes is None else routes):
        path, widths = r["path"], r["widths"]
        if len(widths) != len(path) - 1:
            sys.exit(f"{r['net']}: {len(path)} points needs {len(path)-1} widths, "
                     f"got {len(widths)}")
        for (p, q, w) in zip(path, path[1:], widths):
            out.append((r["net"], r["layer"], p, q, w, r["why"]))
    return out


def validate(pads, keepouts, vias, box):
    problems = []
    all_legs = legs()

    # 1. Ends land in a pad of the net. A path whose end is the start of another
    #    path of the same net is a T, which is fine; so is an end that lands on
    #    the middle of another leg of the same net, or on one of its own vias.
    starts = {(r["net"], r["path"][0]) for r in ROUTES}
    ends = {(r["net"], r["path"][-1]) for r in ROUTES}
    for r in ROUTES:
        own = [(r["path"][i], r["path"][i + 1]) for i in range(len(r["path"]) - 1)]
        for pt, which in ((r["path"][0], "start"), (r["path"][-1], "end")):
            if any(p["net"] == r["net"] and on_layer(p, r["layer"])
                   and pt_in_rect(pt, p["rect"]) for p in pads):
                continue
            if (r["net"], pt) in starts | ends and \
                    pt != r["path"][0 if which == "end" else -1]:
                continue
            if any(pt_seg_gap(pt, p, q) < 1e-6
                   for n, _l, p, q, _w, _y in all_legs
                   if n == r["net"] and (p, q) not in own):
                continue
            if any(n == r["net"] and math.dist(pt, (x, y)) < 1e-6
                   for n, x, y in vias):
                continue
            problems.append(f"{r['net']}: the {which} {pt} is not in a "
                            f"{r['net']} pad and does not meet another "
                            f"{r['net']} track  [{r['why']}]")

    # 2. Track to foreign pad.
    for net, layer, p, q, w, why in all_legs:
        need = CLEARANCE + w / 2
        for pad in pads:
            if pad["net"] == net or not on_layer(pad, layer):
                continue
            gap = seg_rect_gap(p, q, pad["rect"])
            if gap < need - EPS:
                problems.append(
                    f"{net} {p}->{q} w{w}: {gap:.3f} mm to {pad['ref']} pad "
                    f"{pad['pad']} ({pad['net']}), needs {need:.3f}  [{why}]")

    # 3. Track to foreign track.
    for i, (n1, l1, p1, q1, w1, y1) in enumerate(all_legs):
        for n2, l2, p2, q2, w2, y2 in all_legs[i + 1:]:
            if n1 == n2 or l1 != l2:
                continue
            need = CLEARANCE + w1 / 2 + w2 / 2
            gap = seg_seg_gap(p1, q1, p2, q2)
            if gap < need - EPS:
                problems.append(
                    f"{n1} {p1}->{q1} and {n2} {p2}->{q2}: {gap:.3f} mm apart, "
                    f"needs {need:.3f}")

    # 4. Vias: keepouts, the board edge, foreign pads, foreign tracks on any
    #    layer (a via is on all of them), and foreign vias.
    for i, (net, x, y) in enumerate(vias):
        ref = in_dome_keepout(x, y, keepouts, VIA_D / 2)
        if ref:
            problems.append(f"{net} via at ({x:.3f}, {y:.3f}) is inside "
                            f"{ref}'s keepout")
        if box:
            bx0, by0, bx1, by1 = box
            if not (bx0 + EDGE_KEEP + VIA_D / 2 <= x <= bx1 - EDGE_KEEP - VIA_D / 2
                    and by0 + EDGE_KEEP + VIA_D / 2 <= y <= by1 - EDGE_KEEP - VIA_D / 2):
                problems.append(f"{net} via at ({x:.3f}, {y:.3f}) is within "
                                f"{EDGE_KEEP} mm of the board edge")
        for pad in pads:
            if pad["net"] == net:
                continue
            gap = seg_rect_gap((x, y), (x, y), pad["rect"])
            if gap < CLEARANCE + VIA_D / 2 - EPS:
                problems.append(
                    f"{net} via at ({x:.3f}, {y:.3f}): {gap:.3f} mm to "
                    f"{pad['ref']} pad {pad['pad']} ({pad['net']}), "
                    f"needs {CLEARANCE + VIA_D / 2:.3f}")
        for n, _l, p, q, w, why in all_legs:
            if n == net:
                continue
            need = CLEARANCE + VIA_D / 2 + w / 2
            gap = pt_seg_gap((x, y), p, q)
            if gap < need - EPS:
                problems.append(
                    f"{net} via at ({x:.3f}, {y:.3f}): {gap:.3f} mm to the "
                    f"{n} track {p}->{q}, needs {need:.3f}")
        for n, x2, y2 in vias[i + 1:]:
            if n == net:
                continue
            gap = math.dist((x, y), (x2, y2))
            if gap < CLEARANCE + VIA_D - EPS:
                problems.append(
                    f"{net} via at ({x:.3f}, {y:.3f}) and {n} via at "
                    f"({x2:.3f}, {y2:.3f}): {gap:.3f} mm apart, needs "
                    f"{CLEARANCE + VIA_D:.3f}")
    return problems


# --- placing the v3v3 vias ----------------------------------------------------

def plane_vias(pads, keepouts, box, fixed_vias):
    """One via per v3v3 pad, with a stub from the pad, searched for rather than
    written down. The rule is the same as the validator's: clear of every dome
    keepout, every foreign pad, every foreign track and the board edge, and so
    is the stub that reaches it. Nearest legal position wins, which keeps the
    stub short; a via on the pad itself would be shorter still and would need
    the fab to fill and cap it, so the search starts outside the pad."""
    targets = [p for p in pads if p["net"] == VIA_TO_PLANE]
    base = legs()
    placed, stubs, failed, tight = list(fixed_vias), [], [], []

    for pad in sorted(targets, key=lambda p: p["ref"]):
        x0, y0, x1, y1 = pad["rect"]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        # A stub as wide as the pad will fit where the pad fits; anything wider
        # will not. 0.5 mm on the big pads, 0.2 mm on the fine-pitch ones.
        w = POWER_W if min(x1 - x0, y1 - y0) >= 0.9 else FINE_W
        start = (min(max(cx, x0 + w / 2), x1 - w / 2),
                 min(max(cy, y0 + w / 2), y1 - w / 2))

        # Two passes: the comfortable margin first, and only if nowhere on the
        # board will take it, the bare rule. Three pads need the second pass --
        # J2's two 3V3 pins, which are 0.3 mm tall on a 0.5 mm pitch with a
        # ground pin next door, and U3's own 3V3 output, which is boxed in by
        # the dome above it and by its two switch nodes.
        best = None
        for margin in (MARGIN, 0.0):
            r = max(x1 - x0, y1 - y0) / 2 + CLEARANCE + VIA_D / 2
            while r < 6.0 and best is None:
                for step in range(72):
                    a = math.radians(step * 5)
                    vx, vy = cx + r * math.cos(a), cy + r * math.sin(a)
                    if in_dome_keepout(vx, vy, keepouts, VIA_D / 2 + margin):
                        continue
                    if box:
                        bx0, by0, bx1, by1 = box
                        edge = EDGE_KEEP + VIA_D / 2 + margin
                        if not (bx0 + edge <= vx <= bx1 - edge
                                and by0 + edge <= vy <= by1 - edge):
                            continue
                    if not clear(start, (vx, vy), w, pads, base, placed, margin):
                        continue
                    best = (round(vx, 3), round(vy, 3))
                    break
                r += 0.1
            if best:
                if margin == 0.0:
                    tight.append((pad, best))
                break

        if best is None:
            failed.append(pad)
            continue
        placed.append((VIA_TO_PLANE, best[0], best[1]))
        stubs.append(dict(net=VIA_TO_PLANE, layer="B.Cu", path=[start, best],
                          widths=[w],
                          why=f"{pad['ref']} pad {pad['pad']} into the In2.Cu plane"))
    return placed, stubs, failed, tight


def clear(start, via, w, pads, base, placed, margin=MARGIN):
    """Is a via here, reached by a stub from `start`, legal?"""
    for pad in pads:
        if pad["net"] == VIA_TO_PLANE:
            continue
        if seg_rect_gap(via, via, pad["rect"]) < CLEARANCE + VIA_D / 2 + margin:
            return False
        if seg_rect_gap(start, via, pad["rect"]) < CLEARANCE + w / 2 + margin:
            return False
    for n, _l, p, q, tw, _y in base:
        if n == VIA_TO_PLANE:
            continue
        if pt_seg_gap(via, p, q) < CLEARANCE + VIA_D / 2 + tw / 2 + margin:
            return False
        if seg_seg_gap(start, via, p, q) < CLEARANCE + w / 2 + tw / 2 + margin:
            return False
    for n, px, py in placed:
        if n == VIA_TO_PLANE:
            # Same net, so they may touch; but two vias on top of each other is
            # not a drill file anyone wants.
            if math.dist(via, (px, py)) < VIA_D + 0.2:
                return False
            continue
        if math.dist(via, (px, py)) < CLEARANCE + VIA_D + margin:
            return False
        if pt_seg_gap((px, py), start, via) < CLEARANCE + VIA_D / 2 + w / 2 + margin:
            return False
    return True


# --- writing ------------------------------------------------------------------

def fmt(v):
    return f"{v:g}"


def segment(net, layer, p, q, w, tag):
    uid = uuid.uuid5(NS, f"seg {net} {layer} {p} {q} {w} {tag}")
    return (f"\t(segment\n"
            f"\t\t(start {fmt(p[0])} {fmt(p[1])})\n"
            f"\t\t(end {fmt(q[0])} {fmt(q[1])})\n"
            f"\t\t(width {fmt(w)})\n"
            f"\t\t(layer \"{layer}\")\n"
            f"\t\t(net \"{net}\")\n"
            f"\t\t(uuid \"{uid}\")\n"
            f"\t)\n")


def via(net, x, y):
    uid = uuid.uuid5(NS, f"via {net} {x} {y}")
    return (f"\t(via\n"
            f"\t\t(at {fmt(x)} {fmt(y)})\n"
            f"\t\t(size {fmt(VIA_D)})\n"
            f"\t\t(drill {fmt(VIA_DRILL)})\n"
            f"\t\t(layers \"F.Cu\" \"B.Cu\")\n"
            f"\t\t(net \"{net}\")\n"
            f"\t\t(uuid \"{uid}\")\n"
            f"\t)\n")


OURS = re.compile(r'\n\t\((?:segment|via)\n(?:(?!\n\t\)).)*?'
                  r'\(uuid "([0-9a-f-]+)"\)\n\t\)', re.S)

KNOWN = set()


def strip_old(text):
    """Remove only the tracks this script wrote. Returns (text, count)."""
    removed = 0
    while True:
        hit = None
        for m in OURS.finditer(text):
            if m.group(1) in KNOWN:
                hit = m
                break
        if not hit:
            return text, removed
        text = text[:hit.start()] + text[hit.end():]
        removed += 1


def main():
    check = "--check" in sys.argv
    text = PCB.read_text()
    pads = read_pads(text)
    keepouts = read_dome_keepouts(text)
    box = board_box(text)

    vias, stubs, failed, tight = plane_vias(pads, keepouts, box, VIAS)
    ROUTES.extend(stubs)

    problems = validate(pads, keepouts, vias, box)
    for pad in failed:
        problems.append(f"{VIA_TO_PLANE}: no legal via position within 6 mm of "
                        f"{pad['ref']} pad {pad['pad']}")

    nets = sorted({r["net"] for r in ROUTES})
    print(f"{len(legs())} track segments across {len(nets)} nets: "
          f"{', '.join(nets)}")
    print(f"{len(vias)} vias: {len(VIAS)} joining the two F.Cu jumpers, "
          f"{len(vias) - len(VIAS)} taking {VIA_TO_PLANE} into the In2.Cu plane")
    total = sum(math.dist(p, q) for _n, _l, p, q, _w, _y in legs())
    print(f"{total:.1f} mm of copper\n")
    for net in nets:
        rs = [r for r in ROUTES if r["net"] == net]
        length = sum(math.dist(p, q) for r in rs
                     for p, q in zip(r["path"], r["path"][1:]))
        print(f"   {net:12s} {length:6.2f} mm in {len(rs)} paths")

    if problems:
        print(f"\n{len(problems)} PROBLEM(S) -- nothing written:\n")
        for p in problems:
            print(f"   {p}")
        return 1

    print("\nno clearance problems, every end lands in a pad of its net")
    for pad, (vx, vy) in tight:
        print(f"   NOTE {pad['ref']} pad {pad['pad']}'s via at ({vx}, {vy}) is at "
              f"the {CLEARANCE} mm rule rather than comfortably clear of it")

    body = []
    for net, layer, p, q, w, why in legs():
        body.append(segment(net, layer, p, q, w, why))
    for net, x, y in vias:
        body.append(via(net, x, y))

    # Everything this run would write, so strip_old knows what is ours, plus
    # everything any previous run wrote: a v5 uuid on a segment or via is one
    # of ours, because KiCad's own are v4.
    for chunk in body:
        KNOWN.add(re.search(r'\(uuid "([0-9a-f-]+)"\)', chunk).group(1))
    for m in OURS.finditer(text):
        try:
            if uuid.UUID(m.group(1)).version == 5:
                KNOWN.add(m.group(1))
        except ValueError:
            pass

    if check:
        print("--check: nothing written")
        return 0

    text, removed = strip_old(text)
    if removed:
        print(f"replaced {removed} track(s) from a previous run")

    end = text.rindex("\n)")
    PCB.write_text(text[:end] + "\n" + "".join(body).rstrip("\n") + text[end:])
    print(f"wrote {PCB.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
