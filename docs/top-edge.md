# The top edge

Six things come out of the 80 x 15 mm top face of the case, and all six are on
the **back** of the board:

| | part | why it is here |
|---|---|---|
| power slider | Shouhan MSK-12C02 | daily use |
| IR emitter | 940 nm side-view, 1.6 x 0.8 mm | the original 42S's IR window is on this edge |
| USB-C | HCTL HC-TYPE-C-16P-01A | charging and file transfer |
| status LED | RGB side-view, Kingbright APFA3010 outline | boot, error, nominal |
| BOOT | Alps SKRTLAE010 | recovery |
| RESET | Alps SKRTLAE010 | recovery |

## Why the back

The board is 76 x 144 mm inside a 148 x 80 mm case. Above the panel there are
only 6 mm of board, because the front face budget spends 8 mm on the top bezel
and the 2 mm case inset eats a quarter of that.

Six millimetres is not enough. Measured from KiCad's own courtyards:

| part | reaches into the board |
|------|------------------------|
| RGB status LED | 2.00 mm |
| IR emitter | 2.10 mm |
| Alps SKRTLAE010 buttons | 3.55 mm |
| Shouhan MSK-12C02 slider | 5.15 mm |
| USB-C receptacle | 8.57 mm |

On the back, none of that matters: the panel is glued to the front and does not
care what is underneath it. The actuators come out of the *edge* of the board,
so which side they are soldered to only shifts them 1.6 mm in Z, and you are
printing the case anyway.

The alternative is to grow the top bezel to about 14 mm and put all three on
the front above the panel. There is room — the keyboard came in at 78 mm rather
than the 84 mm originally budgeted, so 12 mm are spare, and the gap between
panel and first key row would still be 10.7 mm. It is the cleaner board. It
also drops the display 6 mm lower than the real 42S, which is a bigger change
to the face than it sounds.

## Side actuation is the whole trick

An ordinary slide switch or tact switch has its knob on top, pointing out of
the board's face. It cannot reach a case edge. Both parts here are
side-actuated: the knob and the plunger come out of the *end* of the body, in
the plane of the board.

- **Slider: Shouhan MSK-12C02**, SPDT, 6.7 x 2.8 mm body, knob 1.45 mm proud of
  one end. LCSC C431540.
- **Reset: Alps SKRTLAE010**, 4.5 x 2.56 mm, plunger out the end.
- **USB-C: HCTL HC-TYPE-C-16P-01A**, mouth flush with the board edge.

The nicer slide switch is the C&K JS102011SAQN — better detent, clean 2.5 mm
pad pitch, a proper datasheet. Its courtyard is 8.75 mm deep, so it only
becomes an option if the bezel grows.

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
about 10 ms after release, longer than the contact bounce.

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

Side-emitting RGB, driven HIGH to light with its common pin on ground. That
polarity is not arbitrary: three GPIOs pulled up through LEDs would sit on the
module during strapping, and some of the pins that would be convenient to use
are exactly the sort that decide flash voltage at reset. Driven high, every
channel is dark whenever the pins are high-impedance -- at reset, through
boot, and in deep sleep.

That last one matters more than it sounds. An indicator left on is tens of
milliamps against a 25 uA sleep budget, which turns fifteen months into about
a week. Blink it during boot and on error; leave it dark in normal use.

It costs three GPIOs: IO16, which was spare, and IO39 and IO40, which are two
of the four JTAG pins. That gives up hardware JTAG, which this board had
already lost in practice -- the USB pins go to the OTG peripheral, and
debugging runs over the UART0 test pads. 1k per channel is about 2 mA, plenty
behind a case window.

## Placement

`tools/place_keypad.py` places all six. Y is depth from the board's top edge.

| part | x | y | reaches |
|------|---|---|---------|
| power slider | 11.0 | 2.30 | knob to y = -0.80 |
| IR emitter | 22.0 | 1.20 | lens 0.30 mm inside the edge |
| USB-C | 36.0 | 3.67 | mouth flush at y = 0 |
| status LED | 48.0 | 0.90 | lens 0.20 mm inside the edge |
| BOOT | 57.0 | 1.50 | plunger to y = -0.54 |
| RESET | 66.0 | 1.50 | plunger to y = -0.54 |

The tightest gap between any two courtyards is 2.4 mm, between BOOT and RESET.
There is 6.6 mm of board left of the slider and 7.2 mm right of RESET.

The four mechanical parts are rotated 180 degrees so their actuators face the
edge, each leaving about 0.8 mm proud for the case wall to capture. **The two
LEDs are not rotated** -- their lenses are already the -y end of the body, and
turning them round would aim them into the middle of the board. Both sit just
inside the edge rather than proud of it, so the case needs a window rather
than a slot: clear for the IR, diffused for the RGB.

One thing to watch: this USB-C receptacle anchors with through-hole shield
legs, so it leaves solder fillets on the front of the board, under the panel.
The panel's foam tape will swallow a 0.1 mm fillet, but check it on a dry fit
rather than after gluing. A receptacle with SMD-only shell tabs avoids the
question entirely if you find one you can buy.
