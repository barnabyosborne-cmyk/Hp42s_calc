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
at the top of the back, the board, the panel, its adhesive, a 1 mm light guide
and an air gap — comes to 10.0 mm. The keyboard side is looser still.

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
- **It now has live parts underneath it at the top.** The six top-edge parts
  moved to the front of the board with the 14 mm bezel, and the tallest of
  them — the Alps buttons at 3.3 mm and the USB-C shell at 3.2 — stand in a
  bay that is about 5 mm deep, so there is roughly 1.7 mm between them and a
  plate lying against the case's inner face. That is enough, but it is not a
  lot, and it is a short rather than a scratch if the plate ever sags onto the
  USB-C shell. Either relieve the plate over that strip or make sure the case
  supports it there.
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

Barnaby brought back a second opinion on 21 September 2026 from a separate
conversation with another assistant. It is good work and it moved three things
here. What follows is the merged version; where the two answers disagreed, the
reason for the winner is given.

### The guide: 1.0 mm cast acrylic

I had said 1.5–2 mm. **1.0 mm is better and the other answer's reasoning is
the better reasoning**: below 1 mm the sheet warps under the engraving pass,
above it the parallax grows, and 1.0 mm is the thickness that matches the
profile height of the side-view LEDs you can actually buy. All three of those
are true and the third is the one I had not thought about.

Parallax is the part worth putting numbers on, because it is the cost the user
sees. A 1.0 mm sheet bonded down with about 0.175 mm of optically clear
adhesive puts 1.175 mm of plastic over the ink. Tilt the calculator and the
image slides sideways by

| tilt from normal | 1.0 mm guide | 2.0 mm guide |
|---|---|---|
| 20° | 0.28 mm (0.7 logical px) | 0.51 mm (1.3) |
| 30° | 0.42 mm (1.0 logical px) | 0.78 mm (1.9) |
| 45° | 0.63 mm (1.6 logical px) | 1.17 mm (2.9) |

A logical pixel here is `EPD_SCALE_X` = 2 device pixels, 0.406 mm. So at 1.0 mm
a normal viewing tilt costs about one pixel of float; at 2.0 mm it is two, and
characters start to look like they are swimming above the glass. That settles
it.

**Cast acrylic, not polycarbonate** — and that is a real change, because the
window idea started out as polycarbonate. A CO₂ laser at 10.6 µm cuts cast
acrylic cleanly and chars polycarbonate: yellow edges, no polish, and a
discoloured engrave. Extruded acrylic is also wrong; it engraves grey and
muddy rather than frosted white. This costs something — acrylic is more
brittle and scratches more easily than polycarbonate — but the guide sits
recessed under the etched steel bezel, which takes the handling, and it is
bonded down so it cannot flex. It is also the right optical choice
independently: every commercial light guide plate is PMMA, because
polycarbonate's higher dispersion tints a long light path yellow.

Extraction is a **density-graded dot pattern engraved on the top face**,
sparse at the injection edge and dense at the far edge. The grading is the
whole craft of it; expect to cut several before one looks even. Glowforge
settings that the other answer gave and that match what the process wants:
vector dot grid, dots 0.1 mm at the near edge growing to 0.3 mm at the far
edge, engrave at high speed and low power (of the order of speed 1000, power
10–15, 450–675 LPI) so the beam frosts rather than craters, masking removed
for the engrave, and the injection edge flame-polished afterwards. Treat those
as a starting point to bracket, not as settings.

**The guide is the window.** It is a sheet of acrylic lying on the panel, so it
protects the glass and there is no reason to have a separate window as well.

### Where the LEDs go, and how far off they are

The guide lies on top of the panel, so its edge is well above the board while
a side-view LED soldered to the board emits close to it. Now that the guide is
1.0 mm the mismatch can be stated exactly:

| | height above the board's top copper |
|---|---|
| panel adhesive | 0 → 0.1 mm |
| panel glass | 0.1 → 1.1 mm |
| guide | 1.1 → 2.1 mm, optical centre **1.6 mm** |
| a 1208 LED soldered flat to the board | centre **0.5 mm** |

1.1 mm out, which is most of the light. The fix is one small part: **a 1.0 mm
FR4 sliver lying on the main board** carrying the four LEDs. Its top surface is
then at 1.0 mm, the LED centres at 1.5 mm, and the guide's centre is at 1.6 —
0.1 mm out, which is nothing. Two pads on the main board and two short wires
connect it. That keeps the height problem in mechanical parts, where it is
cheap to iterate, and out of the main board, where it is not.

The strip of free board between the panel and the keyboard, board Y 48.3 to
59.0, is 10.7 mm deep and full width. That is where the sliver and its pads go,
injecting into the guide's bottom edge and lighting upwards across the 30.7 mm
short axis of the active area. It was 16.7 mm until the bezel went to 14 mm on
21 September 2026; 10.7 is still ample for a 4 mm sliver and the driver beside
it.

Two pieces of luck along that edge:

- The active area starts 2.798 mm in from the glass edge on this axis, so
  there is a **2.8 mm mixing zone that is already dead glass**. The near-edge
  hot spots have somewhere to blend before the first visible pixel.
- The aperture is 56.00 mm on a 60.088 mm active area, so roughly 2 mm at each
  end is already hidden behind the bezel. Four LEDs on a 15 mm pitch across a
  60 mm edge leave the corners as the dim spots, and the corners are the part
  the bezel covers.

### The LED

**Dialight 599-2Q01-147F.** White, 1208 right angle, 3.0 × 2.0 × 1.0 mm,
200 mcd typical at 20 mA, 130° viewing angle.

This is the same package and the same land pattern as the status LED already
on the board — `hp42s:Dialight_599_BiColor_1208_RA` — so the footprint is
drawn, checked and in the library already. Nothing new to generate.

The other answer suggested a Kingbright APPA3010. That series is real and is
explicitly the narrow-angle side-firing family, but the search result it was
reading was a KPA-3010EC, which is red/orange, so the white part number in it
should not be trusted without checking. It does not matter now that the
Dialight part lands on a footprint we already own.

130° sounds too wide for edge injection and is not. Light entering acrylic from
air is refracted into a cone of ±42° by Snell's law however wide it arrives, and
everything inside that cone totally-internally-reflects. So the wide part is
free, and it mixes faster and shortens the hot-spot zone at the edge.

### The drive circuit: the boost wins, and not for the stated reason

The other answer said series LEDs with a constant-current boost. I had said
four LEDs in parallel, 100 Ω each, straight off `SYS`, with the MAX17048
compensating the droop in firmware. **The boost is right and my circuit does
not work** — but the argument it gave (that series guarantees matched current)
is not the argument that kills mine. Current matching is a second-order worry
next to how crudely the extraction grading controls brightness anyway.

What kills it is the forward voltage. I had assumed 3.0 V. The real part is
**3.4 V typical, 2.9 to 3.7 V** over the bin. `SYS` is the cell, 3.0 to 4.2 V.
So at a half-empty cell there is no headroom at all, and at a low cell the
frontlight is simply off. No resistor value fixes that and no amount of
firmware compensation invents voltage. The fuel-gauge trick was a good save for
a problem that turns out not to be the problem.

So: **four LEDs in series, about 13.6 V, off a boost**. Series also collapses
four ballast resistors into one current-set resistor and makes the current
independent of the cell all the way down, which removes the firmware
compensation entirely rather than patching it.

The part is a **TPS61165**, which keeps the BOM on the same vendor as the
BQ25185, TPS63900 and TPD4E05U06 already here. 3–18 V in, up to 38 V out, so
the string is comfortably inside it; 200 mV feedback reference at 2%, so the
current-set resistor is 0.2 V ÷ I; 1.2 MHz; SOT-23-6 or a 2 × 2 mm WSON; PWM
brightness straight onto `CTRL` from a GPIO; and open-LED protection, which
matters more than usual because the LEDs are on a separate sliver at the end of
two wires.

| | current set | string | from the cell at 3.7 V | from 1600 mAh |
|---|---|---|---|---|
| reading level | 5 mA, R = 40 Ω | 12.4 V | ≈ 20 mA | ≈ 80 h |
| full | 20 mA, R = 10 Ω | 13.8 V | ≈ 88 mA | ≈ 18 h |

So the 80 hours quoted earlier is the dim setting, which is the one anybody
actually reads by, and full brightness is a 20-hour proposition. Either way it
**defaults off and turning it on is a deliberate act**, the way an e-reader's
is, against a design that otherwise claims 15 months.

The cost of conceding the boost is a second switching node on a board that
works hard to keep the first one — the panel's own DC-DC and its 47 µH
inductor — away from the SPI. Two things contain it: the frontlight switcher
sits at the right-hand end of the Y 42.3–59.0 strip, as far from the FPC
connector and the panel's converter at X 7–20 as the board allows, and it only
runs when the user has asked for light, which is not while the panel is being
refreshed in the dark.

### As drawn

This is now in the schematic, in `elec/src/frontlight.ato`, and wired into the
top level on **`IO41`**. `IO26` and `IO42` stay free and `IO40` stays spoken
for as the sounder's antiphase pin.

Nine parts on the main board:

| | | |
|---|---|---|
| U | TPS61165DBVR | SOT-23-6 |
| L | 22 µH, NR3015T220M | 3.0 × 3.0 × 1.5 mm. TI's own optimum, not a guess — §9.1.2 recommends 10–22 µH and says 22 is the efficient end |
| D | 1N5819HW | the same Schottky as the panel's charge pump, so no new BOM line |
| C | 4.7 µF | input, 0603. TI ask 1 µF minimum |
| C | 1 µF 50 V | output, 0805 — **not 25 V**, see below |
| C | 220 nF | COMP |
| R | 10 Ω | current set: 0.2 V ÷ 20 mA, the LED's rated maximum |
| R | 10 kΩ | in series with CTRL |
| R | 1 MΩ | holds CTRL down |

plus two solder pads, `FL+` and `FL−`, and the four LEDs on the sliver.
Thirteen active parts rather than the seven the parallel scheme would have
taken.

**The output capacitor is the one thing here that could have gone bang.** In
normal running it sees 13.8 V, which a 25 V part covers comfortably — and that
is what this was until the datasheet arrived. What sets the rating is the
fault. If the LED string opens, the boost runs the output up until the open-LED
protection trips, and TI put that threshold at 37 V minimum, 38 typical and
**39 V maximum**. A 25 V part there fails, and it fails with 39 V behind it.
50 V in 0805, because a 50 V 0603 would lose most of its capacitance to DC bias
derating at 13.8 V. The same number is why the Schottky has to be a 40 V part:
TI's own recommendations for this position, the MBR0540 and ZHCS400, are both
40 V. That is only 1 V of margin on a fault that LEDs at the end of two
hand-soldered wires can genuinely produce, so a 60 V PMEG6010CEH in the same
SOD-123 outline is worth the BOM line if you want it.

**Both CTRL resistors are the datasheet's, not my taste.** The 10 kΩ in series
is there because CTRL is not only a PWM input — it is also the EasyScale
one-wire interface, and the part can pull CTRL down itself to acknowledge a
command. TI recommend a series resistor limiting CTRL current to 500 µA when
the driver is push-pull, which an ESP32 GPIO is, both for an accidentally
requested acknowledge and to protect the internal ACKN-MOSFET. 3.3 V over 10 kΩ
is 330 µA. The 1 MΩ pull-down sits on the IC side of it: CTRL low is shutdown,
and the driving GPIO is high impedance at reset and through boot, so without it
the frontlight's state during boot is whatever leakage decides. 4.7 MΩ would
cost a fifth as much standing current but leaves CTRL at nearly half a volt,
too near the threshold to trust. The two divide 3.3 V by 1.01, so CTRL still
sees 3.27 V high.

Two soldered wires to the sliver rather than a connector: a connector inside a
case that is never opened is a part that can work loose, and it would have to
be under 1 mm tall to fit beside the guide.

**What it costs when it is off.** `SYS` is upstream of the power slider, so the
driver is live whenever there is a cell in the case: the TPS61165's shutdown
current plus 4.2 µA through the 1 MΩ comes to about **5 µA**. Against a board
that otherwise sits at 10 µA switched off, that turns six years in a drawer
into about four. It is a real cost and it is the reason the whole block is
fitted per unit: a calculator built without a light guide has none of these
parts on it and none of the 5 µA.

### Bonding

Optically clear adhesive, 125–175 µm, the way e-readers are assembled. Pre-cut
phone-repair sheets are the cheap source; 3M 8211/8212/8215 or Lohmann
DuploCOLL are the named products. Laser-cutting OCA is possible but it is a
sticky, fumey job — cutting it oversize with a blade against a template and
trimming after lamination is less trouble. Roll it on from one edge to chase
the bubbles out, and do it in the least dusty room in the house, because every
speck under it is permanent.

## What I would build

1. **The plate, now.** It is the lowest-risk, highest-return item on this list,
   and the aperture is already specified. The only board change it asks for is
   a ground bond pad.
2. **No separate window** — if the frontlight happens the guide is the window,
   and if it does not, the panel's own hard coat is enough.
3. **The frontlight as an option — now drawn.** Thirteen parts and one GPIO is
   cheap enough that leaving room for it costs nothing, and the light guide is
   the part that might not come out well, which is a question of laser time
   rather than of board respins. The circuit is in `elec/src/frontlight.ato`;
   a unit built without a guide simply does not have any of it fitted.
