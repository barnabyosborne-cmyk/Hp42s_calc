#!/usr/bin/env python3
"""
Generate the land patterns KiCad does not ship, from the vendor drawings.

    python3 tools/gen_ic_footprints.py

Writes into elec/footprints/hp42s.pretty/. Same idea as
gen_dome_footprints.py: the numbers live here, in one place, next to the
drawing they came from, rather than being clicked into a footprint editor
where nobody can check them afterwards.

TPS63900, DSK0010A -- WSON-10, TI drawing 4218903/C, "EXAMPLE BOARD LAYOUT":

    8X (0.5)      pad pitch, five a side
    10X (0.6)     pad length, outward
    10X (0.25)    pad width
    (2.3)         outer edge to outer edge across the two rows
    (2) x (1.2)   thermal pad
    0.07 min      solder mask relief, non-solder-mask-defined (TI's preference)

Pad 11 is the thermal pad, which is KiCad's convention and matches the
netlist. TI's drawing calls it pin 11 too.
"""

import os

OUTDIR = os.path.join(os.path.dirname(__file__), "..", "elec", "footprints", "hp42s.pretty")


def wson(name, descr, tags, pins, pitch, pad_l, pad_w, span, body, ep_w, ep_h):
    """A two-row leadless package. pins must be even; numbering runs down the
    left column then back up the right, which is what every DFN/WSON does."""
    per = pins // 2
    x = (span - pad_l) / 2.0
    y0 = -(per - 1) * pitch / 2.0

    out = [
        f'(footprint "{name}"',
        '\t(version 20221018)',
        '\t(generator "gen_ic_footprints.py")',
        '\t(layer "F.Cu")',
        f'\t(descr "{descr}")',
        f'\t(tags "{tags}")',
        '\t(attr smd)',
        f'\t(fp_text reference "REF**" (at 0 {-body/2 - 1:.2f}) (layer "F.SilkS")'
        ' (effects (font (size 1 1) (thickness 0.15))))',
        f'\t(fp_text value "{name}" (at 0 {body/2 + 1:.2f}) (layer "F.Fab")'
        ' (effects (font (size 1 1) (thickness 0.15))))',
    ]

    # body outline on F.Fab, with a chamfer at pin 1
    h = body / 2.0
    c = 0.4
    out.append(
        f'\t(fp_poly (pts (xy {-h:.3f} {-h + c:.3f}) (xy {-h + c:.3f} {-h:.3f}) '
        f'(xy {h:.3f} {-h:.3f}) (xy {h:.3f} {h:.3f}) (xy {-h:.3f} {h:.3f})) '
        '(stroke (width 0.1) (type solid)) (fill none) (layer "F.Fab"))'
    )
    # courtyard: 0.25 mm beyond the wider of body and pads
    cx = max(h, x + pad_l / 2.0) + 0.25
    cy = max(h, -y0 + pad_w / 2.0) + 0.25
    out.append(
        f'\t(fp_rect (start {-cx:.3f} {-cy:.3f}) (end {cx:.3f} {cy:.3f}) '
        '(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))'
    )
    # pin 1 dot, clear of the pads
    out.append(
        f'\t(fp_circle (center {-x - pad_l/2 - 0.3:.3f} {y0:.3f}) '
        f'(end {-x - pad_l/2 - 0.15:.3f} {y0:.3f}) '
        '(stroke (width 0.12) (type solid)) (fill solid) (layer "F.SilkS"))'
    )

    def pad(n, px, py, w, hh):
        return (f'\t(pad "{n}" smd roundrect (at {px:.3f} {py:.3f}) '
                f'(size {w:.3f} {hh:.3f}) (layers "F.Cu" "F.Paste" "F.Mask") '
                '(roundrect_rratio 0.15))')

    for i in range(per):                       # left column, top to bottom
        out.append(pad(i + 1, -x, y0 + i * pitch, pad_l, pad_w))
    for i in range(per):                       # right column, bottom to top
        out.append(pad(per + 1 + i, x, y0 + (per - 1 - i) * pitch, pad_l, pad_w))
    out.append(pad(pins + 1, 0.0, 0.0, ep_w, ep_h))

    out.append(')')
    return "\n".join(out) + "\n"


def main():
    outdir = os.path.abspath(OUTDIR)
    os.makedirs(outdir, exist_ok=True)

    fps = {
        "TI_DSK0010A_WSON-10-1EP_2.5x2.5mm_P0.5mm_EP2x1.2mm": wson(
            name="TI_DSK0010A_WSON-10-1EP_2.5x2.5mm_P0.5mm_EP2x1.2mm",
            descr="TI DSK0010A, WSON-10 2.5x2.5mm, 0.5mm pitch, exposed pad 1.2x2.0mm. "
                  "From TI drawing 4218903/C example board layout. Used by TPS63900.",
            tags="WSON DFN TPS63900 DSK0010A",
            pins=10, pitch=0.5, pad_l=0.6, pad_w=0.25, span=2.3,
            body=2.5, ep_w=1.2, ep_h=2.0,
        ),
    }
    for name, text in fps.items():
        path = os.path.join(outdir, name + ".kicad_mod")
        with open(path, "w") as f:
            f.write(text)
        print("wrote", path)


if __name__ == "__main__":
    main()
