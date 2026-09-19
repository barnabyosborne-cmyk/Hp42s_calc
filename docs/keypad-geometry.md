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

| | F08210 (8.5 mm, OD 9.00) | F10260 (10 mm, OD 10.50) |
|---|---|---|
| Vertical, 12.0 mm pitch | 3.00 mm | **1.50 mm** |
| Horizontal, 12.5 mm pitch | 3.50 mm | — |
| Horizontal, 15.0 mm pitch | — | 4.50 mm |
| Courtyard gap, vertical | 2.00 mm | **0.50 mm** |
| Solder mask web, vertical | 2.20 mm | **0.70 mm** |

Those ODs come from Snaptron's catalogue pages (2026-09-19), which give the
dome diameter tip to tip across opposite legs: 8.5 mm and 10.0 mm. The ring
covers that circle with 0.25 mm of margin, so OD is 0.5 mm larger. The
numbers above are 0.1 mm tighter than the earlier guessed ones and still
clear.

Two other figures from the same pages. The domes stand **0.48 mm** (F08210)
and **0.56 mm** (F10260) above the board unpressed, which is the clearance a
keycap plunger has to respect. The pages do not state travel; treat it as
less than the height until we have the pad drawing. Force is 210 gf and
260 gf, both plus or minus 30.

The numeric block is the tight one, and it is tight in the **row** direction.
Nothing routes between those domes on the front layer: column nets go on an
inner layer and come up into each ring with a via outside the courtyard.

The outermost column is close to the board edge too — `SW1` and friends sit at
board X 6.75, so an F08210's mask opening stops 1.85 mm short of the edge.
Fine for fab, but there is no room for a via ring on that side.

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
