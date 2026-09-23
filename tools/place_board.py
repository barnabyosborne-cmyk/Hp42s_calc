#!/usr/bin/env python3
"""
Place the board by rewriting default.kicad_pcb directly.

    python3 tools/place_board.py

Run it with KiCad CLOSED, then open the board.

WHY NOT THE SCRIPTING CONSOLE
-----------------------------
place_keypad.py asks KiCad's SWIG API to put footprints at absolute
millimetre positions. Under KiCad 10.0 on 23 September 2026 that did not
work: every footprint it touched landed hundreds of millimetres from where it
was asked, by a different amount on each run (414.5 mm, then 345.0 mm), while
board outline and comment rectangles drawn through the same API in the same
run landed exactly right. Reading a position back through the API returned the
value we had asked for, so the script could not even detect the problem.

This does the same arithmetic and writes the co-ordinates into the file, where
they can be checked by eye and by `git diff`. The numbers come from the same
place they always did: Barnaby's measurements of a real HP-42S, via
place_keypad.py, which stays the reference for where every key goes.

WHAT IT SETS
------------
The 38 dome sites, the six top-edge parts and the panel FPC, at the positions
docs/keypad-geometry.md and docs/display-mounting.md give. Rotations and layer
assignments are left exactly as they are: those came through the API
correctly, and are already right in the file.

The other 74 parts have not been placed yet -- step 7 of the walkthrough is
placing them by hand. They are moved as a block to sit just right of the
board, keeping their arrangement, so they are somewhere sensible to drag from
rather than 600 mm off the page.
"""

import re
import sys
from pathlib import Path

PCB = Path(__file__).resolve().parent.parent / "elec/layout/default/default.kicad_pcb"

CASE_H = 148.0
INSET = 2.0

# --- the key grid, in case coordinates, from place_keypad.py ----------------
ROW_Y = [84.0, 72.0, 60.0, 48.0, 36.0, 24.0, 12.0]
COL_TOP = [8.75, 21.25, 33.75, 46.25, 58.75, 71.25]
COL_PAD = [25.0, 40.0, 55.0, 70.0]
COL_LEFT = 8.75

KEYS = {}
for _i, _ref in enumerate(["SW1", "SW2", "SW3", "SW4", "SW5", "SW6"]):
    KEYS[_ref] = (COL_TOP[_i], ROW_Y[0])
for _i, _ref in enumerate(["SW7", "SW8", "SW9", "SW10", "SW11", "SW12"]):
    KEYS[_ref] = (COL_TOP[_i], ROW_Y[1])
for _i, _ref in enumerate(["SW13", "SW38", "SW14", "SW15", "SW16", "SW17"]):
    KEYS[_ref] = (COL_TOP[_i], ROW_Y[2])
for _row, _refs in enumerate([
    ["SW18", "SW19", "SW20", "SW21", "SW22"],
    ["SW23", "SW24", "SW25", "SW26", "SW27"],
    ["SW28", "SW29", "SW30", "SW31", "SW32"],
    ["SW33", "SW34", "SW35", "SW36", "SW37"],
], start=3):
    KEYS[_refs[0]] = (COL_LEFT, ROW_Y[_row])
    for _i, _ref in enumerate(_refs[1:]):
        KEYS[_ref] = (COL_PAD[_i], ROW_Y[_row])


def to_board(x_case, y_case):
    return x_case - INSET, (CASE_H - y_case) - INSET


# --- everything, in board coordinates --------------------------------------
TARGETS = {ref: to_board(*xy) for ref, xy in KEYS.items()}

# Top-edge parts and the panel FPC. Y is depth from the board's top edge.
TARGETS.update({
    "SW39": (11.0, 3.00),      # C&K power slider
    "D4":   (22.0, 1.60),      # IR emitter
    "J1":   (36.0, 3.675),     # USB-C
    "D5":   (48.0, 1.80),      # status LED
    "SW41": (57.0, 1.50),      # boot
    "SW40": (66.0, 1.50),      # reset
    "J2":   (9.00, 30.15),     # panel FPC, on the back
})

# Where the unplaced block goes: clear of the board's right edge at X 76.
HEAP_ORIGIN = (90.0, 20.0)

FP_SPLIT = "\n\t(footprint "
AT_RE = re.compile(r'(\n\t\t\(at )(-?[\d.]+) (-?[\d.]+)((?: -?[\d.]+)?\))')
REF_RE = re.compile(r'\(property "Reference" "([^"]+)"')


def main():
    text = PCB.read_text()
    head, *blocks = text.split(FP_SPLIT)

    refs = [REF_RE.search(b).group(1) for b in blocks]

    # The heap keeps its shape, so work out its corner before moving anything.
    heap = [i for i, r in enumerate(refs) if r not in TARGETS]
    coords = []
    for i in heap:
        m = AT_RE.search(blocks[i])
        coords.append((float(m.group(2)), float(m.group(3))))
    dx = HEAP_ORIGIN[0] - min(c[0] for c in coords)
    dy = HEAP_ORIGIN[1] - min(c[1] for c in coords)

    out, moved = [], 0
    for i, block in enumerate(blocks):
        ref = refs[i]
        m = AT_RE.search(block)
        if ref in TARGETS:
            x, y = TARGETS[ref]
        else:
            x, y = float(m.group(2)) + dx, float(m.group(3)) + dy
        new = f"{m.group(1)}{x:g} {y:g}{m.group(4)}"
        out.append(block[:m.start()] + new + block[m.end():])
        moved += 1

    PCB.write_text(head + FP_SPLIT + FP_SPLIT.join(out))

    print(f"placed {len(TARGETS)} parts, moved the other {moved - len(TARGETS)} "
          f"to a block at ({HEAP_ORIGIN[0]:g}, {HEAP_ORIGIN[1]:g})")

    missing = [r for r in TARGETS if r not in refs]
    if missing:
        print("not on the board: " + ", ".join(sorted(missing)))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
