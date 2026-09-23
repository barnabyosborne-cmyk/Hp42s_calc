# Mounting the panel, and where the cell can go

Every number here is off Good Display's *GDEY0266T90 Specification* (rev
2021/10/12), mechanical drawing on page 5, except where it says otherwise.
Measure the physical panel before committing the board — the drawing gives the
tail length to ±0.3 mm and does not say unambiguously which edge of the glass
it is measured from.

**The Pi Hut's panel is the same panel.** Barnaby found a
`ZJY296152-0266EAAMFGN` (Zhengzhou Zhongjingyuan, spec rev 1.1, 16 Nov 2022)
he can buy locally, and it is a drop-in: SSD1680, 296 × 152, 30.704 × 60.088
active area, 36.30 × 71.82 × 1.0 glass, 14.30 mm tail, 12.50 mm wide, 0.30
thick, 24 contacts at 0.5 mm over an 11.50 mm span, and the same 24-pin
assignment from NC/GDR/RESE through to VCOM. The application circuit on its
page 28 is the same one in `elec/src/display.ato`, down to the 2.2 Ω sense
resistor, the MBR0530s, the Si1304BDL and the 47 µH inductor. Both are the
same OEM glass on the same `FPC-A003` flex, which is why the numbers agree to
the third decimal. Nothing on the board or in the firmware changes.

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

### Which face the contacts are on, and what it costs

**The contacts are on the panel's viewing face.** Two independent checks say
so. The `ZJY296152` drawing's side view labels *contact side* on the left-hand
face, which in third-angle projection — side view to the right of the front
view — is the front of the module. And Barnaby laid the physical panel face up
on 23 September 2026 and photographed it: the gold fingers are on top.

That settles the connector, and not the way the board was drawn. The panel
sits on the FRONT of the board with its viewing face pointing away from the
board, so its contacts point away from the board too. The half-turn around the
left edge carries that straight through: on the back they still face away from
the board. So the contacts present themselves to the **top** of whatever is
mounted there.

**The connector therefore has to be top contact.** It was a Hirose
FH12-24S-0.5SH, which is bottom contact — Hirose's own series page says
"0.5mm Pitch, Height 2.0mm Bottom Contact, Front Flip". A bottom-contact part
clamps the flex's board-facing side, which here is the bare backing. It would
have held the flex perfectly well and connected nothing.

It is now an **Amphenol F32Q-1A7H1-11024**: top contact, 0.5 mm pitch, 24 way,
2.00 mm high, 0.5 A, right-angle SMT ZIF. Same height as the FH12, 1.2 mm
shallower front to back. The **F32R** is the identical shell with bottom
contacts, so the letter matters when ordering.

There is no way to fold round this. A Z-fold before the edge would flip the
flex over, but the tail has 14.30 mm in it and the edge wrap already spends
3.30 of that; there is not another fold's worth left.

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
connector. **So the FPC connector goes on the back with its pad row about 7 mm in from
the notched edge**, which is where the last 3 mm of flex lands. That is a firm
constraint, not a preference: there is no slack to move it. The connector body
can extend as far right as it likes.

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
| **1.2 mm** | **2.55 mm from the case face** | **0.55 mm** | **1.52 mm** |
| 1.5 mm | 2.85 | 0.85 | 1.82 mm |
| 2.0 mm | 3.35 | 1.35 | 2.32 mm |
| 2.5 mm | 3.85 | 1.85 | 2.82 mm |

**Barnaby's decision, 2026-09-20: the wall is 1.2 mm**, so the top row is the
one that is built. The wall thickness on that one side is the whole lever —
everything else in the sum is fixed by the panel and the board.

### Widening the case does not earn its keep

Barnaby offered to grow the case to 81 or 82 mm. It does help, at exactly
0.5 mm of centring per millimetre of case, because half the extra width lands
on each side while the left-hand stack stays put:

| case | image off centre | left bezel | right bezel |
|---|---|---|---|
| 80 mm | 1.52 mm | 11.48 | 8.43 |
| 81 mm | 1.02 mm | 11.48 | 9.43 |
| 82 mm | 0.52 mm | 11.48 | 10.43 |
| 83 mm | 0.02 mm | 11.48 | 11.43 |

So 83 mm would put the image dead centre. It would also stop the thing being
an HP-42S, which is the point of the project — the 148 × 80 × 15 mm case is a
decision made deliberately on 18 September and this is not a good enough
reason to reopen it. 1.5 mm is a real asymmetry but it is 1.5 mm.

**Barnaby's decision, 2026-09-20: the case stays 80 mm, and the aperture is
centred.** The image is masked in software to suit — see "The visible window"
below.

## The visible window

A centred aperture masks the panel unequally, because the active area is not
centred behind it. The widest centred aperture that stays inside the active
area is **57.04 mm**, against the active area's own 60.088 mm.

The firmware assumes **56.00 mm**, which runs case X 12.00 → 68.00 and leaves
0.52 mm of active area behind the case on the left and 3.57 mm on the right.
That is deliberately a millimetre inside the 57.04 limit: the left-hand margin
is the thin one, and if the aperture drifts left you start looking at the
panel's border rather than its ink.

In panel pixels that is columns **3 to 277** — 275 of 296, with 3 hidden on
the left and 18 on the right. `firmware/main/epd.h` carries it as
`EPD_VIEW_X` and `EPD_VIEW_W`, and `shell_blitter` drops anything that falls
outside rather than clipping it, so a glyph is either whole or absent.

**The cost is one character column**: 23 instead of 24, because 24 needs
286 pixels and we have 275. The original HP-42S showed 22, and Plus42's floor
is 22, so 23 is comfortable. Working in `docs/character-size.md`.

**Vertically nothing is lost.** The active area *is* centred on its own glass
across the short axis, 2.798 mm either side, so a centred aperture masks
nothing and all 152 rows survive.

If the aperture ends up a different width, the two constants in `epd.h` are
where it lives, and the column count follows from
`(cols × 6 − 1) × 2 ≤ EPD_VIEW_W`.

### The notch

The board is inset 2 mm from the case face all round, so with any wall of
1.35 mm or more **the board reaches the wall and there is nowhere for the fold
to go**. It needs a local notch in the board's left edge, `wall − 0.65` mm
deep, over about 16 mm of height centred on the panel. That is the cutout
Barnaby proposed, and this is the number for it.

The panel's left edge then sits flush with the notched board edge, the fold
wraps that edge, and the apex lands 0.3 mm clear of the case wall.

### Placement, as built

Board coordinates, X from the board's nominal left edge, Y down from its top.
`tools/place_keypad.py` now carries all of this and will draw it.

**Every Y moved 6 mm down on 21 September 2026**, when Barnaby chose a 14 mm
top bezel over the 8 mm this had been drawn at. Nothing in X changed, and
nothing about the fold or the centring changed — the panel simply sits lower
on the board. See `docs/top-edge.md`.

| | |
|---|---|
| Notch | X 0 → 0.55, Y 22.15 → 38.15 (16 mm, centred on the tail) |
| Glass | X 0.55 → 72.37, Y 12.00 → 48.30 |
| Active area | X 9.48 → 69.57, Y 14.80 → 45.50 |
| Image centre | X 39.52 against a board centre of 38.00 |
| Tail, unfolded | X −13.75 → 0.55, Y 23.90 → 36.40 |
| Fold apex | X −0.50, which is 0.30 mm clear of the case wall |
| Back leg ends | X 10.50 |
| FPC connector | origin X 9.75, Y 30.15, 270°, on the back, mouth facing the left edge |
| Connector body | X 7.50 → 10.50, courtyard X 5.80 → 12.50, Y 20.00 → 40.30 |
| Solder pad row | X 6.85, pin 1 at Y 24.40, pin 24 at Y 35.90 |

The connector is an Amphenol F32Q-1A7H1-11024. Its body is 3.00 mm deep, and
the back wall of that body goes at X 10.50 — where the flex ends — so the flex
bottoms out against it and its own 3.00 mm of exposed finger fills the body
exactly. Wherever inside that body the contact point actually is, it is on
copper. The solder pads stand 0.65 mm proud of the mouth and land at X 6.85.

**Corrected 23 September 2026.** The board file had this at 90° rather than
270°, which is a single error that showed up twice: the mouth pointed right,
away from the fold, with the flex arriving at the closed end of the connector;
and the pin order ran backwards. Both are fixed by the one turn.

The pin order, from first principles: on the panel's own front view the tail
leaves the bottom edge with pin 1 at the left. Mounted landscape with the tail
to the left, that is a quarter turn clockwise, which puts pin 1 at the top of
the board. The fold is about the board's left edge, a vertical axis, so it
mirrors X and leaves Y alone. Pin 1 therefore arrives at Y 24.40 and pin 24 at
Y 35.90, which is what 270° gives.

The cost of turning it round is that the body now runs right, into the battery
bay, as far as X 12.50. See below.

There is still 3.63 mm of board to the right of the glass, so nothing on that
side is tight.

### Which side the tail is on is a free choice

Rotating the panel 180° puts the tail on the right instead, and the firmware
absorbs it with a rotation in `epd_pixel()`. So pick whichever side suits the
case; nothing on the board depends on it. If it goes on the right, the 8.93 mm
border moves to the right and the image offset flips with it.

## Where this leaves the cell

**Settled 2026-09-21: the cell goes on the back**, at the top, which is where
Barnaby asked for it on 2026-09-20. The layout as drawn had it behind the
keyboard. What that costs is below, and the short version is that the top of
the back is currently the electronics bay, so the electronics move.

**Settled the same day: the bezel went to 14 mm and the six top-edge parts
moved to the front**, which is what makes the cell fit. The bay used to be
about 49 mm tall because the USB-C receptacle reached 8.83 mm into the board
from the top edge, against a 1600 mAh cell that wants 50. With the receptacle
on the front the bay is about 54 mm — 54 rather than 57 because the
receptacle's through-hole shield legs now leave their fillets on the back, and
the cell has to stay clear of board Y 0 to 5 in that region. See
`docs/top-edge.md`.

**The ribbon can never reach the cell.** At 14.30 mm it is spent before it
clears the connector. So "short ribbon stopping before the battery" is not a
choice to make — it is the only thing the part can do. Which is just as well,
because running a 0.3 mm FPC under a pouch cell is a bad idea in any design:
the cell's case is soft aluminium laminate, it grows over its life, and the
board flexes. That is an abrasion path to an internal short, and an internal
short in a LiPo is a fire. Nothing goes under the cell.

### What actually fits up there

**As the board now stands**, the top of the back is bounded by the USB-C
receptacle's through-hole shield fillets, which land in about board Y 0 to 5,
and by the keyboard, which starts at board Y 59. That leaves a bay **about
54 mm tall**, full width apart from the FPC connector in the left 13 mm. A
50 × 60 × 5 mm cell fits, and the three ways out below are no longer needed —
they are kept because they are the fallbacks if the cell you can actually buy
is a different shape.

**The cell's X moved on 23 September 2026.** It was drawn at X 10 → 70. The
FPC connector, turned the right way round, reaches X 12.50, so the cell now
starts at **X 14** and runs to **X 74** — still 60 mm, with 1.5 mm to the
connector and 2 mm to the board's right edge. `check_placement.py` has the bay
starting at X 13 to match. This is a number for the case model: the cell
pocket is not centred on the board.

What follows was written when the six top-edge parts were on the back and the
bay was 49 mm:

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
