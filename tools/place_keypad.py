#!/usr/bin/env python3
"""
Place the 37 dome sites on the keypad grid.

Run this from KiCad's scripting console (Tools > Scripting Console) with the
board open, AFTER importing build/default.net so the footprints exist:

    exec(open('tools/place_keypad.py').read())

It moves SW1..SW38 onto the key grid and, if Edge.Cuts is empty, draws the
board outline. It touches nothing else -- run it again after a re-import and
it just puts the keys back.

UNTESTED IN KICAD. The geometry is checked by arithmetic; the pcbnew API
calls have not been run. If it throws, paste the error back.

WHERE THE NUMBERS COME FROM
---------------------------
Barnaby measured a real HP-42S on 19 September 2026. These are his figures,
not a reconstruction, which is why the grid is not uniform:

  case                80 x 148 mm
  keyboard area       70 x 78 mm, datum 5 mm in from the left, 9 mm up from
                      the bottom, so it spans case X 5..75, Y 9..87
  row pitch           12.0 mm, seven rows
  keycaps             6.0 mm tall throughout

Two different column grids, which is the part a uniform pitch gets wrong:

  rows 1-3   6 columns at 12.5 mm pitch, keycaps 7.5 mm wide
             centres 8.75, 21.25, 33.75, 46.25, 58.75, 71.25
  rows 4-7   the left column stays at 8.75 with a 7.5 mm cap (UP, DOWN,
             SHIFT, EXIT), then four numeric columns at 15.0 mm pitch with
             10 mm caps, centres 25, 40, 55, 70

ENTER is a 20 x 6 mm cap centred at case X 15 on row 3, spanning the first
two column positions. It gets two domes, at 8.75 and 21.25, wired in
parallel -- see docs/connections.md.

COORDINATES
-----------
Barnaby measures X from the left edge of the case and Y UP from the bottom.
KiCad measures Y down from the board origin, and the board is inset 2 mm
from the case all round. So:

    x_board = x_case - 2
    y_board = 146 - y_case

which puts the keyboard at board Y 59..137 and leaves 59 mm above it for the
bezel and the display, and a 7 mm chin below.
"""

import pcbnew

# --- case and board --------------------------------------------------------
CASE_W, CASE_H = 80.0, 148.0
INSET = 2.0
BOARD_W, BOARD_H = CASE_W - 2 * INSET, CASE_H - 2 * INSET   # 76 x 144

# --- measured key grid, in case coordinates (Y up from the bottom) ---------
ROW_Y = [84.0, 72.0, 60.0, 48.0, 36.0, 24.0, 12.0]          # rows 1..7
COL_TOP = [8.75, 21.25, 33.75, 46.25, 58.75, 71.25]         # rows 1-3
COL_PAD = [25.0, 40.0, 55.0, 70.0]                          # rows 4-7, numeric
COL_LEFT = 8.75                                             # rows 4-7, left column

# --- ref -> case (x, y) ----------------------------------------------------
# Designators are the calculator core's own key numbers, so SW19 is the 7 key.
# SW38 is ENTER's second dome.
KEYS = {}
for i, ref in enumerate(["SW1", "SW2", "SW3", "SW4", "SW5", "SW6"]):
    KEYS[ref] = (COL_TOP[i], ROW_Y[0])
for i, ref in enumerate(["SW7", "SW8", "SW9", "SW10", "SW11", "SW12"]):
    KEYS[ref] = (COL_TOP[i], ROW_Y[1])
for i, ref in enumerate(["SW13", "SW38", "SW14", "SW15", "SW16", "SW17"]):
    KEYS[ref] = (COL_TOP[i], ROW_Y[2])
for row, refs in enumerate([
    ["SW18", "SW19", "SW20", "SW21", "SW22"],
    ["SW23", "SW24", "SW25", "SW26", "SW27"],
    ["SW28", "SW29", "SW30", "SW31", "SW32"],
    ["SW33", "SW34", "SW35", "SW36", "SW37"],
], start=3):
    KEYS[refs[0]] = (COL_LEFT, ROW_Y[row])
    for i, ref in enumerate(refs[1:]):
        KEYS[ref] = (COL_PAD[i], ROW_Y[row])


def to_board(x_case, y_case):
    return x_case - INSET, (CASE_H - y_case) - INSET


def mm(v):
    return pcbnew.FromMM(float(v))


def place():
    board = pcbnew.GetBoard()

    placed, missing = 0, []
    for ref, (xc, yc) in sorted(KEYS.items()):
        fp = board.FindFootprintByReference(ref)
        if fp is None:
            missing.append(ref)
            continue
        x, y = to_board(xc, yc)
        fp.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        fp.SetOrientationDegrees(0)
        placed += 1

    draw_outline(board)

    pcbnew.Refresh()
    print(f"placed {placed} dome sites")
    if missing:
        print("not found on the board: " + ", ".join(missing))
        print("import build/default.net first -- the footprints have to exist")


def draw_outline(board):
    """Draw the board rectangle, but only if Edge.Cuts is empty."""
    for d in board.GetDrawings():
        if d.GetLayer() == pcbnew.Edge_Cuts:
            print("Edge.Cuts already has geometry -- leaving the outline alone")
            return

    corners = [(0, 0), (BOARD_W, 0), (BOARD_W, BOARD_H), (0, BOARD_H)]
    for i in range(4):
        x1, y1 = corners[i]
        x2, y2 = corners[(i + 1) % 4]
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(pcbnew.VECTOR2I(mm(x1), mm(y1)))
        seg.SetEnd(pcbnew.VECTOR2I(mm(x2), mm(y2)))
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetWidth(mm(0.1))
        board.Add(seg)
    print(f"drew a {BOARD_W} x {BOARD_H} mm outline on Edge.Cuts")


place()
