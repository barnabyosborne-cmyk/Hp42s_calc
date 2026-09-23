#!/usr/bin/env python3
"""
Put the back-side parts on the back.

Run from KiCad's Scripting Console with the board open:

    exec(open('/Users/barnaby osborne/Documents/Personal/02 Projects/Calculator/Hp42s_calc1/tools/flip_back.py').read())

then save, quit KiCad, and run tools/place_board.py to set the positions.

WHY KICAD HAS TO DO THIS ONE
----------------------------
place_board.py writes positions into the .kicad_pcb because KiCad 10.0's
scripting API puts footprints in the wrong place. Flipping is the other way
round. A flipped footprint is not the same footprint with B.* layer names: it
has every pad and graphic mirrored in y inside the block, and every pad angle
negated. Swapping the layer names alone was tried on 23 September 2026 and it
produced 62 footprints whose copper did not match their outlines.

SetLayerAndFlip, unlike SetPosition, works correctly -- place_keypad.py has
been flipping J2 to the back with it since the start, and tools/fix_pads.py
confirms J2's pads are mirrored exactly as its library says they should be.
So the split is: KiCad flips, the file sets positions.

Afterwards run tools/fix_pads.py --check. If KiCad has left any pad off its
own footprint, that will say so, and running it without --check puts them
back.

It moves nothing. Run it before place_board.py or after; the order does not
matter.
"""

import pcbnew

BACK = ['BT1', 'C10', 'C11', 'C12', 'C13', 'C14', 'C15', 'C16', 'C17', 'C18', 'C19', 'C2', 'C20', 'C21', 'C22', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9', 'D1', 'D2', 'D3', 'D6', 'L1', 'L2', 'L3', 'LS1', 'Q1', 'R10', 'R11', 'R12', 'R13', 'R14', 'R15', 'R16', 'R17', 'R22', 'R23', 'R24', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9', 'TP10', 'TP11', 'TP4', 'TP5', 'TP6', 'TP7', 'TP8', 'TP9', 'U2', 'U3', 'U4', 'U5', 'U6']


def flip():
    board = pcbnew.GetBoard()
    done, missing = 0, []
    for ref in BACK:
        fp = board.FindFootprintByReference(ref)
        if fp is None:
            missing.append(ref)
            continue
        if fp.GetLayer() != pcbnew.B_Cu:
            fp.SetLayerAndFlip(pcbnew.B_Cu)
            done += 1
    pcbnew.Refresh()
    print("flipped %d of %d to the back" % (done, len(BACK)))
    if done == 0:
        print("all of them were already there")
    if missing:
        print("not on the board: " + ", ".join(missing))


flip()
