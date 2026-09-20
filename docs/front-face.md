# The front face: metal plate, window, frontlight

Barnaby raised three things on 20 September 2026: a silk-screened thin metal
plate as the keyboard surround and display bezel, a window over the panel, and
— if the window were thick enough — edge-lit LEDs to make it a frontlight.

Short answers: **the plate is the best idea of the three and has a precedent**;
**a separate window is probably a mistake**; **the frontlight is real, and if
you build it the light guide becomes the window**, so the second and third
ideas collapse into one part.

The front stack-up is not the constraint on any of it. The 15 mm case with
1.2 mm shells leaves 12.6 mm inside, and the deepest arrangement — a 6 mm cell
at the top of the back, the board, the panel, its adhesive, a 2 mm light guide
and an air gap — comes to 11.0 mm. The keyboard side is looser still.

## The metal plate

This is how the DM42 is built, and how the Voyager series was built before it,
so it is a well-trodden path rather than an experiment.

**Process: photochemical etching, not laser cutting.** 0.5 mm stainless, etched
and then screen printed with epoxy ink. Etching gives a square, burr-free edge
and holds ±0.05 mm on a part this size; a laser leaves a heat-affected edge and
a taper you will see on a 0.5 mm sheet at reading distance. It is also the
cheaper process once there are 37 holes in the part.

The plate is strong enough easily. Allowing 0.25 mm of clearance round each
keycap:

| | hole | web to the next hole |
|---|---|---|
| function rows, 7.5 mm caps | 8.00 × 6.50 | 4.50 mm |
| numeric block, 10 mm caps | 10.50 × 6.50 | 4.50 mm |
| every row, vertically | | 5.50 mm |
| ENTER to `x↔y` | 20.50 × 6.50 | 3.25 mm |

3.25 mm is the tightest and that is still stiff in 0.5 mm stainless.

Three things follow that are not obvious:

- **The keycaps need a lip wider than their hole.** That is what retains them:
  the flange sits under the plate and the cap cannot fall out. Travel is the
  dome's 0.48–0.55 mm, so the flange wants about 1 mm of clearance beneath the
  plate before anything bottoms out.
- **Bond the plate to ground.** A metal plate the user touches is an ESD entry
  path straight onto the board. One bond, near the USB-C shield's ground
  stitch rather than near the module, gives the charge somewhere to go that is
  not through the MCU. A pad and a spring finger or a screw boss is enough.
- **The plate must not reach the antenna.** The module sits at the bottom edge
  with its antenna overhanging the board outline, so it is in the bottom few
  millimetres of the case. Steel directly over it will detune it badly. **Stop
  the plate at the keyboard's bottom edge, case Y 9**, and leave the 9 mm chin
  printed — which is where the original's badge goes anyway. Even then, check
  BLE range on the first build with the plate on and off. This one is a
  measurement, not a calculation.

One thing the plate buys for free: **the display aperture gets a crisp etched
edge** instead of a printed one. That is the same aperture worked out in
`docs/display-mounting.md`, 56.00 mm wide and centred on the case, and it will
look considerably better in steel. It does not buy back the 24th character
column — that needs 58.06 mm and the active area only allows 57.04 — so the
display stays 23 × 6 either way.

## The window

**On its own, I would not.** The panel already has a hard-coat antiglare
surface, so a window adds protection you mostly have and takes away contrast
you cannot spare.

E-paper is reflective: light goes in through the front and comes back out the
same way. A window with an air gap behind it adds two more glass-to-air
interfaces, each reflecting about 4%, and that shows up as veiling glare on a
display whose contrast ratio is only about 10:1 to begin with. It is not a
rounding error on a reflective display the way it would be on a backlit one.

If a window goes on anyway, **optically bond it** — an optically clear
adhesive sheet, the way e-readers are assembled — or at minimum use an
anti-reflective coated one. Do not leave a plain air gap.

## The frontlight

This is a real technique, not a hopeful one: every Kindle Paperwhite and Kobo
has exactly this, an edge-lit guide **in front of** the e-paper rather than a
backlight behind it, which reflective displays cannot have.

### What makes it work, and what will bite

A plain slab of polycarbonate will not do it. Light injected at the edge
totally-internally-reflects and comes out of the far edge, not downwards. It
needs an **extraction pattern** on the top face — dots, laser-etched or
printed, **graded in density with distance from the LEDs** so the near end is
not a hot spot and the far end is not dark. That grading is the whole craft of
it, and getting it even is iterative. A diode laser on acrylic does the job;
expect to make several before one looks right.

Thicker is *not* better, which is the one place the original idea needs
turning round. Commercial guides are 0.3–0.5 mm. Thick means light travels
further before extraction and the module gets deeper. For something you will
make yourself, **1.5–2 mm** is the sensible compromise: stiff enough to handle
and to couple LEDs into, thin enough to extract evenly.

The guide will haze the display slightly even when off. That is the honest
trade: some daylight contrast for night readability.

**The guide is the window.** It is a sheet of polycarbonate or acrylic lying on
the panel, so it protects the glass and there is no reason to have a separate
window as well. Bond it to the panel with OCA for the same reason as above.

### Where the LEDs go — the awkward part

The guide lies on top of the panel, so its edge is 1.2 mm or more above the
board, while a side-view LED soldered to the board emits about 0.5 mm above
it. They do not line up, and that misalignment is most of the light.

There are 16.7 mm of free board on the **front**, below the panel and above
the keyboard, which is the natural place. But rather than fight the height in
copper, **put a two-pin pad pair there and let the LEDs live wherever the
optics want them** — on a scrap of FPC or a thin sub-board glued to the right
height under the front shell. That decouples the mechanical problem, which is
Barnaby's to solve in CAD, from the electrical one, which is easy.

### The electrical side, which is easy

Four white side-view LEDs, forward voltage about 3.0 V. They cannot run from
the 3.3 V rail — there is no headroom — so they run from `SYS`, which is the
cell, 3.0 to 4.2 V.

The obvious problem is that a plain resistor gives three times the current at
full charge as at empty:

| `SYS` | per LED through 100 Ω | four LEDs |
|---|---|---|
| 4.2 V | 12.0 mA | 48 mA |
| 3.7 V | 7.0 mA | 28 mA |
| 3.4 V | 4.0 mA | 16 mA |

**The fuel gauge already solves this.** The MAX17048 reports cell voltage over
I²C, so the firmware scales the PWM duty to hold the brightness constant as
the cell falls. That turns the droop into a software problem and saves a boost
converter — which matters, because a boost would be a second fast switching
node on a board where the only one is already kept deliberately far from the
panel's SPI.

So the whole thing is seven parts: four LEDs, four resistors, an N-channel FET
(the same 2N7002 already used for the IR emitter), a gate resistor and a
pull-down. One GPIO for PWM — `GPIO26`, `41` and `42` are free, and `GPIO40`
is spoken for as the sounder's antiphase pin.

### What it costs to run

20 mA is about 80 hours of light from a 1600 mAh cell. Against a design that
otherwise claims 15 months, that is not a rounding error: **it has to default
off and be a deliberate act to turn on**, the way an e-reader's is. Held at
low brightness it is much less, and nobody leaves a calculator's reading light
on all day.

## What I would build

1. **The plate, now.** It is the lowest-risk, highest-return item on this list,
   and the aperture is already specified. The only board change it asks for is
   a ground bond pad.
2. **No separate window.**
3. **The frontlight as an option.** Seven parts and one GPIO is cheap enough
   that leaving room for it costs nothing, and the light guide is the part
   that might not come out well — which is a question of laser time, not of
   board respins. Say the word and I will add the footprints; they can be
   fitted or not on a per-unit basis.
