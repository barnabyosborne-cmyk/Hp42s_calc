"""Where the e-paper board (branch `main`) and the MIP board (branch `mip`)
differ in shape.

The MIP panel's glass is taller than the e-paper's, so on that branch
everything below the old glass -- the frontlight lands, the keyboard, every
part on the back from the charger down, the bottom edge -- moves down by
DROP as one block. The tables in place_board.py, route_power.py,
mounting.py and the rest keep the e-paper numbers and pass every board Y
through drop(), so a fix to one of those tables on `main` merges into `mip`
unchanged.

On `main` DROP is 0 and every tool behaves exactly as it did before this
file existed. THIS IS THE `ls027` BRANCH'S COPY: keep it when merging main
or mip.
"""

BOARD_W = 76.0
BOARD_H = 142.0             # 144 on the e-paper board, 146 on mip

# The LS032B7DD02's glass is 47.02 tall against the e-paper's 36.30; the top
# edge was at Y 12 with the frontlight sliver below it (DROP 11, board 155).
# 2 October 2026 (Barnaby): no sliver or frontlight, and a 9.5 mm top bezel,
# so the glass starts at Y 7.5 and everything below it moves 2.0, board 146,
# case 150. docs/mip-display.md.
#
# 4 October 2026, branch ls027: the 2.7 inch LS027B7DH01 (glass 62.8 x 42.82,
# centred across the board) with an optional Azumo 11103-06 front light. The
# glass ends at Y 50.32 and its tail folds back through a slot just below,
# so the keyboard comes up 4.0 from mip: DROP -2, board 142, case 146.
# docs/ls027-display.md.
GLASS_Y = (7.5, 50.32)      # the panel glass, board Y, front
GLASS_X = (6.6, 69.4)
DROP_FROM = 48.3            # the e-paper glass's lower edge
DROP = -2.0

# Holes through the board, besides the mounting holes: (x0, y0, x1, y1).
# The front light's coupler sits behind the glass at its right-hand end and
# passes through the board (38.1 x 6.9 x 2.6, 0.25 mm clearance all round);
# the panel's FPC folds back through the slot below the glass, 0.9-2.6 mm
# from the glass edge (Sharp: bend 0.8-6.0 mm out, inner R >= 0.45).
CUTOUTS = [(59.85, 7.75, 67.25, 46.45),     # Azumo light coupler
           (32.75, 51.2, 43.25, 52.9)]      # LS027 FPC slot

# The cell on the back: 6 x 38 x 50 (603850 class). 45 x 55 no longer fits
# between the top-edge parts and the FPC's fold, and the coupler takes the
# right-hand 9 mm.
BAY = (5.0, 12.5, 55.0, 50.5)

# Back-side strip the front light's LED flex lies along, from the coupler to
# its two wire pads: keep parts out of it.
FLEX = (62.8, 46.0, 66.6, 79.0)


def drop(y):
    """A board Y from the e-paper tables, on this branch's board."""
    return y + DROP if y > DROP_FROM else y


def drop_pt(p):
    return (p[0], drop(p[1]))
