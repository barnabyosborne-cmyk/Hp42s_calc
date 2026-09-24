# The top edge

Five things come out of the 80 x 15 mm top face of the case, and all five are on
the **back** of the board:

| | part | why it is here |
|---|---|---|
| IR emitter | Vishay VSMB2943SLX01, 940 nm side-looking | the original 42S's IR window is on this edge |
| USB-C | GCT USB4105-GF-A | charging and file transfer |
| status LED | Dialight 599-0Q70-247F, red/green side-view | boot, error, nominal |
| BOOT | Alps SKRTLAE010, side push with guide bosses | recovery |
| RESET | Alps SKRTLAE010, side push with guide bosses | recovery |

**There used to be a sixth, a C&K JS102011SAQN power slider.** It went on
24 September 2026: a real HP-42S switches on with a key, and so does this one.
`docs/power-control.md` has the whole of that change. It freed board X 6 to 16
on this edge and nothing has claimed it.

## Why the back

Barnaby asked on 24 September 2026 to put them on the back, "more balanced for
the centering of them in the top panel". He is right, and the stack-up says by
how much.

`docs/front-face.md` sets the vertical budget: a 15 mm case with 1.2 mm shells
leaves 12.6 mm inside. Measured from the case's outer **front** surface, with
the light guide against the inside of the front shell:

| | from | to |
|---|---|---|
| front shell | 0.00 | 1.20 |
| light guide, 1.0 mm cast acrylic | 1.20 | 2.20 |
| air gap | 2.20 | 3.00 |
| adhesive | 3.00 | 3.20 |
| panel glass | 3.20 | 4.20 |
| **board, 1.6 mm** | **4.20** | **5.80** |
| cell, 6 mm | 5.80 | 11.80 |
| slack | 11.80 | 13.80 |
| back shell | 13.80 | 15.00 |

So the board's front face sits 4.20 mm inside the case and its back face 5.80.
The top wall's centreline is at 7.50. Each part's aperture is on the axis of
whatever comes out of it, and that axis is a fixed height above the face the part
is soldered to — measured off the vendor STEP models in
`elec/footprints/hp42s.3dshapes`:

| part | axis above its own face | on the FRONT | on the BACK | off centre, front / back |
|---|---|---|---|---|
| USB-C mouth | 1.28 | 2.92 | **7.08** | 4.58 / 0.42 |
| IR optical axis | 1.15 | 3.05 | **6.95** | 4.45 / 0.55 |
| tact plunger | 1.65 | 2.55 | **7.45** | 4.95 / 0.05 |
| status LED lens | 0.50 | 3.70 | **6.30** | 3.80 / 1.20 |

On the back all four apertures land within 1.2 mm of the wall's centreline, and
the two mechanical ones within half a millimetre. On the front they sat 4 to 5 mm
high in a 15 mm wall.

**And the USB-C one was not merely off centre, it did not fit.** With the
receptacle on the front, the top of its 2.56 mm shell is at 1.64 mm — which is
0.44 mm short of the front shell's inner face at 1.20. That is a 0.44 mm ledge of
resin over the cut-out, which is not a printable feature. Worse, the plug: a
Type-C plug's overmould is about 4.5 mm across, so centred on a mouth 2.92 mm
below the outer surface it would stand about half a millimetre **outside** the
case's front face. The receptacle could have been soldered; the cable could not
have been plugged in without slotting the front of the case.

On the back the same plug body spans 4.8 to 9.3 mm, with 3.6 mm of clearance to
the front shell and 4.5 mm to the back one.

### What it costs

**3.5 mm of battery bay, and then 1 mm of cell thickness.** Two steps, and the
second is the one Barnaby's case model has to absorb.

The bay was board Y 5 to 59, about 54 mm, and it took a 5 x 50 x 60 mm cell —
1600 mAh with a millimetre to spare. The five parts on the back reach as far in
as the USB-C's courtyard at Y 7.24, so the bay would start at Y 8.5: 50.5 mm,
which the same cell still fits, with nothing to spare.

Then Barnaby asked for every reflowed part on one side (below), which put the
nine parts that serve the top edge on the back as well. The deepest of those is
U1 at Y 11.66, so **the bay is now Y 13 to 58, 45 mm, X 14 to 69.**

A 6 x 45 x 55 mm cell is about 14,850 mm³ against the 505060's 15,000, so it is
**the same 1600 mAh one millimetre thicker**, and it was always the second of the
three fallbacks in `docs/display-mounting.md`. The 6 mm is already in the table
above: `docs/front-face.md` budgeted a 6 mm cell from the start and the deepest
arrangement still leaves 2.0 mm of slack. Nothing has to grow.

If a 6 mm cell in that footprint turns out to be hard to buy, the other two
fallbacks are unchanged and both still work: let the cell run past Y 58 into the
keyboard region, or accept about 1400 mAh in 5 x 48 x 55.

### What it gives back

**The USB-C's four through-hole shield fillets are on the FRONT now.** They used
to land in the battery bay at board Y 0 to 5, under the cell, which is why the
bay was 54 mm and not 57 — a pouch cell resting on four solder fillets is not a
risk worth taking, because the case is soft aluminium laminate and it grows over
its life. Those fillets now come through under the bezel, where nothing touches
them.

One thing to check against the case model: keep the frontlight's light guide
clear of board Y 0 to 5, or let it stop at the glass. There is 3.0 mm of air in
front of the board in the bezel band and a through-hole lead cut for a 1.6 mm
board stands well under that, but the guide is the only part that could foul it.

## Everything the fab house solders is on the back

Barnaby asked for this on 24 September 2026, to make the board a single-sided
assembly. It is the cheaper build: one stencil, one paste print, one reflow, no
glue and no second pass.

**The front now carries nothing that comes back from the fab already soldered.**
What is on the front is the panel, the 38 dome sites and the frontlight sliver's
two lands and ground point, all of which go on afterwards.

What moved with it, from the front at exactly the same x and y:

| | serves |
|---|---|
| U1, R1, R2, C1 | the USB-C: ESD array, CC pulldowns, VBUS bulk cap |
| Q2, R18, R19 | the IR emitter's driver |
| R20, R21 | the status LED's two ballast resistors |

They are all directly behind where they were, so every distance to the part it
serves is unchanged, and the USB pair no longer has to cross the board through
vias to reach its ESD array. `tools/check_placement.py` reports the whole board
clear at 1 mm courtyard to courtyard.

Turning a footprint over mirrors it in y, so pin 1 of U1 and of Q2 has moved from
one end of the body to the other. Neither matters — the ESD array's four channels
are interchangeable and the SOT-23 is a single transistor — and nothing is routed
yet.

**One thing still spoils the single-sided story, and it is worth a look now.**
This USB-C receptacle anchors with four through-hole shield legs. Every 16-pin
Type-C part does; they take the cable strain, which is why the case gets a lip
rather than the connector getting a different land pattern. But a through-hole
part is a second operation whichever side it protrudes from. A receptacle with
**SMD-only shell tabs** would make this board genuinely one-pass. The two
locating pegs and the Alps switches' guide bosses are non-plated holes and cost
nothing. `BT1` is already on its way from a through-hole JST PH to the SMD
`S2B-PH-SM4-TB`.

## Side actuation is the whole trick

An ordinary tact switch has its plunger on top, pointing out of the board's face.
It cannot reach a case edge. Both switches here are side-actuated: the plunger
comes out of the *end* of the body, in the plane of the board.

- **Reset and BOOT: Alps SKRTLAE010**, body 4.5 x 2.56 mm with the plunger
  **1.05 mm** proud of it (0.84 was the catalogue figure; Alps' own STEP model,
  checked 23 September 2026, has it reaching 2.261 mm from the origin),
  4.5 x 3.55 overall and 3.3 tall, with the guide bosses 0.5 below the board
  face. 1.6 N to operate and 0.2 mm of travel, so it is a deliberate press with
  a fingernail or a pen, not something a pocket does by accident. 100,000
  cycles, which for these two is forever.

  It is the `-LAE010`, the variant **with guide bosses**, so each one needs two
  0.9 mm non-plated holes in the board as well as its five pads, and a 2.0 x
  1.2 mm patch between the mounting pads that Alps marks as prohibited for
  copper. All three are in the footprint. The `-LBE010` is the same switch with
  no bosses and no holes if that ever becomes awkward.
- **USB-C: GCT USB4105-GF-A**, mouth flush with the board edge. Shell outside
  8.64 x 2.56 mm, body 8.94 wide x 7.35 deep, with four through-hole shell legs
  and two 0.65 mm locating pegs. KiCad's footprint is drawn from GCT's own
  document and marks the product edge on Dwgs.User at 3.675 mm from the origin,
  which is what the placement is set from — the same number the Same Sky UJ20 it
  replaced on 22 September 2026 used, so the case cut-out line did not move.

  **A Same Sky UJC-HP-G-5-SMT-TR was evaluated on 24 September 2026 and
  rejected: it is power-only.** It has six contacts — A5/B5 `CC`, A9/B9 `VBUS`,
  A12/B12 `GND` — and no `D+`/`D-` at all. That is a fine part for a charge-only
  product and it is a smaller one, 11.54 x 7.14 x 3.21 mm from its STEP model,
  but this board needs USB **data** twice over. Once because file transfer over
  USB is a headline feature, the thing you plug in to load a program. And once
  because the S3's own USB peripheral is the only flashing path that exists
  here: there is no USB-UART bridge on the board (see "Why a BOOT button as well
  as RESET" below), so with a power-only receptacle a bricked board could not be
  reflashed at all, by anyone, ever. Keep the USB4105-GF-A.

## Reset

A plain button from the module's `EN` to ground. It is a hardware reset of the
chip and does not go near the firmware, which is the only reason to have it — you
press it when the firmware has stopped working. With no power slider it is also
the only way to interrupt firmware that has hung: see `docs/power-control.md`.

The existing 10k and 1 uF on `EN` debounce it for free: the cap holds `EN` down
for about 10 ms after release, and Alps specifies the contact bounce at 10 ms
when new and 20 ms at end of life. Those are the same order, so the RC does not
swallow the bounce outright — what it does is turn a bounce train into one slow
ramp, because the cap cannot recharge through 10k faster than the contacts are
chattering. The chip sees one release. `BOOT` is the one that needs the software
debounce: 20 ms or more, from the same Alps number.

Recess it in the case. This is not a key. A reset button you can press while
holding the calculator is a reset button you will press while holding the
calculator.

## Why a BOOT button as well as RESET

Because it is the only recovery path, and without it the recovery path is a
screwdriver.

A dev board gets away without a BOOT button because its USB-UART bridge wiggles
`EN` and `IO0` from the host, which is how esptool puts the chip into download
mode on its own. This board has no bridge — the S3 drives USB itself. The moment
the firmware claims the USB OTG peripheral for mass storage, the USB-Serial/JTAG
path that esptool could otherwise reset through is no longer on those pins. And
if the firmware is broken enough not to enumerate at all, nothing on the host can
reach the chip by any route.

Hold BOOT, tap RESET, release BOOT, and the ROM bootloader comes up regardless of
what is in flash. Recess BOOT deeper than RESET; it is pressed roughly never, and
the two should not feel alike.

## The status LED

Dialight 599-0Q70-247F: two dice, red and yellow-green, sharing a **common
anode**, so a channel is driven LOW to light.

It is bi-colour, not RGB, and that is the right answer rather than a concession.
Red and green together read as amber, so two dice give three states, which is all
the indicator was ever asked for. A true RGB part would need a blue die, every
blue die is InGaN, and InGaN wants up to 3.9 V forward against this board's 3.3 V
rail. The 599's two AlGaInP dice run at 2.0 to 2.4 V with room to spare.
Barnaby's first pick, the -0Q40-, is yellow plus yellow-green, which no one can
tell apart through a diffused window; the -0Q70- is the same part with a red die
instead of the yellow.

Common anode does leave a weak pull-up on the two driving pins while they are
high impedance. That was a real objection when the plan was three channels on an
unverified part, and it is not one now: `IO16` and `IO39` are not strapping pins
— only `IO0`, `IO3`, `IO45` and `IO46` are — and the current through an unlit LED
is leakage rather than a divider. Dark at reset, through boot, and in deep sleep,
which is what matters: an indicator left on is milliamps against a 21 uA sleep
budget. Blink it during boot and on error, and leave it dark in normal use.

It costs two GPIOs rather than three. `IO16` was spare; `IO39` is one of the four
JTAG pins, which this board had already given up in practice — the USB pins go to
the OTG peripheral, and debugging runs over the UART0 test pads. **`IO40` goes
back to the free list**, and `docs/power-control.md` wants it: moving `LED_RED`
off `IO16` would free the S3's `XTAL_32K` pair for a real 32.768 kHz timebase.
1k on a 2.0 V die off 3.3 V is about 1.3 mA, plenty behind a case window.

**The lens is 1.0 mm tall and its axis sits 0.50 mm above the face it is
soldered to**, measured from Dialight's STEP model on 24 September 2026. This
file used to say "roughly 1.0 to 2.0 mm", which was a guess and was wrong. The
lens wants a diffused window rather than the clear one the IR needs.

## Placement

`tools/place_board.py` places all five, on the back. Y is depth from the board's
top edge, and each part is pushed out until its own pads stop it.

| part | x | y | courtyard across x | courtyard reaches | protrudes past the edge |
|------|---|---|---|---|---|
| IR emitter | 25.33 | 0.900 | 22.98 .. 27.68 | y = 2.34 | 0.73 mm |
| USB-C | 38.00 | 2.475 | 32.68 .. 43.32 | y = 7.23 | 1.70 mm |
| status LED | 50.57 | 1.050 | 48.32 .. 52.82 | y = 2.45 | 0.77 mm |
| BOOT | 60.65 | 1.800 | 57.82 .. 63.48 | y = 3.85 | 0.50 mm |
| RESET | 71.31 | 1.800 | 68.48 .. 74.14 | y = 3.85 | 0.50 mm |

**Two rules fix every x on this edge**, and they were applied on 24 September
2026 in place of the older hand-chosen numbers:

1. **The USB-C sits on the board's centreline.** The board is 76 mm wide, so
   `J1` is at x = 38.00 and the plug goes into the middle of the case's top
   face. That is the one number a user looks at, so it is the one that gets the
   symmetry.
2. **Every adjacent pair is 5.00 mm courtyard to courtyard.** Not centre to
   centre: these five parts are wildly different widths (the USB-C is
   10.64 mm across, the status LED 4.50 mm), so equal centre spacing would look
   crowded at the USB-C and empty at the LED. Equal *gaps* is what the eye
   reads as even, and it is also what matters for a stencil and for a fat
   thumb on a button.

The two indicators therefore straddle the USB-C — the IR emitter to its left,
the status LED to its right — and the status LED shares its side with the two
buttons, which is what Barnaby asked for: BOOT and RESET at 60.65 and 71.31,
each 5.00 mm clear of its neighbour.

What the rules cost: 22.98 mm of empty board left of the IR emitter, where the
slider used to be, and only **1.86 mm** right of RESET before the board edge.
That is the tightest number on the edge and it is the reason the chain cannot
grow: one more 5 mm gap and RESET would hang off the board. If anything else
ever has to go on this edge it displaces the chain leftwards, it does not
extend it.

X changed for all five when they were centred, so **any case hole drawn against
the old numbers moves**. The mapping itself is unchanged and does not depend on
which side a part is soldered to: `x_case = x_board + 2` either way. Depth in
the 15 mm wall also changed when they went to the back, by 4.16 mm.

**The rotations are not the front's rotations.** Turning a footprint over negates
every child y, so an actuator that pointed at -Y on the front points at +Y once
it is over: the 180 degrees comes off the USB-C and the two buttons rather than
going on. The two LEDs are the opposite — their lens faces are already the -y end
of the body, so they wanted 0 on the front and want 180 here. Get it wrong and
the IR beam and both plungers aim into the middle of the board.
`tools/check_placement.py` prints all five with their courtyards for exactly this
reason: every one must reach past y = 0.

**Both lenses are proud of the board edge, not inside it** — the IR dome by
0.45 mm and the status LED's lens by 0.475 mm, measured off the vendor STEP
models on 23 September 2026. The board is inset 2 mm from the case, so there is
room, but the case needs a relief pocket for each lens and not merely a window in
the wall: clear for the IR, diffused for the status LED.

## The IR emitter

Vishay VSMB2943SLX01, confirmed side-looking from document 83479 rev 1.2:
2.3 x 2.55 x 2.3 mm, 940 nm, 20 mW/sr, half angle +/- 25 degrees, 1.35 V typical
at 100 mA, 15 ns rise time. It is a far bigger part than the 1.6 x 0.6 mm pattern
that was standing in for it — two 0.9 x 1.2 mm pads 4.2 mm across the outsides —
so it has its own footprint, generated from Vishay's IPC 7351 solder pad proposal
by `tools/gen_ic_footprints.py`.

Two numbers for the case:

- The **optical axis sits 1.15 mm above the face of the board the part is
  soldered to**, from Vishay's own STEP model. It is on the back, so the beam
  runs 1.15 mm behind the back copper, at 6.95 mm from the case's outer front
  surface. **If you have already cut an IR window for the front, it moves.**
- The dome tip does not stop short of the board edge: it reaches 1.35 mm from the
  part's origin, and with D4 at board Y 0.900 that puts the tip at board
  **Y -0.45**, so it overhangs the edge by 0.45 mm. The lens is 1.8 mm across, so
  a 2.5 mm window centred on x = 25.33 clears the beam without vignetting the
  +/- 25 degrees — but the wall has to be relieved for the dome rather than
  merely windowed.
