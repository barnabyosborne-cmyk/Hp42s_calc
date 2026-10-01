"""Where the e-paper board (branch `main`), the MIP board (branch `mip`) and
the Displaytech board (branch `dt`) differ in shape.

The MIP panel's glass is taller than the e-paper's, so on that branch
everything below the old glass -- the frontlight lands, the keyboard, every
part on the back from the charger down, the bottom edge -- moves down by
DROP as one block. The tables in place_board.py, route_power.py,
mounting.py and the rest keep the e-paper numbers and pass every board Y
through drop(), so a fix to one of those tables on `main` merges into `mip`
unchanged.

On `main` DROP is 0 and every tool behaves exactly as it did before this
file existed. THIS IS THE `dt` BRANCH'S COPY (Displaytech 64128M): keep it
when merging main or mip.
"""

BOARD_W = 76.0
BOARD_H = 147.0             # 144 on the e-paper board, 155 on mip

# The 64128M's glass is 75 x 50, mounted upright (pins at the bottom, the
# standard 6 o'clock part). Its top edge sits at Y 10.5, below mounting holes
# A and B's 6 mm clear circles; the clip-pin row is 0.25 mm below the glass,
# at Y 60.75, and the first dome sites start 2 mm under the pads. Everything
# below the e-paper glass's old lower edge moves 6.0. 64128M COG series spec
# v1.0, page 7; docs/displaytech-display.md.
GLASS_Y = (7.5, 57.5)      # the panel glass, board Y, front
PIN_ROW_Y = 57.75           # J2's pin row, footprint origin
DROP_FROM = 48.3            # the e-paper glass's lower edge
DROP = 3.0
# The cell bay runs from Y 8.5 (the USB parts moved out of the band under J1)
# to 0.75 mm above J2's pin pads: 47.5 mm, for a 47 x 55 cell.
BAY_TOP = 8.5
BAY_BOTTOM = 56.0


def drop(y):
    """A board Y from the e-paper tables, on this branch's board."""
    return y + DROP if y > DROP_FROM else y


def drop_pt(p):
    return (p[0], drop(p[1]))
