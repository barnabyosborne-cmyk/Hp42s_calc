#!/usr/bin/env python3
"""
Check the footprints we drew ourselves for pads too close together.

    python3 tools/check_footprints.py

WHY THIS EXISTS
---------------
On 25 September 2026, while routing step 9.1, the clearance validator in
route_power.py reported that a track could not get out of U3 without coming
within 0.25 mm of U3's own ground pad. That was true, and the reason was worse
than the track: **the TPS63900's exposed pad land was 1.2 mm wide while its
signal lands started at 0.55 mm, so all ten pins were shorted to ground.**

Nothing had caught it. It is invisible in the netlist, which is about pin names.
It is invisible to check_netlist.py, which asks whether a pin lands on a pad.
It is invisible to check_placement.py, which measures courtyards between parts
and never looks inside one. And it is invisible on screen at any zoom where you
can see the whole part. KiCad's own DRC would have found it, on a board none of
us can open here.

So this is the missing check, and it is cheap: for every footprint in
`elec/footprints/hp42s.pretty`, compare every pair of pads that share a copper
layer and have different names, and report any that overlap or come closer than
the board's 0.2 mm clearance.

It compares POLYGONS, not bounding boxes. That is not fussiness: a metal dome's
outer ring is a C, an octagonal annulus with a slot on one side for the centre
contact's tab to escape through. Its bounding box is the whole 8.5 mm square and
contains the tab entirely, so a box comparison calls every dome on the board a
short. The real gap there is 0.92 mm. A tool that cries wolf on 38 parts is a
tool nobody runs.

WHAT IT DELIBERATELY DOES NOT FLAG
----------------------------------
- **Pads with the same name.** They are the same net by definition and KiCad
  merges them.
- **Two pads at exactly the same place with the same shape.** That is one piece
  of metal carrying two pin numbers, which is how a Type-C receptacle is drawn:
  A1 and B12 are the same contact. Different names, so the name rule above does
  not catch them, but an identical outline is not something you draw by accident.
- **Pads that share no copper layer.** The dome footprints have an `F.Mask`-only
  aperture sitting on top of the ring, which is a mask opening and not copper.
  Comparing layer *names* rather than copper layers reports it, wrongly; that
  was this script's first bug.
- **Non-plated holes.** A boss hole has no copper to short.
"""

import glob
import math
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRETTY = ROOT / "elec/footprints/hp42s.pretty"

CLEARANCE = 0.2

PAD_HEAD = re.compile(r'\(pad\s+"([^"]*)"\s+(\S+)\s+(\S+)')


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


def copper_layers(pad):
    m = re.search(r'\(layers([^)]*)\)', pad)
    if not m:
        return set()
    out = set()
    for tok in m.group(1).replace('"', " ").split():
        if tok == "*.Cu":
            out |= {"F.Cu", "In1.Cu", "In2.Cu", "B.Cu"}
        elif tok.endswith(".Cu"):
            out.add(tok)
    return out


def pads_of(path):
    text = Path(path).read_text()
    out = []
    for m in PAD_HEAD.finditer(text):
        pad = block_at(text, m.start())
        at = re.search(r'\(at\s+(-?[\d.]+)\s+(-?[\d.]+)(?:\s+(-?[\d.]+))?', pad)
        size = re.search(r'\(size\s+([\d.]+)\s+([\d.]+)\)', pad)
        if not (at and size):
            continue
        if "np_thru_hole" in (m.group(2), m.group(3)):
            continue
        cu = copper_layers(pad)
        if not cu:
            continue
        x, y = float(at.group(1)), float(at.group(2))
        w, h = float(size.group(1)), float(size.group(2))
        if abs((float(at.group(3) or 0.0) % 180) - 90) < 1:
            w, h = h, w
        # A pad is one or more polygons. A plain pad is its rectangle; a custom
        # pad is whatever its primitives say, which for a dome ring is a C.
        polys = []
        prim = pad.split("(primitives", 1)
        if len(prim) > 1:
            for g in re.finditer(r'\(gr_poly \(pts ((?:\(xy -?[\d.]+ -?[\d.]+\) ?)+)\)',
                                 prim[1]):
                polys.append([(x + float(a), y + float(b)) for a, b in
                              re.findall(r'\(xy (-?[\d.]+) (-?[\d.]+)\)', g.group(1))])
            for cxs, cys, exs, eys in re.findall(
                    r'\(gr_circle \(center (-?[\d.]+) (-?[\d.]+)\)'
                    r'\s*\(end (-?[\d.]+) (-?[\d.]+)\)', prim[1]):
                cx, cy = x + float(cxs), y + float(cys)
                r = math.dist((float(cxs), float(cys)), (float(exs), float(eys)))
                polys.append([(cx + r * math.cos(t), cy + r * math.sin(t))
                              for t in [i * math.pi / 12 for i in range(24)]])
        if not polys:
            polys = [[(x - w / 2, y - h / 2), (x + w / 2, y - h / 2),
                      (x + w / 2, y + h / 2), (x - w / 2, y + h / 2)]]
        out.append(dict(name=m.group(1), cu=cu, polys=polys))
    return out


def pt_in_poly(pt, poly):
    inside = False
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        if (y0 > pt[1]) != (y1 > pt[1]):
            xi = x0 + (pt[1] - y0) * (x1 - x0) / (y1 - y0)
            if pt[0] < xi:
                inside = not inside
    return inside


def pt_seg_gap(pt, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    if dx == 0 and dy == 0:
        return math.dist(pt, a)
    t = max(0.0, min(1.0, ((pt[0] - a[0]) * dx + (pt[1] - a[1]) * dy)
                     / (dx * dx + dy * dy)))
    return math.dist(pt, (a[0] + t * dx, a[1] + t * dy))


def seg_seg_gap(p1, p2, p3, p4):
    def cross(a, b):
        return a[0] * b[1] - a[1] * b[0]

    def sub(a, b):
        return (a[0] - b[0], a[1] - b[1])

    r, s = sub(p2, p1), sub(p4, p3)
    den = cross(r, s)
    if abs(den) > 1e-12:
        t = cross(sub(p3, p1), s) / den
        u = cross(sub(p3, p1), r) / den
        if 0 <= t <= 1 and 0 <= u <= 1:
            return 0.0
    return min(pt_seg_gap(p1, p3, p4), pt_seg_gap(p2, p3, p4),
               pt_seg_gap(p3, p1, p2), pt_seg_gap(p4, p1, p2))


def edges(poly):
    return [(poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly))]


def poly_gap(a, b):
    """Shortest distance between two polygons, or None if they intersect."""
    if any(pt_in_poly(pt, b) for pt in a) or any(pt_in_poly(pt, a) for pt in b):
        return None
    best = float("inf")
    for e1 in edges(a):
        for e2 in edges(b):
            g = seg_seg_gap(e1[0], e1[1], e2[0], e2[1])
            if g == 0.0:
                return None
            best = min(best, g)
    return best


def gap(a, b):
    """Shortest distance between two pads, or None if any part overlaps."""
    best = float("inf")
    for pa in a:
        for pb in b:
            g = poly_gap(pa, pb)
            if g is None:
                return None
            best = min(best, g)
    return best


def same_metal(a, b):
    """Two pads drawn at exactly the same place are one piece of metal."""
    def key(polys):
        return sorted(tuple(round(v, 6) for v in pt) for p in polys for pt in p)
    return key(a) == key(b)


def main():
    files = sorted(glob.glob(str(PRETTY / "*.kicad_mod")))
    if not files:
        sys.exit(f"no footprints in {PRETTY}")

    bad = 0
    for path in files:
        pads = pads_of(path)
        issues = []
        for i, a in enumerate(pads):
            for b in pads[i + 1:]:
                if a["name"] == b["name"] or not (a["cu"] & b["cu"]):
                    continue
                if same_metal(a["polys"], b["polys"]):
                    continue
                g = gap(a["polys"], b["polys"])
                if g is None or g < CLEARANCE - 1e-9:
                    issues.append((a["name"], b["name"], g))
        name = os.path.basename(path)
        if issues:
            bad += 1
            print(f"{name}: {len(issues)} problem(s)")
            for n1, n2, g in sorted(issues, key=lambda t: (t[2] is not None, t[2])):
                what = "OVERLAP -- these two nets are shorted" \
                    if g is None else f"{g:.3f} mm, needs {CLEARANCE}"
                print(f"   pad {n1 or '<unnamed>':>3s} and pad "
                      f"{n2 or '<unnamed>':>3s}: {what}")
        else:
            print(f"{name}: {len(pads)} copper pads, all clear")

    print()
    if bad:
        print(f"{bad} of {len(files)} footprints have a problem")
        return 1
    print(f"all {len(files)} footprints clear at {CLEARANCE} mm")
    return 0


if __name__ == "__main__":
    sys.exit(main())
