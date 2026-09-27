#!/usr/bin/env python3
"""Turn panel frames into pictures.

    python3 frames.py DIR            # DIR/frame-*.pbm from hp42s_host
    python3 frames.py LOG DIR        # EPDFRAME lines from a Wokwi run's output

Writes each frame as a PNG at three times size in e-paper colours, with the
case aperture from firmware/main/epd.h marked, plus DIR/sheet.png with every
frame in order. Needs Pillow.
"""

import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw

W, H = 296, 152
VIEW_X, VIEW_W = 3, 275          # firmware/main/epd.h EPD_VIEW_X, EPD_VIEW_W
PAPER, INK, HIDDEN = (228, 226, 216), (34, 34, 38), (150, 150, 150)
SCALE = 3


def from_pbm(path):
    tok = path.read_text().split()
    assert tok[0] == "P1" and (int(tok[1]), int(tok[2])) == (W, H), path
    bits = "".join(tok[3:])
    return [[bits[y * W + x] == "1" for x in range(W)] for y in range(H)]


def from_log(log):
    """EPDFRAME <update> <first gate> <hex>: 8 gate lines of 19 bytes, bit 7
    of the first byte at source 0, a set bit paper. Lines may carry serial
    output in front of them; a frame missing any line is dropped."""
    frames = {}
    for m in re.finditer(r"EPDFRAME (\d+) (\d+) ([0-9a-f]+)", log):
        frames.setdefault(int(m[1]), {})[int(m[2])] = bytes.fromhex(m[3])
    out = []
    for n in sorted(frames):
        chunks = frames[n]
        if set(chunks) != set(range(0, W, 8)):
            print(f"frame {n}: incomplete, skipped")
            continue
        ram = b"".join(chunks[g] for g in range(0, W, 8))
        out.append([[not (ram[x * 19 + (y >> 3)] & (0x80 >> (y & 7)))
                     for x in range(W)] for y in range(H)])
    return out


def picture(ink):
    im = Image.new("RGB", (W, H), PAPER)
    px = im.load()
    for y in range(H):
        for x in range(W):
            hidden = not VIEW_X <= x < VIEW_X + VIEW_W
            if ink[y][x]:
                px[x, y] = INK
            elif hidden:
                px[x, y] = HIDDEN
    return im.resize((W * SCALE, H * SCALE), Image.NEAREST)


def main():
    if len(sys.argv) == 2:
        out = Path(sys.argv[1])
        frames = [from_pbm(p) for p in sorted(out.glob("frame-*.pbm"))]
    else:
        out = Path(sys.argv[2])
        out.mkdir(parents=True, exist_ok=True)
        frames = from_log(Path(sys.argv[1]).read_text(errors="replace"))
    pics = [picture(f) for f in frames]
    for i, p in enumerate(pics):
        p.save(out / f"frame-{i:02d}.png")
    if pics:
        gap = 12
        sheet = Image.new("RGB", (pics[0].width, len(pics) * (pics[0].height + gap)),
                          (255, 255, 255))
        d = ImageDraw.Draw(sheet)
        for i, p in enumerate(pics):
            y = i * (p.height + gap)
            sheet.paste(p, (0, y))
            d.text((4, y + 2), str(i), fill=(200, 0, 0))
        sheet.save(out / "sheet.png")
    print(f"{len(pics)} frame(s) to {out}")


if __name__ == "__main__":
    main()
