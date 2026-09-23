# Board thickness, and flex under the keyboard

Barnaby asked on 23 September 2026 whether 1.0 mm was too thin under 37 dome
switches, and whether the case should grow to take a 1.6 mm board.

**Short answer: go to 1.6 mm, and the case does not need to grow.** The 0.6 mm
comes out of slack the stack-up already has. But thickness is the weaker of the
two levers, and the case's support geometry is the stronger one, so do both.

---

## Why it matters

A metal dome works by snapping through. It gives you a crisp click because the
force falls off sharply once it goes over centre. Anything compliant in series
with the dome — a flexing board, a soft keycap, a springy faceplate — eats part
of the travel and smears that force curve out. The click goes from *snap* to
*squash*, and the key feels dead even though it works electrically.

The domes on this board (`docs/keypad-geometry.md`):

| | force | travel |
|---|---|---|
| Snaptron F08210, 8.5 mm | 210 gf (2.06 N) | 0.48 mm |
| Keystone 5134TR, 8.4 mm | 280 g (2.75 N) | 0.50 mm |
| Snaptron F10260, 10 mm | 260 gf (2.55 N) | 0.56 mm |
| Keystone 5154TR, 10 mm | 280 g (2.75 N) | 0.55 mm |

So roughly **0.5 mm of travel** and **2.1 to 2.8 N to snap it**. Nobody presses
a key with exactly the snap force; a firm press is more like 5 N. Board
deflection wants to stay under about 10% of the dome's travel, so **under
0.05 mm**, and preferably a good deal under.

---

## The numbers

Flexural rigidity goes as the cube of thickness:

```
D = E·t³ / 12(1 − ν²)
```

with E = 20 GPa (bare FR4 laminate, the conservative end of 18–24) and
ν = 0.16:

| | D |
|---|---|
| 1.0 mm | 1.71 N·m |
| 1.6 mm | 7.01 N·m |

**1.6 mm is 4.10× stiffer.** That is the whole of the thickness argument.

Deflection under a point load on a rectangular plate goes as `W·b²/D`, where
`b` is the short unsupported span. Roark's coefficients for a plate simply
supported on all four edges, load at the centre:

**At the snap force (2.75 N, the stiffest dome):**

| How the case supports the board | 1.0 mm | 1.6 mm |
|---|---|---|
| perimeter only — 76 mm span | **0.152 mm** | 0.037 mm |
| one support line down the middle — 38 mm | 0.038 mm | 0.009 mm |
| posts on a ~25 mm grid | 0.017 mm | 0.004 mm |
| ribs between key columns — ~15 mm | 0.006 mm | 0.001 mm |

**At a firm press (5 N):**

| | 1.0 mm | 1.6 mm |
|---|---|---|
| perimeter only | **0.276 mm** | 0.067 mm |
| one support line | 0.070 mm | 0.017 mm |
| ~25 mm grid | 0.030 mm | 0.007 mm |
| ribs between columns | 0.011 mm | 0.003 mm |

The top-left cell is the answer to the question. **A 1.0 mm board supported
only at its edges moves 0.28 mm under a firm press, against 0.5 mm of dome
travel.** Over half the travel would be going into bending the board rather
than snapping the dome. It would feel exactly as bad as Barnaby suspected.

### What the model assumes

- **Simply supported, not clamped.** A real case ledge is somewhere between the
  two, and a clamped edge deflects roughly 2.5× less, so these numbers are
  pessimistic.
- **Bare laminate at 20 GPa.** Four copper layers with large pours stiffen it,
  the outer two significantly, so again pessimistic.
- **Load at the centre of the span.** Keys near a supported edge move less.
- It ignores the components on the back, which act as local stiffeners where
  they happen to be.

The absolute numbers are therefore an upper bound. The *ratios* are solid, and
the ratios are what decide this.

---

## Support geometry is the stronger lever

Deflection goes as span **squared**. Halving the unsupported span is 4×, which
is the same as the entire 1.0 → 1.6 mm change, and it costs nothing in a case
that is being printed anyway.

Read down the columns rather than across: **one support line under the middle
of the keyboard does as much for a 1.0 mm board as going to 1.6 mm does for an
unsupported one.** Doing both leaves the board effectively rigid, and that is
what to aim for.

### The conflict to plan around

The 14 mm bezel decision on 21 September 2026 put the cell at the top of the
back and evicted the electronics to **behind the keyboard** — which is exactly
where the support posts want to be. Posts and parts are now competing for the
same real estate.

This is worth knowing *during* placement rather than after it. When placing the
back-side parts in step 7 of `docs/layout-walkthrough.md`, leave corridors
clear for the case to bear on — the gaps between key columns are the natural
place, since nothing routes there on the front anyway. Perfection is not
needed; three or four bearing points spread through the keyboard area is the
difference between the first and second rows of the table.

---

## Why the case does not need to grow

`docs/front-face.md` already worked the vertical budget out, before this
question came up:

> The 15 mm case with 1.2 mm shells leaves 12.6 mm inside, and the deepest
> arrangement — a 6 mm cell at the top of the back, the board, the panel, its
> adhesive, a 1 mm light guide and an air gap — comes to 10.0 mm.

That is **2.6 mm of slack**, in the deepest region of the board. Spending
0.6 mm of it on the board leaves 2.0 mm. The keyboard region is looser still,
because the tallest thing there is the module at 2.4 mm rather than a 6 mm
cell.

So the case stays at **148 × 80 × 15 mm**, which is the original HP-42S size and
a decision Barnaby has already made twice.

---

## Two things that get better, not worse

**The display geometry already assumed 1.6 mm.** `docs/display-mounting.md`
derives the flex fold's radius as half of the Z separation between its two
legs, and writes that separation out as `0.5 glass + 1.6 board`, giving
**1.05 mm**. Every number downstream of it — the 3.30 mm the half-turn eats,
the 11.00 mm of back leg, where the FPC connector's pad row has to land, how
far right of centre the image ends up — follows from that radius.

In other words the panel mounting was worked out for a 1.6 mm board all along,
and the 1.0 mm in the stackup was the number that did not match. Going to
1.6 mm makes the repo self-consistent. Staying at 1.0 mm would mean redoing
that arithmetic with a 0.75 mm radius, which frees about 0.9 mm of back leg —
a small gain, but it is a change, not a saving.

**The through-hole protrusions get shorter.** The USB-C receptacle's four
shield legs and the JST cell connector are through-hole parts, and through-hole
leads are cut for a nominal 1.6 mm board. On a 1.0 mm board they stand 0.6 mm
further proud of the back — directly into the battery bay, which is the "do not
let the cell rest on four solder fillets" caveat in `docs/top-edge.md`. A
1.6 mm board takes 0.6 mm off that problem for free.

---

## What it costs

- **0.6 mm of interior depth**, from 2.6 mm of slack.
- **About 12.5 g**, over the 76 × 144 mm board. The original HP-42S is around
  170 g, so this is well inside the range where it reads as "solid" rather than
  "heavy", and arguably in the right direction for an object that is supposed
  to feel like a tool.
- **Nothing in money.** 4-layer at 1.0 mm and at 1.6 mm are the same price at
  the fabs this board would go to, and 1.6 mm is the default, which is one
  fewer thing to get wrong on the order form.

---

## Decision

**1.6 mm, four layers, case unchanged at 15 mm.** Set it in KiCad's Board Setup
→ Board Stackup → Physical Stackup, step 4a of the walkthrough.

**And plan the case to bear on the board inside the keyboard area**, not only
around the edge. That is Barnaby's part of the job, and it is worth more than
the thickness change is.
