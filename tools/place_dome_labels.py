#!/usr/bin/env python3
"""Put every key dome's reference label where it touches nothing.

The dome footprints carry their reference 0.8 mm above the ring, which is
right for a dome standing alone and wrong on this keypad: the rows are 12 mm
apart, so a 10 mm dome's mask opening reaches to within 1.5 mm of the one
above, and the label lands in that dome's opening. KiCad calls it
silk_over_copper and the fab clips it, so it prints as fragments (Barnaby's
3D view, 30 September 2026).

For each dome this tries a short list of spots, in order of how plainly they
read as belonging to that dome, and takes the first whose text box keeps
CLEAR away from every mask opening, every exposed front pad, every label
already placed and the board edge:

    above the ring, upright        -- where the footprint puts it
    left of the ring, turned 90    -- the 4.5 mm gap between numeric keys,
                                      and first choice for the 10 mm domes
    the same two in 0.8 mm text

    python3 tools/place_dome_labels.py --check   # report, write nothing
    python3 tools/place_dome_labels.py           # write the board
"""

import re
import sys
from pathlib import Path

from shapely.geometry import Polygon, box
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).parent))
import route_power as rp            # noqa: E402  the board reader lives there

ROOT = Path(__file__).resolve().parent.parent
PCB = ROOT / "elec/layout/default/default.kicad_pcb"

CLEAR = 0.2      # text box to any mask opening, exposed pad or other label
EDGE = 0.3       # text box to the board edge
ADVANCE = 0.95   # KiCad's stroke font, per character, as a fraction of size
                 # (generous: a real "SW25" at 1.0 mm is about 3.4 mm long)


def text_box(x, y, n, size, thick, turned):
    w = n * ADVANCE * size + thick
    h = size + thick
    if turned:
        w, h = h, w
    return box(x - w / 2, y - h / 2, x + w / 2, y + h / 2)


def candidates(r):
    """(dx, dy, angle, size) spots for a ring of half-width r, best first.

    Each sits just outside the dome's own mask opening, which is 0.25 mm
    beyond the ring, with CLEAR to spare.
    """
    a = r + 0.25 + CLEAR + 0.01
    out = []
    for size in (1.0, 0.8):
        h = (size + (0.15 if size >= 1.0 else 0.12)) / 2
        above, left = (0, -(a + h), 0, size), (-(a + h), 0, 90, size)
        # The 10 mm numeric keys all go on the left, so the block reads the
        # same all the way down; only the bottom three rows are forced there.
        out += [left, above] if r >= 5 else [above, left]
    return out


def footprints(text):
    for m in re.finditer(r'\n\t\(footprint "', text):
        start = m.start() + 2
        yield start, rp.block_at(text, start)


def mask_openings(text):
    """Front mask openings: every F.Mask pad of every footprint."""
    out = []
    for _s, blk in footprints(text):
        at = rp.FP_AT.search(blk)
        fx, fy = float(at.group(1)), float(at.group(2))
        fr = float(at.group(3)) if at.group(3).strip() else 0.0
        for pm in re.finditer(r'\n\t\t\(pad "', blk):
            pad = rp.block_at(blk, pm.start() + 2)
            lay = re.search(r'\(layers ([^)]*)\)', pad)
            if not lay or not re.search(r'"F\.Mask"|"\*\.Mask"', lay.group(1)):
                continue
            pat = re.search(r'\(at (-?[\d.]+) (-?[\d.]+)(?: (-?[\d.]+))?\)', pad)
            rx, ry = rp.rot(float(pat.group(1)), float(pat.group(2)), fr)
            polys = rp.pad_shapes(pad, fx + rx, fy + ry,
                                  float(pat.group(3) or 0.0))
            out.append(unary_union([Polygon(q).buffer(0) for q in polys]))
    return unary_union(out)


def main():
    check = "--check" in sys.argv
    text = PCB.read_text()
    blocked = mask_openings(text).buffer(CLEAR)
    x0, y0, x1, y1 = rp.board_box(text)
    inside = box(x0 + EDGE, y0 + EDGE, x1 - EDGE, y1 - EDGE)

    placed = []
    edits = []
    failed = []
    for start, blk in footprints(text):
        m = re.match(r'\(footprint "hp42s:Dome_4Leg_([\d.]+)mm"', blk)
        if not m:
            continue
        r = float(m.group(1)) / 2
        ref = rp.REF_RE.search(blk).group(1)
        at = rp.FP_AT.search(blk)
        fx, fy = float(at.group(1)), float(at.group(2))
        for dx, dy, ang, size in candidates(r):
            thick = 0.15 if size >= 1.0 else 0.12
            tb = text_box(fx + dx, fy + dy, len(ref), size, thick, ang == 90)
            if (tb.intersects(blocked) or not inside.contains(tb)
                    or any(tb.distance(p) < CLEAR for p in placed)):
                continue
            placed.append(tb)
            edits.append((start, blk, ref, dx, dy, ang, size, thick))
            break
        else:
            failed.append(ref)

    def num(ref):
        return int(ref[2:])
    for _s, _b, ref, dx, dy, ang, size, _t in sorted(edits, key=lambda e: num(e[2])):
        where = "above" if ang == 0 else "left, turned"
        print(f"  {ref:5s} {where:13s} ({dx:+.3f}, {dy:+.3f}) {size:.1f} mm")
    if failed:
        print("no clear spot for: " + ", ".join(failed))
        return 1
    if check:
        print("--check: nothing written")
        return 0

    out = text
    for start, blk, ref, dx, dy, ang, size, thick in sorted(edits, reverse=True):
        prop = re.search(r'\(property "Reference" "[^"]+"', blk)
        pblk = rp.block_at(blk, prop.start())
        ang_s = f" {ang}" if ang else " 0"
        new = re.sub(r'\(at -?[\d.]+ -?[\d.]+(?: -?[\d.]+)?\)',
                     f"(at {dx:g} {dy:g}{ang_s})", pblk, count=1)
        new = re.sub(r'\(size [\d.]+ [\d.]+\)', f"(size {size:g} {size:g})",
                     new, count=1)
        new = re.sub(r'\(thickness [\d.]+\)', f"(thickness {thick:g})",
                     new, count=1)
        nblk = blk.replace(pblk, new, 1)
        out = out[:start] + nblk + out[start + len(blk):]
    PCB.write_text(out)
    print(f"{len(edits)} dome labels placed; wrote {PCB.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
