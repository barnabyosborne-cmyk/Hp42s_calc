# Battery life

`tools/battery_life.py` works out how long a charge lasts from the parts'
figures and a usage pattern. It needs nothing but Python 3.

    python3 tools/battery_life.py                        # the standard profiles
    python3 tools/battery_life.py --hours 1 --keys 600   # your own day
    python3 tools/battery_life.py --hours 1 --keys 600 --ble-min 30 --light-min 10 --frontlight
    python3 tools/battery_life.py --set panel_refresh_mA=5   # try a different figure
    python3 tools/battery_life.py --sources              # every figure and where it came from

## What it says (27 September 2026)

1600 mAh, 90 % usable, 2 % a month self-discharge, no Bluetooth, no light:

| profile | on per day | keystrokes | load | lasts | ignoring self-discharge |
|---|---|---|---|---|---|
| drawer | 0 | 0 | 0.53 mAh/day | 30 months | 90 months |
| light | 15 min | 150 | 0.72 mAh/day | 27 months | 66 months |
| daily | 1 h | 600 | 1.29 mAh/day | 20 months | 37 months |
| heavy | 2 h | 1500 | 2.30 mAh/day | 14 months | 20 months |
| exam day | 4 h | 3000 | 4.07 mAh/day | 9 months | 12 months |

The heavy row is the old "15 months" case, and it still comes out at about
that.

## What it means

- **Self-discharge is the biggest single drain** for anyone but a heavy user:
  about 1 mAh a day against 1.3 for a daily day. Nothing on the board can
  change that.
- **A keystroke costs about 0.67 µAh**, the same as `firmware/README.md`'s
  0.70, and that only holds while the firmware light-sleeps through the
  refresh. Spinning through it instead costs about five times as much.
- **The frontlight and Bluetooth dwarf everything else when they are on.**
  Ten minutes of light a day is 3.3 mAh, more than two heavy days of
  calculating. Half an hour of BLE is about 1.4 mAh, and that figure is
  rough.

## How far to trust it

The model is sound; several inputs are not yet. `--sources` marks each one
`ok` or `check`. The ones that move the answer most:

1. **`panel_refresh_mA`** (3 mA assumed). Each keystroke's refresh is a third
   of a daily day, so doubling it takes "daily" from 20 to about 18 months.
   Measure it on the breadboard panel (`docs/breadboard.md` step 1).
2. **`key_active_s`**, how long the CPU runs flat out per keystroke (50 ms
   assumed). Same measurement.
3. **The TPS63900 efficiency curve.** 92 % at 10 µA is TI's headline; the
   rest of the table is the usual shape, not read off the datasheet figure.
4. **The charger's and fuel gauge's standing current** (4 µA each, from
   `docs/connections.md`), which are 15 % of a daily day between them.

The datasheets could not be read when this was written: the environment's
network policy allowed `ti.com` but not `www.ti.com`, where TI's PDFs live.
