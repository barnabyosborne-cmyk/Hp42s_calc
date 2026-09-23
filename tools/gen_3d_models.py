#!/usr/bin/env python3
"""Build the 3D models the seven hp42s footprints have no vendor STEP for.

Run it with cadquery available:

    python3 tools/gen_3d_models.py

It writes elec/footprints/hp42s.3dshapes/*.step and adds the matching
(model ...) line to each .kicad_mod, so the models survive a netlist
re-import -- the board file only carries what the library gave it.

WHAT THESE ARE. Simplified envelopes built from the dimensions in each
footprint's own fab outline and description, which came off the vendor
drawings. They are the right size and in the right place; they are not
vendor CAD, so they have no chamfers, no leads and no markings. That is
enough for what they are for: seeing the board in 3D, and checking the case
against the parts that stand proud of it.

COORDINATES. KiCad's 3D space has +Y pointing UP the screen while footprint
coordinates have +Y pointing DOWN, so every y here is the negative of the
footprint's. Z is up out of the board's front face, in millimetres.
"""

import sys
from pathlib import Path

import cadquery as cq

ROOT = Path(__file__).resolve().parent.parent
PRETTY = ROOT / "elec" / "footprints" / "hp42s.pretty"
SHAPES = ROOT / "elec" / "footprints" / "hp42s.3dshapes"


def dome(diameter, height, foil=0.075):
    """A four-leg metal dome: a spherical cap of sheet steel sitting on the
    board. Base diameter across the flats, height at the crown, both from
    the Snaptron pad table in the footprint's description."""
    r = diameter / 2.0
    sphere_r = (r * r + height * height) / (2 * height)
    centre = height - sphere_r

    def cap(rad, dz):
        return (cq.Workplane("XY")
                .sphere(rad, centered=(True, True, True))
                .translate((0, 0, centre + dz))
                .intersect(cq.Workplane("XY")
                           .box(diameter, diameter, height * 2,
                                centered=(True, True, False))))

    outer = cap(sphere_r, 0)
    inner = cap(sphere_r, -foil)
    return outer.cut(inner)


def alps_skrtlae010():
    """Body 4.5 x 2.56 x 3.3, plunger 2.0 wide standing 0.83 proud of the
    +y face. The plunger's height on the body is not in the drawing I have,
    so it is drawn centred: 1.5 mm tall at mid-height."""
    body = cq.Workplane("XY").box(4.5, 2.56, 3.3, centered=(True, False, False))
    body = body.translate((0, -1.21, 0))          # fab y -1.35..1.21, negated
    plunger = (cq.Workplane("XY")
               .box(2.0, 0.83, 1.5, centered=(True, False, False))
               .translate((0, -2.04, 0.9)))
    return body.union(plunger)


def dialight_599_ra():
    """1208 right-angle LED. Body 3.0 x 1.0 x 2.0 with the lens bulging
    1.07 mm out of the -y face over the top half of the body."""
    body = cq.Workplane("XY").box(3.0, 1.0, 2.0, centered=(True, True, False))
    lens = (cq.Workplane("XY", origin=(0, 0.5, 1.0))
            .ellipse(1.0, 1.07).extrude(1.0)
            .intersect(cq.Workplane("XY")
                       .box(3.0, 1.07, 2.0, centered=(True, False, False))
                       .translate((0, 0.5, 0))))
    return body.union(lens)


def vishay_vsmb2943():
    """940 nm side-looker. Body 2.2 x 1.62 x 2.3 with the lens bulging
    0.95 mm out of the -y face, 1.8 mm across, on the optical axis 1.2 mm
    above the board."""
    body = (cq.Workplane("XY").box(2.2, 1.62, 2.3, centered=(True, False, False))
            .translate((0, -1.19, 0)))
    lens = (cq.Workplane("XY", origin=(0, 0.43, 0.3))
            .ellipse(0.9, 0.95).extrude(1.8)
            .intersect(cq.Workplane("XY")
                       .box(2.2, 0.95, 2.3, centered=(True, False, False))
                       .translate((0, 0.43, 0))))
    return body.union(lens)


def usaon_dqa0010a():
    """TI USON-10, 2.5 x 1.0, 0.6 max tall."""
    return cq.Workplane("XY").box(2.5, 1.0, 0.6, centered=(True, True, False))


def wson_dsk0010a():
    """TI WSON-10, 2.5 x 2.5, 0.8 max tall, pin 1 corner chamfered 0.4."""
    pts = [(-1.25, 0.85), (-0.85, 1.25), (1.25, 1.25),
           (1.25, -1.25), (-1.25, -1.25)]
    return cq.Workplane("XY").polyline(pts).close().extrude(0.8)


PARTS = {
    "Dome_4Leg_10mm": lambda: dome(10.0, 0.56),
    "Dome_4Leg_8.5mm": lambda: dome(8.5, 0.48),
    "Alps_SKRTLAE010_SidePush": alps_skrtlae010,
    "Dialight_599_BiColor_1208_RA": dialight_599_ra,
    "Dialight_599_White_1208_RA": dialight_599_ra,
    "Vishay_VSMB2943SLX01_SideView": vishay_vsmb2943,
    "TI_DQA0010A_USON-10_2.5x1mm_P0.5mm": usaon_dqa0010a,
    "TI_DSK0010A_WSON-10-1EP_2.5x2.5mm_P0.5mm_EP2x1.2mm": wson_dsk0010a,
}

MODEL_BLOCK = """\t(model "${{KIPRJMOD}}/../../footprints/hp42s.3dshapes/{name}.step"
\t\t(offset (xyz 0 0 0))
\t\t(scale (xyz 1 1 1))
\t\t(rotate (xyz 0 0 0))
\t)
"""


def add_model_to_footprint(name):
    f = PRETTY / f"{name}.kicad_mod"
    t = f.read_text()
    if "(model " in t:
        return False
    end = t.rstrip().rfind("\n)")
    if end < 0:
        raise SystemExit(f"{f}: cannot find the closing paren")
    f.write_text(t[:end + 1] + MODEL_BLOCK.format(name=name) + ")\n")
    return True


def main():
    SHAPES.mkdir(exist_ok=True)
    for name, build in PARTS.items():
        solid = build()
        out = SHAPES / f"{name}.step"
        cq.exporters.export(solid, str(out))
        bb = solid.val().BoundingBox()
        print(f"{name}\n    {out.stat().st_size / 1024:.0f} kB   "
              f"x {bb.xmin:.2f}..{bb.xmax:.2f}  "
              f"y {bb.ymin:.2f}..{bb.ymax:.2f}  "
              f"z {bb.zmin:.2f}..{bb.zmax:.2f}")
        if add_model_to_footprint(name):
            print("    added the (model ...) line to the footprint")
    return 0


if __name__ == "__main__":
    sys.exit(main())
