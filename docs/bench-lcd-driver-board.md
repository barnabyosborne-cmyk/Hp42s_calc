# Bench rig: Waveshare ESP32-S3-LCD-Driver-Board

Barnaby's bench board for firmware bring-up (2 October 2026). It carries an
ESP32-S3-WROOM-1 **N8R8**: 8 MB flash, 8 MB octal PSRAM. The calculator board
has the N16R2 (16 MB flash, 2 MB quad PSRAM), so:

- cap PSRAM at 2 MB in menuconfig and keep the partition table inside 8 MB;
- octal PSRAM takes IO35-IO37 here, so the panel/NAND clock moves to IO4 on
  the bench only (it is IO37 on the board). Everything else that can keep its
  board pin does.

Only 15 GPIOs reach its headers: TX(43), RX(44), 4, 5, 15, 7, 17, 16, 6 on
the left; 42, 2, 1, 39, 41, 40 on the right. The full 13-line keypad does not
fit, and Barnaby is not prototyping it (the 37-key matrix passed in Wokwi).

**Check before wiring:** the board's own touch connector, I2C and LCD may
share some header pins. Read Waveshare's schematic for IO4-IO7, IO15-IO17 and
IO39-IO42 first and swap to a free one if any is taken.

| Function | Bench pin | Board pin | Notes |
|---|---|---|---|
| Panel + NAND SCK | IO4 | IO37 | shared bus |
| Panel + NAND MOSI | IO5 | IO38 | shared bus |
| Panel SCS (active high) | IO40 | IO40 | |
| Panel DISP | IO6 | IO45 | |
| Panel EXTCOMIN | RTC CLKOUT, or IO7 on LEDC at 1-60 Hz | RTC CLKOUT | |
| Panel 5 V | header 5V, always on | TPS610997 on IO35 | no boost on the bench |
| NAND CS# | IO41, 10k to 3V3 | IO41 | |
| NAND SO | IO42 | IO42 | WP#, HOLD# to 3V3; 100 nF at VCC |
| I2C SDA (RTC, gauge) | IO17 | IO17 | 4.7k pull-ups if the breakout has none |
| I2C SCL | IO16 | IO18 | |
| Key column 0 (wake) | IO1 | IO1 | columns must be RTC GPIOs for ext1 wake |
| Key column 1 (wake) | IO2 | IO2 | |
| Key row 0 | IO39 | IO8 | 2 x 2 = four keys |
| Key row 1 | IO15 | IO9 | |
| Console | USB-C (USB-Serial-JTAG) | same | TX/RX left free |

Breakouts needed: the panel's 10-pin 0.5 mm FPC (an FH34-style FPC-to-DIP
board), and the NAND's 8 x 6 mm WSON/U-PDFN (a WSON-8 to DIP adapter).
