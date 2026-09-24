#!/usr/bin/env python3
"""
Place the 37 dome sites on the keypad grid.

Run this from KiCad's scripting console (Tools > Scripting Console) with the
board open, AFTER importing build/default.net so the footprints exist:

    exec(open('tools/place_keypad.py').read())

It moves SW1..SW38 onto the key grid and, if Edge.Cuts is empty, draws the
board outline. It touches nothing else -- run it again after a re-import and
it just puts the keys back.

POSITIONS FROM THIS SCRIPT ARE NOT TRUSTWORTHY under KiCad 10.0. It gets the
outline, the reference rectangles, the layers and every rotation right, but
the footprint positions land hundreds of millimetres out, by a different
amount each run, and reading them back through the API returns the value that
was asked for -- so nothing here can detect it. Run tools/place_board.py
afterwards, which writes the same positions into the .kicad_pcb directly.
This file stays the reference for WHERE everything goes.

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



# ---------------------------------------------------------------------------
# TOP-EDGE CONTROLS
#
# The five top-edge parts live on the BACK of the board, below the battery bay.
# They are found by footprint rather than by reference designator: atopile
# assigns SW39/SW40 automatically and those numbers move whenever a part is
# added.
#
# THERE ARE FIVE, NOT SIX, AND THEY ARE ON THE BACK AGAIN. Both changes are
# from 24 September 2026:
#
#   - The power slider is gone. On/off is the EXIT/ON key, the way it is on a
#     real 42S. See docs/power-control.md.
#   - They went back to the back. A part on the FRONT sits with its aperture
#     1.6 to 2.9 mm from the case's outer front face, which leaves under half a
#     millimetre of resin between the USB cut-out and the front surface. On the
#     back the same mouth lands 7.1 mm into a 15 mm wall -- near enough dead
#     centre -- with 4.6 mm of material above it and 5.4 below. That is the
#     whole argument, and docs/top-edge.md has the stack-up it comes from.
#
# What it costs is 3.5 mm of battery bay, which the 50 mm cell still fits in.
# What it gives back is the USB-C's four through-hole shield fillets, which
# land on the FRONT now, under the bezel where nothing touches them, instead of
# in the bay under the cell.
#
# THE ROTATIONS ARE NOT THE FRONT'S ROTATIONS. Turning a footprint over negates
# every child y, so an actuator that pointed at -Y on the front points at +Y
# once it is flipped, and the 180 comes off rather than goes on. The two LEDs
# are the other way round -- see LENS_PARTS below.
#
# Y here is depth into the board from its top edge. Each part sits far enough
# in that its actuator clears the board by a little under a millimetre and
# pokes into the case wall.
#
#   part            x     y      actuator reaches   courtyard reaches
#   IR emitter     25.33  0.900   y = -0.73          y = 2.34
#   USB-C          38.00  2.475   y = -1.71          y = 7.24
#   status LED     50.57  1.050   y = -0.77          y = 2.45
#   BOOT           60.65  1.800   y = -0.50          y = 3.85
#   RESET          71.31  1.800   y = -0.50          y = 3.85
#
# THE X POSITIONS COME FROM ONE RULE, from 24 September 2026. Barnaby asked for
# the USB-C centred on the board and for the rest spaced evenly off it, measured
# EDGE TO EDGE rather than centre to centre, which is what the eye sees. So J1
# sits at 38.00 -- the board's centreline, and the case's at x_case 40 -- and
# every gap between adjacent courtyards is 5.00 mm. The two LEDs are either side
# of the connector and the two buttons beyond the status LED, so everything that
# blinks or gets pressed is in the right-hand half.
#
# 5.00 is the one free number in that and it is near the largest that fits: the
# chain is anchored at the centre and runs right, and 5.45 would put RESET's
# courtyard on the 0.5 mm edge limit. As drawn RESET clears the edge by 1.86 mm
# and the board is empty from x = 0 to 22.98, where the slider used to be.
#
# THE USB-C CHANGED ON 22 September 2026, to a GCT USB4105-GF-A from a Same Sky
# UJ20, to get off a doubtful land pattern and onto one drawn from the vendor's
# own document; see parts.ato. Its y did not change with the swap: GCT's mouth
# sits at 3.675 mm from the origin, the same as the Same Sky "PRODUCT EDGE"
# line did.
#
EDGE_PARTS = {
    "Vishay_VSMB2943SLX01_SideView": (25.33, 0.900, "IR emitter"),
    "USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal": (38.00, 2.475, "USB-C"),
    "Dialight_599_BiColor_1208_RA": (50.57, 1.050, "status LED"),
}

# The two tact switches, by the net each one pulls down: BOOT sits inboard of
# RESET so the finger that reaches the corner finds RESET first.
# hp42s.ato declares sw_reset before sw_boot, and atopile hands out
# designators in declaration order, so the LOWER reference number is RESET.
TACT_FOOTPRINT = "Alps_SKRTLAE010_SidePush"
TACT_ORDER = [(71.31, 1.800, "reset"), (60.65, 1.800, "boot")]

# Both LEDs are the edge parts that ARE rotated 180 -- the opposite of the
# other three, and the opposite of what they wanted on the front. Their lens
# faces are the -y end of the body, so on the front 0 degrees already aimed
# them at the top edge; turning the part over aims that face into the middle of
# the board, and 180 brings it back. Both origins are the pad centreline rather
# than the lens, so both y values are the lens depth plus that offset. Neither
# lens stops short of the board edge: the IR dome reaches 0.45 mm past it and
# the status LED's lens 0.475, so each needs a relief pocket in the case wall
# and not merely a hole.
LENS_PARTS = {
    "Vishay_VSMB2943SLX01_SideView",
    "Dialight_599_BiColor_1208_RA",
}


def place_edge(board):
    """Put the five top-edge parts on the top edge, on the back."""
    found = 0
    for fp in board.GetFootprints():
        name = str(fp.GetFPID().GetLibItemName())
        if name not in EDGE_PARTS:
            continue
        x, y, label = EDGE_PARTS[name]
        if fp.GetLayer() != pcbnew.B_Cu:
            fp.SetLayerAndFlip(pcbnew.B_Cu)
        fp.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        fp.SetOrientationDegrees(180 if name in LENS_PARTS else 0)
        print(f"  {fp.GetReference():5s} {label:13s} -> back, ({x}, {y})")
        found += 1
    # The two tact switches share a footprint, so they go by reference order
    # rather than by name: lowest number is RESET, see TACT_ORDER above.
    tacts = sorted(
        (fp for fp in board.GetFootprints()
         if str(fp.GetFPID().GetLibItemName()) == TACT_FOOTPRINT),
        key=lambda fp: int("".join(c for c in fp.GetReference() if c.isdigit()) or 0),
    )
    for fp, (x, y, label) in zip(tacts, TACT_ORDER):
        if fp.GetLayer() != pcbnew.B_Cu:
            fp.SetLayerAndFlip(pcbnew.B_Cu)
        fp.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        fp.SetOrientationDegrees(0)
        print(f"  {fp.GetReference():5s} {label:13s} -> back, ({x}, {y})")
        found += 1

    expected = len(EDGE_PARTS) + len(TACT_ORDER)
    if found != expected:
        print(f"top edge: placed {found} of {expected} -- check the netlist import")
    return found


# ---------------------------------------------------------------------------
# THE PANEL, ITS NOTCH, AND THE FPC CONNECTOR
# ---------------------------------------------------------------------------
# Barnaby settled two things on 20 September 2026: the display IMAGE is what
# gets centred, not the glass, and the case wall is 1.2 mm. Those two numbers
# fix everything below. The working is in docs/display-mounting.md; the short
# version is that the active area sits 8.93 mm in from the glass's tail edge,
# and wall + air + fold radius + that border is more than the 9.956 mm a
# centred image would need, so the image lands 1.52 mm right of centre and
# that is as good as an 80 mm case gets.
#
#   glass left edge   case X 1.2 + 0.30 + 1.05 = 2.55   ->  board X 0.55
#   the board is inset 2 mm, so it has to be notched back 0.55 mm to leave
#   the fold its 0.30 mm of air against the case wall
#
PANEL_W, PANEL_H = 71.82, 36.30     # the glass
AA_W, AA_H = 60.088, 30.704         # the active area
AA_INSET_TAIL = 8.93                # glass border, tail side (the long axis)
AA_INSET_SHORT = 2.798              # glass border, both short-axis sides

PANEL_X = 0.55                      # board X of the glass's left (tail) edge
PANEL_Y = 12.00                     # board Y of its top edge: 14 mm of front
                                    # bezel less the 2 mm case inset. Was 6.00
                                    # on the 8 mm bezel; Barnaby chose 14 on
                                    # 21 September 2026, so everything below
                                    # moved 6 mm down the board with it.

NOTCH_D = 0.55                      # how far the left edge is pulled back
NOTCH_H = 16.0                      # over this much height, centred on the tail

TAIL_W = 12.50                      # the flex, centred on the 36.30 mm edge
FOLD_R = 1.05                       # (0.5 glass + 1.6 board) / 2

# Barnaby's aperture is centred on the CASE, not on the active area, because
# the look of it matters more than the last character column. The widest
# centred aperture that stays inside the active area is 57.04 mm; 56.00 leaves
# a millimetre of margin, all of which is needed on the left. What it hides is
# masked in firmware -- see EPD_VIEW_X in firmware/main/epd.h.
APERTURE_W = 56.00

# The FPC connector goes on the BACK with its opening facing the notched edge.
# The tail is 14.30 mm: no front leg to speak of, 3.30 mm eaten by the fold,
# so 11.00 mm of back leg reaching board X 10.50. The connector's pad row has
# to fall inside the last 3 mm of that, which puts the footprint origin at
# about X 9. There is no slack in this -- moving it 2 mm right pulls the flex
# out of the contacts.
FPC_FOOTPRINT = "Hirose_FH12-24S-0.5SH_1x24-1MP_P0.50mm_Horizontal"
FPC_X = 9.00
FPC_ANGLE = 90.0                    # so the opening faces -X. CHECK THIS ONE
                                    # in the viewer: if the mouth points at
                                    # the middle of the board, use 270.


def panel_geometry():
    """Everything the panel implies, in board coordinates."""
    gx0, gy0 = PANEL_X, PANEL_Y
    gx1, gy1 = gx0 + PANEL_W, gy0 + PANEL_H
    ax0 = gx0 + AA_INSET_TAIL
    ay0 = gy0 + AA_INSET_SHORT
    return (gx0, gy0, gx1, gy1), (ax0, ay0, ax0 + AA_W, ay0 + AA_H)


def place_panel(board):
    """Put the FPC connector on the back, and outline the glass for reference."""
    glass, aa = panel_geometry()
    tail_y = (glass[1] + glass[3]) / 2.0

    fp = next((f for f in board.GetFootprints()
               if str(f.GetFPID().GetLibItemName()) == FPC_FOOTPRINT), None)
    if fp is None:
        print("panel: no FPC connector on the board -- import the netlist first")
    else:
        if fp.GetLayer() != pcbnew.B_Cu:
            fp.SetLayerAndFlip(pcbnew.B_Cu)
        fp.SetPosition(pcbnew.VECTOR2I(mm(FPC_X), mm(tail_y)))
        fp.SetOrientationDegrees(FPC_ANGLE)
        print(f"  {fp.GetReference():5s} panel FPC     -> back, ({FPC_X}, {tail_y:.2f}), "
              f"{FPC_ANGLE:.0f} deg -- check the mouth faces the left edge")

    # Reference geometry on Cmts.User: the glass, the active area, and the
    # flex's width. None of it is manufactured; it is there so that placing
    # anything else on the front is obviously wrong or obviously fine.
    ap_x0 = BOARD_W / 2 - APERTURE_W / 2
    for (x0, y0, x1, y1), label in ((glass, "glass 71.82 x 36.30"),
                                    (aa, "active area 60.088 x 30.704"),
                                    ((ap_x0, aa[1], ap_x0 + APERTURE_W, aa[3]),
                                     f"case aperture {APERTURE_W} mm, centred"),
                                    ((glass[0] - 14.30, tail_y - TAIL_W / 2,
                                      glass[0], tail_y + TAIL_W / 2), "tail, unfolded")):
        r = pcbnew.PCB_SHAPE(board)
        r.SetShape(pcbnew.SHAPE_T_RECT)
        r.SetStart(pcbnew.VECTOR2I(mm(x0), mm(y0)))
        r.SetEnd(pcbnew.VECTOR2I(mm(x1), mm(y1)))
        r.SetLayer(pcbnew.Cmts_User)
        r.SetWidth(mm(0.1))
        r.SetFilled(False)
        board.Add(r)
        print(f"  drew {label} on Cmts.User")

    print(f"  image centre X {(aa[0] + aa[2]) / 2:.2f} against a board centre "
          f"of {BOARD_W / 2:.2f} -- {(aa[0] + aa[2]) / 2 - BOARD_W / 2:.2f} mm right, as designed")
    print(f"  aperture hides {ap_x0 - aa[0]:.2f} mm of active area on the left "
          f"and {aa[2] - (ap_x0 + APERTURE_W):.2f} mm on the right")


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

    print("top edge:")
    place_edge(board)

    print("panel:")
    place_panel(board)

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

    # The left edge is not straight: it steps back NOTCH_D over NOTCH_H,
    # centred on the panel's tail, to give the folded flex its air against
    # the case wall. Walk the outline clockwise from the top left.
    ny0 = PANEL_Y + PANEL_H / 2 - NOTCH_H / 2
    ny1 = ny0 + NOTCH_H
    corners = [
        (0, 0), (BOARD_W, 0), (BOARD_W, BOARD_H), (0, BOARD_H),
        (0, ny1), (NOTCH_D, ny1), (NOTCH_D, ny0), (0, ny0),
    ]
    for i in range(len(corners)):
        x1, y1 = corners[i]
        x2, y2 = corners[(i + 1) % len(corners)]
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(pcbnew.VECTOR2I(mm(x1), mm(y1)))
        seg.SetEnd(pcbnew.VECTOR2I(mm(x2), mm(y2)))
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetWidth(mm(0.1))
        board.Add(seg)
    print(f"drew a {BOARD_W} x {BOARD_H} mm outline on Edge.Cuts, with a "
          f"{NOTCH_D} x {NOTCH_H} mm notch at board Y {ny0:.2f}..{ny1:.2f} "
          f"for the panel's flex")


place()
