# Keypad geometry

Barnaby measured a real HP-42S on 19 September 2026. Everything here is his
figures, not a reconstruction. `tools/place_keypad.py` is generated from the
same numbers, so the board and this table cannot drift apart.

## The grid

| | |
|---|---|
| Case | 80 × 148 mm |
| Board | 76 × 144 mm, inset 2 mm all round |
| Keyboard area | 70 × 78 mm, datum 5 mm from the left, 9 mm up from the bottom |
| Row pitch | 12.0 mm, seven rows |
| Keycap height | 6.0 mm throughout |

The columns are **not** a single pitch, which is the thing a uniform grid gets
wrong:

- **Rows 1–3** — six columns at **12.5 mm** pitch, caps 7.5 mm wide.
  Centres 8.75, 21.25, 33.75, 46.25, 58.75, 71.25.
- **Rows 4–7** — the left column stays at 8.75 with a 7.5 mm cap, then four
  numeric columns at **15.0 mm** pitch with 10 mm caps. Centres 25, 40, 55, 70.

ENTER is a 20 × 6 mm cap centred at X 15 on row 3, covering the first two
column positions, with two domes under it wired in parallel.

## Coordinates

Barnaby measures X from the left edge of the case and Y **up** from the
bottom. KiCad measures Y **down** from the board origin. With the 2 mm inset:

```
x_board = x_case - 2
y_board = 146 - y_case
```

So the keyboard occupies board Y 59–137, leaving **59 mm above it** for the
bezel and display and a **7 mm chin** below.

## What this changes

The earlier plan assumed a uniform 11.8 × 12.0 mm grid and an 84 mm keyboard
block. The row pitch was right. The columns were not, and the keyboard is
78 mm tall rather than 84, which hands back about 12 mm of vertical space
above the display. Panel choice does not change: the 2.66" is limited by the
80 mm case **width**, not by height.

## Clearances that follow

Snaptron's own pad drawing and dimension table arrived 2026-09-19, so these
are measured rather than derived. The ring is an octagon a little wider than
the circle the dome's four legs stand on, with the legs contacting just inside
their tips.

**The pad takes either supplier's dome.** Snaptron sell direct and by quote;
Keystone's equivalents are stocked by the usual distributors:

| | tip to tip | leg circle | force | height |
|---|---|---|---|---|
| Snaptron F08210 | 8.50 mm | — | 210 gf | 0.48 mm |
| Keystone 5134TR | 8.40 mm | 8.00 mm | 280 g | 0.50 mm |
| Snaptron F10260 | 10.00 mm | — | 260 gf | 0.56 mm |
| Keystone 5154TR | 10.00 mm | 9.50 mm | 280 g | 0.55 mm |

Keystone's 9.50 mm leg circle lands just outside the ring Snaptron's table
asks for, which is the sort of half-on-the-pad contact that makes a key feel
intermittent, so the ring's outer flat now goes to whichever is larger: the
Snaptron figure, or the leg circle plus 0.25 mm. Both sites grew a little and
both are still clear.

| | 8.5 mm site | 10 mm site |
|---|---|---|
| Ring, across the flats | 8.50 mm | 10.00 mm |
| Ring, across the corners | 9.20 mm | 10.82 mm |
| Centre pad | 3.48 mm | 4.08 mm |
| Vertical, 12.0 mm pitch | 3.50 mm | **2.00 mm** |
| Horizontal, 12.5 mm pitch | 4.00 mm | — |
| Horizontal, 15.0 mm pitch | — | 5.00 mm |
| Mask web / courtyard, vertical | 3.00 mm | **1.50 mm** |

Mask and courtyard are octagons following the ring rather than circles round
it. A circle wastes 0.8 mm on every flat, and the flats are exactly where the
neighbouring dome is: on the 12.0 mm row pitch that is the difference between
1.5 mm of mask web and 0.7 mm.

Still roomier than the guessed geometry this replaced, which had the numeric
block at 1.50 mm between neighbouring domes.

**The centre pad now escapes on the front layer.** Snaptron's ring is a C
rather than a closed annulus: there is a slot in one side, and the centre pad
carries a 1.55 mm tab out through it with 0.92 to 1.10 mm of clearance either
side. Our footprints put that slot on the +x side, so every centre net leaves
sideways, where the pitch is 12.5 or 15 mm and there is 3 mm or more of room.
That removes the via-inside-the-dome-cavity the earlier plan needed, which
was its weakest part: a via under a dome has to be filled and planarised or
the dome sits on a bump.

The ring itself is a large pad and can be met from any direction, so the row
nets are the easy half of the problem.

The outermost column is close to the board edge — `SW1` and friends sit at
board X 6.75, so the 8.5 mm site's mask opening stops 2.25 mm short of it. Fine for
fab, and the escape tab points inboard.

Snaptron also suggest a 0.89 mm via inside the site, F1 in the centre pad or
F2 in the ring, which doubles as the cavity's air vent. We do not need either
for routing. `tools/gen_dome_footprints.py` has a `VENT` flag for the day the
domes arrive loose rather than in a Peel-N-Place array, which vents through
its own polyester layer.

## Every key

Case coordinates are Barnaby's. Board coordinates are what the script uses.

| Ref | Key | Case X | Case Y | Board X | Board Y | Keycap | Dome |
|---|---|---|---|---|---|---|---|
| `SW1` | Σ+ | 8.75 | 84.0 | 6.75 | 62 | 7.5 × 6 | F08210 |
| `SW2` | 1/x | 21.25 | 84.0 | 19.25 | 62 | 7.5 × 6 | F08210 |
| `SW3` | √x | 33.75 | 84.0 | 31.75 | 62 | 7.5 × 6 | F08210 |
| `SW4` | LOG | 46.25 | 84.0 | 44.25 | 62 | 7.5 × 6 | F08210 |
| `SW5` | LN | 58.75 | 84.0 | 56.75 | 62 | 7.5 × 6 | F08210 |
| `SW6` | XEQ | 71.25 | 84.0 | 69.25 | 62 | 7.5 × 6 | F08210 |
| `SW7` | STO | 8.75 | 72.0 | 6.75 | 74 | 7.5 × 6 | F08210 |
| `SW8` | RCL | 21.25 | 72.0 | 19.25 | 74 | 7.5 × 6 | F08210 |
| `SW9` | R↓ | 33.75 | 72.0 | 31.75 | 74 | 7.5 × 6 | F08210 |
| `SW10` | SIN | 46.25 | 72.0 | 44.25 | 74 | 7.5 × 6 | F08210 |
| `SW11` | COS | 58.75 | 72.0 | 56.75 | 74 | 7.5 × 6 | F08210 |
| `SW12` | TAN | 71.25 | 72.0 | 69.25 | 74 | 7.5 × 6 | F08210 |
| `SW13` | ENTER | 8.75 | 60.0 | 6.75 | 86 | 7.5 × 6 | F08210 |
| `SW38` | ENTER | 21.25 | 60.0 | 19.25 | 86 | 7.5 × 6 | F08210 |
| `SW14` | x↔y | 33.75 | 60.0 | 31.75 | 86 | 7.5 × 6 | F08210 |
| `SW15` | +/− | 46.25 | 60.0 | 44.25 | 86 | 7.5 × 6 | F08210 |
| `SW16` | E | 58.75 | 60.0 | 56.75 | 86 | 7.5 × 6 | F08210 |
| `SW17` | ← | 71.25 | 60.0 | 69.25 | 86 | 7.5 × 6 | F08210 |
| `SW18` | ▲ | 8.75 | 48.0 | 6.75 | 98 | 7.5 × 6 | F08210 |
| `SW19` | 7 | 25.0 | 48.0 | 23 | 98 | 10 × 6 | F10260 |
| `SW20` | 8 | 40.0 | 48.0 | 38 | 98 | 10 × 6 | F10260 |
| `SW21` | 9 | 55.0 | 48.0 | 53 | 98 | 10 × 6 | F10260 |
| `SW22` | ÷ | 70.0 | 48.0 | 68 | 98 | 10 × 6 | F10260 |
| `SW23` | ▼ | 8.75 | 36.0 | 6.75 | 110 | 7.5 × 6 | F08210 |
| `SW24` | 4 | 25.0 | 36.0 | 23 | 110 | 10 × 6 | F10260 |
| `SW25` | 5 | 40.0 | 36.0 | 38 | 110 | 10 × 6 | F10260 |
| `SW26` | 6 | 55.0 | 36.0 | 53 | 110 | 10 × 6 | F10260 |
| `SW27` | × | 70.0 | 36.0 | 68 | 110 | 10 × 6 | F10260 |
| `SW28` | SHIFT | 8.75 | 24.0 | 6.75 | 122 | 7.5 × 6 | F08210 |
| `SW29` | 1 | 25.0 | 24.0 | 23 | 122 | 10 × 6 | F10260 |
| `SW30` | 2 | 40.0 | 24.0 | 38 | 122 | 10 × 6 | F10260 |
| `SW31` | 3 | 55.0 | 24.0 | 53 | 122 | 10 × 6 | F10260 |
| `SW32` | − | 70.0 | 24.0 | 68 | 122 | 10 × 6 | F10260 |
| `SW33` | EXIT/ON | 8.75 | 12.0 | 6.75 | 134 | 7.5 × 6 | F08210 |
| `SW34` | 0 | 25.0 | 12.0 | 23 | 134 | 10 × 6 | F10260 |
| `SW35` | . | 40.0 | 12.0 | 38 | 134 | 10 × 6 | F10260 |
| `SW36` | R/S | 55.0 | 12.0 | 53 | 134 | 10 × 6 | F10260 |
| `SW37` | + | 70.0 | 12.0 | 68 | 134 | 10 × 6 | F10260 |
