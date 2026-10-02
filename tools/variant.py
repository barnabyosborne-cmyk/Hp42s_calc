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
file existed. THIS IS THE `mip` BRANCH'S COPY: keep it when merging main.
"""

BOARD_W = 76.0
BOARD_H = 146.0             # 144 on the e-paper board

# The LS032B7DD02's glass is 47.02 tall against the e-paper's 36.30; the top
# edge was at Y 12 with the frontlight sliver below it (DROP 11, board 155).
# 2 October 2026 (Barnaby): no sliver or frontlight, and a 9.5 mm top bezel,
# so the glass starts at Y 7.5 and everything below it moves 2.0, board 146,
# case 150. docs/mip-display.md.
GLASS_Y = (7.5, 54.52)      # the panel glass, board Y, front
DROP_FROM = 48.3            # the e-paper glass's lower edge
DROP = 2.0


def drop(y):
    """A board Y from the e-paper tables, on this branch's board."""
    return y + DROP if y > DROP_FROM else y


def drop_pt(p):
    return (p[0], drop(p[1]))
