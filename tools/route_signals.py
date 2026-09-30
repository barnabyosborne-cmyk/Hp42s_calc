#!/usr/bin/env python3
"""
Route steps 9.3, 9.4 and 9.5 -- every net route_power.py does not own -- by
writing tracks into default.kicad_pcb.

    python3 tools/route_signals.py --check        # route, audit, write nothing
    python3 tools/route_signals.py                # route, audit, write
    python3 tools/route_signals.py --png out.png  # also draw what it routed

Run it with KiCad CLOSED, after route_power.py and stitch_zones.py. Needs
numpy, scipy and shapely (`pip install numpy scipy shapely`).

WHAT IT IS
----------
A maze router on a 0.05 mm grid over B.Cu and F.Cu, with vias between them.
The two inner layers are planes (In1.Cu ground, In2.Cu 3.3 V) and it never
puts a track on them.

The grid only finds the path. Whether the path is legal is decided twice:

  - on the grid, a cell is open to a net only if it is outside every foreign
    piece of copper grown by (half the track + the clearance + 0.01 mm), so a
    track through open cells cannot come near anything;
  - after routing, every segment and via is measured again as real geometry
    (shapely, not the grid) against every foreign pad, track and via on its
    layer, the rule areas and the board edge. Nothing is written if any of it
    fails.

WHAT IT PREFERS
---------------
  - Ordinary signals on B.Cu. F.Cu costs four times as much, because F.Cu is
    the keypad's layer.
  - The keypad matrix on F.Cu, where both of every dome's pads already are,
    with B.Cu costing three times as much. So each row and column runs as
    front copper between the domes and drops through once, near the module --
    step 9.5's "one via per net, not one per pad" -- without being told where.
  - The panel's SPI and the matrix pay triple inside the three switching-node
    rectangles of step 8.3b, so they go round them when there is a way round.
  - A via costs as much as 2 mm of track (4 mm for the matrix).

The order is short nets first, then the long ones, then the matrix: a short
local net has one sensible path and a long net has many, so the long ones are
the ones that should do the going-round.

OWNERSHIP
---------
Same rule as the other two scripts. A v5 uuid marks generated copper; the net
says whose. This script owns every net it routes and no other, so it never
touches route_power.py's nets or stitch_zones.py's `gnd` vias, and anything
drawn by hand in KiCad (a v4 uuid) is left alone and routed around.
"""

import heapq
import math
import re
import sys
import uuid
from pathlib import Path

import numpy as np
import shapely
import shapely.ops
from shapely.geometry import LineString, Point, Polygon, box as sbox
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parent))
import route_power as rp            # noqa: E402  the board reader lives there
import variant                      # noqa: E402  the MIP branch's taller board
from variant import drop            # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PCB = ROOT / "elec/layout/default/default.kicad_pcb"
NS = uuid.UUID("9a3c17be-0000-4000-8000-000000000093")

G = 0.05                 # grid pitch, mm
W = 0.2                  # signal track, the Default and keypad classes
NECK_W = 0.15            # into a pad too fine for 0.2 (board minimum 0.15)
CLEAR = 0.2
EDGE = 0.5
VIA_D, VIA_DRILL = 0.6, 0.3
SLACK = 0.01             # grid rasterisation margin, on top of the rule
MASK_GAP = 0.05          # foreign F.Cu copper stays this far outside a dome's
                         # mask aperture (see mask_apertures)
LAYERS = ("B.Cu", "F.Cu")

MATRIX = re.compile(r"^(row|col)\d$")
SWITCHERS = [(0.5, 61.0, 24.0, 82.0),      # step 8.3b's three rectangles
             (57.5, 59.0, 74.0, 72.0),
             (30.0, 85.5, 42.0, 95.0)]
SWITCHERS = [(x0, drop(y0), x1, drop(y1)) for x0, y0, x1, y1 in SWITCHERS]

SKIP = {"gnd"}

# Steps 9.3 and 9.4 go first, while the board is emptiest: they are the long
# runs, from the panel's connector at the top left and the USB receptacle at
# the top edge down to the module at the bottom.
BUSES = {"epd_sck", "epd_mosi", "epd_cs", "epd_dc", "epd_rst", "epd_busy",
         "usb_dp", "usb_dm"}

# Layer costs and via cost, per kind of net: (B.Cu, F.Cu, via in mm).
#
# The matrix cannot be one via per net. Row r must reach every dome in its
# row and column c every dome in its column, so every row crosses every
# column somewhere: 42 crossings, and a crossing on one layer is a short.
# The first Freerouting run's 47 vias were close to the floor, not waste.
# So: rows run along F.Cu, where each dome's centre tab already points, and
# columns drop from each ring through one via to a trunk on B.Cu, which is
# empty under the keyboard because every reflowed part is elsewhere.
COSTS = {"row": (5.0, 1.0, 6.0), "col": (1.0, 3.0, 1.0),
         "plain": (1.0, 4.0, 6.0)}
CROWD = 0.5              # see crowd, below
PASSES = 4               # rip-up-and-retry rounds
WEIGHT = 1.3             # weighted A*: a slightly longer path, far fewer steps           # the pours and planes do it


# --- the board ----------------------------------------------------------------

def outline(text):
    segs = []
    for m in re.finditer(r'\(gr_line\s*\(start (-?[\d.]+) (-?[\d.]+)\)\s*'
                         r'\(end (-?[\d.]+) (-?[\d.]+)\)(?:(?!\(gr_).)*?'
                         r'\(layer "Edge\.Cuts"\)', text, re.S):
        a = (float(m.group(1)), float(m.group(2)))
        b = (float(m.group(3)), float(m.group(4)))
        segs.append((a, b))
    lines = [LineString(s) for s in segs]
    poly = shapely.get_geometry(shapely.polygonize(lines), 0)
    return poly


def read_tracks(text):
    segs, vias = [], []
    for m in re.finditer(r'\n\t\(segment\n', text):
        b = rp.block_at(text, m.start() + 1)
        s = re.search(r'\(start (\S+) (\S+)\)', b)
        e = re.search(r'\(end (\S+) (\S+)\)', b)
        segs.append(dict(
            p=(float(s.group(1)), float(s.group(2))),
            q=(float(e.group(1)), float(e.group(2))),
            w=float(re.search(r'\(width (\S+)\)', b).group(1)),
            layer=re.search(r'\(layer "([^"]+)"\)', b).group(1),
            net=re.search(r'\(net "([^"]+)"\)', b).group(1),
            uuid=re.search(r'\(uuid "([^"]+)"\)', b).group(1)))
    for m in re.finditer(r'\n\t\(via\n', text):
        b = rp.block_at(text, m.start() + 1)
        a = re.search(r'\(at (\S+) (\S+)\)', b)
        vias.append(dict(
            at=(float(a.group(1)), float(a.group(2))),
            d=float(re.search(r'\(size (\S+)\)', b).group(1)),
            net=re.search(r'\(net "([^"]+)"\)', b).group(1),
            uuid=re.search(r'\(uuid "([^"]+)"\)', b).group(1)))
    return segs, vias


def is_ours(u):
    try:
        return uuid.UUID(u).version == 5
    except ValueError:
        return False


class Copper:
    """Every piece of copper on B.Cu and F.Cu, as shapely geometry by net."""

    def __init__(self):
        self.items = {L: [] for L in LAYERS}      # (net, geom)

    def add(self, layer, net, geom):
        self.items[layer].append((net, geom))

    def foreign(self, layer, net):
        return [g for n, g in self.items[layer] if n != net]


# --- the grid -----------------------------------------------------------------

class Grid:
    def __init__(self, bx):
        self.x0, self.y0 = bx[0], bx[1]
        self.nx = int(round((bx[2] - bx[0]) / G)) + 1
        self.ny = int(round((bx[3] - bx[1]) / G)) + 1
        self.N = self.nx * self.ny

    def xy(self, i, j):
        return (round(self.x0 + i * G, 4), round(self.y0 + j * G, 4))

    def cells(self, geom):
        """(i-slice, j-slice, bool mask) of cell centres inside geom."""
        x0, y0, x1, y1 = geom.bounds
        i0 = max(0, int(math.floor((x0 - self.x0) / G)))
        i1 = min(self.nx - 1, int(math.ceil((x1 - self.x0) / G)))
        j0 = max(0, int(math.floor((y0 - self.y0) / G)))
        j1 = min(self.ny - 1, int(math.ceil((y1 - self.y0) / G)))
        if i1 < i0 or j1 < j0:
            return None
        xs = self.x0 + np.arange(i0, i1 + 1) * G
        ys = self.y0 + np.arange(j0, j1 + 1) * G
        X, Y = np.meshgrid(xs, ys)
        mask = shapely.contains_xy(geom, X, Y)
        return slice(j0, j1 + 1), slice(i0, i1 + 1), mask


class Blocks:
    """How many foreign pieces of grown copper cover each cell, per layer.

    Kept as a count so a net's own copper can be subtracted back out: a cell
    is open to net N if the only copper near it is N's own.
    """

    def __init__(self, grid, grow):
        self.g, self.grow = grid, grow
        self.count = {L: np.zeros((grid.ny, grid.nx), np.int16) for L in LAYERS}
        self.own = {}                               # net -> [(L, js, is, mask)]

    def add(self, layer, net, geom):
        r = self.g.cells(geom.buffer(self.grow, quad_segs=4))
        if r is None:
            return
        js, is_, m = r
        self.count[layer][js, is_] += m
        self.own.setdefault(net, []).append((layer, js, is_, m))

    def add_shared(self, layer, nets, geom):
        """One block that every net in `nets` may cross, and no other net."""
        r = self.g.cells(geom.buffer(self.grow, quad_segs=4))
        if r is None:
            return
        js, is_, m = r
        self.count[layer][js, is_] += m
        for net in nets:
            self.own.setdefault(net, []).append((layer, js, is_, m))

    def blocked(self, layer, net):
        b = self.count[layer].copy()
        for L, js, is_, m in self.own.get(net, []):
            if L == layer:
                b[js, is_] -= m
        return b > 0


# --- routing ------------------------------------------------------------------

DIRS = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]
TURN = 0.1               # mm of penalty per 45 degrees of turn


def astar(grid, openT, openV, cost_mult, via_cost, sources, targets, win):
    """Cheapest path from any source state to any target state.

    States are layer * N + cell. `openT[L]` is a flat bytes of cells a track
    may occupy; `openV` where a via may; `cost_mult[L]` a flat float array.
    `win` = (i0, j0, i1, j1) bounds the search. One state per cell: the turn
    penalty uses the direction the cell was reached from, which is not exact
    but is enough to stop the staircases a grid router otherwise draws.
    """
    nx, N = grid.nx, grid.N
    tset = set(targets)
    if not tset:
        return None
    ti = [t % N % nx for t in tset]
    tj = [t % N // nx for t in tset]
    tb = (min(ti), min(tj), max(ti), max(tj))
    wi0, wj0, wi1, wj1 = win

    def h(c):
        i, j = c % nx, c // nx
        dx = max(tb[0] - i, 0, i - tb[2])
        dy = max(tb[1] - j, 0, j - tb[3])
        return WEIGHT * G * (max(dx, dy) + 0.4142 * min(dx, dy))

    best, prev, dirn = {}, {}, {}
    heap = []
    for s in sources:
        best[s] = 0.0
        prev[s] = None
        dirn[s] = -1
        heapq.heappush(heap, (h(s % N), 0.0, s))
    diag = G * math.sqrt(2)
    done = set()
    while heap:
        f, g, s = heapq.heappop(heap)
        if s in done:
            continue
        done.add(s)
        if s in tset:
            path = []
            k = s
            while k is not None:
                path.append(k)
                k = prev[k]
            return path[::-1]
        L, c = divmod(s, N)
        i, j = c % nx, c // nx
        oT = openT[L]
        cm = cost_mult[L]
        d = dirn[s]
        base = L * N
        for nd in range(8):
            di, dj = DIRS[nd]
            ii, jj = i + di, j + dj
            if ii < wi0 or jj < wj0 or ii > wi1 or jj > wj1:
                continue
            cc = jj * nx + ii
            if not oT[cc]:
                continue
            ns = base + cc
            if ns in done:
                continue
            if di and dj:
                if not oT[j * nx + ii] or not oT[jj * nx + i]:
                    continue
                ng = g + diag * cm[cc]
            else:
                ng = g + G * cm[cc]
            if d >= 0 and nd != d:
                t = abs(nd - d) % 8
                ng += TURN * min(t, 8 - t)
            if ng < best.get(ns, 1e18) - 1e-9:
                best[ns] = ng
                prev[ns] = s
                dirn[ns] = nd
                heapq.heappush(heap, (ng + h(cc), ng, ns))
        if openV[c]:
            ns = (1 - L) * N + c
            ng = g + (via_cost if np.isscalar(via_cost) else via_cost[c])
            if (ns not in done and openT[1 - L][c]
                    and ng < best.get(ns, 1e18) - 1e-9):
                best[ns] = ng
                prev[ns] = s
                dirn[ns] = -1
                heapq.heappush(heap, (ng + h(c), ng, ns))
    return None


_LIB = None


def c_search():
    """The compiled search from astar.c, built on first use; None if no cc."""
    global _LIB
    if _LIB is not None:
        return _LIB or None
    import ctypes
    import subprocess
    import tempfile
    src = Path(__file__).resolve().parent / "astar.c"
    so = Path(tempfile.gettempdir()) / f"hp42s-astar-{int(src.stat().st_mtime)}.so"
    try:
        if not so.exists():
            subprocess.run(["cc", "-O2", "-shared", "-fPIC", "-o", str(so),
                            str(src), "-lm"], check=True)
        lib = ctypes.CDLL(str(so))
    except (OSError, subprocess.CalledProcessError) as e:
        print(f"   (no C compiler, searching in Python: {e})")
        _LIB = False
        return None
    P = np.ctypeslib.ndpointer
    lib.astar.restype = ctypes.c_int
    lib.astar.argtypes = [
        ctypes.c_int, ctypes.c_int,
        P(np.uint8, flags="C"), P(np.uint8, flags="C"), P(np.float32, flags="C"),
        P(np.float32, flags="C"), ctypes.c_float, ctypes.c_float, ctypes.c_float,
        P(np.int32, flags="C"), ctypes.c_int,
        P(np.uint8, flags="C"),
        ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
        ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
        P(np.int32, flags="C"), ctypes.c_int]
    _LIB = lib
    return lib


def search(grid, openT, openV, cost, via_cost, sources, targets, win):
    """astar(), in C when it can be. openT/cost are (2, ny, nx) arrays."""
    lib = c_search()
    if lib is None:
        return astar(grid, [bytes(o.ravel().astype(np.uint8)) for o in openT],
                     bytes(openV.ravel().astype(np.uint8)),
                     [c.ravel() for c in cost],
                     via_cost if np.isscalar(via_cost) else via_cost.ravel(),
                     sources, targets, win)
    N, nx = grid.N, grid.nx
    tgt = np.zeros(2 * N, np.uint8)
    tl = np.fromiter(targets, np.int64)
    tgt[tl] = 1
    tc = tl % N
    ti, tj = tc % nx, tc // nx
    src = np.fromiter(sources, np.int32)
    out = np.zeros(200000, np.int32)
    n = lib.astar(nx, grid.ny,
                  np.ascontiguousarray(openT.reshape(-1), np.uint8),
                  np.ascontiguousarray(openV.reshape(-1), np.uint8),
                  np.ascontiguousarray(cost.reshape(-1), np.float32),
                  np.ascontiguousarray(
                      np.broadcast_to(np.float32(via_cost), (N,))
                      if np.isscalar(via_cost) else via_cost.reshape(-1),
                      np.float32),
                  TURN, WEIGHT, G, src, len(src), tgt,
                  int(ti.min()), int(tj.min()), int(ti.max()), int(tj.max()),
                  *win, out, len(out))
    return [int(v) for v in out[:n]] if n > 0 else None


def simplify(grid, path):
    """Grid path -> list of (layer, [points]) runs and via points."""
    N, nx = grid.N, grid.nx
    runs, vias = [], []
    cur_L, pts = None, []
    for s in path:
        L, c = divmod(s, N)
        p = grid.xy(c % nx, c // nx)
        if cur_L is None:
            cur_L, pts = L, [p]
        elif L != cur_L:
            runs.append((cur_L, pts))
            vias.append(p)
            cur_L, pts = L, [p]
        else:
            pts.append(p)
    runs.append((cur_L, pts))
    out = []
    for L, pts in runs:
        keep = [pts[0]]
        for a, b in zip(pts[1:], pts[2:]):
            p = keep[-1]
            d1 = (round((a[0] - p[0]) / G), round((a[1] - p[1]) / G))
            d2 = (round((b[0] - a[0]) / G), round((b[1] - a[1]) / G))
            n1 = math.gcd(abs(d1[0]), abs(d1[1])) or 1
            n2 = math.gcd(abs(d2[0]), abs(d2[1])) or 1
            if (d1[0] // n1, d1[1] // n1) != (d2[0] // n2, d2[1] // n2):
                keep.append(a)
        if len(pts) > 1:
            keep.append(pts[-1])
        out.append((LAYERS[L], keep))
    return out, vias


# --- the job ------------------------------------------------------------------

def net_order(pads_by_net, nets):
    def hpwl(n):
        ps = pads_by_net[n]
        xs = [(p["bbox"][0] + p["bbox"][2]) / 2 for p in ps]
        ys = [(p["bbox"][1] + p["bbox"][3]) / 2 for p in ps]
        return (max(xs) - min(xs)) + (max(ys) - min(ys))
    first = sorted((n for n in nets if n in BUSES), key=hpwl)
    plain = sorted((n for n in nets if not MATRIX.match(n) and n not in BUSES),
                   key=hpwl)
    rows = sorted((n for n in nets if n.startswith("row")), key=hpwl)
    cols = sorted((n for n in nets if n.startswith("col")), key=hpwl)
    return first + plain + rows + cols


def mask_apertures(text, pads):
    """Every dome's F.Mask-only aperture, with the nets of its own pads.

    The aperture is not copper, so it is not in `pads`, but any copper of
    another net inside it is bare metal beside the dome: KiCad reports it as a
    solder_mask_bridge, and a bare row track next to a column ring is one
    stray contact away from a phantom key. Found on 30 September 2026, when
    row0 cut 0.12 mm into the corners of SW25's and SW30's apertures.
    """
    nets = {}
    for p in pads:
        if p["net"] and "F.Cu" in p["layers"]:
            nets.setdefault(p["ref"], set()).add(p["net"])
    out = []
    for m in re.finditer(r'\n\t\(footprint "', text):
        blk = rp.block_at(text, m.start() + 1)
        ref = rp.REF_RE.search(blk).group(1)
        at = rp.FP_AT.search(blk)
        fx, fy = float(at.group(1)), float(at.group(2))
        fr = float(at.group(3)) if at.group(3).strip() else 0.0
        for pm in re.finditer(r'\n\t\t\(pad "', blk):
            pad = rp.block_at(blk, pm.start() + 2)
            if '(layers "F.Mask")' not in pad:
                continue
            pat = re.search(r'\(at (-?[\d.]+) (-?[\d.]+)(?: (-?[\d.]+))?\)', pad)
            rx, ry = rp.rot(float(pat.group(1)), float(pat.group(2)), fr)
            polys = rp.pad_shapes(pad, fx + rx, fy + ry,
                                  float(pat.group(3) or 0.0))
            g = unary_union([Polygon(q).buffer(0) for q in polys])
            out.append((ref, nets.get(ref, set()), g))
    return out


def pad_geom(p):
    return unary_union([Polygon(poly).buffer(0) for poly in p["polys"]])


def pad_layers(p):
    ls = p["layers"]
    if "*.Cu" in ls:
        return list(LAYERS)
    return [L for L in LAYERS if L in ls]


# --- negotiated congestion ----------------------------------------------------

ITERS = 200              # negotiation rounds before giving up
PRES0, PRES_GROW, PRES_MAX = 0.5, 1.6, 200.0
HIST = 1.0
PART_CENTRE = {}         # ref -> mean of its pad centres, for escape()


def negotiate(grid, order, pads_by_net, copper, trackB, viaB,
              edge_ok_t, edge_ok_v, ko_t, ko_v, region, pour_ctx):
    """Route every net, letting new tracks share space at a price.

    Routing one net at a time and never revisiting fails here the way the
    first Freerouting pass failed: whichever net goes first through J2's pin
    column, or past U2's pins, takes the only way out and the next one is
    shut in. So this is PathFinder (McMurchie and Ebeling, 1995): each round
    every net in a clash is ripped up and re-routed; a spot near another new
    net's copper costs more each round (present), and a spot fought over in
    earlier rounds costs more for good (history). Nets that can go round, do.

    Where the new nets are is kept as centrelines on the grid, and "near" is
    the rule measured between cell centres: 0.4 mm track to track, 0.6 via
    to track, 0.8 via to via. What counts as a clash, though, is decided by
    geometry every round (new_clashes), because a diagonal between grid
    points can pass a few hundredths closer than any cell centre does.

    Fixed copper -- pads, route_power.py's tracks, the stitching vias --
    is never shared; that is a hard block, as before.
    """
    from scipy import ndimage

    N, nx, ny = grid.N, grid.nx, grid.ny
    TT = W + CLEAR                           # track to track, centres
    TV = W / 2 + CLEAR + VIA_D / 2           # track to via
    VV = VIA_D + CLEAR                       # via to via
    occT = np.zeros((2, ny, nx), np.int16)   # new centreline cells
    occV = np.zeros((ny, nx), np.int16)      # new via cells
    hist = np.zeros((2, ny, nx), np.float32)
    state = {}                               # net -> dict(paths, stubs, ...)
    terms_cache = {}
    # Ground tails, negotiated like everything else: "gnd~R9.2" is a track
    # from R9's ground pad to a new via or a grounded pad, for a pad the pour
    # cannot reach. They join once the signals are clash-free, because only
    # then is it known which pads the signals have cut off.
    special = {}                             # pseudo-net -> dict(pad, targets)

    def base(net):
        return net.split("~")[0]

    def centrelines(path, stubs):
        cells, vias, prev = [[], []], [], None
        for st in path:
            L, c = divmod(st, N)
            cells[L].append(c)
            if prev is not None and prev[0] != L and prev[1] == c:
                vias.append(c)
            prev = (L, c)
        for _n, L2, a, b, _w in stubs:
            li = LAYERS.index(L2)
            k = max(1, int(math.dist(a, b) / G) + 1)
            for t in range(k + 1):
                x = a[0] + (b[0] - a[0]) * t / k
                y = a[1] + (b[1] - a[1]) * t / k
                cells[li].append(int(round(y / G)) * nx + int(round(x / G)))
        return ([np.unique(np.array(c, np.int64)) for c in cells],
                np.unique(np.array(vias, np.int64)))

    def put(net, sign):
        st = state[net]
        for L in (0, 1):
            np.add.at(occT[L].reshape(-1), st["cells"][L], sign)
        np.add.at(occV.reshape(-1), st["vias"], sign)

    def terminals(net, tb):
        if net in terms_cache:
            return terms_cache[net]
        terms, stubs, opened = [], [], [[], []]
        for p in ([special[net]["pad"]] if net in special else pads_by_net[net]):
            g = pad_geom(p)
            r = grid.cells(g)
            t = set()
            for L in pad_layers(p):
                li = LAYERS.index(L)
                inside = np.zeros((ny, nx), bool)
                inside[r[0], r[1]] = r[2]
                ok_here = inside & ~tb[L] & ~ko_t
                idx = np.flatnonzero(ok_here)
                opened[li].append(idx)
                t |= {li * N + int(c) for c in idx}
            if not t:
                open0 = [~tb[L] & edge_ok_t & ~ko_t for L in LAYERS]
                t, stub = escape(grid, copper, p, base(net), open0)
                if stub:
                    stubs.append(stub)
            terms.append((p, t))
        terms_cache[net] = (terms, stubs, opened)
        return terms_cache[net]

    def route_one(net, pres):
        is_m = bool(MATRIX.match(net))
        kind = net[:3] if is_m else "plain"
        noisy = is_m or net.startswith("epd_")
        tb = {L: trackB.blocked(L, base(net)) for L in LAYERS}
        terms, stubs, opened = terminals(net, tb)
        if any(not t for _p, t in terms):
            return None, "no way into " + ", ".join(
                f"{p['ref']}.{p['pad']}" for p, t in terms if not t)
        # Distances to the other new nets, only as far out as the widest
        # search window can reach.
        allt = np.array([t % N for _p, ts in terms for t in ts])
        m40 = int(40.0 / G)
        j0 = max(0, int((allt // nx).min()) - m40)
        j1 = min(ny, int((allt // nx).max()) + m40 + 1)
        i0 = max(0, int((allt % nx).min()) - m40)
        i1 = min(nx, int((allt % nx).max()) + m40 + 1)

        def edt(occ):
            d = np.full((ny, nx), 1e3, np.float32)
            d[j0:j1, i0:i1] = ndimage.distance_transform_edt(
                occ[j0:j1, i0:i1] == 0) * G
            return d
        dT = [edt(occT[0]), edt(occT[1])]
        dV = edt(occV)
        openT = np.zeros((2, ny, nx), np.uint8)
        cost = np.zeros((2, ny, nx), np.float32)
        for li, L in enumerate(LAYERS):
            ok = ~tb[L] & edge_ok_t & ~ko_t
            flat = ok.reshape(-1)
            for idx in opened[li]:
                flat[idx] = True
            openT[li] = ok
            m = np.full((ny, nx), COSTS[kind][li], np.float32)
            if noisy:
                m *= region
            m *= 1 + hist[li]
            m *= 1 + pres * ((dT[li] < TT - 1e-3) | (dV < TV - 1e-3))
            cost[li] = m
        openV = (~viaB.blocked("B.Cu", base(net)) & ~viaB.blocked("F.Cu", base(net))
                 & edge_ok_v & ~ko_v)
        congV = (dT[0] < TV - 1e-3) | (dT[1] < TV - 1e-3) | (dV < VV - 1e-3)
        vcost = (COSTS[kind][2] * (1 + hist.max(axis=0))
                 * (1 + pres * congV)).astype(np.float32)

        tree = set(terms[0][1])
        rest = terms[1:]
        path_all = []
        if net in special:
            tgt = special[net]["targets"]
            for L in (0, 1):
                openT[L].reshape(-1)[[t % N for t in tgt if t // N == L]] = 1
            path = search(grid, openT, openV, cost, vcost, tree, tgt,
                          (0, 0, nx - 1, ny - 1))
            if path is None:
                return None, "no way to ground"
            end = path[-1]
            return dict(paths=[path], stubs=stubs,
                        endvia=None if end in special[net]["onpad"]
                        else end % N), None
        while rest:
            targets = set()
            for _p, t in rest:
                targets |= t
            allc = [t % N for t in tree | targets]
            ci = [c % nx for c in allc]
            cj = [c // nx for c in allc]
            path = None
            for margin in (4.0, 12.0, 40.0):
                mm = int(margin / G)
                win = (max(0, min(ci) - mm), max(0, min(cj) - mm),
                       min(nx - 1, max(ci) + mm), min(ny - 1, max(cj) + mm))
                path = search(grid, openT, openV, cost, vcost, tree, targets,
                              win)
                if path is not None:
                    break
            if path is None:
                return None, "no path to " + ", ".join(
                    f"{p['ref']}.{p['pad']}" for p, _t in rest)
            ps = set(path)
            tree |= ps
            for p, t in terms:
                if t & ps:
                    tree |= t
            rest = [(p, t) for p, t in rest if not (t & tree)]
            path_all.append(path)
        return dict(paths=path_all, stubs=stubs), None

    def copper_of(net, st):
        net_segs, net_vias = [], []
        name = base(net)
        for path in st["paths"]:
            runs, vs = simplify(grid, path)
            for L, pts in runs:
                for a, b in zip(pts, pts[1:]):
                    net_segs.append((name, L, a, b, W))
            for v in vs:
                net_vias.append((name, v))
        if st.get("endvia") is not None:
            c = st["endvia"]
            net_vias.append((name, grid.xy(c % nx, c // nx)))
        return ([(name,) + tuple(x[1:]) for x in net_segs + st["stubs"]],
                net_vias)

    def add_ground_tails():
        """Pseudo-nets for the gnd pads the current copper strands."""
        import check_pour
        pads_, keep_segs, keep_vias, edge, keepouts = pour_ctx
        segs = [dict(p=a, q=b, w=w, layer=L, net=n)
                for st in state.values() for n, L, a, b, w in st["segs"]]
        vias = [dict(at=v, d=VIA_D, net=n)
                for st in state.values() for n, v in st["vs"]]
        _n, shapes, stranded = check_pour.islands(
            pads_, segs + keep_segs, vias + keep_vias, edge, keepouts)
        by_label = {f"{p['ref']}.{p['pad']}": p for p in pads_
                    if p["net"] == "gnd"}
        new = [lab for lab, _g in stranded
               if f"gnd~{lab}" not in special and lab in by_label]
        if not new:
            return []
        tb = trackB.blocked("B.Cu", "gnd")
        openV = (~viaB.blocked("B.Cu", "gnd") & ~viaB.blocked("F.Cu", "gnd")
                 & edge_ok_v & ~ko_v & ~tb & ~trackB.blocked("F.Cu", "gnd"))
        near_pad = np.zeros((ny, nx), bool)
        for q in pads_:
            if q["net"] == "gnd" and rp.on_layer(q, "B.Cu"):
                rq = grid.cells(pad_geom(q).buffer(VIA_D / 2 + 0.05))
                if rq:
                    near_pad[rq[0], rq[1]] |= rq[2]
        tgt = set(np.flatnonzero(openV & ~near_pad).tolist())
        onpad = set()
        for lab, g2, ok in shapes:
            if ok and not lab.startswith("gnd track") \
                    and not lab.startswith("gnd via"):
                r2 = grid.cells(g2)
                if r2:
                    m2 = np.zeros((ny, nx), bool)
                    m2[r2[0], r2[1]] = r2[2]
                    onpad |= set(np.flatnonzero(m2 & ~tb).tolist())
        added = []
        for lab in dict.fromkeys(new):
            special[f"gnd~{lab}"] = dict(pad=by_label[lab],
                                         targets=tgt | onpad, onpad=onpad)
            added.append(f"gnd~{lab}")
        return added

    def new_clashes():
        """(net, net, layer, where) for every real clearance breach between
        two new nets, measured as geometry."""
        items = {L: [] for L in LAYERS}
        for net, st in state.items():
            for _n, L, a, b, w in st["segs"]:
                items[L].append((net, LineString([a, b]).buffer(w / 2, quad_segs=8)))
            for _n, v in st["vs"]:
                g = Point(v).buffer(VIA_D / 2, quad_segs=8)
                for L in LAYERS:
                    items[L].append((net, g))
        out, seen = [], set()
        for L in LAYERS:
            geoms = [g for _n, g in items[L]]
            tree = shapely.STRtree(geoms)
            for k, (n1, g1) in enumerate(items[L]):
                for m in tree.query(g1.buffer(CLEAR - 1e-6)):
                    n2, g2 = items[L][m]
                    if base(n2) == base(n1) or m <= k:
                        continue
                    if g1.distance(g2) < CLEAR - 1e-6:
                        pa, pb = shapely.ops.nearest_points(g1, g2)
                        where = ((pa.x + pb.x) / 2, (pa.y + pb.y) / 2)
                        key = (min(n1, n2), max(n1, n2), L,
                               round(where[0], 1), round(where[1], 1))
                        if key not in seen:
                            seen.add(key)
                            out.append((n1, n2, L, where))
        return out

    failed = {}
    todo = list(order)
    pres = PRES0
    seen_sig = []
    best = None
    for it in range(ITERS):
        for net in todo:
            if net in state:
                put(net, -1)
                del state[net]
            res, why = route_one(net, pres)
            if res is None:
                failed[net] = why
                continue
            failed.pop(net, None)
            res["cells"], res["vias"] = centrelines(
                [s_ for pth in res["paths"] for s_ in pth], res["stubs"])
            # centrelines() finds vias from consecutive states, so feed it
            # each path on its own for the via cells.
            vc = [centrelines(pth, [])[1] for pth in res["paths"]]
            if res.get("endvia") is not None:
                vc.append(np.array([res["endvia"]], np.int64))
            res["vias"] = np.unique(np.concatenate(vc)) if vc else res["vias"]
            res["segs"], res["vs"] = copper_of(net, res)
            state[net] = res
            put(net, +1)
        clashes = new_clashes()
        hot = set()
        for n1, n2, L, (x, y) in clashes:
            hot |= {n1, n2}
            li = LAYERS.index(L)
            r = grid.cells(Point(x, y).buffer(0.6))
            if r:
                hist[li][r[0], r[1]] += HIST * r[2]
        print(f"   round {it + 1}: {len(state)} routed, {len(failed)} blocked, "
              f"{len(clashes)} clashes among {len(hot)} nets"
              + (f" ({', '.join(sorted(hot))})" if 0 < len(hot) <= 6 else ""),
              flush=True)
        if best is None or len(clashes) < best[0]:
            best = (len(clashes), {k: dict(v) for k, v in state.items()})
        if not clashes:
            added = add_ground_tails()
            if not added:
                break
            print(f"   {len(added)} gnd pad(s) cut off from the pour: "
                  f"{', '.join(a.split('~')[1] for a in added)}", flush=True)
            order = list(order) + added
            todo = added
            seen_sig = []
            continue
        seen_sig.append((frozenset(hot), len(clashes)))
        if len(seen_sig) >= 12 and len(set(seen_sig[-12:])) == 1:
            break
        pres = min(pres * PRES_GROW, PRES_MAX)
        todo = [n for n in order if n in hot]

    order = list(order) + [n for n in special if n not in order]
    if best is not None and best[0]:
        print(f"   keeping the best round: {best[0]} clashes left")
        state = best[1]
    routed, new_segs, new_vias = {}, [], []
    for net in order:
        if net not in state:
            continue
        net_segs, net_vias = state[net]["segs"], state[net]["vs"]
        new_segs += net_segs
        new_vias += net_vias
        length = sum(math.dist(a, b) for _n, _L, a, b, _w in net_segs)
        routed[net] = (length, len(net_vias))
    for net in order:
        if net in routed:
            print(f"   {net:15s} {routed[net][0]:7.2f} mm  "
                  f"{routed[net][1]} via(s)")
    return routed, sorted(failed.items()), new_segs, new_vias


# --- ground tails -------------------------------------------------------------

def ground_tails(grid, pads, keep_segs, keep_vias, new_segs, new_vias, edge,
                 keepouts, trackB, viaB, edge_ok_t, edge_ok_v, ko_t, ko_v,
                 add_fixed, copper):
    """Give every ground pad the pour cannot reach its own way to the plane.

    Most ground pads have no track at all: the B.Cu pour reaches them. But
    the pour keeps 0.5 mm from everything else, so it never gets between
    the pins of a 0.4 mm pitch part, and the signal tracks written above cut
    it into pieces. check_pour.py predicts which gnd pads end up on a piece
    with no via to In1.Cu; each of those gets a short track, either to a
    ground pad that is already grounded or to a new via of its own.
    """
    import check_pour

    N, nx, ny = grid.N, grid.nx, grid.ny
    segs = [dict(p=a, q=b, w=w, layer=L, net=n) for n, L, a, b, w in new_segs]
    segs += keep_segs
    vias = [dict(at=v, d=VIA_D, net=n) for n, v in new_vias] + keep_vias
    out_s, out_v = [], []
    tried = {}
    by_label = {f"{p['ref']}.{p['pad']}": p for p in pads if p["net"] == "gnd"}
    for _round in range(150):
        _n, shapes, stranded = check_pour.islands(pads, segs, vias, edge,
                                                  keepouts)
        # A pad can be tried again after others are grounded: a group that
        # had nowhere to go may now have a grounded neighbour to reach.
        todo = [(lab, g) for lab, g in stranded if tried.get(lab, 0) < 3]
        if not todo:
            return out_s, out_v, stranded
        todo.sort(key=lambda lg: tried.get(lg[0], 0))
        lab, g = todo[0]
        tried[lab] = tried.get(lab, 0) + 1
        tb = trackB.blocked("B.Cu", "gnd")
        openT = np.zeros((2, ny, nx), np.uint8)
        openT[0] = ~tb & edge_ok_t & ~ko_t
        r = grid.cells(g)
        inside = np.zeros((ny, nx), bool)
        inside[r[0], r[1]] = r[2]
        src = np.flatnonzero(inside & ~tb)
        stub = None
        if not len(src):
            t, stub = escape(grid, copper, by_label[lab], "gnd",
                             [openT[0].astype(bool), openT[1].astype(bool)])
            src = [c for c in t]
        openT[0].reshape(-1)[src] = 1
        # Targets: a grounded gnd pad, or a cell a via may take.
        openV = (~viaB.blocked("B.Cu", "gnd") & ~viaB.blocked("F.Cu", "gnd")
                 & edge_ok_v & ~ko_v & ~tb & ~trackB.blocked("F.Cu", "gnd"))
        # Not in a pad: via-in-pad wants the fab to fill and cap it.
        near_pad = np.zeros((ny, nx), bool)
        for q in pads:
            if q["net"] == "gnd" and rp.on_layer(q, "B.Cu"):
                rq = grid.cells(pad_geom(q).buffer(VIA_D / 2 + 0.05))
                if rq:
                    near_pad[rq[0], rq[1]] |= rq[2]
        openV &= ~near_pad
        tgt = openV.copy()
        for lab2, g2, ok in shapes:
            if ok and not lab2.startswith("gnd track"):
                r2 = grid.cells(g2)
                if r2:
                    m2 = np.zeros((ny, nx), bool)
                    m2[r2[0], r2[1]] = r2[2]
                    tgt |= m2 & ~tb
                    openT[0] |= (m2 & ~tb).astype(np.uint8)
        c = g.centroid
        i0, j0 = int(c.x / G), int(c.y / G)
        R = int(12.0 / G)
        win = (max(0, i0 - R), max(0, j0 - R), min(nx - 1, i0 + R),
               min(ny - 1, j0 + R))
        wm = np.zeros((ny, nx), bool)
        wm[win[1]:win[3] + 1, win[0]:win[2] + 1] = True
        targets = set(np.flatnonzero(tgt & wm).tolist())
        cost = np.ones((2, ny, nx), np.float32)
        path = search(grid, openT, np.zeros((ny, nx), np.uint8), cost,
                      1e9, set(int(x) for x in src), targets, win)
        if path is None:
            if "--debug" in sys.argv:
                print(f"   (no tail from {lab}: {len(src)} start cells, "
                      f"{len(targets)} targets in reach)")
            continue
        runs, _vs = simplify(grid, path)
        new = [("gnd", L, a, b, W) for L, pts in runs
               for a, b in zip(pts, pts[1:])]
        if stub:
            new.append(stub)
        end = path[-1] % N
        end_xy = grid.xy(end % nx, end // nx)
        on_pad = any(ok and g2.intersects(Point(end_xy))
                     for lab2, g2, ok in shapes
                     if not lab2.startswith("gnd track"))
        for n_, L, a, b, w in new:
            add_fixed(L, "gnd", LineString([a, b]).buffer(w / 2, quad_segs=8))
            segs.append(dict(p=a, q=b, w=w, layer=L, net="gnd"))
        out_s += new
        if not on_pad:
            gv = Point(end_xy).buffer(VIA_D / 2, quad_segs=8)
            for L in LAYERS:
                add_fixed(L, "gnd", gv)
            vias.append(dict(at=end_xy, d=VIA_D, net="gnd"))
            out_v.append(("gnd", end_xy))
        print(f"   gnd tail from {lab}: {sum(math.dist(a, b) for *_x, a, b, _w in new):.2f} mm"
              + ("" if on_pad else f", via at {end_xy}"), flush=True)
    _n, _shapes, stranded = check_pour.islands(pads, segs, vias, edge, keepouts)
    return out_s, out_v, stranded


def main():
    check = "--check" in sys.argv
    png = sys.argv[sys.argv.index("--png") + 1] if "--png" in sys.argv else None
    only = None
    if "--nets" in sys.argv:
        only = sys.argv[sys.argv.index("--nets") + 1].split(",")

    text = PCB.read_text()
    pads = rp.read_pads(text)
    keepouts = rp.read_keepouts(text)
    edge = outline(text)
    segs, vias = read_tracks(text)

    by_ref = {}
    for p in pads:
        b = p["bbox"]
        by_ref.setdefault(p["ref"], []).append(((b[0] + b[2]) / 2, (b[1] + b[3]) / 2))
    for ref, pts in by_ref.items():
        PART_CENTRE[ref] = (sum(x for x, _ in pts) / len(pts),
                            sum(y for _, y in pts) / len(pts))

    pads_by_net = {}
    for p in pads:
        if p["net"]:
            pads_by_net.setdefault(p["net"], []).append(p)

    # Which nets are ours: every multi-pad net with no copper that somebody
    # else generated or drew. Our own copper from a previous run is removed
    # and re-derived, so it does not count as somebody else's.
    mine = _our_uuids(text)
    theirs = {s["net"] for s in segs if s["uuid"] not in mine}
    nets = [n for n, ps in pads_by_net.items()
            if len(ps) >= 2 and n not in SKIP and n not in theirs]
    if only:
        nets = [n for n in nets if n in only]
    order = net_order(pads_by_net, nets)

    # Everything that stays: all pads, and every track and via we did not write.
    # Our gnd copper (the ground tails) is ours too: the write strips it, so it
    # must not stand in for the plane while routing, or the new layout leans
    # on tails that are about to be deleted.
    ours = set(nets) | {"gnd"}
    keep_segs = [s for s in segs if s["net"] not in ours or s["uuid"] not in mine]
    keep_vias = [v for v in vias if v["net"] not in ours or v["uuid"] not in mine]

    grid = Grid((0, 0, variant.BOARD_W, variant.BOARD_H))
    # Static blocks: the board edge and the rule areas.
    inner_t = edge.buffer(-(W / 2 + EDGE + SLACK))
    inner_v = edge.buffer(-(VIA_D / 2 + EDGE + SLACK))
    r = grid.cells(inner_t)
    edge_ok_t = np.zeros((grid.ny, grid.nx), bool)
    edge_ok_t[r[0], r[1]] = r[2]
    r = grid.cells(inner_v)
    edge_ok_v = np.zeros((grid.ny, grid.nx), bool)
    edge_ok_v[r[0], r[1]] = r[2]
    ko_t = np.zeros((grid.ny, grid.nx), bool)
    ko_v = np.zeros((grid.ny, grid.nx), bool)
    ko_geoms_t, ko_geoms_v = [], []
    for name, poly, tracks_ok, vias_ok in keepouts:
        pg = Polygon(poly).buffer(0)
        if not tracks_ok:
            ko_geoms_t.append((name, pg))
            r = grid.cells(pg.buffer(W / 2 + SLACK))
            if r:
                ko_t[r[0], r[1]] |= r[2]
        if not vias_ok:
            ko_geoms_v.append((name, pg))
            r = grid.cells(pg.buffer(VIA_D / 2 + SLACK))
            if r:
                ko_v[r[0], r[1]] |= r[2]

    region = np.ones((grid.ny, grid.nx), np.float32)
    for x0, y0, x1, y1 in SWITCHERS:
        r = grid.cells(sbox(x0, y0, x1, y1))
        region[r[0], r[1]][r[2]] = 3.0

    # The fixed copper: every pad, and every track and via this script does
    # not own. Nothing new may come near it -- that is a hard block.
    copper = Copper()
    trackB = Blocks(grid, W / 2 + CLEAR + SLACK)
    viaB = Blocks(grid, VIA_D / 2 + CLEAR + SLACK)

    def add_fixed(layer, net, geom):
        copper.add(layer, net, geom)
        trackB.add(layer, net, geom)
        viaB.add(layer, net, geom)

    for p in pads:
        g = pad_geom(p)
        for L in pad_layers(p):
            add_fixed(L, p["net"] or f"~{p['ref']}.{p['pad']}", g)
    # The dome apertures block tracks of every net but the dome's own. trackB
    # grows everything by W/2 + CLEAR; shrinking the aperture by CLEAR - MASK_GAP
    # first makes that W/2 + MASK_GAP. Vias are kept out by the dome keepouts.
    apertures = mask_apertures(text, pads)
    for _ref, own_nets, g in apertures:
        trackB.add_shared("F.Cu", own_nets, g.buffer(MASK_GAP - CLEAR))
    for s_ in keep_segs:
        if s_["layer"] in LAYERS:
            add_fixed(s_["layer"], s_["net"],
                      LineString([s_["p"], s_["q"]]).buffer(s_["w"] / 2,
                                                            quad_segs=8))
    for v in keep_vias:
        g = Point(v["at"]).buffer(v["d"] / 2, quad_segs=8)
        for L in LAYERS:
            add_fixed(L, v["net"], g)

    # The negotiation is the slow part and depends only on the board as it
    # stands without our copper, this script and astar.c. Cache it by that.
    import hashlib
    import pickle
    import tempfile
    h = hashlib.sha1()
    h.update(strip_ours(text, set(nets) | {"gnd"}).encode())
    src = Path(__file__).read_text()
    h.update(src.encode())
    h.update((Path(__file__).parent / "astar.c").read_bytes())
    h.update(repr(order).encode())
    cache = Path(tempfile.gettempdir()) / f"hp42s-route-{h.hexdigest()[:16]}.pkl"
    if cache.exists():
        print(f"   negotiated routing from cache {cache.name}")
        routed, failed, new_segs, new_vias = pickle.loads(cache.read_bytes())
    else:
        routed, failed, new_segs, new_vias = negotiate(
            grid, order, pads_by_net, copper, trackB, viaB,
            edge_ok_t, edge_ok_v, ko_t, ko_v, region,
            (pads, keep_segs, keep_vias, edge, keepouts))
        cache.write_bytes(pickle.dumps((routed, failed, new_segs, new_vias)))

    # Put the new copper in with the fixed, for the tails and the audit.
    for n, L, a, b, w in new_segs:
        add_fixed(L, n, LineString([a, b]).buffer(w / 2, quad_segs=8))
    for n, v in new_vias:
        g = Point(v).buffer(VIA_D / 2, quad_segs=8)
        for L in LAYERS:
            add_fixed(L, n, g)

    tail_segs, tail_vias, stranded = ground_tails(
        grid, pads, keep_segs, keep_vias, new_segs, new_vias, edge, keepouts,
        trackB, viaB, edge_ok_t, edge_ok_v, ko_t, ko_v, add_fixed, copper)
    new_segs += tail_segs
    new_vias += tail_vias
    for label, _g in stranded:
        failed.append(("gnd", f"{label} still has no way to the plane"))
    new_segs, new_vias, merged = merge_vias(new_segs, new_vias, keep_vias)
    if merged:
        print(f"   {merged} via(s) merged into a neighbour of the same net")

    # --- the audit: real geometry, not the grid -------------------------------
    problems = audit(copper, new_segs, new_vias, edge, ko_geoms_t, ko_geoms_v,
                     apertures)

    print(f"\n{len(routed)} nets routed, {len(failed)} failed, "
          f"{len(new_segs)} segments, {len(new_vias)} vias, "
          f"{sum(v[0] for v in routed.values()):.1f} mm")
    for net, why in failed:
        print(f"   FAILED {net}: {why}")
    if png:
        draw(png, pads, keep_segs, new_segs, new_vias, keep_vias)
    if problems:
        print(f"\n{len(problems)} PROBLEM(S) -- nothing written:")
        tally = {}
        for p in problems:
            k = p.split(" (")[0].split(":")[0]
            tally[k] = tally.get(k, 0) + 1
        print("   by net: " + ", ".join(f"{k} {v}" for k, v in
                                        sorted(tally.items(), key=lambda kv: -kv[1])))
        for p in problems[:40]:
            print("   " + p)
        return 1
    print("audit: every new segment and via clears every foreign pad, track, "
          "via, rule area and the edge")
    if check:
        print("--check: nothing written")
        return 0 if not failed else 1

    body = [rp.segment(n, L, a, b, w, "sig").replace(
                str(uuid.uuid5(rp.NS, f"seg {n} {L} {a} {b} {w} sig")),
                str(uuid.uuid5(NS, f"seg {n} {L} {a} {b} {w}")))
            for n, L, a, b, w in new_segs]
    for n, v in new_vias:
        body.append(
            f"\t(via\n\t\t(at {rp.fmt(v[0])} {rp.fmt(v[1])})\n"
            f"\t\t(size {rp.fmt(VIA_D)})\n\t\t(drill {rp.fmt(VIA_DRILL)})\n"
            f"\t\t(layers \"F.Cu\" \"B.Cu\")\n\t\t(net \"{n}\")\n"
            f"\t\t(uuid \"{uuid.uuid5(NS, f'via {n} {v}')}\")\n\t)\n")
    text = strip_ours(text, set(nets) | {"gnd"})
    end = text.rindex("\n)")
    PCB.write_text(text[:end] + "\n" + "".join(body).rstrip("\n") + text[end:])
    print(f"wrote {PCB.relative_to(ROOT)}")
    return 0 if not failed else 1


HOLE_GAP = 0.25          # board setup: minimum hole to hole


def merge_vias(new_segs, new_vias, keep_vias):
    """Drop every new via that sits on or beside another via of its net.

    Each stranded ground pad is its own pseudo-net during negotiation, and
    several of them would pick the same free cell for their via: KiCad found
    eleven vias drilled on top of each other at (33.35, 137.25) and two more
    closer than the 0.25 mm hole-to-hole rule (28 September 2026). A via too
    close to one of its own net is replaced by a short B.Cu track into that
    one, which keeps whatever it connected connected."""
    kept = [(v["net"], v["at"], v["d"] / 2) for v in keep_vias]   # drill ~ d/2
    out_v, extra, merged = [], [], 0
    for n, v in new_vias:
        near = [(math.dist(v, a), a) for n2, a, dr in kept
                if n2 == n and math.dist(v, a) < dr / 2 + VIA_DRILL / 2 + HOLE_GAP]
        if near:
            d, a = min(near)
            if d > 1e-6:
                extra.append((n, "B.Cu", v, a, W))
            merged += 1
            continue
        kept.append((n, v, VIA_DRILL))
        out_v.append((n, v))
    return new_segs + extra, out_v, merged


def _our_uuids(text):
    """Uuids this script would have generated for the copper now in the file."""
    out = set()
    for m in rp.OURS.finditer(text):
        blk = m.group(0)
        net = re.search(r'\(net "([^"]+)"\)', blk).group(1)
        if "(segment" in blk:
            s = re.search(r'\(start (\S+) (\S+)\)', blk)
            e = re.search(r'\(end (\S+) (\S+)\)', blk)
            w = float(re.search(r'\(width (\S+)\)', blk).group(1))
            L = re.search(r'\(layer "([^"]+)"\)', blk).group(1)
            a = (float(s.group(1)), float(s.group(2)))
            b = (float(e.group(1)), float(e.group(2)))
            out.add(str(uuid.uuid5(NS, f"seg {net} {L} {a} {b} {w}")))
        else:
            a = re.search(r'\(at (\S+) (\S+)\)', blk)
            v = (float(a.group(1)), float(a.group(2)))
            out.add(str(uuid.uuid5(NS, f"via {net} {v}")))
    return out


def strip_ours(text, nets):
    mine = _our_uuids(text)
    kept, last = [], 0
    for m in rp.OURS.finditer(text):
        if m.group(1) in mine:
            net = re.search(r'\(net "([^"]+)"\)', m.group(0)).group(1)
            if net in nets:
                kept.append(text[last:m.start()])
                last = m.end()
    kept.append(text[last:])
    return "".join(kept)


def escape(grid, copper, p, net, openT):
    """A pad with no open cell inside it: too fine a pitch for the grid.

    Leave it by a short straight stub, measured exactly, to the nearest open
    cell. Try the full 0.2 mm track first and the 0.15 mm neck after.
    """
    g = pad_geom(p)
    c = g.centroid
    # First choice: straight out of the package, along the axis from the
    # part's centre to the pad, so the stubs of neighbouring pins run side by
    # side instead of each taking whichever nearby cell it finds first and
    # crossing its neighbour's (which is what U2's pins 8 and 9 did).
    cx, cy = PART_CENTRE[p["ref"]]
    dx, dy = c.x - cx, c.y - cy
    ax = (1 if dx > 0 else -1, 0) if abs(dx) >= abs(dy) else (0, 1 if dy > 0 else -1)
    x0, y0, x1, y1 = g.bounds
    half = (x1 - x0) / 2 if ax[0] else (y1 - y0) / 2
    for L in pad_layers(p):
        li = LAYERS.index(L)
        foreign = unary_union(copper.foreign(L, net))
        o = openT[li]
        for extra in (0.45, 0.6, 0.8):
            ex = c.x + ax[0] * (half + extra)
            ey = c.y + ax[1] * (half + extra)
            i, j = int(round((ex - grid.x0) / G)), int(round((ey - grid.y0) / G))
            if not (0 <= i < grid.nx and 0 <= j < grid.ny) or not o[j, i]:
                continue
            q = grid.xy(i, j)
            a = (round(c.x, 4), round(c.y, 4))
            for w in (W, NECK_W):
                line = LineString([a, q]).buffer(w / 2, quad_segs=8)
                if line.distance(foreign) >= CLEAR:
                    return {li * grid.N + j * grid.nx + i}, (net, L, a, q, w)
    for L in pad_layers(p):
        li = LAYERS.index(L)
        foreign = unary_union(copper.foreign(L, net))
        o = openT[li]
        i0 = int((c.x - grid.x0) / G)
        j0 = int((c.y - grid.y0) / G)
        R = int(1.5 / G)
        cand = []
        for j in range(max(0, j0 - R), min(grid.ny, j0 + R + 1)):
            for i in range(max(0, i0 - R), min(grid.nx, i0 + R + 1)):
                if o[j, i]:
                    q = grid.xy(i, j)
                    cand.append((math.dist(q, (c.x, c.y)), i, j, q))
        cand.sort()
        for w in (W, NECK_W):
            for dd, i, j, q in cand[:400]:
                line = LineString([(c.x, c.y), q]).buffer(w / 2, quad_segs=8)
                if line.distance(foreign) >= CLEAR:
                    a = (round(c.x, 4), round(c.y, 4))
                    return {li * grid.N + j * grid.nx + i}, (net, L, a, q, w)
    return set(), None


def audit(copper, new_segs, new_vias, edge, ko_t, ko_v, apertures=()):
    probs = []
    for net, L, a, b, w in new_segs:
        if L != "F.Cu":
            continue
        g = LineString([a, b]).buffer(w / 2, quad_segs=16)
        for ref, own_nets, ap in apertures:
            if net not in own_nets and g.distance(ap) < MASK_GAP - 1e-6:
                probs.append(f"{net} {L} {a}-{b}: in {ref}'s mask aperture")
    idx = {}
    for L in LAYERS:
        items = copper.items[L]
        idx[L] = (shapely.STRtree([g for _n, g in items]), items)
    boundary = edge.exterior
    for net, L, a, b, w in new_segs:
        g = LineString([a, b]).buffer(w / 2, quad_segs=16)
        tree, items = idx[L]
        for k in tree.query(g.buffer(CLEAR)):
            n, other = items[k]
            if n == net:
                continue
            d = g.distance(other)
            if d < CLEAR - 1e-6:
                probs.append(f"{net} {L} {a}-{b}: {d:.3f} mm from {n}")
        if not edge.contains(g):
            probs.append(f"{net} {L} {a}-{b}: off the board")
        de = g.distance(boundary)
        if de < EDGE - 1e-6 and not _into_edge_pad(copper, L, net, g):
            probs.append(f"{net} {L} {a}-{b}: {de:.3f} mm from the edge")
        for name, pg in ko_t:
            if g.intersects(pg):
                probs.append(f"{net} {L} {a}-{b}: inside {name}")
    for net, v in new_vias:
        g = Point(v).buffer(VIA_D / 2, quad_segs=16)
        for L in LAYERS:
            tree, items = idx[L]
            for k in tree.query(g.buffer(CLEAR)):
                n, other = items[k]
                if n != net and g.distance(other) < CLEAR - 1e-6:
                    probs.append(f"via {net} {v}: {g.distance(other):.3f} mm "
                                 f"from {n} on {L}")
        if g.distance(boundary) < EDGE - 1e-6:
            probs.append(f"via {net} {v}: too near the edge")
        for name, pg in ko_v + ko_t:
            if g.intersects(pg):
                probs.append(f"via {net} {v}: inside {name}")
    return probs


def _into_edge_pad(copper, L, net, g):
    """A track that is near the edge only because its own pad is."""
    for n, other in copper.items[L]:
        if n == net and other.intersects(g) and other.area < 20:
            return True
    return False


def draw(path, pads, keep_segs, new_segs, new_vias, keep_vias):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as MP
    fig, ax = plt.subplots(figsize=(14, 26))
    for p in pads:
        col = "tab:red" if "F.Cu" in p["layers"] and "B.Cu" not in p["layers"] \
            else "tab:blue"
        for poly in p["polys"]:
            ax.add_patch(MP(poly, closed=True, fc=col, alpha=0.25, ec="none"))
    for s in keep_segs:
        ax.plot([s["p"][0], s["q"][0]], [s["p"][1], s["q"][1]], color="grey",
                lw=s["w"] * 4)
    for n, L, a, b, w in new_segs:
        ax.plot([a[0], b[0]], [a[1], b[1]],
                color="navy" if L == "B.Cu" else "crimson", lw=w * 5)
    for n, v in new_vias:
        ax.plot(v[0], v[1], "o", color="green", ms=3)
    for v in keep_vias:
        ax.plot(v["at"][0], v["at"][1], "o", color="grey", ms=2)
    ax.set_xlim(-1, 77)
    ax.set_ylim(145, -1)
    ax.set_aspect("equal")
    plt.savefig(path, dpi=100, bbox_inches="tight")


if __name__ == "__main__":
    sys.exit(main())
