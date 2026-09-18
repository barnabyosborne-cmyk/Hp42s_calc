#!/usr/bin/env python3
"""
Place the 37 dome sites on the keypad grid.

Run this from KiCad's scripting console (Tools > Scripting Console) with the
board open, AFTER importing build/default.net so the footprints exist:

    exec(open('/path/to/Hp42s_calc/tools/place_keypad.py').read())

It moves SW1..SW38 onto the key grid and, if Edge.Cuts is empty, draws the
board outline. It touches nothing else -- run it again after a re-import and
it just puts the keys back.

UNTESTED. There is no KiCad in the environment this was written in, so the
geometry has been checked by arithmetic and the API calls have not been run.
If it throws, paste the error back.

WHERE THE NUMBERS COME FROM
---------------------------
Case 148 x 80 mm, board 144 x 76 mm, so the board is inset 2 mm all round.

The face budget that makes 148 mm work, measured down the case:

     8.0  top bezel
    36.3  display outline (GDEY0266T90)
     6.0  gap
    84.0  keyboard, 7 rows at 12.0 mm
    13.7  chin
   -----
   148.0

The chin is the only free number in that column. If something has to give,
take it from the chin and protect the row pitch -- 12.0 mm down and 11.8 mm
across is what makes the keyboard feel like a 42S rather than a toy.

Columns: 6 x 11.8 mm = 70.8 mm across a 76 mm board, so 2.6 mm each side.
"""

import pcbnew

# --- grid ------------------------------------------------------------------
# Board coordinates, origin at the top left corner of the board outline.
BOARD_W = 76.0
BOARD_H = 144.0

COL_PITCH = 11.8
ROW_PITCH = 12.0

COL_X = [8.5 + i * COL_PITCH for i in range(6)]      # 8.5 .. 67.5
ROW_Y = [54.3 + i * ROW_PITCH for i in range(7)]     # 54.3 .. 126.3

# --- which key goes where --------------------------------------------------
# ref -> (col, row). Key numbers are the calculator core's own, so SW19 is the
# 7 key. SW38 is ENTER's second dome: ENTER is a double-width key spanning
# columns 0 and 1 on row 2, with two domes under one keycap.
KEYS = {
    "SW1":  (0, 0), "SW2":  (1, 0), "SW3":  (2, 0),
    "SW4":  (3, 0), "SW5":  (4, 0), "SW6":  (5, 0),

    "SW7":  (0, 1), "SW8":  (1, 1), "SW9":  (2, 1),
    "SW10": (3, 1), "SW11": (4, 1), "SW12": (5, 1),

    "SW13": (0, 2), "SW38": (1, 2), "SW14": (2, 2),
    "SW15": (3, 2), "SW16": (4, 2), "SW17": (5, 2),

    "SW18": (0, 3), "SW19": (1, 3), "SW20": (2, 3),
    "SW21": (3, 3), "SW22": (4, 3),

    "SW23": (0, 4), "SW24": (1, 4), "SW25": (2, 4),
    "SW26": (3, 4), "SW27": (4, 4),

    "SW28": (0, 5), "SW29": (1, 5), "SW30": (2, 5),
    "SW31": (3, 5), "SW32": (4, 5),

    "SW33": (0, 6), "SW34": (1, 6), "SW35": (2, 6),
    "SW36": (3, 6), "SW37": (4, 6),
}


def mm(v):
    return pcbnew.FromMM(float(v))


def place():
    board = pcbnew.GetBoard()

    placed, missing = 0, []
    for ref, (col, row) in sorted(KEYS.items()):
        fp = board.FindFootprintByReference(ref)
        if fp is None:
            missing.append(ref)
            continue
        fp.SetPosition(pcbnew.VECTOR2I(mm(COL_X[col]), mm(ROW_Y[row])))
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
