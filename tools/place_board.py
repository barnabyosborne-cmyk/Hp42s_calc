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
Every footprint's position, and its rotation: the 38 dome sites, the six
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
# PLACEMENT OF EVERYTHING ELSE, 23 September 2026
#
# (x, y, layer, rotation), board coordinates, Y down from the top edge.
# docs/placement.md has the reasoning. In short:
#
#   FRONT  Y 0..5      the six top-edge parts, set by the case
#          Y 5..11.6   the USB, IR and indicator parts that serve them
#          Y 12..48.3  the panel's glass
#          Y 48.3..57  the frontlight sliver's two lands and a ground point
#          Y 57..137   the keyboard
#   BACK   Y 5..59     the battery bay, full width but for the FPC in the
#                      left 10 mm. Nothing else goes there. Ever.
#          Y 59..144   every IC and every passive
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
    # -- FRONT, Y 5..11.6: what the six top-edge parts need ------------------
    # U1 is the USB ESD array; it sits directly under J1's D+/D- pins so the
    # pair is protected before it goes anywhere. R1/R2 are the CC pulldowns,
    # at U1's CC pins. C1 is VBUS's bulk cap, at the connector where the
    # current enters.
    "U1":  (35.56, 10.16, "F", 0),
    "R1":  (28.575, 10.16, "F", 0),
    "R2":  (31.75, 10.16, "F", 0),
    "C1":  (40.005, 10.16, "F", 0),
    # The IR emitter's driver, under D4.
    "Q2":  (22.86, 8.89, "F", 0),
    "R18": (20.955, 4.445, "F", 0),
    "R19": (18.415, 8.89, "F", 0),
    # The status LED's two ballast resistors, under D5.
    "R20": (49.53, 4.445, "F", 0),
    "R21": (46.355, 4.445, "F", 0),

    # -- FRONT, Y 48.3..57 ---------------------------------------------------
    # TP1 and TP2 are the frontlight sliver's solder lands, 60 mm apart
    # because that is the sliver's length. TP3 is a ground point to clip a
    # scope to while the frontlight is being set up.
    "TP1": (9.5, 50.5, "F", 0),
    "TP2": (69.5, 50.5, "F", 0),
    "TP3": (3.81, 53.34, "F", 0),

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
        if ref in TARGETS:
            x, y = TARGETS[ref]
        elif ref in FIRST_PASS:
            x, y, _layer, r = FIRST_PASS[ref]
            rot = f" {r})" if r else ")"
            block = turn_pads(block, r - was)
            m = AT_RE.search(block)
        else:
            x, y = float(m.group(2)) + dx, float(m.group(3)) + dy
        new = f"{m.group(1)}{x:g} {y:g}{rot}"
        block = block[:m.start()] + new + block[m.end():]
        want = FIRST_PASS[ref][2] if ref in FIRST_PASS else side_of(block)
        if side_of(block) != want:
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
