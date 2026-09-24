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
Every footprint's position, and its rotation: the 38 dome sites, the five
top-edge parts and the panel FPC at the positions docs/keypad-geometry.md and
docs/display-mounting.md give, and all 74 of the rest from the table below.
docs/placement.md explains the table.

It also puts each part on the side of the board it belongs on. A flipped
footprint is not the same footprint with B.* layer names: every graphic and
every text inside it is mirrored in y as well. This does that, and leaves the
pads to fix_pads.py, which rewrites them from the library outright.

AFTERWARDS
----------
Always run these two, in this order:

    python3 tools/fix_pads.py          # every pad, from its library footprint
    python3 tools/check_placement.py   # clearances, outline, bay, keepout, grid
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

# The five top-edge parts are NOT here any more. They are in FIRST_PASS below,
# because they now need a layer as well as an x and a y: on 24 September 2026
# they moved to the BACK of the board, and the power slider was deleted
# outright. docs/top-edge.md has both arguments; the short versions are that a
# part on the front sits so close to the case's front face that its aperture
# breaks out of it, and that the on/off switch is the EXIT/ON key now, the way
# it is on a real 42S.
#
# ---------------------------------------------------------------------------
# PLACEMENT OF EVERYTHING ELSE, 23 September 2026
#
# (x, y, layer, rotation), board coordinates, Y down from the top edge.
# docs/placement.md has the reasoning. In short:
#
#   FRONT  nothing that the fab house solders, since 24 September 2026. The
#          USB-C's four through-hole shield fillets come through at Y 0..5, the
#          panel's glass covers Y 12..48.3, the frontlight sliver's two lands
#          and a ground point sit at Y 48.3..57, and the 38 dome sites fill
#          Y 57..137. Panel, sliver and domes all go on after the board comes
#          back from the fab, which is the whole point of the arrangement.
#   BACK   Y 0..8      the five top-edge parts, set by the case
#          Y 4..11.7   the nine parts that serve them, interleaved with those
#          Y 13..58    the battery bay, X 14..69. Nothing else goes there. Ever.
#          Y 59..144   every other IC and every other passive
#
# Placement order was fixed parts, then the ICs, then the passives around
# them, following the guidelines Barnaby sent on 23 September:
#
#   Zoning        Each supply is one block, and the two boosts -- the
#                 display's +-20 V and the frontlight's 38 V -- sit at
#                 opposite corners. The fuel gauge, the only analogue part
#                 on the board, is as far from both as the space allows:
#                 14 mm below the display boost's inductor, 45 mm from the
#                 frontlight's.
#   Signal flow   Power runs down the back: charger at Y 72, regulator at
#                 Y 89, ESP32 at Y 133. USB runs J1 -> U1 -> down to the
#                 module. The display block sits under the FPC connector
#                 and the frontlight block under the sliver's right land.
#   Decoupling    Every bypass capacitor is beside the pin it serves, named
#                 in the comments below.
#   Grid          ICs and connectors on a 1.27 mm (50 mil) grid, passives
#                 on 0.635 mm (25 mil). The keys, the top-edge parts, the
#                 FPC, the sliver lands and the ESP32 are not on either:
#                 their positions come from the case, the panel and the
#                 antenna, which is what "fixed parts first" means.
#   Clearance     At least 1.0 mm between courtyards, near enough the 40 mil
#                 the guidelines ask for. The 100 mil to the board edge is
#                 not possible on a board this full: see docs/placement.md.
#   Orientation   Every two-terminal passive is at 0 degrees, so the whole
#                 board is one pick-and-place orientation.
#
# Nothing is routed yet, and routing will move things.
FIRST_PASS = {
    # -- BACK, Y 0..8: the five top-edge parts --------------------------------
    #
    # Y is depth from the board's top edge, and each part is pushed out as far
    # as its own pads allow, so its mouth or lens gets as close to the outside
    # of the case as it can. The board edge is 2.00 mm inside the case's outer
    # surface: 0.80 mm of assembly clearance to the wall, then the 1.20 mm wall
    # itself. Reach, and what limits it:
    #
    #   part          Y      protrudes   limited by
    #   USB-C       2.475      1.71 mm   through-hole shield legs, 0.5 mm to edge
    #   IR emitter  0.900      0.73 mm   pads, 0.3 mm to edge
    #   status LED  1.050      0.77 mm   pads, 0.3 mm to edge
    #   tact x2     1.800      0.50 mm   pads, 0.3 mm to edge
    #
    # None of the four reaches the outside on its own, so the case has to come
    # to them: a recessed, chamfered mouth for USB-C, relief pockets for the
    # two lenses -- both are proud of the board edge, see docs/top-edge.md --
    # and pinholes for the recovery buttons, which is what recovery buttons
    # want anyway.
    #
    # THE ROTATIONS ARE NOT THE FRONT'S ROTATIONS. A flip to the back negates
    # every child y, so a part whose actuator pointed at -Y on the front points
    # at +Y once it is turned over, and the 180 has to come off rather than go
    # on. The two LEDs are the other way round: their lenses are already at the
    # -y end of the body, so they wanted 0 on the front and want 180 here.
    # Getting this wrong aims the IR beam and the button plungers into the
    # middle of the board, which is why check_placement.py prints each of these
    # five with its courtyard: every one must reach past y = 0.
    #
    # THE X POSITIONS ARE SET BY ONE RULE, from 24 September 2026: the USB-C
    # sits on the board's centreline, and every gap between adjacent courtyards
    # along the edge is the same 5.00 mm. Barnaby asked for the connector
    # centred and for the rest spaced evenly off it, measured edge to edge
    # rather than centre to centre, which is what you see rather than what a
    # datum sheet says.
    #
    #   part   centre   courtyard        gap to the next
    #   D4     25.33    22.98 .. 27.68   5.00 to J1
    #   J1     38.00    32.68 .. 43.32   board centre, and case centre at 40
    #   D5     50.57    48.32 .. 52.82   5.00 from J1
    #   SW41   60.65    57.82 .. 63.48   5.00 from D5
    #   SW40   71.31    68.48 .. 74.14   5.00 from SW41, 1.86 to the board edge
    #
    # 5.00 mm is the one free number and it is near the biggest that fits: the
    # chain is anchored at the centre and runs right, so 5.45 would put SW40's
    # courtyard on the 0.5 mm edge limit. The left of the edge is empty from
    # x = 0 to 22.98, where the power slider used to be. Nothing has claimed it.
    #
    # The two LEDs sit either side of the connector and the two buttons beyond
    # the status LED, so everything that blinks or gets pressed is in the
    # right-hand half and the IR window is on its own. That is Barnaby's
    # arrangement, not a derived one.
    "D4":   (25.33, 0.900, "B", 180),  # IR emitter
    "J1":   (38.00, 2.475, "B", 0),    # USB-C, on the board's centreline
    "D5":   (50.57, 1.050, "B", 180),  # status LED
    "SW41": (60.65, 1.800, "B", 0),    # BOOT
    "SW40": (71.31, 1.800, "B", 0),    # RESET

    # -- BACK, Y 4..11.7: what the five top-edge parts need -------------------
    #
    # These nine were on the FRONT until 24 September 2026, at exactly these x
    # and y. Barnaby asked for every reflowed part on one side so the board
    # takes a single-sided assembly, which is the cheaper build, and the front
    # now carries nothing the fab house solders. So they crossed over to sit
    # directly behind where they were, keeping every distance to the part each
    # one serves. What paid for it is the battery bay: it starts at Y 13 now
    # rather than 8.5, which is what makes the cell 6 x 45 x 55 mm instead of
    # 5 x 50 x 60 -- the same capacity, one millimetre deeper. See
    # docs/top-edge.md.
    #
    # Turning them over mirrors each footprint in y, so pin 1 of U1 and of Q2
    # moves from the -y end of the body to the +y end. Neither matters: the
    # ESD array's four channels are interchangeable, the SOT-23 is a single
    # transistor, and nothing is routed yet.
    #
    # U1 is the USB ESD array; it sits directly under J1's D+/D- pins so the
    # pair is protected before it goes anywhere, and it is on the connector's
    # own side of the board now rather than across two vias. R1/R2 are the CC
    # pulldowns, at U1's CC pins. C1 is VBUS's bulk cap, at the connector where
    # the current enters.
    #
    # All nine moved with the top-edge parts on 24 September 2026, keeping the
    # part each one serves directly in front of it. They are back on their grids
    # afterwards -- 1.27 mm for U1, 0.635 for the passives -- which is why the
    # shifts are not exactly the shifts above.
    "U1":  (38.1, 10.16, "B", 0),
    "R1":  (31.115, 10.16, "B", 0),
    "R2":  (34.29, 10.16, "B", 0),
    "C1":  (42.545, 10.16, "B", 0),
    # The IR emitter's driver, behind D4.
    "Q2":  (25.4, 8.89, "B", 0),
    "R18": (24.13, 4.445, "B", 0),
    "R19": (20.955, 8.89, "B", 0),
    # The status LED's two ballast resistors, behind D5.
    "R20": (52.07, 4.445, "B", 0),
    "R21": (48.895, 4.445, "B", 0),

    # -- FRONT, Y 48.3..57 ---------------------------------------------------
    # TP1 and TP2 are the frontlight sliver's solder lands, 60 mm apart
    # because that is the sliver's length. TP3 is a ground point to clip a
    # scope to while the frontlight is being set up.
    "TP1": (9.5, 50.5, "F", 0),
    "TP2": (69.5, 50.5, "F", 0),
    "TP3": (3.81, 53.34, "F", 0),

    # -- BACK, Y 20..40, left edge: the panel's FPC connector ----------------
    # The one placement on the board with no slack in it, and it was wrong in
    # both of the ways it could be until 23 September 2026. It was at 90
    # degrees; it wants 270.
    #
    # WHICH WAY THE MOUTH FACES. The flex comes around the left board edge
    # and runs rightwards along the back, so the connector's mouth has to
    # face LEFT and its body has to sit to the RIGHT of it. At 90 degrees it
    # was the other way round: mouth at X 12.00 facing right, body running
    # back to X 4.10, with the flex arriving at the closed end of it.
    #
    # HOW FAR IN. The back leg of the tail ends at X 10.50 and cannot be
    # made to end anywhere else -- see docs/display-mounting.md. The F32Q's
    # body is 3.00 mm deep, so its BACK WALL goes at X 10.50 and the flex
    # bottoms out against it: mouth at X 7.50, and the flex's own 3.00 mm of
    # exposed finger runs X 7.50..10.50, which is exactly the body. Wherever
    # inside that body the contact point actually is, it is on copper.
    # X 9.75 is what puts the back wall there, and the solder pads, which
    # stand 0.65 mm proud of the mouth, land at X 6.85.
    #
    # Y 30.15 is the tail's own centreline: the tail is centred on the
    # panel's 36.30 mm edge, 11.90 + 12.50 + 11.90, and the glass spans
    # Y 12.00..48.30.
    #
    # PIN ORDER. On the panel's own front view the tail leaves the bottom
    # edge with pin 1 at the left. Mounted landscape with the tail to the
    # left that is a quarter turn clockwise, which puts pin 1 at the TOP of
    # the board. The fold is about the board's left edge, a vertical axis,
    # so it mirrors X and leaves Y alone, and pin 1 arrives at Y 24.40 with
    # pin 24 at Y 35.90. 270 degrees gives that. 90 gave the reverse, which
    # is the same single error as the mouth pointing the wrong way.
    #
    # WHERE THE CELL GOES. At 270 the connector's body runs right to
    # X 12.50 instead of stopping at 12.00 the wrong way round, so the cell
    # has to start at X 14 rather than the 10 the bay was drawn at. It has
    # the room -- 60 mm of cell in a 62 mm bay -- but it is a note for the
    # case model, and it is why BAY in check_placement.py now starts at 13.
    "J2": (9.75, 30.15, "B", 270),

    # -- BACK, Y 59.5..64: the panel's own rail capacitors -------------------
    # These six belong at J2's pins. They cannot get there: the battery bay
    # is in the way and nothing goes under a pouch cell. So they sit in the
    # first two rows below the bay, directly under the connector, which is
    # the closest the geometry allows. C10 v3v3, C11 VDD, C12 VSH1,
    # C13 VSH2, C14 VSL, C15 VCOM.
    "C10": (3.175, 60.325, "B", 0),
    "C11": (7.62, 60.325, "B", 0),
    "C12": (12.065, 60.325, "B", 0),
    "C13": (3.175, 62.865, "B", 0),
    "C14": (7.62, 62.865, "B", 0),
    "C15": (12.065, 62.865, "B", 0),

    # -- BACK, Y 65..81, left: the display boost -----------------------------
    # The noisiest block on the board. Q1 switches L2 against the 3V3 rail;
    # D1 rectifies PREVGH into C17; D2/D3 and C18 are the inverting charge
    # pump that makes PREVGL into C19. The inductor is hard against Q1's
    # drain so the switching loop stays small, and the whole block sits
    # under the FPC connector, away from the fuel gauge.
    "Q1":  (8.89, 71.12, "B", 0),
    "L2":  (13.97, 71.12, "B", 0),
    "C16": (13.97, 65.405, "B", 0),   # 3V3 into L2
    "R15": (5.08, 70.485, "B", 0),    # gate pulldown, at Q1 pin 1
    "R16": (5.08, 73.025, "B", 0),    # RESE, at Q1 pin 2
    "D1":  (20.32, 69.85, "B", 0),
    "C17": (20.32, 73.025, "B", 0),   # PREVGH reservoir, after D1
    "C18": (8.255, 75.565, "B", 0),   # the pump capacitor
    "D2":  (6.35, 79.375, "B", 0),
    "D3":  (12.7, 79.375, "B", 0),
    "C19": (19.05, 79.375, "B", 0),   # PREVGL reservoir, after D3

    # -- BACK, Y 59.5..72, right: the frontlight boost -----------------------
    # U6 sits at the sliver's FB end, so the high-impedance feedback trace is
    # short and the 38 V rail is what takes the long way to TP1. L3, D6 and
    # C20 close the switching loop in that order.
    "U6":  (66.04, 66.04, "B", 0),
    "L3":  (60.325, 66.04, "B", 0),
    "C21": (60.325, 61.595, "B", 0),  # SYS into L3
    "D6":  (66.04, 61.595, "B", 0),
    "C20": (71.12, 61.595, "B", 0),   # VLED reservoir, after D6
    "C22": (71.12, 65.405, "B", 0),   # COMP, at U6 pin 5
    "R22": (71.12, 67.945, "B", 0),   # FB sense, at U6 pin 6
    "R23": (63.5, 70.485, "B", 0),    # CTRL divider, at U6 pin 2
    "R24": (66.675, 70.485, "B", 0),

    # -- BACK, Y 60..79, centre: the battery and the charger -----------------
    # BT1 is hard against the bottom edge of the bay, turned 180 so its mouth
    # faces the bay and the cell's leads run straight in without doubling
    # back. It moved right, out from under the charger, because the side-entry
    # part's courtyard is 9.2 x 10.2 mm against the vertical one's 6.9 x 5.5.
    # U2 keeps its place: C2 at its BAT pin and C3 at its SYS pin, with the
    # four programming resistors on its right-hand side where those pins are.
    "BT1": (50.8, 64.77, "B", 180),
    "U2":  (33.02, 72.39, "B", 0),
    "C2":  (28.575, 71.755, "B", 0),  # BAT, at U2 pin 2
    "C3":  (28.575, 74.93, "B", 0),   # SYS, at U2 pin 1
    "R7":  (28.575, 68.58, "B", 0),   # CHG_STAT2 pullup, at pin 3
    "R5":  (36.83, 70.485, "B", 0),   # TS_MR, at pin 6
    "R3":  (36.83, 73.025, "B", 0),   # ILIM_VSET, at pin 7
    "R4":  (36.83, 75.565, "B", 0),   # ISET, at pin 8
    "R6":  (40.005, 70.485, "B", 0),  # CHG_STAT pullup, at pin 9

    # -- BACK, Y 86..96, centre: the 3V3 regulator ---------------------------
    # L1 straddles the TPS63900's two switch pins. C4 and C5 are the output
    # capacitors, at the VOUT pin; R11 and the three CFG resistors are on
    # the left where their pins are.
    "U3":  (33.02, 88.9, "B", 0),
    "L1":  (38.735, 88.9, "B", 0),
    "C4":  (33.02, 92.71, "B", 0),    # 3V3 out, at U3 pin 6
    "C5":  (36.83, 92.71, "B", 0),
    "R11": (28.575, 87.63, "B", 0),   # REG_EN, at pin 1
    "R9":  (28.575, 90.17, "B", 0),   # CFG1
    "R10": (28.575, 92.71, "B", 0),   # CFG2
    "R8":  (28.575, 95.25, "B", 0),   # CFG3

    # -- BACK, Y 87..91, left: the fuel gauge --------------------------------
    # The one analogue part on the board, so it is kept away from both
    # boosts: 14 mm below the display inductor and 45 mm from the
    # frontlight's. C6 is its BAT bypass, at pin 3; R12 and R13 pull the
    # I2C bus up, at pins 7 and 8.
    "U4":  (7.62, 88.9, "B", 0),
    "C6":  (3.81, 89.535, "B", 0),
    "R12": (11.43, 87.63, "B", 0),
    "R13": (11.43, 90.17, "B", 0),

    # -- BACK, Y 108..125, right: the sounder --------------------------------
    "LS1": (64.77, 118.11, "B", 0),
    "R17": (64.77, 108.585, "B", 0),

    # -- BACK, Y 123..138: the ESP32 module ----------------------------------
    # U5's position and rotation are set by its antenna, not by the grid.
    # The antenna sits at one end of the module and must hang over the
    # bottom edge of the board, with the module's own keepout wing -- 45.4
    # by 19.5 mm -- clear of copper on every layer.
    #
    # ROTATION 0, NOT 180. It was 180 while the module was on the front. A
    # part is mirrored when it goes to the back, which reverses the antenna
    # end, so the rotation that pointed the antenna at the bottom edge now
    # points it up into the keyboard. Barnaby caught that on the board on
    # 23 September 2026; check_placement.py now works the keepout out from
    # the footprint itself rather than from a number I typed in, so it
    # cannot go unnoticed again.
    #
    # Everything around the module mirrors with it: 3V3 (pin 3) and BOOT
    # (pin 4) are on the left now, EN (pin 45) and the UART on the right.
    "U5":  (38, 133.5, "B", 0),
    "C8":  (27.305, 135.255, "B", 0),  # 3V3, at pin 3
    "C9":  (27.305, 137.795, "B", 0),
    "C7":  (47.625, 136.525, "B", 0),  # EN, at pin 45
    "R14": (47.625, 133.985, "B", 0),
    "TP10": (50.8, 136.525, "B", 0),  # EN
    "TP11": (27.94, 132.08, "B", 0),  # BOOT
    "TP8": (48.26, 130.81, "B", 0),   # UART0 TX, at pin 39
    "TP9": (48.26, 128.27, "B", 0),   # UART0 RX, at pin 40

    # -- BACK, Y 85..90, right: the power test points ------------------------
    "TP4": (50.8, 86.36, "B", 0),     # BAT
    "TP5": (53.34, 86.36, "B", 0),    # SYS
    "TP6": (50.8, 88.9, "B", 0),      # 3V3
    "TP7": (53.34, 88.9, "B", 0),     # GND
}

# Where anything not in the table goes, if the netlist grows.
HEAP_ORIGIN = (90.0, 20.0)

FP_SPLIT = "\n\t(footprint "
AT_RE = re.compile(r'(\n\t\t\(at )(-?[\d.]+) (-?[\d.]+)((?: -?[\d.]+)?\))')
REF_RE = re.compile(r'\(property "Reference" "([^"]+)"')
# A pad's own (at x y angle). The angle there is absolute -- it already
# includes the footprint's rotation -- so turning a footprint has to turn
# every one of its pads by the same amount or the land pattern comes out
# wrong. tools/fix_pads.py checks that it did.
PAD_AT_RE = re.compile(
    r'(\(pad "[^"]*" \w+ \w+\s*\(at )(-?[\d.]+) (-?[\d.]+)(?: (-?[\d.]+))?(\))')


def turn_pads(block, delta):
    """Add delta degrees to every pad angle in a footprint block."""
    if not delta % 360:
        return block

    def one(m):
        ang = (float(m.group(4) or 0.0) + delta) % 360
        tail = f" {ang:g}" if ang else ""
        return f"{m.group(1)}{m.group(2)} {m.group(3)}{tail}{m.group(5)}"

    return PAD_AT_RE.sub(one, block)


def back_refs():
    """The parts that belong on the back."""
    return sorted(r for r, v in FIRST_PASS.items() if v[2] == "B")


LAYER_RE = re.compile(r'"([FB])\.([A-Za-z]+)"')
# Every coordinate pair inside a footprint that is measured from the
# footprint's own origin. The footprint's own (at ...) is cut out first.
XY_RE = re.compile(r'\((at|start|end|center|mid|xy|offset) '
                   r'(-?[\d.]+) (-?[\d.]+)((?: -?[\d.]+)?)\)')
FONT_RE = re.compile(r'\(effects\n((\t+)\(font\n(?:.*?\n)*?\2\)\n)', re.S)
MODEL_RE = re.compile(r'\n\t\t\(model ')
SIDE_RE = re.compile(r'\(layer "([FB])\.Cu"\)')


def side_of(block):
    """Which side of the board a footprint block is on."""
    m = SIDE_RE.search(block)
    return m.group(1) if m else "F"


def swap_layers(text):
    return LAYER_RE.sub(
        lambda g: f'"{"B" if g.group(1) == "F" else "F"}.{g.group(2)}"', text)


def flip(block):
    """Turn a footprint block over.

    A flipped footprint is not the same footprint with B.* layer names: KiCad
    mirrors every coordinate inside it in y as well, and marks its text as
    mirrored so it still reads the right way round when you look at that side
    of the board.

    Two things are deliberately left alone. The 3D model block, because KiCad
    places the model from the footprint's side rather than from anything
    written there. And the pads, because fix_pads.py rewrites those from the
    library footprint outright, which is the only place their true geometry
    lives -- and it reads the side from the layer this sets.
    """
    m = MODEL_RE.search(block)
    body, tail = (block[:m.start()], block[m.start():]) if m else (block, "")

    at = AT_RE.search(body)
    head = swap_layers(body[:at.start()])
    own_at = body[at.start():at.end()]
    rest = swap_layers(body[at.end():])

    rest = XY_RE.sub(
        lambda g: f"({g.group(1)} {g.group(2)} {-float(g.group(3)) + 0.0:g}{g.group(4)})",
        rest)

    if side_of(head) == "B":
        rest = FONT_RE.sub(
            lambda g: f"(effects\n{g.group(1)}{g.group(2)}(justify mirror)\n", rest)
    else:
        rest = re.sub(r'\n\t+\(justify mirror\)', '', rest)

    def turn_one_pad(g):
        ang = (-float(g.group(4) or 0.0)) % 360
        return (f"{g.group(1)}{g.group(2)} {g.group(3)}"
                f"{f' {ang:g}' if ang else ''}{g.group(5)}")

    rest = PAD_AT_RE.sub(turn_one_pad, rest)

    return head + own_at + rest + tail


def main():
    text = PCB.read_text()
    head, *blocks = text.split(FP_SPLIT)

    # The footprints are one contiguous run, and everything after the last of
    # them -- the outline, the reference rectangles, the zones -- comes back
    # attached to it. Cut it off first: flip() swaps F. and B. layer names,
    # and it must not reach a zone.
    end = blocks[-1].index("\n\t)") + 3
    blocks[-1], tail = blocks[-1][:end], blocks[-1][end:]

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
        was = float(rot.strip(" )") or 0.0)
        want = FIRST_PASS[ref][2] if ref in FIRST_PASS else side_of(block)
        turning_over = side_of(block) != want
        if ref in TARGETS:
            x, y = TARGETS[ref]
        elif ref in FIRST_PASS:
            x, y, _layer, r = FIRST_PASS[ref]
            rot = f" {r})" if r else ")"
            # A mirror reverses the rotation the part is coming FROM, so the
            # delta is r + was going over and r - was staying put. See flip().
            block = turn_pads(block, r + was if turning_over else r - was)
            m = AT_RE.search(block)
        else:
            x, y = float(m.group(2)) + dx, float(m.group(3)) + dy
        new = f"{m.group(1)}{x:g} {y:g}{rot}"
        block = block[:m.start()] + new + block[m.end():]
        if turning_over:
            block = flip(block)
            flipped += 1
        out.append(block)
        moved += 1

    PCB.write_text(head + FP_SPLIT + FP_SPLIT.join(out) + tail)

    print(f"placed {len(TARGETS)} from the keypad script and {len(FIRST_PASS)} "
          f"from the first pass")
    print(f"{len(back_refs())} of them belong on the back; "
          f"{flipped} had to be turned over to get there")
    left = moved - len(TARGETS) - len(FIRST_PASS)
    if left:
        print(f"{left} not in either table, parked at "
              f"({HEAP_ORIGIN[0]:g}, {HEAP_ORIGIN[1]:g})")

    missing = [r for r in list(TARGETS) + list(FIRST_PASS) if r not in refs]
    if missing:
        print("not on the board yet, skipped: " + ", ".join(sorted(missing)))

    # J2's X is the one number on the board that is set by a part's internal
    # geometry rather than by where it should sit, so it is worth saying out
    # loud when the part in the file is not the part the number was worked
    # out for. 10.05 assumes the Amphenol F32Q's 2.90 mm pad offset; the
    # Hirose FH12 it replaced had 1.85 and wanted 9.00.
    if "J2" in refs:
        lib = blocks[refs.index("J2")].split('"', 2)[1]
        if "F32Q" not in lib:
            print(f"WARNING: J2 is still {lib}.\n"
                  "         X 9.75 is worked out from the Amphenol F32Q's "
                  "own depth, so the mouth\n"
                  "         has landed in the wrong place. Rebuild and "
                  "re-import the netlist,\n"
                  "         then run this again.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
