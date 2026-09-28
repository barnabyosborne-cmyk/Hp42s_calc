#!/usr/bin/env python3
"""Does every track end land on copper of its own net?

    python3 tools/check_ends.py

KiCad calls a track end that touches nothing of its net `track_dangling`,
and the pad it was meant for `unconnected_items`. This asks the same question
here, against pads read as their real shape: TP9, TP10 and TP11 are 0.75 mm
radius circles, and tracks ending in the corners of the 1.5 mm squares the
tools once took them for were exactly this fault (28 September 2026).

Exit status 1 if any end dangles.
"""

import sys
from collections import defaultdict
from pathlib import Path

from shapely.geometry import LineString, Point

sys.path.insert(0, str(Path(__file__).resolve().parent))
import route_power as rp            # noqa: E402
import route_signals as rs          # noqa: E402


def main():
    text = rp.PCB.read_text()
    pads = rp.read_pads(text)
    segs, vias = rs.read_tracks(text)
    copper = defaultdict(list)          # (layer, net) -> [(key, geometry)]
    for p in pads:
        for L in rs.pad_layers(p):
            copper[(L, p["net"])].append(("pad", rs.pad_geom(p)))
    for v in vias:
        for L in rs.LAYERS:
            copper[(L, v["net"])].append(("via", Point(v["at"]).buffer(v["d"] / 2)))
    for k, s in enumerate(segs):
        copper[(s["layer"], s["net"])].append((k, LineString([s["p"], s["q"]])))

    bad = []
    for k, s in enumerate(segs):
        for end in (s["p"], s["q"]):
            pt = Point(end)
            if not any(key != k and g.distance(pt) < 1e-3
                       for key, g in copper[(s["layer"], s["net"])]):
                bad.append((s["net"], s["layer"], end))
    if not bad:
        print(f"every end of {len(segs)} tracks lands on copper of its own net")
        return 0
    print(f"{len(bad)} dangling track end(s):")
    for net, layer, end in bad:
        print(f"   {net:12s} {layer}  {end}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
