#!/usr/bin/env python3
"""
Give every footprint the pads its library says it has.

    python3 tools/fix_pads.py --check          # report, change nothing
    python3 tools/fix_pads.py                  # repair the board

WHY THIS EXISTS
---------------
In default.kicad_pcb every footprint's pads were sitting about 1.1 metres
away from the footprint they belong to, while the silkscreen, the courtyard
and the fabrication outline were all in the right place. Every pad on the
board had the same offset applied -- (-702.5, -880.5) for the parts at 0
degrees, (1212.5, 1211.5) for the four at 180, (1301.0, -1123.0) for the
flipped FPC connector -- so all 119 footprints' pads landed on top of each
other in one pile off the side of the board.

That pile is what showed up in KiCad as a cluster of copper nowhere near
anything. It was there from the first save, before any of the placement
scripts wrote to the file, so it came from the netlist import itself.

KiCad's board format is explicit that "all coordinates are relative to the
origin of their containing object", so a pad's (at x y) is measured from its
footprint's own origin. That means the correct value is simply the library
footprint's, and this writes exactly that -- no offset, no guessing.

THE TWO THINGS THAT ARE NOT A STRAIGHT COPY
-------------------------------------------
A footprint on the BACK of the board has every coordinate inside it mirrored
in y, so the library's y is negated. And a pad's angle is absolute: it
carries the footprint's own rotation, so it comes out as the footprint's
rotation plus (or, on the back, minus) the library's angle.

Which side a footprint is on is read from the footprint's own layer, which
tools/place_board.py sets. So the order is always place_board.py first, this
second.

Library footprints come from --libdir. On a Mac with KiCad 10 installed the
default is already right; the hp42s ones are found in the repo.
"""

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PCB = ROOT / "elec/layout/default/default.kicad_pcb"
HP42S = ROOT / "elec/footprints/hp42s.pretty"
MAC_LIBS = Path("/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints")

FP_SPLIT = "\n\t(footprint "
REF_RE = re.compile(r'\(property "Reference" "([^"]+)"')
FP_AT_RE = re.compile(r'\n\t\t\(at (-?[\d.]+) (-?[\d.]+)((?: -?[\d.]+)?)\)')
SIDE_RE = re.compile(r'\(layer "([FB])\.Cu"\)')
PAD_RE = re.compile(
    r'(\(pad "([^"]*)" \w+ \w+\s*\(at )(-?[\d.]+) (-?[\d.]+)'
    r'(?: (-?[\d.]+))?(\))')
TOL = 0.0015   # KiCad rounds to the nanometre; 1 um of slop is normal


def lib_pads(lib_id, libdirs):
    """A library footprint's pads, as [(name, x, y, angle), ...]."""
    lib, name = lib_id.split(":", 1)
    for d in list(libdirs) + [HP42S.parent]:
        for cand in (d / f"{lib}.pretty" / f"{name}.kicad_mod",
                     d / f"{lib}__{name}.kicad_mod"):
            if cand.exists():
                return parse(cand.read_text())
    if lib == "hp42s" and (HP42S / f"{name}.kicad_mod").exists():
        return parse((HP42S / f"{name}.kicad_mod").read_text())
    return None


def parse(text):
    return [(m.group(2), float(m.group(3)), float(m.group(4)),
             float(m.group(5) or 0.0)) for m in PAD_RE.finditer(text)]


def targets(want, side, fp_rot):
    """What each pad's (at x y angle) should be, grouped by pad name."""
    m = -1 if side == "B" else 1
    by_name = defaultdict(list)
    for n, x, y, a in want:
        by_name[n].append((x, m * y, round((m * a + fp_rot) % 360, 3)))
    for v in by_name.values():
        v.sort()
    return by_name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="report and change nothing")
    ap.add_argument("--libdir", action="append", type=Path, default=[],
                    help="a KiCad footprint library directory (repeatable)")
    args = ap.parse_args()
    libdirs = args.libdir or [MAC_LIBS]

    head, *blocks = PCB.read_text().split(FP_SPLIT)
    out, moved, clean, failed = [], [], 0, []

    for block in blocks:
        ref = REF_RE.search(block).group(1)
        lib_id = block.splitlines()[0].strip().strip('"')
        want = lib_pads(lib_id, libdirs)
        if want is None:
            failed.append(f"{ref}: no library footprint for {lib_id}")
            out.append(block)
            continue

        fm = FP_AT_RE.search(block)
        fp_rot = float(fm.group(3)) if fm.group(3).strip() else 0.0
        sm = SIDE_RE.search(block)
        side = sm.group(1) if sm else "F"
        by_name = targets(want, side, fp_rot)

        board = parse(block)
        if sorted(n for n, *_ in board) != sorted(n for n, *_ in want):
            failed.append(f"{ref}: its pads are not the ones in {lib_id}")
            out.append(block)
            continue

        # Pair board pads with library pads name by name, in sorted order.
        # Where a name repeats on this board the pads are symmetric and
        # carry the same net, so which of them gets which is immaterial.
        order = defaultdict(list)
        for n, x, y, a in sorted(board, key=lambda p: (p[0], p[1], p[2])):
            order[n].append((x, y, a))
        fix = {}
        for n, v in order.items():
            for (bx, by, ba), tgt in zip(v, by_name[n]):
                if (abs(bx - tgt[0]) > TOL or abs(by - tgt[1]) > TOL
                        or abs((ba - tgt[2] + 180) % 360 - 180) > 0.01):
                    fix[(n, bx, by)] = tgt

        if not fix:
            clean += 1
            out.append(block)
            continue
        moved.append(f"{ref}: {len(fix)} of {len(board)} pads")

        def rewrite(m):
            key = (m.group(2), float(m.group(3)), float(m.group(4)))
            if key not in fix:
                return m.group(0)
            x, y, a = fix[key]
            return f"{m.group(1)}{x:g} {y:g}{f' {a:g}' if a else ''}{m.group(6)}"

        out.append(PAD_RE.sub(rewrite, block))

    for line in moved[:12]:
        print("  " + line)
    if len(moved) > 12:
        print(f"  ... and {len(moved) - 12} more")
    print(f"{len(moved)} footprints with pads out of place, "
          f"{clean} already correct")

    if failed:
        print("\nNOT REPAIRED:")
        for f in failed:
            print("  " + f)

    if args.check:
        return 1 if moved or failed else 0
    if failed:
        print("\nNothing written: fix the above first.")
        return 1
    PCB.write_text(head + FP_SPLIT + FP_SPLIT.join(out))
    print(f"\nwrote {PCB.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
