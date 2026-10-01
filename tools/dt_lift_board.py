#!/usr/bin/env python3
"""One-off, dt branch: shrink the MIP board (155) into the Displaytech board.

The mip branch moved everything below Y 48.3 down by 11.0; dt wants 6.0
(variant.DROP), so everything below Y 59.3 comes back up by 5.0: footprints
by their position, and every track, via, zone, keepout and outline point by
its co-ordinates -- including the rule areas stored inside footprints, which
are in board co-ordinates and would otherwise stay behind. The FPC notch on
the left edge goes: the 64128M has clip pins, not a flex tail. Run once, on
a board whose outline still reaches 155; it refuses anything else.

Tracks that crossed Y 59.3 come out bent; route_power.py and
route_signals.py replace every one of them.

    python3 tools/dt_lift_board.py
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import route_power as rp            # noqa: E402
import variant                      # noqa: E402

PCB = Path(__file__).resolve().parent.parent / "elec/layout/default/default.kicad_pcb"
PAIR = re.compile(r'\((start|end|mid|center|xy|at) (-?[\d.]+) (-?[\d.]+)')
MIP_DROP = 11.0
LINE = variant.DROP_FROM + MIP_DROP          # 59.3
LIFT = MIP_DROP - variant.DROP               # 5.0
NOTCH = (29.01, 42.01)


def fmt(v):
    return f"{round(v, 4):g}"


def lift(y):
    return y - LIFT if y > LINE else y


def shift(m):
    return f"({m.group(1)} {m.group(2)} {fmt(lift(float(m.group(3))))}"


def main():
    text = PCB.read_text()
    if abs(rp.board_box(text)[3] - 155.0) > 1e-6:
        raise SystemExit("the outline does not reach Y 155: not the mip board, "
                         "or already done")
    out, pos = [], 0
    for m in re.finditer(r'\n\t\((\w+)', text):
        start = m.start() + 2
        if start < pos:
            continue
        orig = rp.block_at(text, start)
        blk = orig
        out.append(text[pos:start])
        pos = start + len(orig)
        kind = m.group(1)
        if kind == "footprint":
            at = rp.FP_AT.search(blk)
            y = float(at.group(2))
            blk = (blk[:at.start()] + f"\n\t\t(at {at.group(1)} {fmt(lift(y))}"
                   f"{at.group(3)})" + blk[at.end():])
            # embedded rule areas are in board co-ordinates
            parts, p = [], 0
            for z in re.finditer(r'\(zone\b', blk):
                if z.start() < p:
                    continue
                zb = rp.block_at(blk, z.start())
                parts.append(blk[p:z.start()])
                parts.append(PAIR.sub(shift, zb))
                p = z.start() + len(zb)
            parts.append(blk[p:])
            blk = "".join(parts)
        elif kind in ("segment", "via", "zone", "gr_line", "gr_circle",
                      "gr_rect", "gr_arc", "gr_poly", "gr_text", "arc"):
            if kind == "gr_line" and '"Edge.Cuts"' in blk:
                ends = re.findall(r'\((start|end) (-?[\d.]+) (-?[\d.]+)\)', blk)
                pts = {(float(x), float(y)) for _, x, y in ends}
                if any(abs(x - 0.55) < 1e-6 for x, _ in pts) or \
                        pts == {(0.0, 151.0), (0.0, NOTCH[1])}:
                    out.append("")          # the notch, and the edge below it
                    continue
                if pts == {(0.0, NOTCH[0]), (0.0, 2.0)}:
                    blk = blk.replace(f"(start 0 {NOTCH[0]:g})", "(start 0 151)")
            blk = PAIR.sub(shift, blk)
        out.append(blk)
    out.append(text[pos:])
    new = "".join(out)
    PCB.write_text(new)
    print("board now", rp.board_box(new))


if __name__ == "__main__":
    main()
