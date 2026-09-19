# The top edge: USB-C, power slider, reset

All three sit on the 80 x 15 mm top face of the case, and all three are on the
**back** of the board.

## Why the back

The board is 76 x 144 mm inside a 148 x 80 mm case. Above the panel there are
only 6 mm of board, because the front face budget spends 8 mm on the top bezel
and the 2 mm case inset eats a quarter of that.

Six millimetres is not enough. Measured from KiCad's own courtyards:

| part | reaches into the board |
|------|------------------------|
| Alps SKRTLAE010 reset button | 3.55 mm |
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

## Placement

`tools/place_keypad.py` now places all three, by footprint rather than by
reference designator, since atopile renumbers SW39/SW40 whenever a part is
added. Y is depth from the board's top edge.

| part | x | y | actuator reaches |
|------|---|---|------------------|
| slider | 14.0 | 2.30 | y = -0.80 |
| USB-C | 38.0 | 3.67 | y = 0.00 (mouth flush) |
| reset | 62.0 | 1.50 | y = -0.54 |

Each is rotated 180 degrees so the actuator faces the edge, and each leaves
about 0.8 mm of actuator standing proud of the board for the case wall to
capture.

One thing to watch: this USB-C receptacle anchors with through-hole shield
legs, so it leaves solder fillets on the front of the board, under the panel.
The panel's foam tape will swallow a 0.1 mm fillet, but check it on a dry fit
rather than after gluing. A receptacle with SMD-only shell tabs avoids the
question entirely if you find one you can buy.
