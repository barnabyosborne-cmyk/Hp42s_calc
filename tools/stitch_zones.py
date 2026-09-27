#!/usr/bin/env python3
"""Tie the inner ground islands to the ground plane.

Step 8.3b carves three ground islands out of the 3.3 V plane on `In2.Cu`, so
that the three switching nodes have a return directly underneath them. Copper
on an inner layer can only be reached by a via, and those three had none, so
KiCad reported them as `isolated_copper` and they were doing nothing at all:
an island of metal with no connection is not a ground, it is an antenna.

This places stitching vias inside each island -- plain vias on `gnd` with no
track, which is all a zone needs, because every pour of the net fills up to a
via of its own net and bonds to it. A through via also passes through the
`B.Cu` pour and the `In1.Cu` plane on its way, so one via ties all three.

    python3 tools/stitch_zones.py --check   # report, write nothing
    python3 tools/stitch_zones.py           # place them

Ownership: a via is this script's if its uuid is the one this script would
generate for that net at that spot, so it removes its own stitching vias and
nothing else -- not the gnd tails route_signals.py writes, not a via drawn by
hand; `route_power.py` owns the nets in its own table. Getting that
wrong once would have had each script quietly delete the other's work.
"""

import math
import re
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import route_power as rp            # noqa: E402  the board reader lives there

ROOT = Path(__file__).resolve().parent.parent
PCB = ROOT / "elec/layout/default/default.kicad_pcb"

NET = "gnd"
LAYER = "In2.Cu"
NS = uuid.UUID("9a3c17be-0000-4000-8000-000000000092")

INSET = rp.VIA_D / 2 + 0.3       # keep the whole annulus inside the fill
SPACING = 3.0                    # nearest two stitching vias may sit
GRID = 0.5
PER_MM2 = 1 / 30.0               # one via per 30 mm2 of island
MOST = 8


def islands(text):
    """The ground zones on the inner 3.3 V layer, smallest first.

    The full-board pours are on `B.Cu` and `In1.Cu`, so layer plus net picks
    out the three step 8.3b islands and nothing else. A fourth one added later
    is picked up without changing this script.
    """
    out = []
    for m in re.finditer(r"\n\t\(zone\n", text):
        blk = rp.block_at(text, m.start() + 1)
        if "(keepout" in blk:
            continue
        net = re.search(r'\(net "([^"]+)"\)', blk)
        lay = re.search(r"\(layers? \"([^\"]+)\"\)", blk)
        if not net or not lay or net.group(1) != NET or lay.group(1) != LAYER:
            continue
        poly = re.search(r"\(polygon\b", blk)
        if not poly:
            continue
        pts = [(float(a), float(b)) for a, b in re.findall(
            r"\(xy (-?[\d.]+) (-?[\d.]+)\)", rp.block_at(blk, poly.start()))]
        if len(pts) >= 3:
            out.append(pts)
    return sorted(out, key=area)


def area(poly):
    s = 0.0
    for i, (x, y) in enumerate(poly):
        x2, y2 = poly[(i + 1) % len(poly)]
        s += x * y2 - x2 * y
    return abs(s) / 2


def inside_by(pt, poly):
    """How far this point is inside the polygon; negative when outside."""
    d = min(rp.pt_seg_gap(pt, poly[i], poly[(i + 1) % len(poly)])
            for i in range(len(poly)))
    return d if rp.pt_in_poly(pt, poly) else -d


def read_copper(text):
    """The tracks and vias already on the board, from the board itself."""
    segs, vias = [], []
    for m in re.finditer(
            r"\(segment\n\s*\(start ([-\d.]+) ([-\d.]+)\)\n\s*\(end "
            r"([-\d.]+) ([-\d.]+)\)\n\s*\(width ([\d.]+)\)\n\s*"
            r"\(layer \"([^\"]+)\"\)\n\s*\(net \"([^\"]+)\"\)", text):
        x1, y1, x2, y2, w, lay, net = m.groups()
        segs.append((net, lay, (float(x1), float(y1)),
                     (float(x2), float(y2)), float(w)))
    for x, y, net in re.findall(
            r"\(via\n\s*\(at ([-\d.]+) ([-\d.]+)\)[\s\S]*?\(net \"([^\"]+)\"\)",
            text):
        vias.append((net, float(x), float(y)))
    return segs, vias


def legal(pt, poly, pads, keepouts, box, segs, vias, placed):
    """Why this spot will not take a stitching via, or None if it will."""
    x, y = pt
    if inside_by(pt, poly) < INSET:
        return "not far enough inside the island"
    name = rp.in_keepout(pt, keepouts, rp.VIA_D / 2, "via")
    if name:
        return f"inside {name!r}"
    bx0, by0, bx1, by1 = box
    edge = rp.EDGE_KEEP + rp.VIA_D / 2
    if not (bx0 + edge <= x <= bx1 - edge and by0 + edge <= y <= by1 - edge):
        return "too close to the board edge"
    for pad in pads:
        # Ground pads are the same net, so copper may touch; the drill still
        # has to land outside one, or this is a via in a pad and the fab has
        # to fill and cap it.
        need = (rp.VIA_DRILL / 2 + 0.05 if pad["net"] == NET
                else rp.CLEARANCE + rp.VIA_D / 2)
        if rp.pad_gap(pt, pt, pad, cutoff=need) < need:
            return f"{need:.2f} mm of {pad['ref']} pad {pad['pad']}"
    for net, _lay, p, q, w in segs:
        need = (rp.VIA_D / 2 + w / 2 if net == NET
                else rp.CLEARANCE + rp.VIA_D / 2 + w / 2)
        if rp.pt_seg_gap(pt, p, q) < need:
            return f"too close to a {net} track"
    for net, vx, vy in vias:
        need = rp.VIA_D + 0.2 if net == NET else rp.CLEARANCE + rp.VIA_D
        if math.dist(pt, (vx, vy)) < need:
            return f"too close to a {net} via"
    for px, py in placed:
        if math.dist(pt, (px, py)) < SPACING:
            return "too close to another stitching via"
    return None


def spread(candidates, want):
    """Farthest-point sampling: take the most spread-out `want` of them.

    Stitching is about bonding the whole island, so vias clustered in the one
    roomy corner would satisfy the rule check and leave the far end as bad as
    it was.
    """
    if not candidates:
        return []
    cx = sum(p[0] for p in candidates) / len(candidates)
    cy = sum(p[1] for p in candidates) / len(candidates)
    picked = [max(candidates, key=lambda p: math.dist(p, (cx, cy)))]
    while len(picked) < want:
        rest = [p for p in candidates if p not in picked]
        if not rest:
            break
        picked.append(max(rest, key=lambda p: min(math.dist(p, q)
                                                  for q in picked)))
    return picked


def via(x, y):
    uid = uuid.uuid5(NS, f"stitch {NET} {x} {y}")
    return (f"\t(via\n"
            f"\t\t(at {rp.fmt(x)} {rp.fmt(y)})\n"
            f"\t\t(size {rp.fmt(rp.VIA_D)})\n"
            f"\t\t(drill {rp.fmt(rp.VIA_DRILL)})\n"
            f"\t\t(layers \"F.Cu\" \"B.Cu\")\n"
            f"\t\t(net \"{NET}\")\n"
            f"\t\t(uuid \"{uid}\")\n"
            f"\t)\n")


def strip_ours(text):
    """Remove the stitching vias a previous run wrote, and nothing else."""
    removed = 0
    while True:
        hit = None
        for m in rp.OURS.finditer(text):
            net = re.search(r'\(net "([^"]+)"\)', m.group(0))
            if not net or net.group(1) != NET:
                continue
            if "(via" not in m.group(0):
                continue
            # Ours only if the uuid is the one via() would give this very
            # via. A v5 uuid on a gnd via is not enough: route_signals.py
            # writes gnd vias too, for the pads the pour cannot reach.
            at = re.search(r'\(at (\S+) (\S+)\)', m.group(0))
            x, y = float(at.group(1)), float(at.group(2))
            if m.group(1) == str(uuid.uuid5(NS, f"stitch {NET} {x} {y}")):
                hit = m
                break
        if not hit:
            return text, removed
        text = text[:hit.start()] + text[hit.end():]
        removed += 1


def main():
    check = "--check" in sys.argv
    text = PCB.read_text()
    text, removed = strip_ours(text)

    pads = rp.read_pads(text)
    keepouts = rp.read_keepouts(text)
    box = rp.board_box(text)
    segs, vias = read_copper(text)
    zones = islands(text)
    if not zones:
        print(f"no {NET} zones on {LAYER}: nothing to stitch")
        return 1

    print(f"{len(zones)} ground island(s) on {LAYER}"
          + (f", after dropping {removed} via(s) from a previous run" if removed
             else ""))
    placed, problems = [], []
    for poly in zones:
        x0 = min(p[0] for p in poly)
        x1 = max(p[0] for p in poly)
        y0 = min(p[1] for p in poly)
        y1 = max(p[1] for p in poly)
        a = area(poly)
        want = max(2, min(MOST, round(a * PER_MM2)))

        ok, why = [], {}
        n = 0
        while x0 + n * GRID <= x1:
            x = x0 + n * GRID
            n += 1
            m = 0
            while y0 + m * GRID <= y1:
                y = y0 + m * GRID
                m += 1
                bad = legal((x, y), poly, pads, keepouts, box, segs, vias, [])
                if bad:
                    why[bad] = why.get(bad, 0) + 1
                else:
                    ok.append((round(x, 3), round(y, 3)))

        chosen = []
        for pt in spread(ok, want):
            if not legal(pt, poly, pads, keepouts, box, segs, vias,
                         chosen + placed):
                chosen.append(pt)
        placed.extend(chosen)

        where = f"x {x0:.1f}..{x1:.1f}, y {y0:.1f}..{y1:.1f}"
        print(f"   island {where} ({a:.0f} mm2): wanted {want}, "
              f"{len(ok)} legal spots, placed {len(chosen)}")
        for pt in chosen:
            print(f"      via at ({pt[0]:.3f}, {pt[1]:.3f})")
        if not chosen:
            problems.append(f"island at {where} has nowhere to put a via; "
                            f"commonest reason: "
                            f"{max(why, key=why.get) if why else 'unknown'}")

    if problems:
        print(f"\n{len(problems)} PROBLEM(S) -- nothing written:\n")
        for p in problems:
            print(f"   {p}")
        return 1

    print(f"\n{len(placed)} stitching via(s), all clear of the rule")
    if check:
        print("--check: nothing written")
        return 0

    end = text.rindex("\n)")
    body = "".join(via(x, y) for x, y in placed)
    PCB.write_text(text[:end] + "\n" + body.rstrip("\n") + text[end:])
    print(f"wrote {PCB.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
