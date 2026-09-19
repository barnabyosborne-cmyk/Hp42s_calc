# Breadboarding with parts already on the bench

Barnaby has a **Seeed Studio XIAO ESP32-S3** and a **Waveshare 26337**
2.66" e-Paper (G) module (panel GDEY0266F51H, controller JD79667) left over
from another project. This is what those two can and cannot prove about this
design, checked against the vendors' own specifications on 2026-09-19.

## Short answer

Use the XIAO. Do not expect the (G) panel to stand in for ours — it is a
different controller with a 26 second refresh — but it is worth keeping on
the bench as a **mechanical** mock-up, because its glass is the same size as
ours to a hundredth of a millimetre.

## The XIAO ESP32-S3 — same silicon, a third of the pins

Same chip family as the ESP32-S3-MINI-1-N8 on our board, so everything in
`firmware/main/` that is not a pin number compiles and runs on it unchanged:
the SPI driver, the keypad scan, the deep-sleep and ext1 wake path.

The problem is the header. The XIAO breaks out **11 GPIOs**:

| Header | D0 | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| GPIO | 1 | 2 | 3 | 4 | 5 | 6 | 43 | 44 | 7 | 8 | 9 |

Our board needs **19**: 6 keypad columns + 7 keypad rows + CS, DC, RST, BUSY,
SCK, MOSI. The full 6 × 7 keyboard alone wants 13, so it does not fit even
with the panel unplugged.

Two other differences worth knowing before the pin map is copied across:

- The XIAO carries an **ESP32-S3R8 with octal PSRAM**, so GPIO33–37 are
  consumed by the PSRAM bus and are not on the header at all. Those are
  exactly the pins `board.h` gives the panel — we chose the no-PSRAM `-N8`
  module precisely so they would be free. Panel pins must be remapped for
  any XIAO bring-up; do not carry the remap back into `board.h`.
- GPIO43/44 (D6/D7) are UART0, the serial console. Usable, but not while
  watching `idf.py monitor` over the UART.

### Getting the whole keyboard onto it anyway

An **MCP23017** costs three XIAO pins (SDA, SCL and INT) and gives back 16,
which covers all 13 keypad lines with room to spare. That leaves eight pins
for the panel, which is enough. The catch is that the scan code then talks
I²C rather than driving GPIOs directly, so `keypad.c` would need a parallel
implementation that gets thrown away later. Worth it only if the goal is to
feel the whole keyboard under the fingers; for proving the scan algorithm, a
3 × 3 corner of the matrix on bare XIAO pins proves the same thing.

## The Waveshare 26337 — wrong controller, right size

| | Waveshare 26337 (on the bench) | GDEY0266T90 (the design) |
|---|---|---|
| Controller | JD79667 | SSD1680 |
| Resolution | 360 × 184 | 296 × 152 |
| Colours | black / white / yellow / red | black / white |
| Full refresh | **26 s** | ~2 s |
| Partial refresh | **not supported** | ~0.4 s |
| Active area | 60.05 × 30.69 mm | 60.088 × 30.704 mm |

Three consequences:

1. **`firmware/main/epd.c` will not drive it.** It is written against the
   SSD1680 command set — 0x24/0x26 RAM writes, 0x22 update sequences, the
   0x18 temperature sensor select. JD79667 is a different command set with a
   two-bits-per-pixel framebuffer for the four colours. Nothing transfers
   except the SPI plumbing and the BUSY handshake.
2. **26 seconds per update, with no partial mode.** That is not a tuning
   problem, it is what four-colour ink costs: the panel has to shuttle three
   pigments into place. A calculator cannot be driven off it at all. Any
   timing measured on this panel says nothing about the 0.4 s figure the
   e-paper decision was made on.
3. **The glass is the same size as ours** — 60.05 × 30.69 mm against
   60.088 × 30.704 mm, which is the same panel size rounded differently.
   So it is an accurate stand-in for the **bezel question that is still
   open**: hold it in the case at 8 mm from the top edge and again at 14 mm
   and see which looks right. That is a decision no simulation settles.

## What to buy to test the real display

A **GDEY0266T90 with a DESPI-C02 adapter board**. The DESPI-C02 is Good
Display's universal 24-pin 0.5 mm FPC e-paper breakout with 2.54 mm headers,
which is the connector our panel uses; Good Display sell the two together.
That combination runs `epd.c` as written, on the XIAO, with the six panel
pins remapped to header pins. It is the only way to see the real refresh
time before the board exists.

## Suggested order of work

1. **Panel first, on the real GDEY0266T90 + DESPI-C02.** Six pins, no
   keypad, nothing else on the breadboard. Confirms the SSD1680 init
   sequence and gives the honest per-keystroke number.
2. **Keypad second, panel unplugged.** A 3 × 3 corner on bare XIAO pins
   confirms the scan, the debounce and the ext1 wake.
3. **Both together only with an MCP23017**, and only if the full keyboard
   feel matters at this stage.
