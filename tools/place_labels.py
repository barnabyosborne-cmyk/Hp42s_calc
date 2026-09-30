#!/usr/bin/env python3
"""Move every reference label that overlaps something to where it doesn't.

KiCad places a part's reference wherever its library footprint says, which on
a board this dense lands a good few of them on a neighbour's pads, on another
label or on their own outline. DRC reports those as silk_over_copper and
silk_overlap; the fab clips silk off pads, so they print as fragments.

A label is left exactly where it is unless it hits something. One that does
is moved to the nearest spot around its own part where its text box keeps
CLEAR from:

  - every mask opening on its side of the board (pads, domes);
  - every silkscreen line, circle and outline on its side;
  - every other label on its side, including ones already moved;
  - the board edge;

and, if such a spot exists, off every other part's courtyard as well, so the
label is not hidden under a component once the board is assembled. The dome
labels have their own rules in place_dome_labels.py and are left alone here,
though they count as obstacles.

    python3 tools/place_labels.py --check   # report, write nothing
    python3 tools/place_labels.py           # write the board
"""

import math
import re
import sys
from pathlib import Path

from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).parent))
import route_power as rp            # noqa: E402  the board reader lives there

ROOT = Path(__file__).resolve().parent.parent
PCB = ROOT / "elec/layout/default/default.kicad_pcb"

CLEAR = 0.15     # the board's silk clearance, with a little to spare
EDGE = 0.3
ADVANCE = 0.85   # KiCad stroke font, per character, as a fraction of size
STEP = 0.1       # search step, mm
REACH = 4.0      # how far from its part a label may go


def num(pat, blk, default=None):
    m = re.search(pat, blk)
    return m if m else default


def footprints(text):
    for m in re.finditer(r'\n\t\(footprint "', text):
        start = m.start() + 2
        yield start, rp.block_at(text, start)


def fp_frame(blk):
    at = rp.FP_AT.search(blk)
    fx, fy = float(at.group(1)), float(at.group(2))
    fr = float(at.group(3)) if at.group(3).strip() else 0.0

    def to_board(x, y):
        rx, ry = rp.rot(x, y, fr)
        return fx + rx, fy + ry
    return fx, fy, fr, to_board


def side(blk):
    return "B" if re.search(r'\n\t\t\(layer "B\.Cu"\)', blk) else "F"


def silk_shapes(blk, to_board, layer):
    """Every silkscreen graphic of one footprint on one layer, grown by its
    stroke, in board co-ordinates."""
    out = []
    for g in re.finditer(r'\n\t\t\((fp_line|fp_circle|fp_rect|fp_poly|fp_arc)\b',
                         blk):
        kind = g.group(1)
        gb = rp.block_at(blk, g.start() + 3)
        if f'(layer "{layer}")' not in gb:
            continue
        w = float(num(r'\(width ([\d.]+)\)', gb).group(1)) if num(
            r'\(width ([\d.]+)\)', gb) else 0.12

        def pt(tag):
            m = re.search(r'\(' + tag + r' (-?[\d.]+) (-?[\d.]+)\)', gb)
            return to_board(float(m.group(1)), float(m.group(2)))
        if kind == "fp_line":
            out.append(LineString([pt("start"), pt("end")]).buffer(w / 2))
        elif kind == "fp_arc":
            out.append(LineString([pt("start"), pt("mid"), pt("end")])
                       .buffer(w / 2))
        elif kind == "fp_circle":
            c, e = pt("center"), pt("end")
            r = math.dist(c, e)
            ring = Point(c).buffer(r + w / 2)
            filled = "(fill yes)" in gb or "(fill solid)" in gb
            out.append(ring if filled else ring.difference(
                Point(c).buffer(max(r - w / 2, 0))))
        elif kind == "fp_rect":
            a, b = pt("start"), pt("end")
            out.append(box(min(a[0], b[0]), min(a[1], b[1]),
                           max(a[0], b[0]), max(a[1], b[1]))
                       .exterior.buffer(w / 2))
        elif kind == "fp_poly":
            pts = [to_board(float(x), float(y)) for x, y in
                   re.findall(r'\(xy (-?[\d.]+) (-?[\d.]+)\)', gb)]
            if len(pts) >= 3:
                out.append(Polygon(pts).buffer(w / 2))
    return out


def courtyard(blk, to_board, layer):
    pts = []
    for g in re.finditer(r'\n\t\t\((fp_line|fp_rect|fp_poly|fp_circle)\b', blk):
        gb = rp.block_at(blk, g.start() + 3)
        if f'(layer "{layer}")' not in gb:
            continue
        for x, y in re.findall(r'\((?:start|end|xy|center) (-?[\d.]+) (-?[\d.]+)\)',
                               gb):
            pts.append(to_board(float(x), float(y)))
    if len(pts) < 2:
        return None
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return box(min(xs), min(ys), max(xs), max(ys))


def mask_openings(blk, to_board, fr, layer):
    out = []
    for pm in re.finditer(r'\n\t\t\(pad "', blk):
        pad = rp.block_at(blk, pm.start() + 3)
        lay = re.search(r'\(layers ([^)]*)\)', pad)
        if not lay or not re.search(f'"{layer}"|"\\*\\.Mask"', lay.group(1)):
            continue
        pat = re.search(r'\(at (-?[\d.]+) (-?[\d.]+)(?: (-?[\d.]+))?\)', pad)
        cx, cy = to_board(float(pat.group(1)), float(pat.group(2)))
        polys = rp.pad_shapes(pad, cx, cy, float(pat.group(3) or 0.0))
        out.append(unary_union([Polygon(q).buffer(0) for q in polys]))
    return out


def label(blk, to_board, fr):
    """The Reference field: its block, board position, size, angle, box."""
    m = re.search(r'\(property "Reference" "([^"]+)"', blk)
    pb = rp.block_at(blk, m.start())
    at = re.search(r'\(at (-?[\d.]+) (-?[\d.]+)(?: (-?[\d.]+))?\)', pb)
    lx, ly = float(at.group(1)), float(at.group(2))
    ang = float(at.group(3) or 0.0)
    size = float(re.search(r'\(size ([\d.]+)', pb).group(1))
    th = re.search(r'\(thickness ([\d.]+)\)', pb)
    thick = float(th.group(1)) if th else 0.15
    x, y = to_board(lx, ly)
    hidden = "(hide yes)" in pb
    return dict(ref=m.group(1), blk=pb, x=x, y=y, lx=lx, ly=ly, ang=ang,
                size=size, thick=thick, hidden=hidden)


def text_box(x, y, n, size, thick, ang):
    w = n * ADVANCE * size + thick
    h = size + thick
    if round(ang) % 180 == 90:
        w, h = h, w
    return box(x - w / 2, y - h / 2, x + w / 2, y + h / 2)


def main():
    check = "--check" in sys.argv
    text = PCB.read_text()
    x0, y0, x1, y1 = rp.board_box(text)
    inside = box(x0 + EDGE, y0 + EDGE, x1 - EDGE, y1 - EDGE)

    parts = []
    for start, blk in footprints(text):
        fx, fy, fr, to_board = fp_frame(blk)
        s = side(blk)
        lab = label(blk, to_board, fr)
        parts.append(dict(
            start=start, blk=blk, side=s, fr=fr, fx=fx, fy=fy,
            to_board=to_board, lab=lab,
            dome=blk.startswith('(footprint "hp42s:Dome_'),
            silk=silk_shapes(blk, to_board, f"{s}.SilkS"),
            mask=mask_openings(blk, to_board, fr, f"{s}.Mask"),
            crt=courtyard(blk, to_board, f"{s}.CrtYd")))

    moves, stuck = [], []
    for s in ("F", "B"):
        mine = [p for p in parts if p["side"] == s]
        hard = unary_union([g for p in mine for g in p["silk"] + p["mask"]])
        boxes = {}
        for p in mine:
            L = p["lab"]
            if not L["hidden"]:
                boxes[L["ref"]] = text_box(L["x"], L["y"], len(L["ref"]),
                                           L["size"], L["thick"], L["ang"])

        def clash(ref, tb):
            if tb.distance(hard) < CLEAR - 1e-6 or not inside.contains(tb):
                return True
            return any(tb.distance(b) < CLEAR - 1e-6 for r, b in boxes.items()
                       if r != ref)

        order = sorted((p for p in mine if not p["dome"]
                        and not p["lab"]["hidden"]),
                       key=lambda p: (p["fy"], p["fx"]))
        for p in order:
            L = p["lab"]
            if not clash(L["ref"], boxes[L["ref"]]):
                continue
            others = unary_union([q["crt"] for q in mine
                                  if q is not p and q["crt"] is not None])
            best = None
            for size in (L["size"], 0.8):
                thick = min(L["thick"], 0.15 if size >= 1 else 0.12)
                for strict in (True, False):
                    cands = []
                    k = int(REACH / STEP)
                    for i in range(-k, k + 1):
                        for j in range(-k, k + 1):
                            x = round(p["fx"] + i * STEP, 3)
                            y = round(p["fy"] + j * STEP, 3)
                            tb = text_box(x, y, len(L["ref"]), size, thick, 0)
                            if clash(L["ref"], tb):
                                continue
                            if strict and tb.intersects(others):
                                continue
                            if p["crt"] is not None:
                                d = tb.distance(p["crt"])
                            else:
                                d = math.dist((x, y), (p["fx"], p["fy"]))
                            cands.append((round(d, 3), abs(y - p["fy"]),
                                          abs(x - p["fx"]), x, y, tb))
                    if cands:
                        best = min(cands)[3:] + (size, thick)
                        break
                if best:
                    break
            if not best:
                stuck.append(L["ref"])
                continue
            x, y, tb, size, thick = best
            boxes[L["ref"]] = tb
            moves.append((p, x, y, size, thick))

    for p, x, y, size, _t in moves:
        L = p["lab"]
        print(f"  {L['ref']:5s} ({L['x']:.3f}, {L['y']:.3f}) -> "
              f"({x:.3f}, {y:.3f})  {size:g} mm")
    if stuck:
        print("no clear spot within reach for: " + ", ".join(stuck))
    if check:
        print("--check: nothing written")
        return 1 if stuck else 0

    out = text
    for p, x, y, size, thick in sorted(moves, key=lambda m: -m[0]["start"]):
        L = p["lab"]
        # board -> footprint frame: undo the translation, then the rotation
        lx, ly = rp.rot(x - p["fx"], y - p["fy"], -p["fr"])
        new = re.sub(r'\(at -?[\d.]+ -?[\d.]+(?: -?[\d.]+)?\)',
                     f"(at {round(lx, 3):g} {round(ly, 3):g} "
                     f"{round(L['ang']):g})", L["blk"], count=1)
        new = re.sub(r'\(size [\d.]+ [\d.]+\)', f"(size {size:g} {size:g})",
                     new, count=1)
        new = re.sub(r'\(thickness [\d.]+\)', f"(thickness {thick:g})",
                     new, count=1)
        blk = p["blk"].replace(L["blk"], new, 1)
        out = out[:p["start"]] + blk + out[p["start"] + len(p["blk"]):]
    PCB.write_text(out)
    print(f"{len(moves)} label(s) moved; wrote {PCB.relative_to(ROOT)}")
    return 1 if stuck else 0


if __name__ == "__main__":
    sys.exit(main())
