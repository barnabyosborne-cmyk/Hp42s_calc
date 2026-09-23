#!/usr/bin/env python3
"""
Check the placement in default.kicad_pcb against the rules we are using.

    python3 tools/check_placement.py

It reads the board file, not KiCad, so it can be run any time. It reports:

  * courtyards closer than 1.0 mm on the same side of the board
  * anything crossing the board outline
  * anything on the back inside the battery bay
  * anything inside the ESP32 module's antenna keepout
  * anything on the front under the panel glass or under the keys
  * parts off the grid they are supposed to be on

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
ANTENNA = (15.3, 138.75, 60.7, 144.0)
GRID_IC = 1.27
GRID_PASSIVE = 0.635
# Positions that come from the case, the panel or the antenna, not the grid.
OFF_GRID = {"J2", "U5", "TP1", "TP2", "SW39", "SW40", "SW41", "J1", "D4", "D5"}

REF_RE = re.compile(r'\(property "Reference" "([^"]+)"')
FP_AT = re.compile(r'\n\t\t\(at (-?[\d.]+) (-?[\d.]+)((?: -?[\d.]+)?)\)')
PAD_RE = re.compile(r'\(pad "[^"]*" \w+ \w+\s*\(at (-?[\d.]+) (-?[\d.]+)'
                    r'(?: (-?[\d.]+))?\)\s*\(size (-?[\d.]+) (-?[\d.]+)\)')
GR_RE = re.compile(r'\(fp_(?:line|rect)\s*\(start (-?[\d.]+) (-?[\d.]+)\)\s*'
                   r'\(end (-?[\d.]+) (-?[\d.]+)\)(.*?)\n\t\t\)', re.S)


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
        pts = []
        for p in PAD_RE.finditer(b):
            px, py = float(p.group(1)), float(p.group(2))
            w, h = float(p.group(4)), float(p.group(5))
            pr = float(p.group(3) or 0.0) - fr
            if abs((pr % 180) - 90) < 1:
                w, h = h, w
            pts += [(px - w / 2, py - h / 2), (px + w / 2, py + h / 2),
                    (px - w / 2, py + h / 2), (px + w / 2, py - h / 2)]
        crt = []
        for g in GR_RE.finditer(b):
            if "CrtYd" in g.group(5):
                crt += [(float(g.group(1)), float(g.group(2))),
                        (float(g.group(3)), float(g.group(4)))]
        use = pts if ref == "U5" or not crt else crt
        xs, ys = [], []
        for x, y in use:
            rx, ry = rot(x, y, fr)
            xs.append(fx + rx)
            ys.append(fy + ry)
        side = "B" if pb.FIRST_PASS.get(ref, (0, 0, "F"))[2] == "B" else "F"
        if ref == "J2":
            side = "B"
        parts[ref] = dict(x=fx, y=fy, rot=fr, side=side,
                          bb=(min(xs), min(ys), max(xs), max(ys)))
    return parts


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

    print("\n--- inside the ESP32's antenna keepout ---")
    n = 0
    for r in refs:
        if r == "U5":
            continue
        if boxes_overlap(parts[r]["bb"], ANTENNA, 0.0):
            n += 1
            print(f"  {r}: {parts[r]['bb']}")
    print("  none" if not n else f"  {n} parts")
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
