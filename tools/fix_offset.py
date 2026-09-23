#!/usr/bin/env python3
"""
Move the parts place_keypad.py placed onto the board outline.

Run from KiCad's Scripting Console with the board open:

    exec(open('/Users/barnaby osborne/Documents/Personal/02 Projects/Calculator/Hp42s_calc1/tools/fix_offset.py').read())

WHY THIS EXISTS
---------------
On 23 September 2026 the first real run of place_keypad.py under KiCad 10.0
put every footprint it touched 414.5 mm left and 492.5 mm above where it asked
for them. The board outline and the Cmts.User rectangles, drawn by the same
script in the same run, landed exactly where they were asked. So the outline
sat at board (0,0)-(76,144) with the keys and the six top-edge parts in a
tidy, correctly-spaced block a long way off the page.

The relative geometry was right to the micron: all 45 footprints were out by
one identical offset, and every rotation was correct. Only the translation was
wrong, which is why this fixes it rather than replacing the placement.

WHAT IT DOES
------------
It measures the error rather than hard-coding it: SW1 has a known target, so
the delta between where SW1 is and where it belongs is the delta every placed
part needs. Running it a second time moves nothing, because by then the delta
is zero.
"""

import pcbnew

INSET = 2.0
CASE_H = 148.0

# SW1 is the top-left key: case (8.75, 84.0), so board (6.75, 62.0).
ANCHOR_REF = "SW1"
ANCHOR_TARGET_MM = (8.75 - INSET, (CASE_H - 84.0) - INSET)

# Everything place_keypad.py positions: 38 dome sites plus the seven parts it
# places by footprint name. Nothing else on the board has been placed yet.
PLACED_REFS = (
    ["SW%d" % i for i in range(1, 42)]      # 38 domes + slider + 2 tact switches
    + ["J1", "J2", "D4", "D5"]
)


def fix():
    board = pcbnew.GetBoard()

    anchor = board.FindFootprintByReference(ANCHOR_REF)
    if anchor is None:
        print(f"{ANCHOR_REF} is not on the board -- import the netlist first")
        return

    here = anchor.GetPosition()
    want = pcbnew.VECTOR2I(pcbnew.FromMM(ANCHOR_TARGET_MM[0]),
                           pcbnew.FromMM(ANCHOR_TARGET_MM[1]))
    dx, dy = want.x - here.x, want.y - here.y

    print(f"{ANCHOR_REF} is at ({pcbnew.ToMM(here.x):.2f}, {pcbnew.ToMM(here.y):.2f}) mm, "
          f"wants ({ANCHOR_TARGET_MM[0]:.2f}, {ANCHOR_TARGET_MM[1]:.2f})")

    if abs(dx) < pcbnew.FromMM(0.001) and abs(dy) < pcbnew.FromMM(0.001):
        print("already in place -- nothing to do")
        return

    print(f"shifting everything placed by ({pcbnew.ToMM(dx):+.2f}, {pcbnew.ToMM(dy):+.2f}) mm")

    moved, missing = 0, []
    for ref in PLACED_REFS:
        fp = board.FindFootprintByReference(ref)
        if fp is None:
            missing.append(ref)
            continue
        p = fp.GetPosition()
        fp.SetPosition(pcbnew.VECTOR2I(p.x + dx, p.y + dy))
        moved += 1

    pcbnew.Refresh()
    print(f"moved {moved} footprints")
    if missing:
        print("not found: " + ", ".join(missing))

    check = board.FindFootprintByReference(ANCHOR_REF).GetPosition()
    print(f"{ANCHOR_REF} now reads ({pcbnew.ToMM(check.x):.2f}, "
          f"{pcbnew.ToMM(check.y):.2f}) mm -- should be "
          f"({ANCHOR_TARGET_MM[0]:.2f}, {ANCHOR_TARGET_MM[1]:.2f})")
    print("if those two disagree, paste this output back -- it means the API is "
          "not putting footprints where it is told, and the cause is worth finding")


fix()
