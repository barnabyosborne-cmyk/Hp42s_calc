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
#
# Y is depth from the board's top edge, and each of the six is pushed out as
# far as its own pads allow, so its knob, mouth or lens gets as close to the
# outside of the case as it can. The board edge is 2.00 mm inside the case's
# outer surface: 0.80 mm of assembly clearance to the wall, then the 1.20 mm
# wall itself. Reach, and what limits it:
#
#   part          Y      protrudes   limited by
#   slider      1.500      2.30 mm   nothing; set to stand 0.3 mm proud
#   USB-C       2.475      1.20 mm   through-hole shield legs, 0.5 mm to edge
#   IR emitter  0.900      1.08 mm   pads, 0.3 mm to edge
#   status LED  1.050      1.12 mm   pads, 0.3 mm to edge
#   tact x2     1.800      0.24 mm   pads, 0.3 mm to edge
#
# Only the slider reaches the outside. The other five need the case to come to
# them: a recessed, chamfered mouth for USB-C, clear holes for the two LEDs,
# and pinholes for the recovery buttons, which is what recovery buttons want
# anyway.
#
# THE TACT SWITCHES MOVED INWARD, from 1.50 to 1.80. At 1.50 their pads sat
# exactly on the board outline with no copper-to-edge clearance at all.
TARGETS.update({
    "SW39": (11.0, 1.500),     # C&K power slider
    "D4":   (22.0, 0.900),     # IR emitter
    "J1":   (36.0, 2.475),     # USB-C
    "D5":   (48.0, 1.050),     # status LED
    "SW41": (57.0, 1.800),     # boot
    "SW40": (66.0, 1.800),     # reset
    "J2":   (9.00, 30.15),     # panel FPC, on the back
})

# ---------------------------------------------------------------------------
# FIRST-PASS PLACEMENT OF EVERYTHING ELSE, 23 September 2026
#
# (x, y, layer, rotation). The reasoning is in docs/placement.md; the summary
# is that three areas are already spoken for and what is left is not much:
#
#   FRONT  Y 0..5      the six top-edge parts
#          Y 12..48.3  the panel's glass
#          Y 59..137   the keyboard
#   BACK   Y 5..59     the battery bay, full width but for the FPC in the
#                      left 10 mm. Nothing else goes there. Ever.
#
# So the electronics live on the BACK below Y 59, and the two slivers of
# FRONT that nothing else wants: Y 5..12 above the glass, and Y 48.3..59
# between the glass and the keys.
#
# This is a first pass. It groups by function, keeps each switcher's loop
# tight, and leaves the keyboard's column gaps clear for the case to bear on
# (docs/board-thickness.md). It has NOT been routed, and routing will move
# things.
FIRST_PASS = {
    # --- FRONT, the band between the top-edge parts and the glass (Y 5..12) ---
    # The USB front end, directly behind J1, plus the drives for the two LEDs
    # that are also up here. Nothing else can be near them: the whole of the
    # back above Y 59 is the battery bay.
    "U1": (15.55, 9.6, "F", 0),
    "R1": (19.1, 9.6, "F", 0),
    "R2": (21.9, 9.6, "F", 0),
    "C1": (24.95, 9.6, "F", 0),
    "Q2": (29.05, 9.6, "F", 0),
    "R18": (32.9, 9.6, "F", 0),
    "R19": (35.7, 9.6, "F", 0),
    "R20": (38.5, 9.6, "F", 0),
    "R21": (41.3, 9.6, "F", 0),

    # --- FRONT, the strip between the panel and the keyboard (Y 48.3..59) ---
    # TP1 and TP2 are the frontlight sliver's two ends; the sliver spans
    # between them, along the guide's injection edge. TP3 bonds the metal
    # faceplate to ground and has to be on the front, under the plate.
    "TP1": (9.5, 50.5, "F", 0),
    "TP2": (69.5, 50.5, "F", 0),
    "TP3": (72, 54.5, "F", 0),

    # --- BACK, top left: the panel's boost -------------------------------
    # As near J2 as the battery bay allows. The ten rail capacitors sit with
    # it rather than at the connector, which is the compromise the bay forces.
    "L2": (4.35, 62.35, "B", 0),
    "Q1": (8.85, 61.25, "B", 0),
    "D1": (13.15, 61.05, "B", 0),
    "D2": (18.25, 61.05, "B", 0),
    "D3": (23.35, 61.05, "B", 0),
    "R15": (27.1, 60.5, "B", 0),
    "R16": (2.8, 66, "B", 0),
    "C16": (5.45, 66.15, "B", 0),
    "C18": (8.35, 66.15, "B", 0),
    "C10": (11.25, 66.15, "B", 0),
    "C11": (14.15, 66.15, "B", 0),
    "C12": (17.05, 66.15, "B", 0),
    "C13": (19.95, 66.15, "B", 0),
    "C14": (22.85, 66.15, "B", 0),
    "C15": (25.75, 66.15, "B", 0),
    "C17": (28.65, 66.15, "B", 0),
    "C19": (3.05, 68.25, "B", 0),

    # --- BACK, top right: the frontlight driver ---------------------------
    # Far from J2 and from the panel boost, which is what frontlight.ato asks
    # for: a second switching node kept away from the display SPI. FL+ and
    # FL- run up through vias to TP1 and TP2 and are DC, so length is free.
    "U6": (47.85, 61.65, "B", 0),
    "L3": (52.35, 60.95, "B", 0),
    "D6": (57.15, 61.05, "B", 0),
    "C20": (61.35, 60.8, "B", 0),
    "C21": (64.45, 60.65, "B", 0),
    "C22": (67.1, 60.5, "B", 0),
    "R22": (69.5, 60.5, "B", 0),
    "R23": (71.9, 60.5, "B", 0),
    "R24": (46.8, 64.6, "B", 0),

    # --- BACK: the cell connector ----------------------------------------
    # Just below the bay so the cell's leads drop straight down into it.
    "BT1": (37, 63, "B", 0),

    # --- BACK, middle: charger, regulator, gauge --------------------------
    "U2": (3.35, 85.35, "B", 0),
    "U3": (7.1, 85.6, "B", 0),
    "U4": (10.85, 85.35, "B", 0),
    "L1": (15.35, 86.35, "B", 0),
    "C2": (19.75, 84.8, "B", 0),
    "C3": (23.05, 84.8, "B", 0),
    "C4": (26.35, 84.8, "B", 0),
    "C5": (29.2, 84.5, "B", 0),
    "C6": (31.6, 84.5, "B", 0),
    "R3": (34, 84.5, "B", 0),
    "R4": (36.4, 84.5, "B", 0),
    "R5": (38.8, 84.5, "B", 0),
    "R6": (41.2, 84.5, "B", 0),
    "R7": (43.6, 84.5, "B", 0),
    "R8": (46, 84.5, "B", 0),
    "R9": (48.4, 84.5, "B", 0),
    "R10": (50.8, 84.5, "B", 0),
    "R11": (53.2, 84.5, "B", 0),
    "R12": (55.6, 84.5, "B", 0),
    "R13": (58, 84.5, "B", 0),

    # --- BACK, bottom: the module -----------------------------------------
    # Rotated 180 so the antenna faces the board's bottom edge and radiates
    # off it. Its keepout then covers Y 138.75..144 from X 15 to 61, which is
    # the chin -- where docs/front-face.md already keeps the faceplate out.
    # NOTHING, including ground pour, goes in that rectangle.
    "U5": (38, 133.5, "B", 180),
    "C8": (27.25, 116.8, "B", 0),
    "C9": (30.1, 116.5, "B", 0),
    "C7": (32.5, 116.5, "B", 0),
    "R14": (34.9, 116.5, "B", 0),

    # --- BACK: the programming and measurement points ---------------------
    "TP4": (63, 109, "B", 0),
    "TP5": (65.8, 109, "B", 0),
    "TP6": (68.6, 109, "B", 0),
    "TP7": (71.4, 109, "B", 0),
    "TP8": (63, 111.8, "B", 0),
    "TP9": (65.8, 111.8, "B", 0),
    "TP10": (68.6, 111.8, "B", 0),
    "TP11": (71.4, 111.8, "B", 0),

    # --- BACK, bottom left: the buzzer ------------------------------------
    # It needs a hole through the case back. Clear of the antenna keepout.
    "LS1": (11, 128, "B", 0),
    "R17": (11, 119, "B", 0),
}

# Where anything not in the table goes, if the netlist grows.
HEAP_ORIGIN = (90.0, 20.0)

FP_SPLIT = "\n\t(footprint "
AT_RE = re.compile(r'(\n\t\t\(at )(-?[\d.]+) (-?[\d.]+)((?: -?[\d.]+)?\))')
REF_RE = re.compile(r'\(property "Reference" "([^"]+)"')


def set_layer(block, want):
    """Move a footprint to F.Cu or B.Cu.

    KiCad stores a flipped footprint by swapping every F.* layer name in the
    block for its B.* twin and leaving the child coordinates alone -- it
    mirrors at render time. Verified against J2, which KiCad itself flipped.
    "*.Cu" on a through-hole pad means both sides and is left as it is.
    """
    now = re.search(r'\n\t\t\(layer "([FB])\.Cu"\)', block)
    if now is None or now.group(1) == want:
        return block
    return re.sub(r'"([FB])\.([A-Za-z0-9]+)"',
                  lambda m: '"%s.%s"' % ("B" if m.group(1) == "F" else "F", m.group(2)),
                  block)


def main():
    text = PCB.read_text()
    head, *blocks = text.split(FP_SPLIT)

    refs = [REF_RE.search(b).group(1) for b in blocks]

    # The heap keeps its shape, so work out its corner before moving anything.
    heap = [i for i, r in enumerate(refs) if r not in TARGETS and r not in FIRST_PASS]
    coords = []
    for i in heap:
        m = AT_RE.search(blocks[i])
        coords.append((float(m.group(2)), float(m.group(3))))
    if coords:
        dx = HEAP_ORIGIN[0] - min(c[0] for c in coords)
        dy = HEAP_ORIGIN[1] - min(c[1] for c in coords)
    else:
        dx = dy = 0.0

    out, moved, flipped = [], 0, 0
    for i, block in enumerate(blocks):
        ref = refs[i]
        m = AT_RE.search(block)
        rot = m.group(4)
        if ref in TARGETS:
            x, y = TARGETS[ref]
        elif ref in FIRST_PASS:
            x, y, layer, r = FIRST_PASS[ref]
            rot = f" {r})" if r else ")"
            if set_layer(block, layer) != block:
                flipped += 1
            block = set_layer(block, layer)
            m = AT_RE.search(block)
        else:
            x, y = float(m.group(2)) + dx, float(m.group(3)) + dy
        new = f"{m.group(1)}{x:g} {y:g}{rot}"
        out.append(block[:m.start()] + new + block[m.end():])
        moved += 1

    PCB.write_text(head + FP_SPLIT + FP_SPLIT.join(out))

    print(f"placed {len(TARGETS)} from the keypad script and {len(FIRST_PASS)} "
          f"from the first pass; {flipped} moved to the back")
    left = moved - len(TARGETS) - len(FIRST_PASS)
    if left:
        print(f"{left} not in either table, parked at "
              f"({HEAP_ORIGIN[0]:g}, {HEAP_ORIGIN[1]:g})")

    missing = [r for r in list(TARGETS) + list(FIRST_PASS) if r not in refs]
    if missing:
        print("not on the board yet, skipped: " + ", ".join(sorted(missing)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
