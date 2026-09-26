#!/usr/bin/env python3
"""Put each footprint's embedded rule area back where its footprint is.

A zone drawn inside a footprint -- the Alps switch's prohibited copper area,
the ESP module's antenna keepout -- is stored in the board file in *board*
co-ordinates, not in the footprint's own frame the way its pads and silkscreen
are. `place_board.py` moves a footprint by rewriting its `(at ...)` and letting
KiCad rebuild everything local, so the zone is the one thing that does not
come with it: it stays wherever it was when the netlist was first imported.

On this board all three of them were left roughly 600 mm off the south-west
corner, which means they forbid nothing, and KiCad reports each one as a
`lib_footprint_mismatch` because the board's copy no longer matches the
library's. This script reads the library footprint, rotates its zone into
place, and writes the polygon the board should have had.

    python3 tools/fix_footprint_zones.py --check   # report, write nothing
    python3 tools/fix_footprint_zones.py           # fix what it can

A footprint from a library we do not carry here (KiCad's own RF_Module, say)
cannot be checked against anything, so it is reported and left alone.
"""

import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOARD = ROOT / "elec/layout/default/default.kicad_pcb"
LIBS = {"hp42s": ROOT / "elec/footprints/hp42s.pretty"}
TOL = 0.001


def block_at(text, i):
    """The s-expression starting at or just after index i, braces balanced."""
    i = text.index("(", i)
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "(":
            depth += 1
        elif text[j] == ")":
            depth -= 1
            if depth == 0:
                return text[i:j + 1], i, j + 1
    raise ValueError("unbalanced s-expression")


def rot(x, y, deg):
    """Rotate a footprint-local point by the footprint's rotation.

    KiCad's y axis points down, so a positive rotation turns clockwise on
    screen; the negative angle here is what makes that come out right.
    """
    a = math.radians(-deg)
    return x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)


def zones_of(block):
    """Every `(zone ...)` inside this block, as (text, start, end)."""
    out = []
    for m in re.finditer(r"\(zone\n", block):
        out.append(block_at(block, m.start()))
    return out


def polygon_of(zone):
    """The zone's `(polygon ...)` points, and the span that block occupies.

    Read with balanced brackets rather than a lazy regex: `(.*?)\)\s*\)` ends
    one bracket early and silently drops the last vertex of the ring.
    """
    m = re.search(r"\(polygon\b", zone)
    if not m:
        return None, None
    blk, a, b = block_at(zone, m.start())
    pts = [(float(x), float(y))
           for x, y in re.findall(r"\(xy (-?[\d.]+) (-?[\d.]+)\)", blk)]
    return pts, (a, b)


def library_polygon(lib, name):
    """The zone polygon of a library footprint, in footprint-local mm."""
    d = LIBS.get(lib)
    if d is None:
        return None
    f = d / (name + ".kicad_mod")
    if not f.exists():
        return None
    zones = zones_of(f.read_text())
    if len(zones) != 1:
        return None
    pts, _ = polygon_of(zones[0][0])
    return pts


def same(a, b):
    if a is None or b is None or len(a) != len(b):
        return False
    # KiCad is free to start the ring at any vertex and wind either way.
    n = len(a)
    for flip in (a, a[::-1]):
        for k in range(n):
            r = flip[k:] + flip[:k]
            if all(abs(p[0] - q[0]) < TOL and abs(p[1] - q[1]) < TOL
                   for p, q in zip(r, b)):
                return True
    return False


def main():
    check = "--check" in sys.argv[1:]
    text = BOARD.read_text()
    edits = []          # (absolute start, absolute end, replacement)
    unknown, ok = [], []

    for m in re.finditer(r"\n\t\(footprint ", text):
        fp, fp0, _ = block_at(text, m.start())
        libname = re.match(r'\(footprint "([^"]+)"', fp).group(1)
        ref = re.search(r'\(property "Reference" "([^"]+)"', fp)
        ref = ref.group(1) if ref else "?"
        at = re.search(r"\n\t\t\(at (-?[\d.]+) (-?[\d.]+)(?: (-?[\d.]+))?\)", fp)
        if not at:
            continue
        fx, fy = float(at.group(1)), float(at.group(2))
        fa = float(at.group(3) or 0)

        for zone, z0, z1 in zones_of(fp):
            name = re.search(r'\(name "([^"]*)"\)', zone)
            name = name.group(1) if name else "unnamed"
            have, span = polygon_of(zone)
            if have is None:
                continue
            lib, _, fpname = libname.partition(":")
            want = library_polygon(lib, fpname)
            if want is None:
                off = min(math.hypot(x - fx, y - fy) for x, y in have)
                unknown.append((ref, libname, name, off))
                continue
            want = [(fx + dx, fy + dy) for dx, dy in (rot(x, y, fa) for x, y in want)]
            if same(have, want):
                ok.append((ref, name))
                continue
            off = min(math.hypot(x - fx, y - fy) for x, y in have)
            print(f"{ref} ({libname}) rule area {name!r}: nearest corner is "
                  f"{off:.1f} mm from the footprint")
            print("   is    " + " ".join(f"({x:g} {y:g})" for x, y in have))
            print("   wants " + " ".join(f"({x:g} {y:g})" for x, y in want))
            body = "(polygon\n\t\t\t\t(pts\n\t\t\t\t\t" + \
                   " ".join(f"(xy {x:g} {y:g})" for x, y in want) + \
                   "\n\t\t\t\t)\n\t\t\t)"
            a = fp0 + z0 + span[0]
            b = fp0 + z0 + span[1]
            edits.append((a, b, body))

    for ref, libname, name, off in unknown:
        print(f"{ref} ({libname}) rule area {name!r}: no library here to check "
              f"it against; nearest corner is {off:.1f} mm from the footprint")
    if ok:
        print("already in place: " + ", ".join(f"{r} {n!r}" for r, n in ok))

    if not edits:
        print("nothing to move")
        return
    if check:
        print(f"{len(edits)} rule area(s) would move; nothing written")
        return
    for a, b, body in sorted(edits, reverse=True):
        text = text[:a] + body + text[b:]
    BOARD.write_text(text)
    print(f"moved {len(edits)} rule area(s); wrote {BOARD.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
