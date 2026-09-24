#!/usr/bin/env python3
"""
Put a via keepout over every dome site.

    python3 tools/dome_keepouts.py           # write them
    python3 tools/dome_keepouts.py --check   # report, change nothing

WHY
---
A metal dome is a shallow disc that has to sit FLAT on its ring. A via inside
that ring lifts it, and a lifted dome either never closes or closes at the
wrong force. Nothing in the board file says so: to KiCad the dome site is two
copper shapes and some silkscreen, and a router asked to find its way out of a
6x7 matrix will drop a via in the middle of one without hesitating.

docs/layout-walkthrough.md step 9.5 already routes the matrix this way by hand,
from the same reasoning. A rule in a walkthrough is not a rule an autorouter can
read, and step 9a hands the keypad matrix to Freerouting deliberately, so the
rule has to exist in the board.

WHAT IT WRITES
--------------
One rule area per dome, named `dome via keepout <ref>`, on all four copper
layers, with the dome's own courtyard as its outline:

    tracks      allowed       -- the matrix has to get through here
    vias        NOT allowed   -- the whole point
    pads        allowed
    copperpour  allowed       -- the ground planes are not the problem
    footprints  allowed

The courtyard is an octagon 0.25 mm outside the disc, which is what the
footprints already draw and what check_placement.py measures against. Using it
rather than a bounding square leaves the diagonal gaps between adjacent domes
open, and on a 12 mm pitch with 8.5 and 10 mm domes those gaps are most of the
room the router has.

KiCad 10 exports a board-level rule area to Specctra as a keepout per copper
layer, and one that disallows vias only becomes a `via_keepout` -- read out of
pcbnew/specctra_import_export/specctra_export.cpp on 24 September 2026, so
Freerouting sees these. Run it before any autoroute pass over the keypad.

It is idempotent: every zone it wrote before is removed first, so re-running
after the domes move is the way to update them.
"""

import math
import re
import sys
import uuid
from pathlib import Path

PCB = Path(__file__).resolve().parent.parent / "elec/layout/default/default.kicad_pcb"
FOOTPRINTS = Path(__file__).resolve().parent.parent / "elec/footprints/hp42s.pretty"

FP_SPLIT = "\n\t(footprint "
REF_RE = re.compile(r'\(property "Reference" "([^"]+)"')
AT_RE = re.compile(r'\n\t\t\(at (-?[\d.]+) (-?[\d.]+)((?: -?[\d.]+)?)\)')
CRTYD_RE = re.compile(r'\(fp_poly \(pts ((?:\(xy [-\d.]+ [-\d.]+\) ?)+)\).*?F\.CrtYd')
XY_RE = re.compile(r'\(xy (-?[\d.]+) (-?[\d.]+)\)')

NAME = "dome via keepout"
LAYERS = '"F.Cu" "B.Cu" "In1.Cu" "In2.Cu"'

# Deterministic uuids, so a re-run produces the same file and `git diff` stays
# readable. The namespace is arbitrary but fixed.
NS = uuid.UUID("6f1d2c4e-0000-4000-8000-000000000042")


def courtyard(library):
    """The footprint's F.CrtYd outline, as a list of (x, y) in its own frame."""
    path = FOOTPRINTS / f"{library}.kicad_mod"
    if not path.exists():
        sys.exit(f"no footprint at {path}")
    m = CRTYD_RE.search(path.read_text())
    if not m:
        sys.exit(f"{path.name} has no F.CrtYd polygon to use as an outline")
    return [(float(x), float(y)) for x, y in XY_RE.findall(m.group(1))]


def place(points, x, y, rot):
    """Turn a footprint-frame outline into board coordinates.

    A footprint's rotation in the board file turns its children the same way
    KiCad does: clockwise positive, (x, y) -> (x cos + y sin, -x sin + y cos).
    Every dome on this board is at 0, so this is here to be correct rather than
    because it is exercised -- which is also why it is worth having, since a
    dome that does get turned would otherwise get a keepout in the wrong place.
    """
    a = math.radians(rot)
    ca, sa = math.cos(a), math.sin(a)
    return [(x + px * ca + py * sa, y - px * sa + py * ca) for px, py in points]


def zone(ref, points):
    pts = " ".join(f"(xy {px:g} {py:g})" for px, py in points)
    uid = uuid.uuid5(NS, f"{NAME} {ref}")
    return f"""\t(zone
\t\t(layers {LAYERS})
\t\t(uuid "{uid}")
\t\t(name "{NAME} {ref}")
\t\t(hatch edge 0.5)
\t\t(connect_pads
\t\t\t(clearance 0)
\t\t)
\t\t(min_thickness 0.25)
\t\t(keepout
\t\t\t(tracks allowed)
\t\t\t(vias not_allowed)
\t\t\t(pads allowed)
\t\t\t(copperpour allowed)
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
\t\t\t\t{pts}
\t\t\t)
\t\t)
\t)
"""


def block_at(text, start):
    """The parenthesised block beginning at `start`, including both parens."""
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    raise ValueError("unbalanced parentheses")


def strip_old(text):
    """Remove the zones a previous run wrote. Returns (text, how many)."""
    removed = 0
    while True:
        m = re.search(r'\n\t\(zone\n(?:(?!\n\t\)).)*?\(name "' + NAME + r' [^"]*"\)',
                      text, re.S)
        if not m:
            return text, removed
        start = text.index("(zone", m.start())
        blk = block_at(text, start)
        # Take the leading tab and the trailing newline with it.
        text = text[:start - 1] + text[start + len(blk) + 1:]
        removed += 1


def main():
    check = "--check" in sys.argv
    text = PCB.read_text()

    domes = []
    for block in text.split(FP_SPLIT)[1:]:
        library = block.split('"')[1]
        if "Dome_4Leg" not in library:
            continue
        ref = REF_RE.search(block)
        at = AT_RE.search(block)
        if not (ref and at):
            sys.exit(f"a {library} footprint has no reference or position")
        rot = float(at.group(3) or 0.0)
        domes.append((ref.group(1), library.split(":")[-1],
                      float(at.group(1)), float(at.group(2)), rot))

    if not domes:
        sys.exit("no dome footprints on the board")

    outlines = {}
    zones = []
    for ref, library, x, y, rot in sorted(domes, key=lambda d: int(d[0][2:])):
        if library not in outlines:
            outlines[library] = courtyard(library)
        zones.append((ref, place(outlines[library], x, y, rot)))

    text, removed = strip_old(text)
    if removed:
        print(f"{removed} keepout(s) from a previous run "
              f"{'would be replaced' if check else 'replaced'}")

    sizes = {}
    for ref, library, *_ in domes:
        sizes[library] = sizes.get(library, 0) + 1
    for library, n in sorted(sizes.items()):
        print(f"{n} x {library}")

    xs = [p[0] for _r, pts in zones for p in pts]
    ys = [p[1] for _r, pts in zones for p in pts]
    print(f"{len(zones)} via keepouts, X {min(xs):.2f}..{max(xs):.2f}, "
          f"Y {min(ys):.2f}..{max(ys):.2f}")

    if check:
        print("--check: nothing written")
        return 0

    # The zones are the last thing in the file, inside the closing paren of the
    # board. Put ours at the end of them.
    end = text.rindex("\n)")
    body = "".join(zone(r, pts) for r, pts in zones).rstrip("\n")
    text = text[:end] + "\n" + body + text[end:]
    PCB.write_text(text)
    print(f"wrote {PCB.relative_to(PCB.parents[3])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
