# The top edge

Six things come out of the 80 x 15 mm top face of the case, and all six are on
the **front** of the board, above the panel:

| | part | why it is here |
|---|---|---|
| power slider | C&K JS102011SAQN | daily use |
| IR emitter | Vishay VSMB2943SLX01, 940 nm side-looking | the original 42S's IR window is on this edge |
| USB-C | GCT USB4105-GF-A | charging and file transfer |
| status LED | Dialight 599-0Q70-247F, red/green side-view | boot, error, nominal |
| BOOT | Alps SKRTLAE010, side push with guide bosses | recovery |
| RESET | Alps SKRTLAE010, side push with guide bosses | recovery |

## Why the front, and why that used to be impossible

**They were on the back until 21 September 2026.** What moved them was the
bezel: Barnaby chose a 14 mm top bezel over the 8 mm the design had been
carrying.

The board is 76 x 144 mm inside a 148 x 80 mm case, and the 2 mm inset eats
2 mm of whatever the front face spends on the bezel. So an 8 mm bezel leaves
6 mm of board above the panel, and 14 mm leaves 12.

Six millimetres was not enough. Measured from KiCad's own courtyards:

| part | reaches into the board |
|------|------------------------|
| status LED | 3.20 mm |
| IR emitter | 3.04 mm |
| Alps SKRTLAE010 buttons | 3.55 mm |
| C&K JS102011SAQN slider | 7.50 mm |
| USB-C receptacle | 8.44 mm |

Twelve is. The USB-C receptacle is the part that decided it either way, and at
8.44 mm it now clears with 3.56 mm to spare.

(Two of those parts changed on 22 September 2026 — the slider from a Shouhan
MSK-12C02 to the C&K, and the receptacle from a Same Sky UJ20 to the GCT — for
land-pattern reasons rather than electrical ones. `docs/before-layout.md` has
the argument. The slider got deeper in the process, 5.15 mm to 7.50, which
12 mm of board absorbs and 6 would not have.)

### What the move buys

- **The cell fits.** The battery bay at the top of the back was about 49 mm
  tall, and it was 49 rather than 57 because the USB-C reached 8.83 mm into
  the board. A 1600 mAh cell wants 50, so it missed by a millimetre and had to
  either spill past the keyboard line or go thicker and narrower. It now has
  about 54 mm (see the caveat below) and simply fits.
- **Nothing is flipped.** Every one of the six was previously placed with a
  layer flip composed with a 180 degree rotation, and the orientation of a
  flipped side-actuated part is the kind of thing you get wrong once and find
  out about at assembly. On the front the 180 degrees is the whole story.
- **The back is clean.** The top of the back is now the battery bay and
  nothing else.

### What it costs

The display drops 6 mm down the face from where the real 42S has it, and the
gap between the panel and the top key row closes from 16.7 mm to 10.7. That is
the whole cost, and it is an aesthetic one. Barnaby accepted it.

### The one thing that swapped sides with them

This USB-C receptacle anchors with **through-hole shield legs**, so its solder
fillets used to be on the front, under the panel, where the panel's foam tape
swallowed them. They are now on the **back**, which is the battery bay.

Keep the cell clear of board Y 0 to 5 in that region — which is where the 54 mm
above comes from rather than 57 — or find a receptacle with SMD-only shell
tabs, which removes the question entirely. A pouch cell resting on four solder
fillets is not a risk worth taking: the case is soft aluminium laminate and it
grows over its life.

## Side actuation is the whole trick

An ordinary slide switch or tact switch has its knob on top, pointing out of
the board's face. It cannot reach a case edge. Both parts here are
side-actuated: the knob and the plunger come out of the *end* of the body, in
the plane of the board.

- **Slider: C&K JS102011SAQN**, SPDT ON-ON, 9.0 x 3.6 x 3.5 mm body, 0.3 A at
  6 V DC, gull-wing SMD with two 0.9 mm locating bosses. Three pads on a clean
  2.5 mm pitch, and no shield tab -- unlike the Shouhan MSK-12C02 it replaced
  on 22 September 2026, which cost `power.ato` its `sw_power.shield`
  connection.
- **Reset and BOOT: Alps SKRTLAE010**, body 4.5 x 2.56 mm with the plunger
  **1.05 mm** proud of it (0.84 was the catalogue figure; Alps' own STEP
  model, checked 23 September 2026, has it reaching 2.261 mm from the
  origin), 4.5 x 3.55 overall and 3.3 tall, with the guide bosses 0.5 below
  the board face. 1.6 N to operate and
  0.2 mm of travel, so it is a deliberate press with a fingernail or a pen,
  not something a pocket does by accident. 100,000 cycles, which for these two
  is forever.

  It is the `-LAE010`, the variant **with guide bosses**, so each one needs two
  0.9 mm non-plated holes in the board as well as its five pads, and a 2.0 x
  1.2 mm patch between the mounting pads that Alps marks as prohibited for
  copper. All three are in the footprint. The `-LBE010` is the same switch with
  no bosses and no holes if that ever becomes awkward.
- **USB-C: GCT USB4105-GF-A**, mouth flush with the board edge. Shell outside
  8.64 x 2.56 mm, body 8.94 wide x 7.35 deep, with four through-hole shell legs
  and two 0.65 mm locating pegs. KiCad's footprint is drawn from GCT's own
  document and marks the product edge on Dwgs.User at 3.675 mm from the origin,
  which is what the placement is set from -- the same number the Same Sky part
  used, so the case cut-out line did not move.

**Fitted 22 September 2026.** The C&K was always the nicer switch — better
detent, clean 2.5 mm pad pitch, a proper datasheet — and its 8.75 mm courtyard
needed a bigger bezel to be possible. Now that it is in, the Shouhan's doubtful
land pattern goes with it. The detent is the difference between a switch that
feels like a calculator and one that feels like a toy.

## What the slider actually switches

Not the load. It drives the buck-boost's enable pin and nothing else, so it
carries microamps: no arcing, no contact resistance in the supply path, and a
2.8 mm switch is plenty.

    SYS ---- pin 1 \
                    pin 2 ---- TPS63900 EN
    GND ---- pin 3 /

Both throws are driven rather than one throw and a pull-up, so EN is never
floating. A floating enable on a buck-boost is how you get a regulator that
hums at the halfway point of the slider's travel.

Charging is deliberately upstream of this. With the slider off, USB still
charges the cell and the fuel gauge still counts.

Fixing a real bug on the way: EN used to be tied to the regulator's own 3.3 V
output. That is a rail which cannot exist until EN is already high, so as drawn
the regulator could never have started.

## What "off" costs

Off is not zero. The charger holds about 4 uA and the fuel gauge about 4 uA in
hibernate, so the calculator sits at roughly 10 uA — call it six years on the
cell. Deep sleep with the slider *on* is about 25 uA, or fifteen months. So the
slider buys very little in daily use. What it buys is a device that survives a
drawer, a shipping box, or firmware that has hung in a way the reset button
cannot reach.

It costs two things:

1. **The clock stops.** The ESP32's RTC dies with the rail. Plus42's TIME and
   DATE will need setting after every power-up unless a backup cell is added.
2. **Unsaved state is lost.** The rail collapses in a few milliseconds and the
   firmware gets no warning.

(2) is a firmware decision, not a hardware one, and the cheap answer is the
right one: persist the calculator state after every completed operation rather
than on shutdown. Plus42's state is a few kilobytes, a LittleFS write is a few
milliseconds, and wear levelling over a 1 MB partition makes 1500 writes a day
a non-issue. Do that and the slider becomes free of consequences.

The hardware alternative is a power-fail-save: a Schottky and a 100 uF holding
the MCU up while a GPIO watches the main rail collapse. It is four more parts
and it drops the MCU to 3.0 V, which is the bottom of the ESP32-S3's range. Not
worth it if the firmware just saves as it goes.

## The fuel gauge moved

With a hard off, the MAX17048 can no longer sit on the 3.3 V rail: a ModelGauge
part that loses power loses the model it has learned, so a calculator coming
out of a drawer would guess at its charge for the first few cycles. It now runs
straight off the cell, which is its normal application.

Check before fab: its SDA/SCL then sit on a 4.2 V part with 3.3 V pull-ups. The
MAX17048's input thresholds are fixed rather than VDD-referenced, so this should
be fine, but read the DC table.

## Reset

A plain button from the module's EN to ground. It is a hardware reset of the
chip and does not go near the firmware, which is the only reason to have it —
you press it when the firmware has stopped working.

The existing 10k and 1 uF on EN debounce it for free: the cap holds EN down for
about 10 ms after release, and Alps specifies the contact bounce at 10 ms when
new and 20 ms at end of life. Those are the same order, so the RC does not
swallow the bounce outright -- what it does is turn a bounce train into one
slow ramp, because the cap cannot recharge through 10k faster than the contacts
are chattering. The chip sees one release. BOOT is the one that needs the
software debounce: 20 ms or more, from the same Alps number.

Recess it in the case. This is not a key. A reset button you can press while
holding the calculator is a reset button you will press while holding the
calculator.

## Why a BOOT button as well as RESET

Because it is the only recovery path, and without it the recovery path is a
screwdriver.

A dev board gets away without a BOOT button because its USB-UART bridge
wiggles EN and IO0 from the host, which is how esptool puts the chip into
download mode on its own. This board has no bridge -- the S3 drives USB
itself. The moment the firmware claims the USB OTG peripheral for mass
storage, the USB-Serial/JTAG path that esptool could otherwise reset through
is no longer on those pins. And if the firmware is broken enough not to
enumerate at all, nothing on the host can reach the chip by any route.

Hold BOOT, tap RESET, release BOOT, and the ROM bootloader comes up regardless
of what is in flash. Recess BOOT deeper than RESET; it is pressed roughly
never, and the two should not feel alike.

## The status LED

Dialight 599-0Q70-247F: two dice, red and yellow-green, sharing a **common
anode**, so a channel is driven LOW to light.

It is bi-colour, not RGB, and that is the right answer rather than a
concession. Red and green together read as amber, so two dice give three
states, which is all the indicator was ever asked for. A true RGB part would
need a blue die, every blue die is InGaN, and InGaN wants up to 3.9 V forward
against this board's 3.3 V rail. The 599's two AlGaInP dice run at 2.0 to
2.4 V with room to spare. Barnaby's first pick, the -0Q40-, is yellow plus
yellow-green, which no one can tell apart through a diffused window; the
-0Q70- is the same part with a red die instead of the yellow.

Common anode does leave a weak pull-up on the two driving pins while they are
high impedance. That was a real objection when the plan was three channels on
an unverified part, and it is not one now: IO16 and IO39 are not strapping
pins -- only IO0, IO3, IO45 and IO46 are -- and the current through an unlit
LED is leakage rather than a divider. Dark at reset, through boot, and in
deep sleep, which is what matters: an indicator left on is milliamps against
a 25 uA sleep budget, and turns fifteen months into about a week. Blink it
during boot and on error, and leave it dark in normal use.

It costs two GPIOs rather than three. IO16 was spare; IO39 is one of the four
JTAG pins, which this board had already given up in practice -- the USB pins
go to the OTG peripheral, and debugging runs over the UART0 test pads. IO40
goes back to the free list. 1k on a 2.0 V die off 3.3 V is about 1.3 mA,
plenty behind a case window.

The lens sits roughly 1.0 to 2.0 mm above the face of the board it is
soldered to, which is now the front, so it wants a diffused window rather than
the clear one the IR needs.

## Placement

`tools/place_keypad.py` places all six, on the front. Y is depth from the
board's top edge.

| part | x | y | reaches |
|------|---|---|---------|
| power slider | 11.0 | 3.00 | knob to y = -0.80 |
| IR emitter | 22.0 | 1.60 | dome tip 0.22 mm inside the edge |
| USB-C | 36.0 | 3.67 | mouth flush at y = 0 |
| status LED | 48.0 | 1.80 | lens 0.23 mm inside the edge |
| BOOT | 57.0 | 1.50 | plunger to y = -0.54 |
| RESET | 66.0 | 1.50 | plunger to y = -0.54 |

Courtyard to courtyard along the edge, with the two new parts: 3.65 mm slider
to IR, 6.42 mm IR to USB-C, 4.32 mm USB-C to the status LED, 3.92 mm status LED
to BOOT, and 3.34 mm BOOT to RESET, which is still the tightest. There is
6.0 mm of board left of the slider and 7.2 mm right of RESET.

The four mechanical parts are rotated 180 degrees so their actuators face the
edge, each leaving about 0.8 mm proud for the case wall to capture. With
everything on the front there is no layer flip on top of that rotation, so
what the viewer shows is what gets built. **The two LEDs are not rotated** -- their lenses are already the -y end of the body, and
turning them round would aim them into the middle of the board.

**Both are proud of the board edge, not inside it** -- the IR dome by
0.45 mm and the status LED's lens by 0.475 mm, measured off the vendor STEP
models on 23 September 2026. The board is inset 2 mm from the case, so
there is room, but the case needs a relief pocket for each lens and not
merely a window in the wall: clear for the IR, diffused for the status LED.

## The IR emitter

Vishay VSMB2943SLX01, confirmed side-looking from document 83479 rev 1.2:
2.3 x 2.55 x 2.3 mm, 940 nm, 20 mW/sr, half angle +/- 25 degrees, 1.35 V
typical at 100 mA, 15 ns rise time. It is a far bigger part than the 1.6 x
0.6 mm pattern that was standing in for it -- two 0.9 x 1.2 mm pads 4.2 mm
across the outsides -- so it has its own footprint, generated from Vishay's
IPC 7351 solder pad proposal by `tools/gen_ic_footprints.py`.

Two numbers for the case:

- The **optical axis sits 1.2 mm above the face of the board the part is
  soldered to**. It is on the front, so the beam runs 1.2 mm in front of the
  front copper, not on the board centreline. (It was on the back until the
  bezel changed, so if you have already cut an IR window, it moves.)
- **Corrected 23 September 2026, from Vishay's own STEP model.** The dome
  tip does not stop short of the board edge: it reaches 1.35 mm from the
  part's origin, and with D4 at board Y 0.900 that puts the tip at board
  **Y -0.45**, so it overhangs the edge by 0.45 mm. The optical axis sits
  **1.15 mm** above the board face, not 1.20. The lens is 1.8 mm across, so
  a 2.5 mm window centred on x = 22.0 still clears the beam without
  vignetting the +/- 25 degrees -- but the case wall has to be relieved for
  the dome rather than merely windowed, and the same is true of the status
  LED, whose lens reaches board Y -0.475.

One thing to watch: this USB-C receptacle anchors with through-hole shield
legs. With the receptacle on the front those fillets are on the back, in the
battery bay — see the caveat at the top of this file. A receptacle with
SMD-only shell tabs avoids the question entirely if you find one you can buy,
and it is worth looking now rather than later.
