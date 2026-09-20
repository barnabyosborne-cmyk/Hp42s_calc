# Mounting the panel, and where the cell can go

Every number here is off Good Display's *GDEY0266T90 Specification* (rev
2021/10/12), mechanical drawing on page 5, except where it says otherwise.
Measure the physical panel before committing the board — the drawing gives the
tail length to ±0.3 mm and does not say unambiguously which edge of the glass
it is measured from.

## The tail

| | |
|---|---|
| Glass | 71.82 × 36.30 × 1.0 mm |
| Tail length beyond the glass | **14.30 ± 0.3 mm** |
| Tail width | 12.50 ± 0.10 mm |
| Tail thickness | 0.30 ± 0.03 mm |
| Contacts | 24 at 0.5 mm pitch, 11.50 mm span, contact side 5.00 ± 0.50 mm |
| Where it exits | centred on one 36.30 mm edge: 11.90 + 12.50 + 11.90 = 36.30 |

**14.30 mm is the whole budget.** Mounted landscape on a 76 mm board the panel
leaves about 2 mm of board either side of it, so an unfolded tail ends roughly
12 mm off the left edge. It cannot reach a slot cut inside the board either:
a slot needs its own width plus a few millimetres of board outboard of it for
strength, and the panel is 71.82 mm wide on a 76 mm board. There is nowhere to
put one.

So the tail folds **around the board's left edge**, which is what Barnaby
proposed and is what every ESL tag using this panel does.

### The fold, with numbers

The two legs are separated in Z by the panel glass plus the board — about
2.1 mm — so the fold's natural radius is **about 1.05 mm** and the half-turn
eats 3.3 mm of tail. That leaves:

```
14.30  tail
-3.30  the half-turn (the panel's edge sits flush with the notched
------  board edge below, so there is no front leg to speak of)
11.00  back leg
```

Eleven millimetres of back leg, of which the last 4 mm sits inside the
connector. **So the FPC connector goes on the back with its contacts starting
within about 5 mm of the notched edge, and its far end no more than 11 mm in.**
That is a firm constraint, not a preference: there is no slack to move it.

A 1.05 mm radius on a 0.3 mm FPC is tight — about 3.5× thickness. It is
normal practice for this class of part, but it is a fold you make **once**, on
assembly, not something that should flex in service. Two things help and both
are free:

- Route the board edge under the fold with a radius rather than leaving the
  square milled edge, and put a strip of Kapton over it. The failure mode is
  the board edge sawing through the FPC, not the bend itself.
- Do not let the case clamp the fold. The notch below gives it 0.3 mm of air
  to the case wall, and it should not get less.

## The panel is not centred on its own glass

This is the part that catches people. Across the long axis the active area sits
**8.93 mm from the tail edge and 2.80 mm from the far edge**. (Across the short
axis it is centred, 2.798 mm each side.) Centre the glass on the board and the
image lands 3.1 mm right of centre, which on a 60 mm image inside an 80 mm case
you would see every time you picked the thing up.

**Barnaby's decision, 2026-09-20: the image is what gets centred.** It cannot
be centred exactly, and it is worth understanding why, because the number that
comes out of it is one Barnaby controls in the case model rather than one this
board can fix.

### Why exactly centred is not available

For the image to be centred in an 80 mm case, its left edge has to sit
**9.956 mm** in from the case's outer face. Working from the outside in, three
things have to fit in that 9.956 mm and they do not:

```
  wall thickness             t
+ air for the fold        0.30
+ fold radius             1.05     half of (0.5 glass + 1.6 board)
+ the glass's own border  8.93     tail side
= where the image can start   t + 10.28
```

So the image ends up **(t + 0.32) mm right of centre** — near enough, off by
the thickness of the case wall. There is no arrangement that beats it. Putting
the tail on the right just mirrors the problem, and routing through a slot in
the board is worse, because a slot needs board outboard of it and that pushes
the panel further right still.

| case wall | panel left edge | board notch | image off centre |
|---|---|---|---|
| 1.2 mm | 2.55 mm from the case face | 0.55 mm | 1.52 mm |
| 1.5 mm | 2.85 | 0.85 | 1.82 mm |
| 2.0 mm | 3.35 | 1.35 | 2.32 mm |
| 2.5 mm | 3.85 | 1.85 | 2.82 mm |

**The wall thickness on that one side is the whole lever.** Everything else in
the sum is fixed by the panel and the board. If 2 mm is the default wall,
thinning it to 1.2 mm over the 16 mm the fold occupies buys back 0.8 mm of
centring, and a local 1.2 mm wall in resin is fine over that span.

### The notch

The board is inset 2 mm from the case face all round, so with any wall of
1.35 mm or more **the board reaches the wall and there is nowhere for the fold
to go**. It needs a local notch in the board's left edge, `wall − 0.65` mm
deep, over about 16 mm of height centred on the panel. That is the cutout
Barnaby proposed, and this is the number for it.

The panel's left edge then sits flush with the notched board edge, the fold
wraps that edge, and the apex lands 0.3 mm clear of the case wall.

### Placement, for a 1.5 mm wall

In board coordinates, board X measured from its nominal left edge:

| | |
|---|---|
| Notch | X 0 → 0.85, about 16 mm tall, centred on the panel |
| Glass | X 0.85 → 72.67 |
| Active area | X 9.78 → 69.87 |
| Image centre | X 39.82 against a board centre of 38.00 |

Re-run the table above if the wall lands anywhere other than 1.5 mm; the panel
moves with it.

### Which side the tail is on is a free choice

Rotating the panel 180° puts the tail on the right instead, and the firmware
absorbs it with a rotation in `epd_pixel()`. So pick whichever side suits the
case; nothing on the board depends on it. If it goes on the right, the 8.93 mm
border moves to the right and the image offset flips with it.

## Where this leaves the cell

Barnaby wants the 1600 mAh cell on the back at the top. The layout as drawn
puts it behind the keyboard. Both work; they cost different things.

**The ribbon can never reach the cell.** At 14.30 mm it is spent before it
clears the connector. So "short ribbon stopping before the battery" is not a
choice to make — it is the only thing the part can do. Which is just as well,
because running a 0.3 mm FPC under a pouch cell is a bad idea in any design:
the cell's case is soft aluminium laminate, it grows over its life, and the
board flexes. That is an abrasion path to an internal short, and an internal
short in a LiPo is a fire. Nothing goes under the cell.

### What actually fits up there

The top of the back is bounded by the USB-C receptacle, which reaches 8.83 mm
into the board, and by the keyboard, which starts at board Y 59. That leaves a
bay **about 49 mm tall**, full width apart from the FPC connector in the
left 10 mm.

A 1600 mAh cell at 5 mm thick is about 50 × 60 mm — a 505060. Turned on its
side it is 60 wide × 50 tall, and 50 does not fit in 49. It misses by a
millimetre, which is the kind of miss that eats a week.

Three ways out, in the order I would try them:

1. **Let the cell run past Y 59 into the keyboard region.** Nothing is on the
   back there — that is the whole reason the bay was put there in the first
   place. A cell sitting at Y 10–70 is still "at the top" in any sense that
   matters for balance, and it fits with room to spare.
2. **Go thicker rather than wider.** There are no keycaps above the display, so
   the back cavity at the top can be deeper than it can be behind the
   keyboard. A 6 mm cell in 45 × 55 mm is about the same 1600 mAh. Whether
   6 mm is there is a question for the case model, not for me.
3. **Accept about 1400 mAh** in a 5 × 48 × 60 cell. On the earlier estimate
   that is roughly 13 months rather than 15, which is not a real loss.

### What moving the cell up costs

The bay at the top of the back is currently the electronics bay: the FPC
connector, the panel's booster, the buck-boost, the charger and the fuel
gauge. Give it to the cell and all of that has to go behind the keyboard —
except the FPC connector and the panel's booster, which are pinned to the top
left by the tail length above and cannot move at all.

That is workable. The module's antenna has to overhang a board edge and the
bottom edge does that as well as the top. But it inverts the layout plan in
`docs/pcb-process.md`, and it means components behind the keys, which then
need a spacer so that pressing a key does not load them.

The one thing that gets **better**: the charger sits next to USB-C at the top
edge, and with the cell at the top the charge current no longer runs the
length of the board.
