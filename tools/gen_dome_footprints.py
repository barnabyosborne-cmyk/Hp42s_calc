#!/usr/bin/env python3
"""
Generate KiCad footprints for the 8.5 mm and 10 mm metal dome switch sites.

A dome site is two pads. The outer one is an octagonal ring the dome's four
legs rest on. The centre one is a circle the dome's underside touches when it
snaps, with a tab that escapes through a slot in the ring so the net can be
routed on the front layer without a via inside the dome cavity.

NUMBERS, AND WHERE THEY COME FROM
---------------------------------
Snaptron's own PCB pad layout drawing and its metric dimension table, sent by
Barnaby 2026-09-19. This replaced a set of guesses. Their letters:

    P1   centre pad diameter
    N1   centre of the site to the OUTER flat of the ring   (half width)
    T1   centre of the site to the INNER flat of the ring   (half width)
    W1   width of the tab that escapes through the slot
    S    clearance either side of that tab, 0.508 mm minimum
    F1   via in the centre pad, optional on a double sided board
    F2   via in the ring, for a single sided board

                     P1      N1      T1      W1      S       F1/F2
    8.5 mm dome      3.48    4.19    2.77    1.55    0.92    0.89
    10 mm dome       4.08    4.67    3.15    1.55    1.10    0.89

N1 and T1 really are half widths: the table's 4 mm row gives N1 2.10, and a
ring 2.10 mm across would not reach the legs of a 4 mm dome. Every row of the
table is consistent with N1 being about 0.47 of the dome diameter, and the
slot height W1/2 + S comes out just inside the octagon's flat in both of our
sizes, which is the arithmetic working.

Note the ring is NARROWER than the dome: 8.38 mm across the flats for an
8.5 mm dome. The legs overhang it slightly and contact just inside the tip.
That is Snaptron's design, not an error.

Two rules from Snaptron that the geometry respects:
  - solder mask keep-out starts at the OUTSIDE edge of the ring and includes
    everything inside it. The whole site is bare copper and bare laminate.
  - four-leg domes must be rotated so that no leg sits over the slot. With
    legs 90 degrees apart, putting them on the diagonals -- 45 degrees to the
    slot -- is the furthest they can be from it. A Peel-N-Place array fixes
    the rotation for you; loose domes do not, so check the first board with a
    meter before trusting 38 of them.
  - the cavity needs an air path or the click goes mushy. A Peel-N-Place
    array vents through the polyester layer, so VENT stays False. Set it True
    only if you are venting through the board, and accept that it is a dust
    path into the cavity.
  - Snaptron's drawing is captioned "one of many possible layouts" and puts
    the final design on us. What we take from it is the dimensions.

Output is KiCad 6-era footprint syntax, which every later version reads and
upgrades on load -- deliberately conservative so it opens in KiCad 10.

Usage:  python3 gen_dome_footprints.py [outdir]
"""

import math
import sys
import pathlib

# dome_dia  nominal dome diameter, mm (the catalogue number)
# p1/n1/t1/w1/s  Snaptron's pad table, above
# foot_dia  the largest LEG CIRCLE any dome we might buy rests on, mm. The
#           ring is widened if Snaptron's N1 would not cover it -- see below.
DOMES = {
    "Dome_4Leg_10mm": dict(
        dome_dia=10.0, p1=4.08, n1=4.67, t1=3.15, w1=1.55, s=1.10,
        foot_dia=9.50,
        note="10 mm, 260 gf, 0.56 mm high -- numeric and operator keys. "
             "Snaptron F10260 or Keystone 5154TR",
    ),
    "Dome_4Leg_8.5mm": dict(
        dome_dia=8.5, p1=3.48, n1=4.19, t1=2.77, w1=1.55, s=0.92,
        foot_dia=8.00,
        note="8.5 mm, 210/280 gf, 0.48 mm high -- function rows and ENTER. "
             "Snaptron F08210 or Keystone 5134TR",
    ),
}

# TWO SUPPLIERS, ONE PAD
#
# Snaptron sell direct and by quote. Keystone's equivalents are stocked by the
# usual distributors, and their drawings (5134TR and 5154TR, both rev A) give
# a "mounting diameter" -- the circle the four legs stand on:
#
#                   tip to tip   mounting dia   force    height
#   Snaptron F08210    8.50          --         210 gf   0.48
#   Keystone 5134TR    8.40         8.00        280 g    0.50
#   Snaptron F10260   10.00          --         260 gf   0.56
#   Keystone 5154TR   10.00         9.50        280 g    0.55
#
# Keystone's 9.50 mm circle lands 0.08 mm OUTSIDE the ring Snaptron's N1 asks
# for, which is the sort of half-on-the-pad contact that makes a key feel
# intermittent. So the ring's outer flat goes to whichever is larger, N1 or
# the leg circle plus 0.25 mm. That widens the 10 mm site from 9.34 to 10.00
# across the flats and the 8.5 mm site from 8.38 to 8.50, both still clear of
# their neighbours on a 12.0 mm row pitch.
#
# Note Keystone publish their own pattern -- four round pads on the leg circle
# plus a centre one -- and we are NOT using it. Four discrete pads need the
# dome rotated to line up with them. A ring does not care, which is worth
# having when 38 of them go down by hand.

# Metal domes come in two kinds and this pad suits one of them. A FOUR LEG
# dome (Snaptron F series, what this board is drawn for) touches the ring only
# at its four legs, so the slot and the escape tab sit under thin air. A ROUND
# dome has a continuous rim, and that rim crosses the slot -- where it would
# land straight on the escape tab and short the switch on permanently.
#
# Set ROUND_DOME_SAFE True to cover the tab with solder mask where the rim
# crosses it. That is the standard trick for round domes, and it is harmless
# for four-leg ones: the patch sits in the gap between the centre pad and the
# ring, under the curve of the dome, where nothing touches anyway. It costs a
# 30 um step in a place the dome clears by more than ten times that.
#
# Left False so that what this generates is Snaptron's own drawing. Flip it if
# the domes you can actually buy turn out to be round.
ROUND_DOME_SAFE = False

VENT = False        # True only if venting through the board rather than the array
VENT_DRILL = 0.60   # mm, NPTH
TAB_OVERHANG = 0.40 # mm the centre tab runs past the ring, for the trace to meet
MASK_MARGIN = 0.25  # mm of mask clearance beyond the ring's corners
CRTYD_MARGIN = 0.25 # mm of courtyard beyond the ring's corners
ANCHOR = 0.30       # mm, the custom pads' anchor circles

TAN2250 = math.tan(math.radians(22.5))
SEC2250 = 1.0 / math.cos(math.radians(22.5))


def octagon(half_width):
    """Regular octagon, flat to flat = 2 * half_width, as (flat half length,
    half width). The chamfers are the 45 degree ones on Snaptron's drawing."""
    return half_width * TAN2250, half_width


def octagon_outline(half_width):
    """The eight corners of a regular octagon, flats on the axes."""
    f, R = octagon(half_width)
    return [(R, -f), (f, -R), (-f, -R), (-R, -f),
            (-R, f), (-f, R), (f, R), (R, f)]


def c_ring(n1, t1, w1, s):
    """The ring as ONE polygon. It is a C rather than an annulus -- the slot
    on the +x side makes it simply connected -- so it traces as a single loop:
    out around the outside, in at the slot, back around the inside.

    Returns a list of (x, y) with -y as up."""
    f, R = octagon(n1)          # outer flat half length, outer half width
    fi, r = octagon(t1)         # inner
    h = w1 / 2.0 + s            # half height of the slot

    if h >= f:
        raise ValueError(f"slot {2*h:.2f} does not fit the {2*f:.2f} outer flat")

    # where the inner boundary meets the slot: on the flat if the slot is
    # narrow enough, otherwise up on the chamfer, whose line is x + y = r + fi
    xi = r if h <= fi else (r + fi) - h

    return [
        (R, -h), (R, -f), (f, -R), (-f, -R), (-R, -f),      # outside, going
        (-R, f), (-f, R), (f, R), (R, h),                   # right-top-left-bottom
        (xi, h), (fi, r), (-fi, r), (-r, fi), (-r, -fi),    # inside, coming back
        (-fi, -r), (fi, -r), (xi, -h),
    ]


def footprint(name, dome_dia, p1, n1, t1, w1, s, foot_dia, note):
    n1 = max(n1, foot_dia / 2.0 + 0.25)     # cover the widest leg circle
    pts = c_ring(n1, t1, w1, s)
    corner = n1 * SEC2250                 # centre to an octagon corner
    # Mask and courtyard follow the ring's shape rather than its circumcircle.
    # A circle round an octagon wastes 0.8 mm on every flat, and the flats are
    # where the neighbouring dome is: on a 12.0 mm row pitch that is the
    # difference between 1.5 mm of mask web and 0.7 mm.
    mask_pts = [(x, y) for x, y in octagon_outline(n1 + MASK_MARGIN)]
    crtyd_pts = [(x, y) for x, y in octagon_outline(n1 + CRTYD_MARGIN)]
    label_y = (n1 + CRTYD_MARGIN) * SEC2250 + 1.2
    ring_mid = (n1 + t1) / 2.0            # where pad 1's anchor sits

    L = []
    a = L.append
    a(f'(footprint "{name}"')
    a('  (version 20221018)')
    a('  (generator "hp42s-gen-dome")')
    a('  (layer "F.Cu")')
    a(f'  (descr "Snaptron metal dome site -- {note}. Ring {2*n1:.2f} mm across '
      f'the flats, centre pad {p1:.2f} mm, tab {w1:.2f} mm out of the +x side. '
      f'From Snaptron pad table P1 {p1} N1 {n1} T1 {t1} W1 {w1} S {s}.")')
    a('  (tags "snaptron dome tactile keypad")')
    a('  (attr smd exclude_from_pos_files)')
    a(f'  (fp_text reference "SW**" (at 0 {-label_y:.3f}) (layer "F.SilkS")')
    a('    (effects (font (size 1 1) (thickness 0.15))))')
    a(f'  (fp_text value "{name}" (at 0 {label_y:.3f}) (layer "F.Fab")')
    a('    (effects (font (size 0.8 0.8) (thickness 0.12))))')

    # Pad 1, the ring. Anchored on the ring itself, at the top, so the anchor
    # circle never lands in the middle of the site where the centre pad is.
    a(f'  (pad "1" smd custom (at 0 {-ring_mid:.4f}) (size {ANCHOR} {ANCHOR})')
    a('    (layers "F.Cu" "F.Mask")')
    a('    (options (clearance outline) (anchor circle))')
    a('    (primitives')
    poly = " ".join(f"(xy {x:.4f} {y + ring_mid:.4f})" for x, y in pts)
    a(f'      (gr_poly (pts {poly}) (width 0) (fill yes))')
    a('    ))')

    # Pad 2, the centre, plus the tab that escapes through the slot.
    tab_x = n1 * SEC2250 + TAB_OVERHANG
    a(f'  (pad "2" smd custom (at 0 0) (size {p1:.3f} {p1:.3f})')
    a('    (layers "F.Cu" "F.Mask")')
    a('    (options (clearance outline) (anchor circle))')
    a('    (primitives')
    a(f'      (gr_poly (pts (xy 0 {-w1/2:.4f}) (xy {tab_x:.4f} {-w1/2:.4f}) '
      f'(xy {tab_x:.4f} {w1/2:.4f}) (xy 0 {w1/2:.4f})) (width 0) (fill yes))')
    a('    ))')

    # Mask keep-out over the whole site: Snaptron want bare copper and bare
    # laminate from the outside edge of the ring inwards.
    a('  (pad "" smd custom (at 0 0) (size 0.2 0.2)')
    a('    (layers "F.Mask")')
    a('    (options (clearance outline) (anchor circle))')
    a('    (primitives')
    a('      (gr_poly (pts ' + " ".join(f"(xy {x:.4f} {y:.4f})" for x, y in mask_pts)
      + ') (width 0) (fill yes))')
    a('    ))')

    if ROUND_DOME_SAFE:
        # a mask patch over the tab, from the centre pad's edge out past the
        # ring, so a continuous rim crosses insulation rather than copper
        patch_w = w1 + 0.4
        x0, x1 = p1 / 2.0 - 0.1, n1 * SEC2250 + 0.1
        a(f'  (fp_poly (pts (xy {x0:.3f} {-patch_w/2:.3f}) (xy {x1:.3f} {-patch_w/2:.3f}) '
          f'(xy {x1:.3f} {patch_w/2:.3f}) (xy {x0:.3f} {patch_w/2:.3f})) '
          '(stroke (width 0) (type solid)) (fill yes) (layer "F.Mask"))')

    if VENT:
        # between the centre pad and the ring, on the -x side, away from the tab
        vent_x = -(p1 / 2.0 + t1) / 2.0
        a(f'  (pad "" np_thru_hole circle (at {vent_x:.3f} 0) (size {VENT_DRILL} {VENT_DRILL})')
        a(f'    (drill {VENT_DRILL}) (layers "F&B.Cu" "*.Mask"))')

    # Courtyard, and the dome itself on F.Fab so the clearances are visible.
    a('  (fp_poly (pts ' + " ".join(f"(xy {x:.4f} {y:.4f})" for x, y in crtyd_pts)
      + ') (stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))')
    a(f'  (fp_circle (center 0 0) (end {dome_dia/2:.3f} 0) (layer "F.Fab") (width 0.1) (fill none))')
    a(')')
    return "\n".join(L) + "\n"


def main():
    outdir = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "elec/footprints/hp42s.pretty")
    outdir.mkdir(parents=True, exist_ok=True)
    for name, spec in DOMES.items():
        path = outdir / f"{name}.kicad_mod"
        path.write_text(footprint(name, **spec))
        n1 = max(spec["n1"], spec["foot_dia"] / 2.0 + 0.25)
        print(f"wrote {path}  ring {2*n1:.2f} mm flats, "
              f"{2*n1*SEC2250:.2f} mm corners, dome {spec['dome_dia']} mm, "
              f"leg circle {spec['foot_dia']} mm")
    print(f"\nAdd {outdir} to KiCad as a footprint library:")
    print("  Preferences > Manage Footprint Libraries > Add, type KiCad, point at the .pretty folder")


if __name__ == "__main__":
    main()
