#!/usr/bin/env python3
"""Does every ground pad on B.Cu still reach the ground plane?

    python3 tools/check_pour.py

The B.Cu ground pour is what connects most of the board's ground pads: they
have no tracks. Every signal track on B.Cu cuts it, with 0.5 mm of zone
clearance either side, so a pad can end up on an island of pour that nothing
connects to In1.Cu. KiCad reports that only after a refill, as an unconnected
item, and only on a machine with KiCad. This predicts it here.

The prediction is the zone filler's own recipe, roughly: the board inset by
the edge clearance, minus every non-ground copper on B.Cu grown by the zone's
clearance, minus the rule areas that forbid pour, then opened by half the
zone's minimum thickness to drop the slivers the filler would drop. A pad or
via of `gnd` that touches a piece joins it. A piece is grounded if it holds a
gnd via or a through-hole gnd pad, since those reach the In1.Cu plane.

It ignores thermal spokes (every gnd zone here connects pads solid) and it is
approximate at the half-tenth-millimetre level. What it is for is the big
failure: a pad with no way to ground at all.

Exit status 1 if any gnd pad is stranded.
"""

import sys
from pathlib import Path

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parent))
import route_power as rp            # noqa: E402
import route_signals as rs          # noqa: E402

ZONE_CLEAR = 0.5
MIN_THICK = 0.25
EDGE = 0.5
LAYER = "B.Cu"


def islands(pads, segs, vias, edge, keepouts):
    """Predict the B.Cu pour. Returns (n_pieces, shapes, stranded) where
    shapes are the gnd (label, geometry, grounded) and stranded the labels
    and geometries of gnd pads with no way to the plane."""
    import shapely
    cut = []
    gnd_shapes = []            # (label, geometry, reaches_plane)
    for p in pads:
        if not rp.on_layer(p, LAYER):
            continue
        g = rs.pad_geom(p)
        if p["net"] == "gnd":
            through = "*.Cu" in p["layers"] or "F.Cu" in p["layers"]
            gnd_shapes.append((f"{p['ref']}.{p['pad']}", g, through))
        else:
            cut.append(g.buffer(ZONE_CLEAR, quad_segs=4))
    for s in segs:
        if s["layer"] != LAYER:
            continue
        g = LineString([s["p"], s["q"]]).buffer(s["w"] / 2, quad_segs=4)
        if s["net"] == "gnd":
            gnd_shapes.append(("gnd track", g, False))
        else:
            cut.append(g.buffer(ZONE_CLEAR, quad_segs=4))
    for v in vias:
        g = Point(v["at"]).buffer(v["d"] / 2, quad_segs=8)
        if v["net"] == "gnd":
            gnd_shapes.append((f"gnd via {v['at']}", g, True))
        else:
            cut.append(g.buffer(ZONE_CLEAR, quad_segs=4))
    for name, poly, tracks_ok, vias_ok in keepouts:
        # Rule areas that forbid pour: every one on this board that forbids
        # tracks (the dome keepouts forbid vias only).
        if not tracks_ok:
            cut.append(Polygon(poly).buffer(0))

    pour = edge.buffer(-EDGE).difference(unary_union(cut))
    pour = pour.buffer(-MIN_THICK / 2).buffer(MIN_THICK / 2)
    pieces = list(getattr(pour, "geoms", [pour]))

    # Union-find over pieces and gnd shapes: a gnd pad bridges two pieces.
    parent = list(range(len(pieces) + len(gnd_shapes)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def join(a, b):
        parent[find(a)] = find(b)

    tree = shapely.STRtree(pieces)
    for k, (_label, g, _thru) in enumerate(gnd_shapes):
        for m in tree.query(g):
            if pieces[m].intersects(g):
                join(len(pieces) + k, m)
    # Two gnd shapes that overlap (a track into a pad) are one.
    gtree = shapely.STRtree([g for _l, g, _t in gnd_shapes])
    for k, (_l, g, _t) in enumerate(gnd_shapes):
        for m in gtree.query(g):
            if m != k and gnd_shapes[m][1].intersects(g):
                join(len(pieces) + k, len(pieces) + m)

    roots = {find(len(pieces) + k) for k, (_l, _g, thru) in enumerate(gnd_shapes)
             if thru}
    shapes = [(label, g, find(len(pieces) + k) in roots)
              for k, (label, g, _t) in enumerate(gnd_shapes)]
    stranded = [(label, g) for label, g, ok in shapes
                if not ok and not label.startswith("gnd track")]
    return len(pieces), shapes, stranded


def main():
    text = rp.PCB.read_text()
    pads = rp.read_pads(text)
    segs, vias = rs.read_tracks(text)
    edge = rs.outline(text)
    n, shapes, stranded = islands(pads, segs, vias, edge, rp.read_keepouts(text))
    print(f"B.Cu pour predicted as {n} pieces; "
          f"{len(shapes)} gnd pads, tracks and vias on it")
    if not stranded:
        print("every gnd pad reaches the In1.Cu plane")
        return 0
    print(f"{len(stranded)} gnd pad(s) with no way to the plane:")
    for label, g in stranded:
        c = g.centroid
        print(f"   {label:10s} at ({c.x:.2f}, {c.y:.2f})")
    return 1


if __name__ == "__main__":
    sys.exit(main())
