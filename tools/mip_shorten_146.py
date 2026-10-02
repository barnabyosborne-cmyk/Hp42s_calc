#!/usr/bin/env python3
"""One-off, MIP branch: shorten the 155 board to 146 (2 October 2026).

Barnaby dropped the frontlight and its sliver and took a 9.5 mm top bezel,
so the glass moves up 4.5 (Y 12 -> 7.5) and everything below Y 59.3 -- the
keyboard, the back from the panel's 5 V block down, the bottom edge -- moves
up 9.0 (variant.DROP 11 -> 2). Footprints move by their position, and every
zone, keepout and outline point by its co-ordinates, including the rule
areas stored inside footprints, which are in board co-ordinates and would
otherwise stay behind. J2 and the FPC notch move up 4.5 with the glass.

It also takes off what is no longer in the source: the frontlight boost
(U8, L3, D3, C15-C17, R21-R23) and the sliver lands TP1/TP2, and moves the
faceplate ground pad TP3 into the keypad, where dt has it, because the glass
now covers its old spot. All tracks and vias are stripped: the board gets a
full reroute afterwards. Refuses a board whose outline does not reach 155.

    python3 tools/mip_shorten_146.py
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import route_power as rp            # noqa: E402
import variant                      # noqa: E402

PCB = Path(__file__).resolve().parent.parent / "elec/layout/default/default.kicad_pcb"
PAIR = re.compile(r'\((start|end|mid|center|xy|at) (-?[\d.]+) (-?[\d.]+)')
LINE, LIFT = 59.3, 9.0
GLASS_LIFT = 4.5
NOTCH = (29.01, 42.01)
GONE = {"U8", "L3", "D3", "C15", "C16", "C17", "R21", "R22", "R23", "TP1", "TP2"}
FACEPLATE = ("TP3", 14.75, variant.drop(103.855))


def fmt(v):
    return f"{round(v, 4):g}"


def lift(y):
    return y - LIFT if y > LINE else y


def moved(blk, fn):
    return PAIR.sub(lambda m: f"({m.group(1)} {m.group(2)} {fmt(fn(float(m.group(3))))}", blk)


def main():
    text = PCB.read_text()
    if abs(rp.board_box(text)[3] - 155.0) > 1e-6:
        raise SystemExit("the outline does not reach Y 155: already done?")
    out, pos, dropped = [], 0, []
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
            ref = rp.REF_RE.search(blk).group(1)
            if ref in GONE:
                dropped.append(ref)
                out.append("")
                continue
            at = rp.FP_AT.search(blk)
            x, y = float(at.group(1)), float(at.group(2))
            if ref == FACEPLATE[0]:
                nx, ny = FACEPLATE[1], FACEPLATE[2]
            elif ref == "J2":
                nx, ny = x, y - GLASS_LIFT
            else:
                nx, ny = x, lift(y)
            dy = ny - y
            blk = (blk[:at.start()] + f"\n\t\t(at {fmt(nx)} {fmt(ny)}"
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
        elif kind in ("zone", "gr_line", "gr_circle", "gr_rect", "gr_arc",
                      "gr_poly", "gr_text"):
            if kind == "gr_line" and '"Edge.Cuts"' in blk:
                blk = moved(blk, lambda v: v - GLASS_LIFT if v in NOTCH else lift(v))
            else:
                blk = moved(blk, lift)
        out.append(blk)
    out.append(text[pos:])
    new = "".join(out)
    PCB.write_text(new)
    print("removed", " ".join(sorted(dropped)))
    print("board now", rp.board_box(new))


if __name__ == "__main__":
    main()
