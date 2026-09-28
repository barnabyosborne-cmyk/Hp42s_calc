#!/usr/bin/env python3
"""Put the vendor 3D models on the footprint origins.

Barnaby found real vendor STEP for all seven parts whose footprints we drew
ourselves, on 23 September 2026. They are in elec/footprints/vendor-3d
exactly as they came. None of them arrives in KiCad's convention: every one
has its own idea of where the origin is and which way is up, so this script
turns and moves each one and writes the result to
elec/footprints/hp42s.3dshapes, which is what the footprints point at.

Run it with cadquery available:

    python3 tools/place_3d_models.py            # write them
    python3 tools/place_3d_models.py --check    # report only

KICAD'S CONVENTION, which is what every transform below is aiming at:

  - millimetres, and the origin is the footprint's origin
  - Z is up out of the board's front face, and z = 0 is the board surface,
    so a part's seating plane goes at 0 and only leads and bosses go below
  - +Y points UP the screen, while a footprint's +Y points DOWN it. So
    model y is the NEGATIVE of footprint y, and that is the single easiest
    thing to get wrong here.

Each transform is checked against the footprint it belongs to: --check
prints the model's bounding box in footprint coordinates next to the fab
outline and courtyard, and any real disagreement is a bug in one or the
other.
"""

import argparse
import re
import sys
from pathlib import Path

import cadquery as cq

ROOT = Path(__file__).resolve().parent.parent
PRETTY = ROOT / "elec" / "footprints" / "hp42s.pretty"
VENDOR = ROOT / "elec" / "footprints" / "vendor-3d"
SHAPES = ROOT / "elec" / "footprints" / "hp42s.3dshapes"

X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)

# footprint name -> (vendor file, axis, degrees, (dx, dy, dz), why)
PLACEMENT = {
    "Dome_4Leg_10mm": (
        "keystone-PN5154TR.step", X, 90, (0, 0, 0),
        "Keystone drew it with the dome's axis along Y. A quarter turn about "
        "X stands it up; it is already centred and its base is already at 0. "
        "The four legs come out along the axes, which is how the ring pad's "
        "octagon is drawn."),
    "Dome_4Leg_8.5mm": (
        "keystone-PN5134TR.step", X, 90, (0, 0, 0),
        "Same as the 10 mm. Note this is the Keystone 5134TR at 8.40 mm "
        "across and 0.50 high, not the Snaptron F08210 at 8.50 and 0.48 -- "
        "the pad takes either, and this is the one modelled."),
    "Alps_SKRTLAE010_SidePush": (
        "Alps-SKRTLA.step", Z, 0, (0, -1.21, 1.65),
        "Already the right way up and the right way round: plunger along -Y, "
        "which is footprint +Y. The body is z -1.65..1.65, so the board face "
        "is at -1.65 and the two guide bosses hang 0.5 below it. In Y the "
        "body runs 0..2.5 and wants to sit at footprint -1.35..1.21."),
    "Dialight_599_BiColor_1208_RA": (
        "Dialight-599-0Q70-247F.step", X, -90, (-1.5, 0.475, 1.0),
        "A right-angle LED, so it lies on its side: Dialight's model has the "
        "part standing with the lens along +Z, and the face that solders "
        "down is y = 1.0. A quarter turn back about X lays it down, which "
        "leaves the lens firing along footprint -Y and the part 1.0 tall."),
    "LiteOn_LTST-S326_BiColor_RA": (
        "Dialight-599-0Q70-247F.step", X, -90, (-1.5, 0.475, 1.0),
        "Stand-in: Lite-On publish no model for the LTST-S326 here, and the "
        "Dialight's is the same 3.0 x 2.0 x 1.0 side-looker with its lens "
        "on the same face, which is all the case check needs."),
    "Dialight_599_White_1208_RA": (
        "Dialight-599-0Q70-247F.step", X, -90, (-1.5, 0.475, 1.0),
        "Same package as the bi-colour, same land, different dice. Dialight "
        "publishes one model for the series."),
    "Vishay_VSMB2943SLX01_SideView": (
        "Vishay-VSMB2943SLX01.step", Y, 180, (0, -0.45, 1.15),
        "A side-looker: the lens is along +Y and has to stay parallel to the "
        "board, so the turn is about Y and not about X. Vishay's model sits "
        "with the body's underside at z = 1.15 and the lead feet at 1.10, "
        "0.05 above it, which is the solder gap -- so the body goes on the "
        "board and the feet just above."),
    "TI_DQA0010A_USON-10_2.5x1mm_P0.5mm": (
        "TI-DQA0010B.step", Z, 0, (0, 0, 0.027),
        "Already in KiCad's convention, and it lands on the pads with no "
        "turn at all. The DQA0010B is the same body as the A. NOTE: this is "
        "what showed up the footprint's fab outline and courtyard being 90 "
        "degrees out -- the pads run down the Y axis, the outline was drawn "
        "across X. The copper was always right. The 0.027 lift "
        "puts TI's seating plane on the board."),
    "TI_DSK0010A_WSON-10-1EP_2.5x2.5mm_P0.5mm_EP2x1.2mm": (
        "TI-DSK0010A.step", Z, 0, (0, 0, 0),
        "Already in KiCad's convention: centred, seating plane at 0, five "
        "pins down each side of Y. TI's exposed pad is 1.45 x 2.50 against "
        "the 1.20 x 2.00 land we draw, which is the safe way round."),

    # --- KiCad's own footprints whose models KiCad does not ship ------------
    # Barnaby found these six on 27 September 2026. The footprints are KiCad
    # stock, so the courtyard check needs KiCad's footprint library: pass
    # --stock with its path (the folder holding RF_Module.pretty and so on).
    # A list of (axis, degrees) is applied in order.
    # The board, not these footprints, points at the models, so KiCad's
    # "Update Footprints from Library" puts back KiCad's missing path. After
    # one, point the six back at hp42s.3dshapes (or re-run this and ask).
    "ESP32-S2-MINI-1": (
        "Espressif-ESP32-S3-MINI-1-N8.step", X, 90, (0, -2.5, 0),
        "Espressif draw it standing on Y with the antenna at -Z. A quarter "
        "turn about X lays it flat with the antenna at footprint -Y, where "
        "KiCad's antenna keepout is. The 2.5 mm puts the centre of the 3 x 3 "
        "ground grid on the footprint's (0, 2.55); the module is 20.5 long "
        "against KiCad's 20.0 fab outline, the extra half millimetre at the "
        "antenna end. The land is shared across the MINI-1 family."),
    "TDFN-8-1EP_2x2mm_P0.5mm_EP0.8x1.2mm": (
        "ADI-MAX17048GT10.step", Z, 0, (0, 0, 0),
        "Already in KiCad's convention. The pin-1 mark is at model (-1, +1), "
        "footprint (-1, -1), which is pin 1."),
    "L_Coilcraft_XxL4020": (
        "Coilcraft-XFL4020-222MEC.step", X, 90, (0, 0, 1.075),
        "Coilcraft stand it on Y and centre it in all three axes. A quarter "
        "turn about X and a 1.075 lift put the terminals on the board; they "
        "land on KiCad's pads at x 0.70..1.68 either side."),
    "Buzzer_Murata_PKLCS1212E": (
        "Murata-PKLCS1212E4001-R1.step", X, 90, (0, 0, 0),
        "Height along Y again; a quarter turn about X. Terminals at x +-5.6, "
        "on KiCad's pads. The sound port ends up at footprint -Y."),
    "JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal": (
        "JST-S2B-PH-SM4-TB.step", Z, 0, (0, -4.4, 0.1),
        "Right way up. JST put the body at y 0..7.6 with the two signal "
        "leads running on to 8.6; moved 4.4 so the body fills KiCad's fab "
        "outline (-3.2..4.4) and the leads land on pads 1 and 2. The leads "
        "dip 0.1 below JST's zero, so the 0.1 lift seats them."),
    "Amphenol_F32Q-1A7x1-11024_1x24-1MP_P0.5mm_Horizontal": (
        "Amphenol-F32Q-1A7H1-11024.step", [(Y, -90), (Z, 180)], None,
        (5.35, 2.25, 0),
        "Amphenol's height is X and its length is Z. A quarter turn about Y "
        "stands it up, a half turn about Z puts the tail leads at footprint "
        "-Y where the pads are, and the move centres the 19.3 mm body and "
        "puts the leads at y -3.25..-2.25 on 1.1 mm pads at -2.9."),
}

# Footprint library each stock footprint above comes from, for --stock.
STOCK_LIB = {
    "ESP32-S2-MINI-1": "RF_Module",
    "TDFN-8-1EP_2x2mm_P0.5mm_EP0.8x1.2mm": "Package_DFN_QFN",
    "L_Coilcraft_XxL4020": "Inductor_SMD",
    "Buzzer_Murata_PKLCS1212E": "Buzzer_Beeper",
    "JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal": "Connector_JST",
    "Amphenol_F32Q-1A7x1-11024_1x24-1MP_P0.5mm_Horizontal": "Connector_FFC-FPC",
}
STOCK = None

FAB = re.compile(r'\(fp_(?:rect|line|poly)[\s\S]*?"F\.Fab"')
XY = re.compile(r'\((?:start|end|xy) (-?[\d.]+) (-?[\d.]+)\)')


def outline(name, layer):
    """The footprint's fab outline or courtyard, as a bounding box in
    FOOTPRINT coordinates."""
    path = PRETTY / f"{name}.kicad_mod"
    if name in STOCK_LIB:
        if STOCK is None:
            return None
        path = STOCK / f"{STOCK_LIB[name]}.pretty" / f"{name}.kicad_mod"
    t = path.read_text()
    pts = []
    for m in re.finditer(r'\(fp_(line|rect|poly)([\s\S]*?)(?=\n\s*\(fp_|\n\s*\(pad|\n\)$)', t):
        if f'"{layer}"' not in m.group(2):
            continue
        pts += [(float(a), float(b)) for a, b in XY.findall(m.group(2))]
    if not pts:
        return None
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def place(name):
    src, axis, deg, (dx, dy, dz), _why = PLACEMENT[name]
    s = cq.importers.importStep(str(VENDOR / src))
    for ax, d in (axis if isinstance(axis, list) else [(axis, deg)]):
        if d:
            s = s.rotate((0, 0, 0), ax, d)
    return s.translate((dx, dy, dz))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="report the placements without writing them")
    ap.add_argument("--stock", type=Path,
                    help="KiCad's footprint library, to check the stock ones")
    args = ap.parse_args()
    global STOCK
    STOCK = args.stock

    SHAPES.mkdir(exist_ok=True)
    bad = 0
    for name in PLACEMENT:
        solid = place(name)
        bb = solid.val().BoundingBox()
        # into footprint coordinates: y is negated, and its ends swap
        fx0, fx1 = bb.xmin, bb.xmax
        fy0, fy1 = -bb.ymax, -bb.ymin
        print(f"\n{name}")
        print(f"   model      x {fx0:7.3f}..{fx1:7.3f}   "
              f"y {fy0:7.3f}..{fy1:7.3f}   z {bb.zmin:6.3f}..{bb.zmax:6.3f}")
        if name in STOCK_LIB and STOCK is None:
            print("   (KiCad stock footprint: pass --stock to check it)")
        for layer in ("F.Fab", "F.CrtYd"):
            o = outline(name, layer)
            if o:
                print(f"   {layer:9s}  x {o[0]:7.3f}..{o[2]:7.3f}   "
                      f"y {o[1]:7.3f}..{o[3]:7.3f}")
        crt = outline(name, "F.CrtYd")
        if crt and (fx0 < crt[0] - 0.01 or fx1 > crt[2] + 0.01
                    or fy0 < crt[1] - 0.01 or fy1 > crt[3] + 0.01):
            print("   *** the model reaches outside the courtyard")
            bad += 1
        if bb.zmin < -0.01 and "Alps" not in name:
            print(f"   *** {bb.zmin:.3f} is below the board face")
            bad += 1
        if not args.check:
            cq.exporters.export(solid, str(SHAPES / f"{name}.step"))
    if not args.check:
        print(f"\nwrote {len(PLACEMENT)} models to {SHAPES}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
