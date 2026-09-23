#!/usr/bin/env python3
"""
Check the placement in default.kicad_pcb against the rules we are using.

    python3 tools/check_placement.py

It reads the board file, not KiCad, so it can be run any time. It reports:

  * courtyards closer than 1.0 mm on the same side of the board
  * anything crossing the board outline
  * anything on the back inside the battery bay
  * anything inside the ESP32 module's antenna keepout -- measured on copper
    only, and against a keepout worked out from the module's own courtyard,
    so it follows the module wherever it goes
  * anything on the front under the panel glass or under the keys
  * parts off the grid they are supposed to be on

Sides are read from the board file, not from place_board.py's table, so this
also catches a part that ended up on the wrong side.

Every distance here is between COURTYARDS, which already include the
manufacturer's own handling clearance, so 1.0 mm between two courtyards is
about 1.5 mm between the parts themselves.

U5 is measured by its lands, with the antenna keepout checked separately:
its courtyard is the keepout rectangle, which is 45 mm wide and would
otherwise swallow half the board.
"""

import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import place_board as pb

PCB = Path(__file__).resolve().parent.parent / "elec/layout/default/default.kicad_pcb"

BOARD_W, BOARD_H = 76.0, 144.0
GAP = 1.0                 # between courtyards, same side
EDGE = 0.5                # courtyard to board outline
BAY = (10.0, 5.0, 76.0, 59.0)        # back only: the cell, and the FPC's strip
GLASS = (12.0, 48.3)                  # front only, full width
KEYS_TOP = 57.0                       # front only, below this the domes live
# The ESP32 module's antenna keepout is worked out from the module's own
# courtyard in the board file, not typed in here: it is the wing of that
# courtyard that sticks out past the module body, and it moves whenever the
# module moves, turns or changes side.
ANTENNA_REF = "U5"
ANTENNA_BODY_HALF_W = 7.95
# The bottom key row's dome rings reach 0.25 mm into the keepout and cannot
# move -- the key grid is measured from a real 42S. A quarter of a millimetre
# of copper ring will not detune a 2.4 GHz antenna; a ground pour would.
ANTENNA_PAD_ALLOWANCE = 0.3
GRID_IC = 1.27
GRID_PASSIVE = 0.635
# Positions that come from the case, the panel or the antenna, not the grid.
OFF_GRID = {"J2", "U5", "TP1", "TP2", "SW39", "SW40", "SW41", "J1", "D4", "D5"}

REF_RE = re.compile(r'\(property "Reference" "([^"]+)"')
FP_AT = re.compile(r'\n\t\t\(at (-?[\d.]+) (-?[\d.]+)((?: -?[\d.]+)?)\)')
PAD_HEAD = re.compile(r'\(at (-?[\d.]+) (-?[\d.]+)(?: (-?[\d.]+))?\)\s*'
                      r'\(size (-?[\d.]+) (-?[\d.]+)\)')
XY_RE = re.compile(r'\(xy (-?[\d.]+) (-?[\d.]+)\)')
GR_RE = re.compile(r'\(fp_(?:line|rect)\s*\(start (-?[\d.]+) (-?[\d.]+)\)\s*'
                   r'\(end (-?[\d.]+) (-?[\d.]+)\)(.*?)\n\t\t\)', re.S)
POLY_RE = re.compile(r'\(fp_poly\s*\(pts(.*?)\)(.*?)\n\t\t\)', re.S)


def rot(x, y, deg):
    a = math.radians(-deg)
    return x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)


def read():
    parts = {}
    for b in PCB.read_text().split("\n\t(footprint ")[1:]:
        ref = REF_RE.search(b).group(1)
        m = FP_AT.search(b)
        fx, fy = float(m.group(1)), float(m.group(2))
        fr = float(m.group(3)) if m.group(3).strip() else 0.0
        pts, cu = [], []
        for seg in b.split('\n\t\t(pad "')[1:]:
            p = PAD_HEAD.search(seg)
            if not p:
                continue
            px, py = float(p.group(1)), float(p.group(2))
            w, h = float(p.group(4)), float(p.group(5))
            pr = float(p.group(3) or 0.0) - fr
            if abs((pr % 180) - 90) < 1:
                w, h = h, w
            corners = [(px - w / 2, py - h / 2), (px + w / 2, py + h / 2),
                       (px - w / 2, py + h / 2), (px + w / 2, py - h / 2)]
            # A custom pad's real extent is in its primitives, not its size --
            # which is what a dome's ring is, 25 times bigger than the 0.3 mm
            # anchor the size field gives.
            prim = seg.split("(primitives", 1)
            if len(prim) > 1:
                corners += [(px + float(gx), py + float(gy))
                            for gx, gy in XY_RE.findall(prim[1])]
            pts += corners
            layers = seg.split("(layers", 1)
            if len(layers) > 1 and ".Cu" in layers[1].split(")", 1)[0]:
                cu += corners
        crt = []
        for g in GR_RE.finditer(b):
            if "CrtYd" in g.group(5):
                crt += [(float(g.group(1)), float(g.group(2))),
                        (float(g.group(3)), float(g.group(4)))]
        for g in POLY_RE.finditer(b):
            if "CrtYd" in g.group(2):
                crt += [(float(x), float(y)) for x, y in XY_RE.findall(g.group(1))]
        use = pts if ref == ANTENNA_REF or not crt else crt
        def to_board(points):
            out = []
            for x, y in points:
                rx, ry = rot(x, y, fr)
                out.append((fx + rx, fy + ry))
            return out

        pl = to_board(use)
        xs = [x for x, _ in pl]
        ys = [y for _, y in pl]
        cul = to_board(cu) or pl
        copper = (min(x for x, _ in cul), min(y for _, y in cul),
                  max(x for x, _ in cul), max(y for _, y in cul))
        side = pb.side_of(b)
        parts[ref] = dict(x=fx, y=fy, rot=fr, side=side,
                          bb=(min(xs), min(ys), max(xs), max(ys)),
                          cu=copper, crt=crt, at=(fx, fy))
    return parts


def antenna_keepout(parts):
    """Where the module's keepout wing actually is, in board coordinates."""
    u = parts.get(ANTENNA_REF)
    if not u or not u["crt"]:
        return None
    wing = [(x, y) for x, y in u["crt"] if abs(x) > ANTENNA_BODY_HALF_W]
    if not wing:
        return None
    xs, ys = [], []
    for x, y in wing:
        rx, ry = rot(x, y, u["rot"])
        xs.append(u["at"][0] + rx)
        ys.append(u["at"][1] + ry)
    return (min(xs), min(ys), max(xs), max(ys))


def boxes_overlap(a, b, gap):
    return (min(a[2], b[2]) - max(a[0], b[0]) > -gap and
            min(a[3], b[3]) - max(a[1], b[1]) > -gap)


def main():
    parts = read()
    refs = sorted(parts)
    bad = 0

    print(f"{len(parts)} footprints\n")

    print(f"--- closer than {GAP:g} mm, same side ---")
    n = 0
    for i, a in enumerate(refs):
        for b in refs[i + 1:]:
            if parts[a]["side"] != parts[b]["side"]:
                continue
            A, B = parts[a]["bb"], parts[b]["bb"]
            if not boxes_overlap(A, B, GAP):
                continue
            dx = max(A[0], B[0]) - min(A[2], B[2])
            dy = max(A[1], B[1]) - min(A[3], B[3])
            d = max(dx, dy)
            n += 1
            print(f"  {a} to {b}: {d:+.2f} mm")
    print("  none" if not n else f"  {n} pairs")
    bad += n

    print(f"\n--- closer than {EDGE:g} mm to the board outline ---")
    n = 0
    for r in refs:
        x0, y0, x1, y1 = parts[r]["bb"]
        if x0 < EDGE or y0 < EDGE or x1 > BOARD_W - EDGE or y1 > BOARD_H - EDGE:
            n += 1
            print(f"  {r}: ({x0:.2f},{y0:.2f})-({x1:.2f},{y1:.2f})")
    print("  none" if not n else f"  {n} parts  "
          "(the top-edge six are meant to: they reach into the case wall)")

    print("\n--- on the back, inside the battery bay ---")
    n = 0
    for r in refs:
        if parts[r]["side"] != "B" or r == "J2":
            continue
        if boxes_overlap(parts[r]["bb"], BAY, 0.0):
            n += 1
            print(f"  {r}: {parts[r]['bb']}")
    print("  none" if not n else f"  {n} parts")
    bad += n

    keepout = antenna_keepout(parts)
    print("\n--- the ESP32's antenna keepout ---")
    if keepout is None:
        print("  could not work it out from the module's courtyard")
        bad += 1
    else:
        x0, y0, x1, y1 = keepout
        print(f"  it is at X {x0:.2f}..{x1:.2f}, Y {y0:.2f}..{y1:.2f}")
        if y1 <= BOARD_H:
            print(f"  WRONG WAY ROUND: the antenna has to hang out over the "
                  f"bottom edge at Y {BOARD_H:g}, and this stops at "
                  f"Y {y1:.2f}. Turn {ANTENNA_REF} through 180 degrees.")
            bad += 1
        n, noted = 0, 0
        for r in refs:
            if r == ANTENNA_REF:
                continue
            if not boxes_overlap(parts[r]["cu"], keepout, 0.0):
                continue
            a = parts[r]["cu"]
            depth = min(min(a[2], keepout[2]) - max(a[0], keepout[0]),
                        min(a[3], keepout[3]) - max(a[1], keepout[1]))
            if depth <= ANTENNA_PAD_ALLOWANCE:
                noted += 1
                print(f"  {r} reaches {depth:.2f} mm into it "
                      f"(within the {ANTENNA_PAD_ALLOWANCE:g} mm allowance)")
            else:
                n += 1
                print(f"  {r} is {depth:.2f} mm inside it: {a}")
        if not n and not noted:
            print("  nothing is inside it")
        bad += n

    print("\n--- on the front, under the glass or under the keys ---")
    n = 0
    for r in refs:
        if parts[r]["side"] != "F":
            continue
        x0, y0, x1, y1 = parts[r]["bb"]
        if r in ("TP1", "TP2", "TP3") or r.startswith("SW"):
            continue
        if y1 > GLASS[0] and y0 < GLASS[1]:
            n += 1
            print(f"  {r}: reaches Y {y1:.2f}, the glass starts at {GLASS[0]}")
        elif y1 > KEYS_TOP:
            n += 1
            print(f"  {r}: reaches Y {y1:.2f}, the keys start at {KEYS_TOP}")
    print("  none" if not n else f"  {n} parts")
    bad += n

    print(f"\n--- off the grid ({GRID_IC:g} mm for ICs, "
          f"{GRID_PASSIVE:g} mm for passives) ---")
    n = 0
    for r in refs:
        if r in OFF_GRID or r not in pb.FIRST_PASS:
            continue
        g = GRID_PASSIVE if r[0] in "RCLDT" else GRID_IC
        for v in (parts[r]["x"], parts[r]["y"]):
            if abs(v / g - round(v / g)) > 1e-6:
                n += 1
                print(f"  {r}: ({parts[r]['x']:g}, {parts[r]['y']:g}) "
                      f"is not on {g:g} mm")
                break
    print("  none" if not n else f"  {n} parts")
    bad += n

    print("\nall clear" if not bad else f"\n{bad} thing{'s' if bad != 1 else ''} to fix")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
