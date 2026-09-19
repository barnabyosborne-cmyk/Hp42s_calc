#!/usr/bin/env python3
"""
Generate KiCad footprints for Snaptron F-series metal dome switch sites.

A dome site is two pads: an outer annular ring the dome's four legs rest on,
and a centre pad the dome's underside contacts when it snaps. Both must be
free of solder mask across the whole dome area, and the area must be flat --
no vias, no silkscreen, no components inside the dome circle.

WHERE THE NUMBERS COME FROM
---------------------------
Snaptron's catalogue pages for the two domes, 2026-09-19:

                    F08210      F10260
    A  dome dia      8.5        10.0     tip to tip across opposite legs
    B  leg width     1.70        2.29
    C  height        0.48        0.56    unpressed, above the board
    D                7.06        8.31
    E                3.30        4.19
    X  dome cavity   7.75        9.14
    force            210 gf      260 gf  both +/- 30 gf, 5M cycles

These are DOME dimensions, not a pad drawing -- Snaptron publish the pad
recommendation separately and snaptron.com is not reachable from here. So the
ring is derived from A, which is the one figure that decides it: the four legs
land on a circle of diameter A, so the ring has to cover that circle with
enough margin for placement tolerance, and it can be as wide inwards as we
like because nothing else touches it until the centre pad.

    ring OD = A + 0.5    0.25 mm of margin outside the leg tips
    ring ID = A - 2.0    a 1.25 mm wide annulus for a 1.7-2.3 mm wide leg

A continuous ring rather than four leg pads, deliberately: it does not care
how the dome is rotated, which matters when there are 38 of them.

Still worth confirming if you can get it: Snaptron's own pad drawing for the
F series, which would also settle the centre pad diameter. That one is still
the old guess at roughly a third of the dome.

Two rules from Snaptron that the geometry already respects:
  - the keycap actuator must be <= 25% of dome diameter, centred. That is a
    keycap constraint, not a footprint one, but it is why CENTRE_DIA is small.
  - the cavity needs an air path or the click goes mushy. If you use a
    Peel-N-Place dome array, Snaptron vents through the polyester layer and
    you want VENT = False. Set it True only if you are venting through the
    board, and accept that it is a dust path into the dome cavity.

Output is KiCad 6-era footprint syntax, which every later version reads and
upgrades on load -- deliberately conservative so it opens in KiCad 10.

Usage:  python3 gen_dome_footprints.py [outdir]
"""

import sys
import pathlib

# --- dome definitions -------------------------------------------------------
# dome_dia   nominal dome diameter, mm (the catalogue number)
# ring_id    inner diameter of the outer contact ring, mm  (from A, see above)
# ring_od    outer diameter of the outer contact ring, mm  (from A, see above)
# centre_dia diameter of the centre contact pad, mm        <-- still a guess
DOMES = {
    "Snaptron_F10260_Dome": dict(
        dome_dia=10.0, ring_id=8.00, ring_od=10.50, centre_dia=3.50,
        note="10 mm, 260 gf, 0.56 mm high, 5M cycles -- numeric and operator keys",
    ),
    "Snaptron_F08210_Dome": dict(
        dome_dia=8.5, ring_id=6.50, ring_od=9.00, centre_dia=3.00,
        note="8.5 mm, 210 gf, 0.48 mm high, 5M cycles -- function rows and ENTER",
    ),
}

VENT = False        # True only if venting through the board rather than the array
VENT_DRILL = 0.60   # mm, NPTH
MASK_MARGIN = 0.40  # mm of mask clearance beyond the ring OD
CRTYD_MARGIN = 0.50 # mm of courtyard beyond the ring OD


def footprint(name, dome_dia, ring_id, ring_od, centre_dia, note):
    mean_r = (ring_id + ring_od) / 4.0    # midway between ID/2 and OD/2
    width = (ring_od - ring_id) / 2.0     # stroke width that fills ID..OD
    mask_r = ring_od / 2.0 + MASK_MARGIN
    crtyd_r = ring_od / 2.0 + CRTYD_MARGIN
    label_y = crtyd_r + 1.2

    L = []
    a = L.append
    a(f'(footprint "{name}"')
    a('  (version 20221018)')
    a('  (generator "hp42s-gen-dome")')
    a('  (layer "F.Cu")')
    a(f'  (descr "Snaptron metal dome site -- {note}. Ring ID {ring_id} mm, OD {ring_od} mm, centre pad {centre_dia} mm. Ring from the catalogue dome diameter; centre pad still a guess.")')
    a('  (tags "snaptron dome tactile keypad")')
    a('  (attr smd exclude_from_pos_files)')
    a(f'  (fp_text reference "SW**" (at 0 {-label_y:.3f}) (layer "F.SilkS")')
    a('    (effects (font (size 1 1) (thickness 0.15))))')
    a(f'  (fp_text value "{name}" (at 0 {label_y:.3f}) (layer "F.Fab")')
    a('    (effects (font (size 0.8 0.8) (thickness 0.12))))')

    # Outer ring: a custom pad whose anchor sits ON the ring so no copper lands
    # in the middle, plus a circle primitive stroked to the annulus width.
    a(f'  (pad "1" smd custom (at 0 {-mean_r:.4f}) (size {width:.4f} {width:.4f})')
    a('    (layers "F.Cu" "F.Mask")')
    a('    (options (clearance outline) (anchor circle))')
    a('    (primitives')
    a(f'      (gr_circle (center 0 {mean_r:.4f}) (end {mean_r:.4f} {mean_r:.4f}) (width {width:.4f}) (fill no))')
    a('    ))')

    # Centre pad
    a(f'  (pad "2" smd circle (at 0 0) (size {centre_dia:.3f} {centre_dia:.3f})')
    a('    (layers "F.Cu" "F.Mask"))')

    # Mask aperture over the whole dome area -- no numbered pad, mask layer only
    a(f'  (pad "" smd circle (at 0 0) (size {2*mask_r:.3f} {2*mask_r:.3f})')
    a('    (layers "F.Mask"))')

    if VENT:
        vent_r = (centre_dia / 2.0 + ring_id / 2.0) / 2.0
        a(f'  (pad "" np_thru_hole circle (at {vent_r:.3f} 0) (size {VENT_DRILL} {VENT_DRILL})')
        a(f'    (drill {VENT_DRILL}) (layers "F&B.Cu" "*.Mask"))')

    # Courtyard and fab outline. Nothing on silkscreen inside the dome circle --
    # the array has to sit on a flat surface.
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
        print(f"wrote {path}")
    print(f"\nAdd {outdir} to KiCad as a footprint library:")
    print("  Preferences > Manage Footprint Libraries > Add, type KiCad, point at the .pretty folder")


if __name__ == "__main__":
    main()
