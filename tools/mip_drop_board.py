#!/usr/bin/env python3
"""One-off, MIP branch: stretch the e-paper board into the MIP board.

Everything below Y 48.3 (the e-paper glass's lower edge) moves down by
variant.DROP: footprints by their position, and every track, via, zone,
keepout and outline point by its co-ordinates. The FPC notch on the left
edge is re-centred on the MIP panel's tail. Run once, on a board that has
not had it yet; it refuses a board whose outline already reaches 155.

Tracks that crossed Y 48.3 come out bent; route_power.py and
route_signals.py replace every one of them.

    python3 tools/mip_drop_board.py
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import route_power as rp            # noqa: E402
import variant                      # noqa: E402

PCB = Path(__file__).resolve().parent.parent / "elec/layout/default/default.kicad_pcb"
PAIR = re.compile(r'\((start|end|mid|center|xy|at) (-?[\d.]+) (-?[\d.]+)')
NOTCH_OLD = (22.15, 38.15)
NOTCH_NEW = (29.01, 42.01)     # 9.47 mm tail at Y 35.51, 1.77 mm either side


def fmt(v):
    return f"{round(v, 4):g}"


def shift(m):
    y = float(m.group(3))
    return f"({m.group(1)} {m.group(2)} {fmt(variant.drop(y))}"


def main():
    text = PCB.read_text()
    if rp.board_box(text)[3] > 150:
        raise SystemExit("the outline already reaches past Y 150: already done")
    out, pos = [], 0
    for m in re.finditer(r'\n\t\((\w+)', text):
        start = m.start() + 2
        if start < pos:
            continue
        blk = rp.block_at(text, start)
        out.append(text[pos:start])
        if m.group(1) == "footprint":
            at = rp.FP_AT.search(blk)
            y = float(at.group(2))
            blk = (blk[:at.start()] + f"\n\t\t(at {at.group(1)} {fmt(variant.drop(y))}"
                   f"{at.group(3)})" + blk[at.end():])
        elif m.group(1) in ("segment", "via", "zone", "gr_line", "gr_circle",
                            "gr_rect", "gr_arc", "gr_poly", "gr_text", "arc"):
            blk = PAIR.sub(shift, blk)
            if m.group(1) == "gr_line" and '"Edge.Cuts"' in blk:
                for old, new in zip(NOTCH_OLD, NOTCH_NEW):
                    blk = re.sub(rf'\((start|end) (-?[\d.]+) {old:g}\)',
                                 lambda k: f"({k.group(1)} {k.group(2)} {new:g})", blk)
        out.append(blk)
        pos = start + len(rp.block_at(text, start))
    out.append(text[pos:])
    PCB.write_text("".join(out))
    print("board stretched to", rp.board_box("".join(out)))


if __name__ == "__main__":
    main()
