# Driving the e-paper panel

## Is there a driver board as well as the panel?

No, and yes.

There is no driver *board*. The controller for the GDEY0266T90 is an SSD1680
bonded directly to the panel's own glass, under the black strip at the edge of
the tail. You cannot buy it separately and you cannot design it out. When you
see a Good Display "driver board" — the DESPI-C02 and its relatives — you are
looking at a carrier that holds an FPC connector, a level shifter you do not
need, and the circuit below. It exists so that a panel can be plugged into an
Arduino. We are not plugging into an Arduino.

There is a driver *circuit*, and it was missing. It is now in
`elec/src/display.ato`. Eighteen parts.

## Why the panel needs anything at all

Electrophoretic ink moves when you push it with about +22 V and pull it with
about -20 V. The SSD1680 generates both rails itself, but it has no inductor
and no power switch on the glass, so it reaches outside for them through two
pins on the tail:

| pin | name | direction | what it does |
|-----|------|-----------|--------------|
| 2 | GDR | out | gate drive. The controller switches the external FET with this. |
| 3 | RESE | in | current sense. The voltage across R2 tells it how hard the inductor is being driven. |

The regulation loop is closed inside the panel. No MCU pin goes near it and
there is nothing for the firmware to do beyond the ordinary SSD1680 power-on
sequence. When the controller is asleep it stops driving GDR, the 1 M pulldown
holds the gate off, and the whole network draws nothing.

## The circuit

One switching node does both rails, which is why the parts count is so low.

    3V3 --+-- L1 47uH --+-------------------- D3 >|-- PREVGH --> VGH (pin 21)
          |             |                                |
         C4            Q1 drain                         C5
        4u7            Q1 gate <-- GDR (pin 2)          1u
          |            Q1 source --> RESE (pin 3)        |
         GND            |           |                   GND
                       R1 1M       R2 2R2
                        |           |
                       GND         GND

                        |
    switching node -----+-- C3 4u7 --+-- D2 >|-- GND
                                     |
                                     +-- |< D1 -- PREVGL --> VGL (pin 23)
                                                      |
                                                     C11 1u
                                                      |
                                                     GND

D3 is an ordinary boost diode and makes the positive rail. D1, D2 and C3 are a
charge pump hanging off the same node and make the negative one: D2 clamps the
pump node to ground on the up-swing, and on the down-swing the node goes below
ground and drags charge off VGL through D1.

Then ten capacitors, all 1 uF/25 V unless noted, all straight to ground:

| on | panel pin | Good Display ref |
|----|-----------|------------------|
| VCI (also 3V3) | 16 | C6 |
| VDD | 18 | C7 |
| VSH1 | 20 | C9 |
| VSH2 | 5 | C2 |
| VSL | 22 | C10 |
| VGH / PREVGH | 21 | C5 |
| VGL / PREVGL | 23 | C11 |
| VCOM | 24 | C12 |
| 3V3 input, 4.7 uF | — | C4 |
| pump, 4.7 uF | — | C3 |

The 25 V rating is not optional. VGH sits near +22 V and a 16 V part there
fails. Nor is it free: a 25 V X5R in 0603 loses most of its capacitance under
bias, which is why these are 0603 and not 0402 like everything else on the
board.

VDD (pin 18) is the controller's *own* internal regulator output. It takes a
capacitor and nothing else. Driving it kills the panel.

BS (pin 8) goes hard to ground, which selects 4-wire SPI. Pins 1, 4 and 19 are
no-connects; 6 and 7 are the touch I2C on the touch version of this glass and
ours has none.

## Where these numbers come from

Good Display's *GDEY0266T90 Specification*, revision 24.12.03, page 28. Not
from a generic SSD1680 application note: the inductor and the pump caps differ
between panels that share this controller, and a 2.13 inch reference circuit
will not drive this one properly.

Their spare-parts table, which is the actual purchasing spec:

    C1-C12   0603/0805, X5R/X7R, >= 25 V
    R1, R2   0603/0805, 1%, >= 0.05 W
    D1-D3    MBR0530: >= 30 V reverse, >= 500 mA, Vf <= 430 mV
    Q1       Si1304BDL / NX3008NBK: BVdss >= 30 V, Vgs(th) 0.9 V typ,
             Rds(on) <= 2.1 Ohm at Vgs = 2.5 V
    L1       Sumida CDRH2D18 or LDNP-470NC, 47 uH, Io = 500 mA max
    P1       24 pins, 0.5 mm pitch

**The MBR0530 is discontinued**, so D1-D3 are `1N5819HW`: 40 V, 1 A, same
SOD-123 outline, stocked everywhere. The 430 mV forward limit is Solomon's
number at their 500 mA sizing current; this pump draws tens of milliamps,
where a 1N5819HW sits well under it. The one thing to keep an eye on is
reverse leakage, because a charge pump holds its rail rather than being fed
one, and Schottky leakage is what drains VGH between refreshes. Nexperia's
PMEG family is the better class of part if a SOD-123 one can be sourced.

**Q1 is the Si1308EDL**, not either part Solomon name, and it beats the spec
they set: 30 V, Rds(on) 0.185 Ohm max at Vgs = 2.5 V against their 2.1 Ohm
limit (Vishay document 63399 rev C). Its package is **SOT-323 / SC-70**, not
the SC-75A this repo had it as.

Q1's low gate threshold is the reason it is not the 2N7002 used elsewhere on
this board: the panel drives that gate from its own 3.3 V logic, and a 2N7002
is only specified to turn on by 2.5 V.

## Layout notes

The switching node — L1, Q1's drain, C3 and D3's anode — is the only fast node
on the board other than the buck-boost. Keep that loop small and keep it away
from the panel's SPI, which runs alongside it into the same connector.

R2 carries the switched current, so it wants a short path to the ground pour,
and its 1% tolerance is real: the panel sets its peak inductor current from the
voltage across it.

L1 in an NR3015 body is 1.5 mm tall, which makes it the tallest part on the
board after the module and the cell.
