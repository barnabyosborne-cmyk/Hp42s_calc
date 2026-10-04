#!/usr/bin/env python3
"""
How long a charge lasts, from the parts' own figures and a usage pattern.

    python3 tools/battery_life.py                      # the standard profiles
    python3 tools/battery_life.py --hours 1 --keys 600 # your own day
    python3 tools/battery_life.py --hours 1 --keys 600 --ble-min 30 --light-min 10
    python3 tools/battery_life.py --sources            # every figure and where it came from

The model is a day with four states in it:

  off       deep sleep with the rail up (there is no power switch, see
            docs/power-control.md). The rest of the day.
  on, idle  light sleep between keystrokes, SRAM kept. "Hours on per day" is
            this, including the minutes before auto-off.
  keystroke a short burst of CPU at full speed (scan, debounce, Plus42,
            render, SPI), then a partial refresh with the chip in light sleep
            waking on BUSY -- firmware/README.md rule 2.
  full      every Nth partial becomes a full refresh, and every power-off
            draws one more (epd_blank_and_sleep).

Everything the ESP32-S3, the panel and the leakage draw is on the 3.3 V rail,
so it goes through the TPS63900 and is divided by its efficiency AT THAT LOAD.
The charger, the fuel gauge and the frontlight sit on BAT/SYS and are taken
straight from the cell. Rail power is converted to cell current at the cell's
average discharge voltage.

Every figure is in PARTS below with its source. The ones marked "check" have
not been read off the datasheet in this repo's history -- run with --sources
to list them -- and the headline numbers should not be quoted as final until
they have. The structure does not change when they do; only the table.
"""

import argparse
import math

# ---------------------------------------------------------------------------
# Figures. (value, unit, source, verified)
# ---------------------------------------------------------------------------

PARTS = {
    # --- cell ---
    "cell_mAh":          (1250, "mAh", "6 x 38 x 50 mm LiPo (the 2.7in board's bay), "
                                       "scaled from 1600 for 6x45x55 by volume", True),
    "cell_usable":       (0.90, "",    "fraction above the firmware's low-battery "
                                       "cut-off; a LiPo at ~3.4 V under load "
                                       "has ~5-10 % left", False),
    "cell_v_avg":        (3.70, "V",   "LiPo nominal, average over a discharge", True),
    "self_discharge":    (0.02, "/month", "LiPo pouch, docs/power-control.md", False),

    # --- 3.3 V rail ---
    "v_rail":            (3.30, "V",   "TPS63900 set point, elec/src/power.ato", True),
    "esp_deep_sleep_uA": (8.0,  "uA",  "ESP32-S3 datasheet, Deep-sleep, RTC memory "
                                       "and RTC peripherals up (docs/connections.md)", True),
    "esp_light_sleep_uA": (240, "uA",  "ESP32-S3 datasheet, Light-sleep, "
                                       "firmware/README.md idle state", False),
    "esp_active_mA":     (24,   "mA",  "firmware/README.md Active state; CPU only, "
                                       "radio off", False),
    "key_active_s":      (0.050, "s",  "CPU awake per keystroke before the panel "
                                       "takes over; a guess, measure on the "
                                       "breadboard (docs/breadboard.md step 1)", False),
    "leak_uA":           (5.0,  "uA",  "rest of the board, docs/power-control.md", False),
    "panel_refresh_mA":  (3.0,  "mA",  "SSD1680 + external booster, average during "
                                       "a refresh; Good Display quote a few mA "
                                       "for 2.66 in panels. Measure it", False),
    "panel_sleep_uA":    (1.0,  "uA",  "SSD1680 deep sleep", False),
    "partial_s":         (0.40, "s",   "partial refresh, the accepted cost of "
                                       "e-paper (build plan, 2026-09-19)", False),
    "full_s":            (3.0,  "s",   "full refresh, mode 1 waveform", False),
    "full_every":        (10,   "partials", "firmware/main/epd.c, 'every tenth "
                                       "partial is the usual rule'", True),

    # --- straight from the cell ---
    "tps_iq_uA":         (0.075, "uA", "TPS63900 quiescent current, TI "
                                       "(75 nA, title of the datasheet)", True),
    "chg_iq_uA":         (4.0,  "uA",  "BQ25185 battery-only quiescent current, "
                                       "docs/connections.md", False),
    "gauge_uA":          (4.0,  "uA",  "MAX17048 hibernate, docs/connections.md", False),
    "imu_uA":            (6.0,  "uA",  "LSM6DSV16X + LIS2MDL both powered down, about "
                                       "3 uA each (ST datasheets, not yet read here)", False),
    "frontlight_standby_uA": (5.0, "uA", "TPS61165 shutdown + 1 M pull-down, "
                                       "docs/front-face.md", True),
    "frontlight_mA":     (20,   "mA",  "reading level, from the cell, "
                                       "docs/front-face.md", True),
    "ble_mA":            (3.0,  "mA",  "BLE connected, 0 dBm, modem sleep between "
                                       "connection events, rail average. Rough", False),
}

# TPS63900 efficiency against output current, VIN about 3.6 V, VOUT 3.3 V.
# Interpolated on log(current). TI headline 92 % at 10 uA; the rest is the
# usual shape of this part's curve, NOT yet read off the datasheet figure.
TPS_EFF = [
    (1e-6, 0.85),
    (1e-5, 0.90),
    (1e-4, 0.92),
    (1e-3, 0.93),
    (1e-2, 0.93),
    (1e-1, 0.92),
    (4e-1, 0.86),
]
TPS_EFF_VERIFIED = False

# Usage profiles: hours on (idle) per day, keystrokes per day, power-offs per
# day. The 2 h / 1500 row is the one the older 15-month figure was quoted for.
PROFILES = [
    ("drawer",     0.0,    0, 0),
    ("light",      0.25, 150, 2),
    ("daily",      1.0,  600, 4),
    ("heavy",      2.0, 1500, 6),
    ("exam day",   4.0, 3000, 8),
]


def P(name):
    return PARTS[name][0]


def tps_eff(i_amps):
    if i_amps <= TPS_EFF[0][0]:
        return TPS_EFF[0][1]
    if i_amps >= TPS_EFF[-1][0]:
        return TPS_EFF[-1][1]
    x = math.log10(i_amps)
    for (i0, e0), (i1, e1) in zip(TPS_EFF, TPS_EFF[1:]):
        if i0 <= i_amps <= i1:
            x0, x1 = math.log10(i0), math.log10(i1)
            return e0 + (e1 - e0) * (x - x0) / (x1 - x0)
    raise AssertionError


def rail_to_cell_mA(i_rail_mA):
    """Cell current for a load on the 3.3 V rail, through the buck-boost."""
    if i_rail_mA <= 0:
        return 0.0
    eff = tps_eff(i_rail_mA / 1000)
    return i_rail_mA * P("v_rail") / (eff * P("cell_v_avg"))


def day(hours_on, keys, offs, ble_min=0.0, light_min=0.0, frontlight=False):
    """mAh drawn from the cell per day, broken down by where it goes."""
    uA = 1e-3
    s_per_h = 3600.0

    # Time spent refreshing and computing comes out of the idle/off hours.
    fulls = keys / P("full_every") + offs
    busy_h = (keys * (P("key_active_s") + P("partial_s"))
              + fulls * P("full_s")) / s_per_h
    on_h = max(hours_on - busy_h, 0.0)
    ble_h = ble_min / 60
    off_h = max(24.0 - max(hours_on, busy_h), 0.0)

    rail_floor = (P("leak_uA") + P("panel_sleep_uA") + P("imu_uA")) * uA  # always there
    idle_rail = P("esp_light_sleep_uA") * uA + rail_floor
    off_rail = P("esp_deep_sleep_uA") * uA + rail_floor
    refresh_rail = P("esp_light_sleep_uA") * uA + P("panel_refresh_mA") + rail_floor
    active_rail = P("esp_active_mA") + rail_floor

    out = {}
    out["off (deep sleep)"] = rail_to_cell_mA(off_rail) * off_h
    out["on, idle"] = rail_to_cell_mA(idle_rail) * on_h
    out["keystrokes"] = (rail_to_cell_mA(active_rail) * keys * P("key_active_s")
                         + rail_to_cell_mA(refresh_rail) * keys * P("partial_s")
                         ) / s_per_h
    out["full refreshes"] = rail_to_cell_mA(refresh_rail) * fulls * P("full_s") / s_per_h
    # BLE rides on top of whatever the chip was doing, so only the extra.
    out["bluetooth"] = (rail_to_cell_mA(P("ble_mA") + idle_rail)
                        - rail_to_cell_mA(idle_rail)) * ble_h
    standing = (P("chg_iq_uA") + P("gauge_uA") + P("tps_iq_uA")) * uA
    if frontlight:
        standing += P("frontlight_standby_uA") * uA
    out["charger + gauge + regulator"] = standing * 24
    out["frontlight"] = P("frontlight_mA") * light_min / 60
    return out


def self_discharge_mAh_per_day():
    return P("cell_mAh") * P("self_discharge") * 12 / 365.25


def life_days(mAh_per_day, with_self_discharge=True):
    load = mAh_per_day + (self_discharge_mAh_per_day() if with_self_discharge else 0)
    return P("cell_mAh") * P("cell_usable") / load


def fmt_days(d):
    if d >= 60:
        return f"{d / 30.44:5.1f} months"
    return f"{d:5.1f} days  "


def print_breakdown(parts):
    total = sum(parts.values())
    for k, v in parts.items():
        if v:
            print(f"    {k:30s} {v:7.3f} mAh/day  {100 * v / total:4.0f} %")
    print(f"    {'total':30s} {total:7.3f} mAh/day")
    print(f"    {'+ self-discharge':30s} {self_discharge_mAh_per_day():7.3f} mAh/day")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--hours", type=float, help="hours switched on per day")
    ap.add_argument("--keys", type=int, help="keystrokes per day")
    ap.add_argument("--offs", type=int, default=None,
                    help="power-offs per day (each costs a full refresh); "
                         "default one per 15 min on, at least 1")
    ap.add_argument("--ble-min", type=float, default=0.0,
                    help="minutes per day with a BLE connection up")
    ap.add_argument("--light-min", type=float, default=0.0,
                    help="minutes per day with the frontlight on (reading level)")
    ap.add_argument("--frontlight", action="store_true",
                    help="unit is built with the frontlight (adds its 5 uA standing)")
    ap.add_argument("--set", action="append", default=[], metavar="NAME=VALUE",
                    help="override any figure in PARTS, e.g. --set panel_refresh_mA=5")
    ap.add_argument("--sources", action="store_true",
                    help="list every figure, its source, and whether it is checked")
    a = ap.parse_args()

    for s in a.set:
        k, v = s.split("=", 1)
        if k not in PARTS:
            ap.error(f"no figure called {k}; see --sources")
        val, unit, src, _ = PARTS[k]
        PARTS[k] = (type(val)(float(v)), unit, "set on the command line", True)

    if a.sources:
        for k, (v, unit, src, ok) in PARTS.items():
            print(f"{'  ok ' if ok else 'check'}  {k:22s} {v:>8} {unit:9s} {src}")
        print(f"{'  ok ' if TPS_EFF_VERIFIED else 'check'}  TPS63900 efficiency curve "
              f"(TPS_EFF): {', '.join(f'{i*1e3:g} mA {e:.0%}' for i, e in TPS_EFF)}")
        return

    extras = dict(ble_min=a.ble_min, light_min=a.light_min, frontlight=a.frontlight)

    if a.hours is not None or a.keys is not None:
        hours = a.hours or 0.0
        keys = a.keys or 0
        offs = a.offs if a.offs is not None else (max(1, round(hours * 4)) if hours else 0)
        parts = day(hours, keys, offs, **extras)
        total = sum(parts.values())
        print(f"{hours:g} h on, {keys} keystrokes, {offs} power-offs a day"
              + (f", {a.ble_min:g} min BLE" if a.ble_min else "")
              + (f", {a.light_min:g} min frontlight" if a.light_min else ""))
        print_breakdown(parts)
        print(f"  lasts {fmt_days(life_days(total)).strip()} "
              f"({fmt_days(life_days(total, False)).strip()} ignoring self-discharge)")
        return

    print(f"{P('cell_mAh')} mAh cell, {P('cell_usable'):.0%} usable, "
          f"self-discharge {P('self_discharge'):.0%}/month"
          + (", frontlight fitted" if a.frontlight else ""))
    print()
    print(f"  {'profile':10s} {'h on':>5s} {'keys':>5s}  {'mAh/day':>8s}  "
          f"{'lasts':>13s}  {'no self-disch.':>14s}")
    for name, hours, keys, offs in PROFILES:
        total = sum(day(hours, keys, offs, **extras).values())
        print(f"  {name:10s} {hours:5g} {keys:5d}  {total:8.2f}  "
              f"{fmt_days(life_days(total)):>13s}  "
              f"{fmt_days(life_days(total, False)):>14s}")
    print()
    print("  where a 'daily' day goes:")
    print_breakdown(day(1.0, 600, 4, **extras))
    unchecked = sum(1 for v in PARTS.values() if not v[3]) + (not TPS_EFF_VERIFIED)
    if unchecked:
        print(f"\n  {unchecked} figures are not yet checked against a datasheet "
              f"or a measurement; --sources lists them.")


if __name__ == "__main__":
    main()
