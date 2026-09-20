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
-1.03  front leg, glass edge out to the fold
-3.30  the half-turn
------
 9.97  back leg
```

Ten millimetres of back leg, of which the last 4 mm sits inside the connector.
**So the FPC connector goes on the back with its contacts starting about 4 mm
in from the left edge, and its far end no more than 10 mm in.** That is a firm
constraint, not a preference: there is no slack to move it.

A 1.05 mm radius on a 0.3 mm FPC is tight — about 3.5× thickness. It is
normal practice for this class of part, but it is a fold you make **once**, on
assembly, not something that should flex in service. Two things help and both
are free:

- Route the board edge under the fold with a radius rather than leaving the
  square milled edge, and put a strip of Kapton over it. The failure mode is
  the board edge sawing through the FPC, not the bend itself.
- Do not let the case clamp the fold. It wants about 1.5 mm of air.

## The panel is not centred on its own glass

This is the part that catches people. Across the long axis the active area sits
**8.93 mm from the tail edge and 2.80 mm from the far edge**. (Across the short
axis it is centred, 2.798 mm each side.) So there are two ways to place the
panel and they are not the same:

| | Glass centred on the board | Image centred on the case |
|---|---|---|
| Glass spans | X 2.09 – 73.91 | X −0.97 – 70.85 |
| Image centre | X 41.06, i.e. **3.1 mm right of centre** | X 38.0 ✓ |
| Glass overhangs the board | no | 0.97 mm on the left |
| The fold | comfortable, 2 mm of air to the case wall | lands hard against the case wall |

3.1 mm of offset on a 60 mm image inside an 80 mm case is visible; you would
see it every time you picked the thing up. **Centre the image**, let the glass
overhang the board by 1 mm on the left, and put a relief pocket in the case
wall for the fold. Barnaby is printing the case, so the pocket is free.

The 1 mm overhang is not a structural problem — the glass is supported by the
board across the other 70 mm of its width.

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
