#!/usr/bin/env python3
"""
Put every pad back on its own footprint.

    python3 tools/fix_pads.py --check          # report, change nothing
    python3 tools/fix_pads.py                  # repair the board

WHAT WENT WRONG
---------------
In default.kicad_pcb every footprint's pads were sitting about 1.1 metres
away from the footprint they belong to, while the silkscreen, the courtyard
and the fabrication outline were all in the right place. Every pad on the
board had the same offset applied -- (-702.5, -880.5) for the parts at 0
degrees, (1212.5, 1211.5) for the four the keypad script rotated 180, and
(1301.0, -1121.4) for the flipped FPC connector -- so all 119 footprints'
pads landed on top of each other in one pile off the side of the board.

That pile is what showed up in KiCad as a cluster of copper nowhere near
anything. It was there from the first save, before any of the placement
scripts wrote to the file, so it came from the netlist import itself.

KiCad's board format is explicit that "all coordinates are relative to the
origin of their containing object", so a pad's (at x y) is measured from its
footprint's own origin, not from the board's. The pad's third number, its
angle, is the exception: that one does include the footprint's rotation,
which is why this script never touches it.

HOW THE REPAIR WORKS
--------------------
For each footprint it loads the library footprint it was placed from, works
out the single translation between the library's pad positions and the
board's, and subtracts it. Then it checks the result: every pad must match
the library exactly, name for name and position for position. If any
footprint does not come out exact, nothing is written.

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
# A pad's own (at ...), wherever the file puts its line breaks.
PAD_RE = re.compile(
    r'(\(pad "([^"]*)" \w+ \w+\s*\(at )(-?[\d.]+) (-?[\d.]+)'
    r'(?: (-?[\d.]+))?(\))')
FP_AT_RE = re.compile(r'\n\t\t\(at (-?[\d.]+) (-?[\d.]+)((?: -?[\d.]+)?)\)')
TOL = 0.0015   # KiCad rounds to the nanometre; 1 um of slop is normal


def lib_pads(lib_id, libdirs):
    """The pad list of a library footprint, as [(name, x, y), ...]."""
    lib, name = lib_id.split(":", 1)
    for d in libdirs:
        for cand in (d / f"{lib}.pretty" / f"{name}.kicad_mod",
                     d / f"{lib}__{name}.kicad_mod"):
            if cand.exists():
                text = cand.read_text()
                return [(m.group(2), float(m.group(3)), float(m.group(4)),
                         float(m.group(5) or 0.0))
                        for m in PAD_RE.finditer(text)]
    if lib == "hp42s":
        cand = HP42S / f"{name}.kicad_mod"
        if cand.exists():
            text = cand.read_text()
            return [(m.group(2), float(m.group(3)), float(m.group(4)),
                     float(m.group(5) or 0.0))
                    for m in PAD_RE.finditer(text)]
    return None


def match(board, want):
    """Find the translation between two pad lists, and the y mirror.

    A footprint on the back of the board has its children stored mirrored in
    y, so the library's y has to be negated before the two can be compared.
    Returns (dx, dy, worst error) for whichever way round fits better.
    """
    best = None
    for mirror in (1, -1):
        lib = [(n, x, mirror * y) for n, x, y, _a in want]
        by_name = defaultdict(list)
        for n, x, y in lib:
            by_name[n].append((x, y))
        for v in by_name.values():
            v.sort()
        pairs = []
        seen = defaultdict(list)
        for n, x, y in board:
            seen[n].append((x, y))
        ok = True
        for n, v in seen.items():
            if len(v) != len(by_name.get(n, [])):
                ok = False
                break
            for (bx, by), (lx, ly) in zip(sorted(v), by_name[n]):
                pairs.append((bx - lx, by - ly))
        if not ok or not pairs:
            continue
        dx = sorted(d[0] for d in pairs)[len(pairs) // 2]
        dy = sorted(d[1] for d in pairs)[len(pairs) // 2]
        err = max(max(abs(a - dx), abs(b - dy)) for a, b in pairs)
        if best is None or err < best[2]:
            best = (dx, dy, err, mirror)
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="report and change nothing")
    ap.add_argument("--libdir", action="append", type=Path, default=[],
                    help="a KiCad footprint library directory (repeatable)")
    args = ap.parse_args()
    libdirs = args.libdir or [MAC_LIBS]

    text = PCB.read_text()
    head, *blocks = text.split(FP_SPLIT)

    out, fixed, clean, failed, turned = [], 0, 0, [], []
    offsets = defaultdict(list)
    for block in blocks:
        ref = REF_RE.search(block).group(1)
        lib_id = block.splitlines()[0].strip().strip('"')
        fm = FP_AT_RE.search(block)
        fp_rot = float(fm.group(3)) if fm.group(3).strip() else 0.0
        board = [(m.group(2), float(m.group(3)), float(m.group(4)),
                  float(m.group(5) or 0.0))
                 for m in PAD_RE.finditer(block)]
        want = lib_pads(lib_id, libdirs)
        if want is None:
            failed.append(f"{ref}: no library footprint for {lib_id}")
            out.append(block)
            continue
        if len(want) != len(board):
            failed.append(f"{ref}: {len(board)} pads on the board, "
                          f"{len(want)} in {lib_id}")
            out.append(block)
            continue
        got = match([(n, x, y) for n, x, y, _a in board], want)
        if got is None or got[2] > TOL:
            failed.append(f"{ref}: pads do not line up with {lib_id}"
                          + (f", out by {got[2]:.3f} mm" if got else ""))
            out.append(block)
            continue
        dx, dy, _err, mirror = got
        # A pad's angle is absolute: it carries the footprint's rotation. On
        # the back of the board the whole footprint is mirrored, so the
        # library's angles turn the other way.
        angles = {}
        by_name = defaultdict(list)
        for n, x, y, a in want:
            by_name[n].append((x, mirror * y, (mirror * a + fp_rot) % 360))
        for v in by_name.values():
            v.sort()
        seen = defaultdict(list)
        for n, x, y, a in board:
            seen[n].append((x - dx, y - dy, a))
        for n, v in seen.items():
            for (bx, by, ba), (lx, ly, la) in zip(sorted(v), by_name[n]):
                if abs((ba - la + 180) % 360 - 180) > 0.01:
                    angles[(n, round(bx, 3), round(by, 3))] = la
        if abs(dx) < TOL and abs(dy) < TOL and not angles:
            clean += 1
            out.append(block)
            continue
        if abs(dx) >= TOL or abs(dy) >= TOL:
            offsets[(round(dx, 3), round(dy, 3))].append(ref)
        if angles:
            turned.append(f"{ref}: {len(angles)} pad angles")
        fixed += 1

        def rewrite(m):
            x, y = float(m.group(3)) - dx, float(m.group(4)) - dy
            a = angles.get((m.group(2), round(x, 3), round(y, 3)),
                           float(m.group(5) or 0.0))
            tail = f" {a:g}" if a else ""
            return f"{m.group(1)}{x:g} {y:g}{tail}{m.group(6)}"

        out.append(PAD_RE.sub(rewrite, block))

    for (dx, dy), refs in sorted(offsets.items(), key=lambda kv: -len(kv[1])):
        print(f"({dx:>8.3f}, {dy:>9.3f})  {len(refs):>3} footprint{'s' if len(refs) != 1 else ''}: "
              f"{', '.join(sorted(refs)[:6])}"
              f"{' ...' if len(refs) > 6 else ''}")
    for line in turned:
        print("  turned: " + line)
    print(f"{fixed} footprints with pads out of place, "
          f"{clean} already correct")

    if failed:
        print("\nNOT REPAIRED:")
        for f in failed:
            print("  " + f)

    if args.check:
        return 1 if fixed or failed else 0
    if failed:
        print("\nNothing written: fix the above first.")
        return 1
    PCB.write_text(head + FP_SPLIT + FP_SPLIT.join(out))
    print(f"\nwrote {PCB.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
