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
from shapely.ops import unary_union
from collections import defaultdict
t=rp.PCB.read_text(); pads=rp.read_pads(t); segs,vias=rs.read_tracks(t)
cop=defaultdict(list)
for p in pads:
    for L in rs.pad_layers(p): cop[(L,p['net'])].append(('pad',rs.pad_geom(p)))
for v in vias:
    for L in rs.LAYERS: cop[(L,v['net'])].append(('via',Point(v['at']).buffer(v['d']/2)))
for i,s in enumerate(segs): cop[(s['layer'],s['net'])].append((i,LineString([s['p'],s['q']])))
bad=[]
for i,s in enumerate(segs):
    for e in (s['p'],s['q']):
        pt=Point(e)
        ok=any((k!=i) and g.distance(pt)<1e-3 for k,g in cop[(s['layer'],s['net'])])
        if not ok: bad.append((s['net'],s['layer'],e))
print(len(bad),'dangling track ends'); [print(' ',b) for b in bad[:20]]
sys.exit(1 if bad else 0)
