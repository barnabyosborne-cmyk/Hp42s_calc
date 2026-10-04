#!/usr/bin/env python3
"""One-off, branch ls027: turn the 146 mm mip board into the 142 mm 2.7 inch
board (4 October 2026).

The LS027B7DH01's glass ends at Y 50.32 instead of the LS032's 54.52, so
everything below Y 54.52 -- the keyboard, every part on the back from the
panel's 5 V block down, the bottom edge, the bottom mounting holes -- moves
up 4.0 (variant.DROP 2 -> -2). Footprints move by their position, and every
zone, keepout and drawing by its co-ordinates, including the rule areas
stored inside footprints, which are in board co-ordinates.

The outline is redrawn from variant.py: 76 x 142 with the 2 mm / 4 mm corner
chamfers, no FPC notch on the left edge any more (the tail now folds back
through a slot under the glass), and the two holes in variant.CUTOUTS. All
tracks and vias are stripped: the board gets a full reroute. Run
tools/mounting.py afterwards to put the mounting holes back. Refuses a board
whose outline does not reach 146.

    python3 tools/ls027_from_mip.py
"""
import re
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import route_power as rp            # noqa: E402
import variant                      # noqa: E402

PCB = Path(__file__).resolve().parent.parent / "elec/layout/default/default.kicad_pcb"
PAIR = re.compile(r'\((start|end|mid|center|xy|at) (-?[\d.]+) (-?[\d.]+)')
LINE, LIFT = 54.52, 4.0
NS = uuid.UUID("5a7e0c27-0000-4000-8000-000000000027")


def fmt(v):
    return f"{round(v, 4):g}"


def lift(y):
    return y - LIFT if y > LINE else y


def moved(blk, fn):
    return PAIR.sub(lambda m: f"({m.group(1)} {m.group(2)} {fmt(fn(float(m.group(3))))}", blk)


def edge_line(a, b, name):
    return (f'\t(gr_line\n\t\t(start {fmt(a[0])} {fmt(a[1])})\n\t\t(end {fmt(b[0])} {fmt(b[1])})\n'
            f'\t\t(stroke\n\t\t\t(width 0.1)\n\t\t\t(type default)\n\t\t)\n'
            f'\t\t(layer "Edge.Cuts")\n\t\t(uuid "{uuid.uuid5(NS, name)}")\n\t)\n')


def outline():
    W, H = variant.BOARD_W, variant.BOARD_H
    pts = [(2, 0), (W - 2, 0), (W, 2), (W, H - 4), (W - 4, H), (4, H), (0, H - 4), (0, 2)]
    out = [edge_line(pts[i], pts[(i + 1) % len(pts)], f"outline {i}") for i in range(len(pts))]
    for k, (x0, y0, x1, y1) in enumerate(variant.CUTOUTS):
        c = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        out += [edge_line(c[i], c[(i + 1) % 4], f"cutout {k} {i}") for i in range(4)]
    return "".join(out)


def main():
    text = PCB.read_text()
    if abs(rp.board_box(text)[3] - 146.0) > 1e-6:
        raise SystemExit("the outline does not reach Y 146: already done?")
    out, pos = [], 0
    for m in re.finditer(r'\n\t\((\w+)', text):
        start = m.start() + 2
        if start < pos:
            continue
        blk = rp.block_at(text, start)
        out.append(text[pos:start])
        pos = start + len(blk)
        kind = m.group(1)
        if kind in ("segment", "via", "arc"):
            out.append("")
            continue
        if kind == "footprint":
            at = rp.FP_AT.search(blk)
            x, y = float(at.group(1)), float(at.group(2))
            ny = lift(y)
            dy = ny - y
            blk = (blk[:at.start()] + f"\n\t\t(at {fmt(x)} {fmt(ny)}"
                   f"{at.group(3)})" + blk[at.end():])
            parts, p = [], 0
            for z in re.finditer(r'\(zone\b', blk):
                if z.start() < p:
                    continue
                zb = rp.block_at(blk, z.start())
                parts.append(blk[p:z.start()])
                parts.append(moved(zb, lambda v: v + dy))
                p = z.start() + len(zb)
            parts.append(blk[p:])
            blk = "".join(parts)
        elif kind == "gr_line" and '"Edge.Cuts"' in blk:
            out.append("")
            # swallow the newline that followed the block
            continue
        elif kind in ("zone", "gr_line", "gr_circle", "gr_rect", "gr_arc",
                      "gr_poly", "gr_text"):
            if not (kind == "gr_circle" and '"Edge.Cuts"' in blk):   # holes: mounting.py
                blk = moved(blk, lift)
        out.append(blk)
    out.append(text[pos:])
    new = "".join(out)
    new = re.sub(r'\n\t\n', '\n', new)
    i = new.rindex("\n)")
    new = new[:i + 1] + outline() + new[i + 1:]
    PCB.write_text(new)
    print("board now", rp.board_box(new))


if __name__ == "__main__":
    main()
