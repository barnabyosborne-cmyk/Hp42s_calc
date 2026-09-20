# Character size, and why the scaling is not square

## The measurement that settled it

Barnaby measured the original HP-42S on 19 September 2026: each pixel on its
display is about **0.42 mm wide and 0.65 mm tall**. They are not square. At
131 × 16 pixels that makes the whole original display 55.0 × 10.4 mm, which is
about what it looks like.

Our panel's pixels *are* square: 0.203 × 0.202 mm, from 296 × 152 pixels over
a 60.088 × 30.704 mm active area.

So a character rendered at the same integer scale on both axes cannot have the
original's proportions. It comes out squat.

## What the scale factors buy

Plus42 draws characters in 6 × 8 pixel cells, of which 5 × 7 is ink.

| | cell | vs original | rows in 152 px |
|---|---|---|---|
| original HP-42S | 2.52 × 5.20 mm | — | 2 |
| 2× across, 2× down | 2.44 × 3.23 mm | 97% wide, **62% tall** | 9 |
| **2× across, 3× down** | **2.44 × 4.85 mm** | **97% wide, 93% tall** | **6** |
| 2× across, 4× down | 2.44 × 6.46 mm | 97% wide, 124% tall | 4 |
| 3× across, 3× down | 3.65 × 4.85 mm | — | doesn't fit: 23 columns needs 411 px |

**2 across by 3 down is the answer.** It lands within 3% of the original on
width and 7% on height, and the aspect ratio comes out at 1:1.99 against the
original's 1:2.06.

## It costs nothing

Both 2×2 and 2×3 use exactly 144 of the panel's 152 rows — nine cells of 16
pixels and six of 24 come to the same number. So the refresh area is identical,
the energy per keystroke is identical, and the 8 pixels left at the bottom are
the annunciator strip either way, drawn at 1× and 1.62 mm tall.

The only cost is rows of text: 6 instead of 9.

## Six rows is the right number anyway

Barnaby's own stated preference, before any of this was worked out, was "4 +
info + status bar". That is six rows.

    row 0   T
    row 1   Z
    row 2   Y
    row 3   X
    row 4   info / equation line
    row 5   menu

Plus42's minimum is 2 rows, so 6 is well inside range, and the original 42S
showed 2.

## Where this lives in the firmware

Nowhere in the Plus42 core. The core paints a 1-bit bitmap of
(cols × 6 − 1) × (rows × 8) pixels and hands it to `shell_blitter`, which is
ours to write. The shell picks the scale factors, independently per axis, and
replicates each logical pixel into a 2 × 3 block.

Two constants. Change them and you are back to 24 × 9 at squat proportions, so
it is worth building both and looking at them before deciding for good — it is
a five-minute change and the sort of thing that only settles when you hold it.

One thing that will look different and should: diagonal strokes step in 3-pixel
increments vertically rather than 2. The original did exactly the same thing,
for exactly the same reason — its pixels were 1:1.55 tall. It will look *more*
like a 42S, not less.

## 23 columns, not 24

The arithmetic above gives 24 columns across the full 296-pixel panel. The
case takes one of them back.

Barnaby settled on 20 September 2026 that **the aperture in the case is
centred**, for the look of the thing, while the panel's active area sits
1.52 mm right of the case centreline for reasons it cannot help — see
`docs/display-mounting.md`. A centred aperture therefore masks the panel
unequally, and the widest one that stays inside the active area is 57.04 mm
against the active area's own 60.088 mm.

At the 56.00 mm aperture the firmware assumes, the visible strip is panel
columns 3 to 277: **275 pixels**, with 3 hidden on the left and 18 on the
right. What fits:

| | logical px | on the panel | fits in 275? |
|---|---|---|---|
| 22 columns | 131 | 262 | yes, 13 to spare |
| **23 columns** | **137** | **274** | **yes, 1 to spare** |
| 24 columns | 143 | 286 | no, 11 over |

So 23. The original HP-42S showed 22, so this is still one better than the
machine it copies, and Plus42's own floor is 22.

**Vertically nothing is lost.** The active area is centred on its own glass
across the short axis, so a centred aperture masks nothing, and all 152 rows
stay: 144 for six rows of text and 8 for the annunciator strip.

## Set it at first boot

`SETDS 23 6`, then leave `ROW±` and `COL±` available in the DISP menu. The
blitter must treat 23 × 6 as a default, not a constant: Plus42 genuinely
resizes at runtime and will hand the shell a different bitmap if asked. The
window clipping in `shell_blitter` is what keeps a larger request from
painting into the masked columns.
