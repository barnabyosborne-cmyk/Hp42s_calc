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
file existed.
"""

BOARD_W = 76.0
BOARD_H = 144.0

GLASS_Y = (12.0, 48.3)      # the panel glass, board Y, front
DROP_FROM = 48.3            # the e-paper glass's lower edge
DROP = 0.0


def drop(y):
    """A board Y from the e-paper tables, on this branch's board."""
    return y + DROP if y > DROP_FROM else y


def drop_pt(p):
    return (p[0], drop(p[1]))
