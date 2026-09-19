#!/usr/bin/env python3
"""
Generate KiCad footprints for Snaptron F-series metal dome switch sites.

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
DOMES = {
    "Snaptron_F10260_Dome": dict(
        dome_dia=10.0, p1=4.08, n1=4.67, t1=3.15, w1=1.55, s=1.10,
        note="10 mm, 260 gf, 0.56 mm high, 5M cycles -- numeric and operator keys",
    ),
    "Snaptron_F08210_Dome": dict(
        dome_dia=8.5, p1=3.48, n1=4.19, t1=2.77, w1=1.55, s=0.92,
        note="8.5 mm, 210 gf, 0.48 mm high, 5M cycles -- function rows and ENTER",
    ),
}

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


def footprint(name, dome_dia, p1, n1, t1, w1, s, note):
    pts = c_ring(n1, t1, w1, s)
    corner = n1 * SEC2250                 # centre to an octagon corner
    mask_r = corner + MASK_MARGIN
    crtyd_r = corner + CRTYD_MARGIN
    label_y = crtyd_r + 1.2
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
    a(f'  (pad "" smd circle (at 0 0) (size {2*mask_r:.3f} {2*mask_r:.3f})')
    a('    (layers "F.Mask"))')

    if VENT:
        # between the centre pad and the ring, on the -x side, away from the tab
        vent_x = -(p1 / 2.0 + t1) / 2.0
        a(f'  (pad "" np_thru_hole circle (at {vent_x:.3f} 0) (size {VENT_DRILL} {VENT_DRILL})')
        a(f'    (drill {VENT_DRILL}) (layers "F&B.Cu" "*.Mask"))')

    # Courtyard, and the dome itself on F.Fab so the clearances are visible.
    a(f'  (fp_circle (center 0 0) (end {crtyd_r:.3f} 0) (layer "F.CrtYd") (width 0.05) (fill none))')
    a(f'  (fp_circle (center 0 0) (end {dome_dia/2:.3f} 0) (layer "F.Fab") (width 0.1) (fill none))')
    a(')')
    return "\n".join(L) + "\n"


def main():
    outdir = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "elec/footprints/hp42s.pretty")
    outdir.mkdir(parents=True, exist_ok=True)
    for name, spec in DOMES.items():
        path = outdir / f"{name}.kicad_mod"
        path.write_text(footprint(name, **spec))
        n1, dome = spec["n1"], spec["dome_dia"]
        print(f"wrote {path}  ring {2*n1:.2f} mm flats, "
              f"{2*n1*SEC2250:.2f} mm corners, dome {dome} mm")
    print(f"\nAdd {outdir} to KiCad as a footprint library:")
    print("  Preferences > Manage Footprint Libraries > Add, type KiCad, point at the .pretty folder")


if __name__ == "__main__":
    main()
