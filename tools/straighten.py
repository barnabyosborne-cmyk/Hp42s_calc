#!/usr/bin/env python3
"""
Straighten route_signals.py's stepped diagonals, in place.

    python3 tools/straighten.py --check     # report, write nothing
    python3 tools/straighten.py             # straighten and write

Run it with KiCad CLOSED, straight after route_signals.py, and again after
every route_signals.py run: the router rewrites its copper from its cache, so
the staircases come back each time it runs.

WHY
---
The router finds its paths on a 0.05 mm grid with a weighted A*, and a path
that wants to go at, say, 30 degrees comes out as a run of 45-degree and
orthogonal pieces a few tenths long: a staircase. It is legal copper, but it
looks careless and it adds corners for no reason (4 October 2026, Barnaby).

WHAT IT DOES
------------
Each net's tracks are cut into chains at every real node: a pad of the net, a
via, the end of any other track of the net (a T), a change of layer or width.
Along a chain it walks from each corner to the furthest corner it can reach
with either
  - one straight segment, if the two points are at 0, 45 or 90 degrees, or
  - one 45-degree dogleg: a straight piece and a diagonal piece, either order,
and swaps the corners in between for that, if the new copper clears every
foreign pad, track and via on its layer by the rule, stays off the edge and
out of the rule areas and the dome apertures. The chain's two ends never
move, so nothing comes unconnected.

It only touches copper route_signals.py wrote (its uuids), and writes the
result with route_signals.py's uuids, so the router still owns it. Then the
router's own audit is run over every one of its segments before anything is
written.
"""

import math
import re
import sys
import uuid

import shapely
from shapely.geometry import LineString, Point

from route_signals import (CLEAR, EDGE, LAYERS, MASK_GAP, NS, PCB, ROOT,
                           VIA_D, _into_edge_pad, _our_uuids, audit,
                           mask_apertures, outline, pad_geom, pad_layers,
                           read_tracks, strip_ours, Copper)
import route_power as rp
from shapely.geometry import Polygon

EPS = 1e-6
R = 4                       # decimals kept in co-ordinates


def key(p):
    return (round(p[0], R), round(p[1], R))


def octant(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    return abs(dx) < EPS or abs(dy) < EPS or abs(abs(dx) - abs(dy)) < EPS


def candidates(a, b):
    """Ways to get from a to b in one or two clean pieces."""
    if octant(a, b):
        return [[a, b]]
    dx, dy = b[0] - a[0], b[1] - a[1]
    sx, sy = math.copysign(1, dx), math.copysign(1, dy)
    d = min(abs(dx), abs(dy))
    # diagonal first, or straight first
    mids = [(a[0] + sx * d, a[1] + sy * d), (b[0] - sx * d, b[1] - sy * d)]
    return [[a, key(m), b] for m in mids]


def angle_ok(prev, pts, nxt):
    """No new corner sharper than 90 degrees where the pieces join."""
    seq = ([prev] if prev else []) + pts + ([nxt] if nxt else [])
    for p, q, r in zip(seq, seq[1:], seq[2:]):
        u = (q[0] - p[0], q[1] - p[1])
        v = (r[0] - q[0], r[1] - q[1])
        if u[0] * v[0] + u[1] * v[1] < -EPS:      # turns back on itself
            return False
    return True


def main():
    check = "--check" in sys.argv
    text = PCB.read_text()
    mine = _our_uuids(text)
    segs, vias = read_tracks(text)
    pads = rp.read_pads(text)
    keepouts = rp.read_keepouts(text)
    edge = outline(text)
    boundary = edge.exterior
    apertures = mask_apertures(text, pads)
    ko_t = [(n, Polygon(p).buffer(0)) for n, p, t_ok, _v in keepouts if not t_ok]
    ko_v = [(n, Polygon(p).buffer(0)) for n, p, _t, v_ok in keepouts if not v_ok]

    ours = [s for s in segs if s["uuid"] in mine]
    theirs = [s for s in segs if s["uuid"] not in mine]

    # Fixed copper: pads, every track not ours, every via.
    fixed = {L: [] for L in LAYERS}
    pad_by_net = {}
    for p in pads:
        g = pad_geom(p)
        n = p["net"] or f"~{p['ref']}.{p['pad']}"
        for L in pad_layers(p):
            fixed[L].append((n, g))
            pad_by_net.setdefault((n, L), []).append(g)
    for s in theirs:
        if s["layer"] in LAYERS:
            fixed[s["layer"]].append(
                (s["net"], LineString([s["p"], s["q"]]).buffer(s["w"] / 2, quad_segs=8)))
    via_pts = {}
    for v in vias:
        g = Point(v["at"]).buffer(v["d"] / 2, quad_segs=8)
        for L in LAYERS:
            fixed[L].append((v["net"], g))
        via_pts.setdefault(v["net"], set()).add(key(v["at"]))

    # Our tracks, by (net, layer, width).
    groups = {}
    for s in ours:
        groups.setdefault((s["net"], s["layer"], s["w"]), []).append(
            (key(s["p"]), key(s["q"])))
    # Every end of every track of a net, any layer or width: a node.
    ends_by_net = {}
    for s in segs:
        ends_by_net.setdefault((s["net"], s["layer"]), []).append(
            (key(s["p"]), key(s["q"]), s["w"]))

    current = dict(groups)        # (net, L, w) -> list of (a, b)

    def live_tree(L):
        items = list(fixed[L])
        for (n, L2, w), lst in current.items():
            if L2 == L:
                for a, b in lst:
                    items.append((n, LineString([a, b]).buffer(w / 2, quad_segs=8)))
        return shapely.STRtree([g for _n, g in items]), items

    edge_cop = Copper()
    for L in LAYERS:
        for n, g in fixed[L]:
            edge_cop.add(L, n, g)

    before = sum(len(v) for v in groups.values())
    changed = 0
    for L in LAYERS:
        for gk in sorted(k for k in groups if k[1] == L):
            net, _L, w = gk
            tree, items = live_tree(L)
            lst = current[gk]
            # Split at T-junctions: another track's end in our interior.
            others = [p for a, b, w2 in ends_by_net.get((net, L), [])
                      for p in (a, b)]
            nodes = set(via_pts.get(net, set()))
            split = []
            for a, b in lst:
                pts = [a, b]
                line = LineString([a, b])
                for p in others:
                    if p not in (a, b) and line.distance(Point(p)) < EPS:
                        pts.append(p)
                        nodes.add(p)
                pts.sort(key=lambda p: (p[0] - a[0]) ** 2 + (p[1] - a[1]) ** 2)
                split += [(p, q) for p, q in zip(pts, pts[1:]) if p != q]
            deg = {}
            for a, b in split:
                deg[a] = deg.get(a, 0) + 1
                deg[b] = deg.get(b, 0) + 1
            # Ends of this net's other-width / other-owner tracks are nodes.
            for a, b, w2 in ends_by_net.get((net, L), []):
                if (a, b) not in lst and (b, a) not in lst:
                    nodes.add(a)
                    nodes.add(b)
            own_pads = pad_by_net.get((net, L), [])
            for p in deg:
                if deg[p] != 2 or any(g.distance(Point(p)) < EPS for g in own_pads):
                    nodes.add(p)
            # Walk the chains.
            adj = {}
            for a, b in split:
                adj.setdefault(a, []).append(b)
                adj.setdefault(b, []).append(a)
            used = set()
            chains = []
            starts = [p for p in adj if p in nodes] + list(adj)
            for s0 in starts:
                for nb in adj[s0]:
                    e = frozenset((s0, nb))
                    if e in used:
                        continue
                    chain = [s0, nb]
                    used.add(e)
                    while chain[-1] not in nodes and chain[-1] != s0:
                        nxt = [q for q in adj[chain[-1]]
                               if frozenset((chain[-1], q)) not in used]
                        if not nxt:
                            break
                        used.add(frozenset((chain[-1], nxt[0])))
                        chain.append(nxt[0])
                    chains.append(chain)

            def legal(pts):
                for p, q in zip(pts, pts[1:]):
                    g = LineString([p, q]).buffer(w / 2, quad_segs=16)
                    for k in tree.query(g.buffer(CLEAR)):
                        n, other = items[k]
                        if n != net and g.distance(other) < CLEAR - EPS:
                            return False
                    if not edge.contains(g):
                        return False
                    if g.distance(boundary) < EDGE - EPS:
                        if not _into_edge_pad(edge_cop, L, net, g):
                            return False
                    for _n, pg in ko_t:
                        if g.intersects(pg):
                            return False
                    if L == "F.Cu":
                        for _r, own, ap in apertures:
                            if net not in own and g.distance(ap) < MASK_GAP - EPS:
                                return False
                return True

            new = []
            for ch in chains:
                out = [ch[0]]
                i = 0
                while i < len(ch) - 1:
                    done = False
                    for j in range(len(ch) - 1, i + 1, -1):
                        for c in candidates(ch[i], ch[j]):
                            if len(c) - 1 >= j - i:
                                continue
                            prev = out[-2] if len(out) > 1 else None
                            nxt = ch[j + 1] if j + 1 < len(ch) else None
                            if not angle_ok(prev, c, nxt):
                                continue
                            if legal(c):
                                out += c[1:]
                                i = j
                                done = True
                                break
                        if done:
                            break
                    if not done:
                        out.append(ch[i + 1])
                        i += 1
                # Merge collinear neighbours the swaps left behind.
                tidy = [out[0]]
                for p, q in zip(out[1:], out[2:]):
                    a = tidy[-1]
                    if abs((p[0] - a[0]) * (q[1] - p[1]) - (p[1] - a[1]) * (q[0] - p[0])) < EPS \
                            and (p[0] - a[0]) * (q[0] - p[0]) + (p[1] - a[1]) * (q[1] - p[1]) > 0 \
                            and p not in nodes:
                        continue
                    tidy.append(p)
                tidy.append(out[-1])
                new += [(p, q) for p, q in zip(tidy, tidy[1:]) if p != q]
            if len(new) != len(lst):
                changed += 1
            current[gk] = new

    after = sum(len(v) for v in current.values())
    new_segs = [(n, L, a, b, w) for (n, L, w), lst in current.items() for a, b in lst]
    # The router's audit, over everything it owns.
    copper = Copper()
    for L in LAYERS:
        for n, g in fixed[L]:
            copper.add(L, n, g)
    for n, L, a, b, w in new_segs:
        copper.add(L, n, LineString([a, b]).buffer(w / 2, quad_segs=8))
    problems = audit(copper, new_segs, [], edge, ko_t, ko_v, apertures)
    print(f"{before} segments -> {after}, {changed} net/layer runs changed")
    if problems:
        print(f"{len(problems)} PROBLEM(S) -- nothing written:")
        for p in problems[:40]:
            print("   " + p)
        return 1
    print("audit: every straightened segment clears every foreign pad, track, "
          "via, rule area and the edge")
    if check:
        print("--check: nothing written")
        return 0

    # Remove only our segments (keep our vias), then write the new ones.
    kept, last = [], 0
    for m in rp.OURS.finditer(text):
        if m.group(1) in mine and "(segment" in m.group(0):
            kept.append(text[last:m.start()])
            last = m.end()
    kept.append(text[last:])
    text = "".join(kept)
    body = []
    for n, L, a, b, w in new_segs:
        body.append(rp.segment(n, L, a, b, w, "sig").replace(
            str(uuid.uuid5(rp.NS, f"seg {n} {L} {a} {b} {w} sig")),
            str(uuid.uuid5(NS, f"seg {n} {L} {a} {b} {w}"))))
    end = text.rindex("\n)")
    PCB.write_text(text[:end] + "\n" + "".join(body).rstrip("\n") + text[end:])
    print(f"wrote {PCB.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
