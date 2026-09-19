# HP-42S clone — connection table

> This document is the reasoning. `elec/src/*.ato` is the same wiring in a form
> the compiler checks — `ato build` turns it into a netlist. If the two ever
> disagree, the `.ato` is what gets fabricated, so fix this file to match.

Rev C, 18 September 2026. Case 148 × 80 × 15 mm, board ~144 × 76 mm, 4 layer.

**How to read this.** IC connections are given by *signal name*, not pin number
— `BQ25185.IN`, not `BQ25185 pin 3`. That is deliberate: pin numbering comes
from the symbol you place in KiCad, and inventing pin numbers here is exactly
the kind of error that costs a board spin. Attach each net to the named pin and
the wiring is correct whatever the numbering turns out to be.

**Everything below still needs checking against the datasheets before fab.**
Pinouts, footprint land patterns and polarity are the three things I cannot
verify from here.

---

## 1. Power nets

| Net | Source | Loads |
|---|---|---|
| `VBUS` | USB-C receptacle VBUS | `BQ25185.IN`, ESD array, 1 µF to GND |
| `BAT` | Cell + | `BQ25185.BAT`, `MAX17048.CELL`, 10 µF to GND |
| `SYS` | `BQ25185.SYS` | `TPS63900.VIN`, 22 µF to GND |
| `+3V3` | `TPS63900.VOUT` | Module `3V3`, panel `VCI`/`VDD`, `MAX17048.VDD`, all pull-ups, 22 µF + 100 nF |
| `GND` | — | Everything. Single plane on layer 2 |

### Power part connections

| Part | Pin (by name) | Net / component |
|---|---|---|
| **BQ25185** | `IN` | `VBUS` |
| | `SYS` | `SYS` |
| | `BAT` | `BAT` |
| | `GND`, thermal pad | `GND` |
| | `ISET` | R to GND — sets charge current, size for 0.5 C of the cell you fit |
| | `ILIM` | Strap for 500 mA input limit |
| | `/CE` | `GND` (charging always enabled) |
| | `/CHG` | `CHG_STAT` → module `GPIO48`, 100 kΩ pull-up to `+3V3` |
| **TPS63900** | `VIN` | `SYS` |
| | `VOUT` | `+3V3` |
| | `L1`, `L2` | 2.2 µH inductor — keep this loop tight, it is the only node that radiates |
| | `VSEL` | `GND` (fixed 3.3 V; tie high only if you want dynamic voltage scaling later) |
| | `FB` | Resistor divider from `+3V3` for 3.3 V |
| | `EN` | `+3V3` |
| | `GND`, thermal pad | `GND` |
| **MAX17048** | `VDD` | `+3V3` |
| | `CELL` | `BAT` |
| | `SDA` / `SCL` | `I2C_SDA` / `I2C_SCL` |
| | `/ALRT` | Leave unconnected, or bring to a spare GPIO if you want low-battery interrupts |
| | `GND` | `GND` |
| **USB-C** | `VBUS` (both) | `VBUS` |
| | `CC1`, `CC2` | 5.1 kΩ each to `GND` — **two separate resistors, not one shared** |
| | `D+`, `D−` (both pairs) | `USB_DP`, `USB_DM` |
| | `SHIELD` | `GND` through a 1 MΩ ‖ 4.7 nF, or direct — your call |
| **TPD4E05U06** | channels | `USB_DP`, `USB_DM`, `CC1`, `CC2` |
| | `GND` | `GND` |

---

## 2. ESP32-S3-MINI-1-N8 GPIO map

**This map assumes the -N8 variant (8 MB flash, no PSRAM).** GPIO33–38 are only
free because there is no octal PSRAM. If you ever switch to the -N4R2, the
panel interface has to move.

| GPIO | Signal | Notes |
|---|---|---|
| 1 | `KEY_COL0` | RTC-capable, needed for `ext1` wake |
| 2 | `KEY_COL1` | RTC |
| 4 | `KEY_COL2` | RTC |
| 5 | `KEY_COL3` | RTC |
| 6 | `KEY_COL4` | RTC |
| 7 | `KEY_COL5` | RTC |
| 8 | `KEY_ROW0` | Output during scan, driven low during sleep |
| 9 | `KEY_ROW1` | |
| 10 | `KEY_ROW2` | |
| 11 | `KEY_ROW3` | |
| 12 | `KEY_ROW4` | |
| 13 | `KEY_ROW5` | |
| 14 | `KEY_ROW6` | |
| 16 | `LED_RED` | Status LED red die. Driven LOW to light — common anode |
| 17 | `I2C_SDA` | 4.7 kΩ pull-up to `+3V3` |
| 18 | `I2C_SCL` | 4.7 kΩ pull-up to `+3V3` |
| 19 | `USB_DM` | Fixed by silicon |
| 20 | `USB_DP` | Fixed by silicon |
| 21 | `BUZZER` | LEDC PWM → 1 kΩ → piezo sounder. Drives the element directly |
| 33 | `EPD_CS` | |
| 34 | `EPD_DC` | |
| 35 | `EPD_RST` | |
| 36 | `EPD_BUSY` | Input. Also the light-sleep wake source during a refresh |
| 37 | `EPD_SCK` | |
| 38 | `EPD_MOSI` | |
| 39 | `LED_GREEN` | Status LED green die. Driven LOW. MTCK, so taking it gives up pad JTAG |
| 43 | `UART0_TX` | Test pad only |
| 44 | `UART0_RX` | Test pad only |
| 47 | `IR_LED` | Optional HP-82240 printing → 2N7002 gate |
| 48 | `CHG_STAT` | From `BQ25185./CHG` |

Deliberately unused: `GPIO0`, `3`, `45`, `46` are the four strapping pins, and
their reset defaults (Espressif table 4-1: `GPIO0` weak pull-up, `GPIO3`
floating, `GPIO45` and `GPIO46` weak pull-down) are already what this board
wants, so `GPIO3`, `45` and `46` carry nothing at all. `GPIO0` carries the BOOT
button and its test pad.

Chip pins 26–32 are the module's internal flash. Only `GPIO26` comes out of the
module, and it is free on the `-N8` — it is the PSRAM pin on an `-N4R2`.

Free: `GPIO26`, `40`, `41`, `42`. `GPIO40` is earmarked for driving the sounder
in antiphase if 75 dB turns out to be too quiet. Hardware JTAG is already gone,
because `GPIO39` is the status LED's green die.

---

## 3. Key matrix

37 keys on a 6 × 7 grid, no diodes. Five grid positions are unused: column 5 is
only populated on the top two rows. Key numbers are the calculator core's own
ordering, so a scan can pass them straight to `core_keydown()`.

| | COL0 | COL1 | COL2 | COL3 | COL4 | COL5 |
|---|---|---|---|---|---|---|
| **ROW0** | Σ+ `1` | 1/x `2` | √x `3` | LOG `4` | LN `5` | XEQ `6` |
| **ROW1** | STO `7` | RCL `8` | R↓ `9` | SIN `10` | COS `11` | TAN `12` |
| **ROW2** | ENTER `13` | ENTER `13` | x↔y `14` | +/− `15` | E `16` | ← `17` |
| **ROW3** | ▲ `18` | 7 `19` | 8 `20` | 9 `21` | ÷ `22` | — |
| **ROW4** | ▼ `23` | 4 `24` | 5 `25` | 6 `26` | × `27` | — |
| **ROW5** | SHIFT `28` | 1 `29` | 2 `30` | 3 `31` | − `32` | — |
| **ROW6** | EXIT/ON `33` | 0 `34` | . `35` | R/S `36` | + `37` | — |

`ENTER` spans COL0 and COL1 on ROW2 and uses **two domes wired in parallel**,
both on `KEY_ROW2` / `KEY_COL0`. `COL1` is genuinely unused on ROW2.

### Per-key wiring

Every key is one dome site: pad 1 (outer ring) → its **column** net, pad 2
(centre) → its **row** net. So `SW19` (the `7` key) has pad 1 on `KEY_COL1`
and pad 2 on `KEY_ROW3`.

Ring-to-column rather than ring-to-row is deliberate: the ring is the larger
conductor and the columns are the nets held at a defined level during sleep,
so the wake path sees the lower impedance.

### Sleep and wake

Before sleeping, all 7 row GPIOs are driven **low** as outputs and the 6 column
GPIOs are inputs with internal pull-ups, armed as `ext1` wake sources on
`ANY_LOW`. Any keypress shorts a column to a row and pulls that column down.
No scanner IC, no external pull-ups, no standing current.

---

## 4. Display — GDEY0266T90, 24-pin 0.5 mm FPC

| FPC signal | Net |
|---|---|
| `BUSY` | `EPD_BUSY` |
| `RES` | `EPD_RST` |
| `D/C` | `EPD_DC` |
| `CS` | `EPD_CS` |
| `SCL` | `EPD_SCK` |
| `SDA` | `EPD_MOSI` |
| `VCI`, `VDD` | `+3V3` |
| `GND`, `VSS` | `GND` |
| charge-pump pins | Per the panel datasheet — several caps and a boost inductor |

The charge-pump network is the part people get wrong. Copy it from Good
Display's own reference schematic for this panel rather than from a generic
SSD1680 example; the cap values differ between panels.

Panel mounts on the **front** of the board with the FPC folding through a slot
to a **back-side** connector, so the connector's height stays out of the front
stack-up.

---

## 5. Misc

| Part | Connection |
|---|---|
| Buzzer | `BUZZER` → 1 kΩ → piezo sounder → `GND`. Murata figure A. It is a ~10 nF capacitor, not a coil, so there is no FET and no flyback diode |
| IR LED | `+3V3` → LED → 22 Ω → 2N7002 drain; gate from `IR_LED` via 1 kΩ |
| Status LED | `+3V3` → common anode; each die → 1 kΩ → its GPIO. Red and green together read as amber |
| Power slider | Wiper → `REG_EN`, one throw → `SYS`, **other throw deliberately unconnected**; 1 MΩ from `REG_EN` to `GND` holds it off |
| Test pads | `BAT`, `SYS`, `+3V3`, `GND`, `UART0_TX`, `UART0_RX`, `EN`, `GPIO0` (BOOT) |
| `EN` | 10 kΩ to `+3V3`, 1 µF to `GND`. This is the MCU's reset, not the regulator's enable |

---

## 6. Layout notes that follow from this

- **The row pitch is what squeezes, not the columns.** A 10 mm dome on the
  12.0 mm row pitch leaves 1.6 mm between adjacent ODs and 0.6 mm between
  courtyards. That is not enough to route a column between them on the front.
  Put the column nets on an inner layer and come up into each ring with a via
  placed outside the dome courtyard. If routing turns painful, dropping to
  `F08210` domes throughout gives 3.1 mm vertically and a lighter action.
  Horizontally there is room either way: 12.5 mm pitch on rows 1-3 and 15.0 mm
  across the numeric block. See `docs/keypad-geometry.md`.
- Nothing inside a dome circle: no vias, no silkscreen, no test points. The
  array has to sit on a flat surface.
- Keep the charger, regulator, fuel gauge and FPC connector in the strip behind
  the display and along the bottom edge beside the module, so the battery bay
  behind the keyboard stays one clean 50 × 60 mm rectangle.
- Module at the bottom edge, antenna overhanging the board outline, all copper
  cleared beneath it, ≥15 mm from the cell.
- The `TPS63900` switch node and its inductor loop is the only fast node on the
  board. Keep it under a few mm² and away from the panel's SPI.
