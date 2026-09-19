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

VSMB2943SLX01, side-looking IR emitter -- Vishay document 83479 rev 1.2,
drawing 6.544-5410.02-4, "Solder pad proposal acc. IPC 7351":

    2 x 0.9 x 1.2   pads
    4.2             outer edge to outer edge
    2.2 x 1.6       body, in plan
    0.95            the dome sticking out past the body front (2.55 overall)
    1.8             lens diameter

The offsets between the pads and the body were scaled off that drawing, which
dimensions both but not the gap between them: the body sits 0.43 mm forward of
the pad centreline and 1.19 mm behind it. Front view: cathode is the left lead
LOOKING INTO THE LENS, which puts it on -x once the lens faces -y.
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


def side_led(name, descr, tags, pad_w, pad_h, span, body_w, back, front,
             dome, lens_d):
    """A two-lead side-looking LED in plan, lens facing -y so that at zero
    degrees it looks at the top edge of the board. Origin is the centre of the
    two pads, which is what the vendor drawing calls the centre of the pick and
    place area. back/front are the body edges either side of that centreline,
    dome is how far the lens sticks out past the front one."""
    x = (span - pad_w) / 2.0
    cx = x + pad_w / 2.0 + 0.25
    out = [
        f'(footprint "{name}"',
        '\t(version 20221018)',
        '\t(generator "gen_ic_footprints.py")',
        '\t(layer "F.Cu")',
        f'\t(descr "{descr}")',
        f'\t(tags "{tags}")',
        '\t(attr smd)',
        f'\t(fp_text reference "REF**" (at 0 {back + 1.3:.2f}) (layer "F.SilkS")'
        ' (effects (font (size 1 1) (thickness 0.15))))',
        f'\t(fp_text value "{name}" (at 0 {back + 2.5:.2f}) (layer "F.Fab")'
        ' (effects (font (size 1 1) (thickness 0.15))))',
        # body in plan
        f'\t(fp_rect (start {-body_w/2:.3f} {-front:.3f}) (end {body_w/2:.3f} {back:.3f}) '
        '(stroke (width 0.1) (type solid)) (fill none) (layer "F.Fab"))',
        # the lens, drawn as the half circle that pokes out of the front face
        f'\t(fp_arc (start {lens_d/2:.3f} {-front:.3f}) '
        f'(mid 0 {-(front + dome):.3f}) (end {-lens_d/2:.3f} {-front:.3f}) '
        '(stroke (width 0.1) (type solid)) (layer "F.Fab"))',
        # optical axis, so the board outline can be lined up against it
        f'\t(fp_line (start 0 {-(front + dome) - 0.6:.3f}) (end 0 {back:.3f}) '
        '(stroke (width 0.05) (type dot)) (layer "F.Fab"))',
        # courtyard
        f'\t(fp_rect (start {-cx:.3f} {-(front + dome) - 0.25:.3f}) '
        f'(end {cx:.3f} {back + 0.25:.3f}) '
        '(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))',
        # cathode bar on silk, outboard of pad 1
        f'\t(fp_line (start {-cx + 0.1:.3f} {-pad_h/2:.3f}) '
        f'(end {-cx + 0.1:.3f} {pad_h/2:.3f}) '
        '(stroke (width 0.15) (type solid)) (layer "F.SilkS"))',
        f'\t(pad "1" smd roundrect (at {-x:.3f} 0) (size {pad_w:.3f} {pad_h:.3f}) '
        '(layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.15))',
        f'\t(pad "2" smd roundrect (at {x:.3f} 0) (size {pad_w:.3f} {pad_h:.3f}) '
        '(layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.15))',
        ')',
    ]
    return "\n".join(out) + "\n"


def bicolor_ra(name, descr, tags):
    """Dialight 599 bi-colour 1208 right angle. Three pads, lens facing -y.
    Hard-coded rather than parameterised: there is one of these and the pad
    arrangement is not a family pattern."""
    out = [
        f'(footprint "{name}"',
        '\t(version 20221018)',
        '\t(generator "gen_ic_footprints.py")',
        '\t(layer "F.Cu")',
        f'\t(descr "{descr}")',
        f'\t(tags "{tags}")',
        '\t(attr smd)',
        '\t(fp_text reference "REF**" (at 0 2.60) (layer "F.SilkS")'
        ' (effects (font (size 1 1) (thickness 0.15))))',
        f'\t(fp_text value "{name}" (at 0 3.80) (layer "F.Fab")'
        ' (effects (font (size 1 1) (thickness 0.15))))',
        # body in plan: 3.0 x 1.0, centred on the two end pads
        '\t(fp_rect (start -1.500 -0.500) (end 1.500 0.500) '
        '(stroke (width 0.1) (type solid)) (fill none) (layer "F.Fab"))',
        # lens: 2.0 mm wide, poking 1.07 mm out of the front face
        '\t(fp_arc (start 1.000 -0.500) (mid 0 -1.570) (end -1.000 -0.500) '
        '(stroke (width 0.1) (type solid)) (layer "F.Fab"))',
        '\t(fp_line (start 0 -2.170) (end 0 0.500) '
        '(stroke (width 0.05) (type dot)) (layer "F.Fab"))',
        '\t(fp_rect (start -2.250 -1.820) (end 2.250 1.400) '
        '(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))',
        # cathode marks: a bar outboard of pin 3, which is the red die
        '\t(fp_line (start -2.150 -0.750) (end -2.150 0.750) '
        '(stroke (width 0.15) (type solid)) (layer "F.SilkS"))',
        '\t(pad "3" smd roundrect (at -1.500 0) (size 1.000 1.500) '
        '(layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.15))',
        '\t(pad "2" smd roundrect (at 1.500 0) (size 1.000 1.500) '
        '(layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.15))',
        '\t(pad "1" smd roundrect (at 0 0.815) (size 0.900 0.650) '
        '(layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.15))',
        ')',
    ]
    return "\n".join(out) + "\n"


def uson_dqa(name, descr, tags):
    """TI DQA0010A, USON-10 2.5 x 1.0 mm. Not the same land as KiCad's generic
    USON-10_2.5x1.0mm_P0.5mm: TI makes the two ground terminals (pins 3 and 8)
    wider than the signal terminals, and puts every pad 0.033 mm further out.
    Hard-coded for the same reason bicolor_ra is -- two pads differ from the
    other eight, so there is no family pattern to parameterise.

    TI drawing 4220328/A, "EXAMPLE BOARD LAYOUT":

        4X (0.5)      pad pitch, five a side
        (0.835)       centre to centre across the two rows
        10X (0.565)   pad length, outward
        8X (0.2)      pad width, the eight signal pads
        2X (0.4)      pad width, pins 3 and 8, the grounds
        0.07 min      solder mask relief, non-solder-mask-defined
    """
    pitch, span, pad_l = 0.5, 0.835, 0.565
    body_w, body_h = 2.5, 1.0
    x = span / 2.0
    wide = {"3", "8"}
    out = [
        f'(footprint "{name}"',
        '\t(version 20221018)',
        '\t(generator "gen_ic_footprints.py")',
        '\t(layer "F.Cu")',
        f'\t(descr "{descr}")',
        f'\t(tags "{tags}")',
        '\t(attr smd)',
        '\t(fp_text reference "REF**" (at 0 -1.60) (layer "F.SilkS")'
        ' (effects (font (size 1 1) (thickness 0.15))))',
        f'\t(fp_text value "{name}" (at 0 1.60) (layer "F.Fab")'
        ' (effects (font (size 1 1) (thickness 0.15))))',
        f'\t(fp_rect (start {-body_w/2:.3f} {-body_h/2:.3f}) '
        f'(end {body_w/2:.3f} {body_h/2:.3f}) '
        '(stroke (width 0.1) (type solid)) (fill none) (layer "F.Fab"))',
    ]
    # courtyard: 0.25 around the pads, which reach further out than the body
    cx = x + pad_l / 2.0 + 0.25
    cy = body_h / 2.0 + 0.25
    out.append(f'\t(fp_rect (start {-body_w/2 - 0.25:.3f} {-cy:.3f}) '
               f'(end {body_w/2 + 0.25:.3f} {cy:.3f}) '
               '(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))')
    # pin 1 dot, outboard of pin 1
    out.append(f'\t(fp_circle (center {-body_w/2 - 0.35:.3f} {-2*pitch:.3f}) '
               f'(end {-body_w/2 - 0.20:.3f} {-2*pitch:.3f}) '
               '(stroke (width 0.15) (type solid)) (fill solid) (layer "F.SilkS"))')
    for i in range(10):
        n = str(i + 1)
        # 1-5 down the left column, 6-10 back up the right
        if i < 5:
            px, py = -x, (i - 2) * pitch
        else:
            px, py = x, (7 - i) * pitch
        w = 0.4 if n in wide else 0.2
        out.append(f'\t(pad "{n}" smd roundrect (at {px:.4f} {py:.3f} 270) '
                   f'(size {w:.3f} {pad_l:.3f}) '
                   '(layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25))')
    out.append(')')
    return "\n".join(out) + "\n"


def usb_c_16p(name, descr, tags):
    """Same Sky (CUI) UJ20-C-H-G-SMT-1A-P16-TR, 16-pin USB 2.0 Type-C
    receptacle, horizontal, from the "Recommended PCB Layout" on page 3 of the
    Same Sky drawing dated 11/03/2025.

    Everything here is dimensioned on that drawing:

        6.40 / 4.80 / 3.50   centre spans of the pad pairs, outermost in
        0.50                 pitch of the eight inner pads
        0.60*4 / 0.30*8      pad widths: four wide lands, eight narrow
        1.80                 pad length, measured back from the front slot line
        5.78, 0.65 dia       the two locating holes
        8.64                 shell slot centres, across
        4.18                 shell slot centres, front to back
        3.68                 locating hole to rear slot centre
        2.10 / 1.70          front slot: copper, then the slot itself
        1.80 / 1.40          rear slot: copper, then the slot itself
        1.00 / 0.60          both slots, across
        2.60                 rear slot centre back to the product edge

    The origin is the middle of the connector, on the locating-hole line, so
    that the product edge -- the case cut-out line -- sits at y = +3.675.

    This is NOT the HCTL HC-TYPE-C-16P-01A land KiCad ships, which this design
    used before. The pad x positions, both locating holes and both slot pitches
    are identical between them, but Same Sky's pads are 1.80 long rather than
    1.30, and its rear slot is 1.40 long rather than 1.20. A UJ20 dropped onto
    the HCTL pattern would not seat: its rear shell legs are 0.2 mm too long
    for the slot.
    """
    pad_l = 1.80
    hole_y = -2.605          # locating holes define y = 0 reference below
    front_slot_y = -3.105
    rear_slot_y = 1.075
    pad_near = front_slot_y  # pads run back from the front slot line
    pad_y = pad_near - pad_l / 2.0
    edge_y = rear_slot_y + 2.60
    slot_x = 4.32
    body_w, body_d = 8.94, 7.80

    lands = [
        (-3.20, 0.60, ["A1", "B12"]),
        (-2.40, 0.60, ["A4", "B9"]),
        (-1.75, 0.30, ["B8"]),
        (-1.25, 0.30, ["A5"]),
        (-0.75, 0.30, ["B7"]),
        (-0.25, 0.30, ["A6"]),
        (0.25, 0.30, ["A7"]),
        (0.75, 0.30, ["B6"]),
        (1.25, 0.30, ["A8"]),
        (1.75, 0.30, ["B5"]),
        (2.40, 0.60, ["B4", "A9"]),
        (3.20, 0.60, ["B1", "A12"]),
    ]

    out = [
        f'(footprint "{name}"',
        '\t(version 20221018)',
        '\t(generator "gen_ic_footprints.py")',
        '\t(layer "F.Cu")',
        f'\t(descr "{descr}")',
        f'\t(tags "{tags}")',
        '\t(attr smd)',
        f'\t(fp_text reference "REF**" (at 0 {pad_y - 1.60:.3f}) (layer "F.SilkS")'
        ' (effects (font (size 1 1) (thickness 0.15))))',
        f'\t(fp_text value "{name}" (at 0 {edge_y + 1.20:.3f}) (layer "F.Fab")'
        ' (effects (font (size 1 1) (thickness 0.15))))',
        # body in plan, 8.94 x 7.80, mouth on the product edge
        f'\t(fp_rect (start {-body_w/2:.3f} {edge_y - body_d:.3f}) '
        f'(end {body_w/2:.3f} {edge_y:.3f}) '
        '(stroke (width 0.1) (type solid)) (fill none) (layer "F.Fab"))',
        # the product edge itself, so the case cut-out has something to sit on
        f'\t(fp_line (start {-body_w/2 - 1.5:.3f} {edge_y:.3f}) '
        f'(end {body_w/2 + 1.5:.3f} {edge_y:.3f}) '
        '(stroke (width 0.1) (type dash)) (layer "Dwgs.User"))',
    ]
    crt_x = slot_x + 0.50 + 0.25
    out.append(f'\t(fp_rect (start {-crt_x:.3f} {pad_y - pad_l/2 - 0.25:.3f}) '
               f'(end {crt_x:.3f} {edge_y + 0.25:.3f}) '
               '(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))')
    # silk: two short marks beside the pad row, clear of every pad and slot
    for sx in (-1, 1):
        out.append(f'\t(fp_line (start {sx * 3.75:.3f} {pad_y - pad_l/2:.3f}) '
                   f'(end {sx * 3.75:.3f} {pad_y + pad_l/2:.3f}) '
                   '(stroke (width 0.12) (type solid)) (layer "F.SilkS"))')
    for px, w, names in lands:
        for n in names:
            out.append(f'\t(pad "{n}" smd roundrect (at {px:.3f} {pad_y:.3f}) '
                       f'(size {w:.3f} {pad_l:.3f}) '
                       '(layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25))')
    for hx in (-2.89, 2.89):
        out.append(f'\t(pad "" np_thru_hole circle (at {hx:.3f} {hole_y:.3f}) '
                   '(size 0.650 0.650) (drill 0.650) (layers "F&B.Cu" "*.Mask"))')
    # shell legs: plated slots, front pair long, rear pair short
    for sx in (-slot_x, slot_x):
        out.append(f'\t(pad "SH" thru_hole oval (at {sx:.3f} {front_slot_y:.3f}) '
                   '(size 1.000 2.100) (drill oval 0.600 1.700) '
                   '(layers "*.Cu" "*.Mask"))')
        out.append(f'\t(pad "SH" thru_hole oval (at {sx:.3f} {rear_slot_y:.3f}) '
                   '(size 1.000 1.800) (drill oval 0.600 1.400) '
                   '(layers "*.Cu" "*.Mask"))')
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
        "Vishay_VSMB2943SLX01_SideView": side_led(
            name="Vishay_VSMB2943SLX01_SideView",
            descr="Vishay VSMB2943SLX01, 940 nm side-looking IR emitter, "
                  "2.3x2.55x2.3 mm. Pads per the IPC 7351 solder pad proposal in "
                  "Vishay document 83479 rev 1.2. Lens faces -y; optical axis sits "
                  "1.2 mm above the board face the part is soldered to. "
                  "Pad 1 = cathode.",
            tags="LED IR 940nm side-view sidelooker VSMB2943SLX01",
            pad_w=0.9, pad_h=1.2, span=4.2, body_w=2.2,
            back=1.19, front=0.43, dome=0.95, lens_d=1.8,
        ),
        "Dialight_599_BiColor_1208_RA": bicolor_ra(
            name="Dialight_599_BiColor_1208_RA",
            descr="Dialight 599 series MicroLED, bi-colour 1208 right angle, "
                  "3.0x2.0x1.0 mm. Pads per the recommended layout on page 1 of the "
                  "Dialight datasheet. Lens faces -y; it spans roughly 1.0 to 2.0 mm "
                  "above the board face the part is soldered to. Pad 2 = common "
                  "anode, pad 3 = LED die 1, pad 1 = LED die 2.",
            tags="LED bicolor side-view right-angle Dialight 599 1208",
        ),
        "TI_DQA0010A_USON-10_2.5x1mm_P0.5mm": uson_dqa(
            name="TI_DQA0010A_USON-10_2.5x1mm_P0.5mm",
            descr="TI DQA0010A, USON-10 2.5x1.0mm, 0.5mm pitch. From TI drawing "
                  "4220328/A example board layout. Pins 3 and 8, the grounds, get "
                  "the wider 0.4mm pads TI draws for them. Used by TPD4E05U06.",
            tags="USON DFN TPD4E05U06 DQA0010A ESD",
        ),
        "SameSky_UJ20-C-H-G-SMT-1A-P16_USB-C": usb_c_16p(
            name="SameSky_UJ20-C-H-G-SMT-1A-P16_USB-C",
            descr="Same Sky (CUI) UJ20-C-H-G-SMT-1A-P16-TR, 16-pin USB 2.0 Type-C "
                  "receptacle, horizontal SMT with through-hole shell legs. From the "
                  "recommended PCB layout in the Same Sky drawing of 11/03/2025. "
                  "Origin on the locating-hole line; the product edge is at y=+3.675.",
            tags="USB-C Type-C receptacle UJ20 SameSky CUI 16P",
        ),
    }
    for name, text in fps.items():
        path = os.path.join(outdir, name + ".kicad_mod")
        with open(path, "w") as f:
            f.write(text)
        print("wrote", path)


if __name__ == "__main__":
    main()
