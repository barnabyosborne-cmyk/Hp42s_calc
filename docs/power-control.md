# On and off

Barnaby asked on 24 September 2026 whether the power slider could go, since a
real HP-42S has no such thing: `ON` is a key, and `OFF` is shift-`EXIT`.

**Yes, and it costs one component, one net and no new parts.** The keypad
already has everything needed. What follows is the argument, the firmware, and
the three details that will bite if they are skipped.

---

## What the slider actually did

Not much, which is the point. It drove the TPS63900's `EN` pin and nothing
else:

    SYS ---- pin 1 \
                    pin 2 ---- TPS63900 EN
    GND ---- pin 3 /

It never carried the load. `EN` is now tied hard to `SYS`, so the 3.3 V rail is
up whenever there is a charged cell in the case, and a 1 MΩ pull-down that used
to hold `EN` low went with the slider — worth 4 µA of a 25 µA sleep budget.

Charging was always upstream of it, so nothing about USB changes.

---

## Off is deep sleep

"Off" is the ESP32-S3 in deep sleep with the rail still up. The e-paper holds
its image with no power at all, so an off calculator looks exactly as off as one
with the rail pulled down.

The standing current, from `docs/connections.md`'s breakdown less the slider's
pull-down:

| | |
|---|---|
| ESP32-S3 deep sleep, RTC memory up | 8 µA |
| BQ25185 charger | 4 µA |
| MAX17048 fuel gauge, hibernate | 4 µA |
| TPS63900 quiescent | 0.075 µA |
| leakage, the rest of the board | ~5 µA |
| **total** | **about 21 µA** |

Add about 5 µA on units built with the frontlight, whose driver sits on `SYS`
and cannot be switched off either.

The old slider-off state was about 10 µA, so **a drawer costs twice what it
used to and it still does not matter.** A lithium pouch cell loses something
like 2 % of its charge a month to self-discharge — on 1600 mAh that is roughly
33 mAh a month, against 15 mAh a month at 21 µA. The chemistry was always the
thing emptying the cell in storage, not the electronics.

In daily use the difference is smaller still. The 15-month figure comes from
2 h/day plus 1500 keystrokes, and sleep is about a sixth of that budget, so
dropping 4 µA of 25 is worth a couple of per cent.

---

## Why only the ON key wakes it

This is the part that makes the whole thing work, and it falls out of the
matrix for free.

`EXIT/ON` is at **row 6, column 0** (`keypad.ato`, row 6). Column 0 is on
`IO1`, which is RTC-capable; row 6 is on `IO14`, which is also RTC-capable —
every GPIO from 0 to 21 is, on the S3.

So before sleeping, **drive row 6 low on its own, leave rows 0 to 5 floating,
and arm `ext1` on column 0 alone.**

- `EXIT/ON` shorts column 0 to row 6, pulls column 0 down, and wakes the chip.
- Every other key in column 0 — `Σ+`, `ENTER`, `UP`, `DOWN`, `SHIFT` — shorts
  column 0 to a row that is floating. Nothing moves.
- Every key on row 6 — `0`, `.`, `R/S`, `+` — pulls its own column down, and
  those columns are not in the wake mask. Nothing moves.

One key, with no dedicated GPIO and no extra part. The general scan, where all
seven rows are driven low and all six columns are armed, is still what a running
calculator uses between keystrokes; this narrower version is only for off.

---

## The firmware

```c
#define COL0  GPIO_NUM_1     /* EXIT/ON's column */
#define ROW6  GPIO_NUM_14    /* EXIT/ON's row    */

static void calculator_off(void)
{
    epd_blank_and_sleep();   /* one full refresh, then SSD1680 deep sleep */
    state_save();            /* LittleFS, a few kB */

    /* 1. Wait for the key that asked for this to come back up. */
    gpio_set_direction(COL0, GPIO_MODE_INPUT);
    gpio_pullup_en(COL0);
    while (gpio_get_level(COL0) == 0)
        vTaskDelay(pdMS_TO_TICKS(20));

    /* 2. Rows 0..5 float, so nothing but row 6 can pull a column down.
          rtc_gpio_isolate also takes their leakage out of the budget. */
    for (int i = 0; i < 6; i++)
        rtc_gpio_isolate(key_row_gpio[i]);

    /* 3. Row 6 keeps driving low right through the sleep. */
    rtc_gpio_init(ROW6);
    rtc_gpio_set_direction(ROW6, RTC_GPIO_MODE_OUTPUT_ONLY);
    rtc_gpio_set_level(ROW6, 0);
    rtc_gpio_hold_en(ROW6);

    /* 4. All six columns pulled up so none of them floats, but only
          column 0 is a wake source. */
    for (int i = 0; i < 6; i++) {
        rtc_gpio_init(key_col_gpio[i]);
        rtc_gpio_set_direction(key_col_gpio[i], RTC_GPIO_MODE_INPUT_ONLY);
        rtc_gpio_pulldown_dis(key_col_gpio[i]);
        rtc_gpio_pullup_en(key_col_gpio[i]);
    }
    esp_sleep_enable_ext1_wakeup_io(BIT64(COL0), ESP_EXT1_WAKEUP_ANY_LOW);

    esp_deep_sleep_start();
}
```

On the way back up: `esp_sleep_get_wakeup_cause()` returns
`ESP_SLEEP_WAKEUP_EXT1`, then `rtc_gpio_hold_dis(ROW6)` and `rtc_gpio_deinit()`
on all thirteen pins, restore the ordinary scan, debounce for 20 ms, and confirm
`EXIT/ON` really is down before drawing anything. If it is not, go straight back
to sleep — see the ghost path below.

Note `ESP_EXT1_WAKEUP_ANY_LOW` rather than `ALL_LOW`: the original ESP32 only
had the all-low form, the S2 and S3 added any-low, and every example written for
the original chip will use the wrong one.

### Three things to get right

1. **Wait for the key to be released before sleeping.** `ext1` is
   level-triggered, not edge-triggered. Going to sleep with column 0 still low
   wakes the chip immediately, forever. This matters most on the off path,
   because the user has just pressed shift then `EXIT` and their finger is still
   on it. That is step 1 above and it is not optional.

2. **Hold row 6 through the sleep.** An ordinary GPIO output stops driving when
   the digital domain powers down. `rtc_gpio_hold_en()` on an RTC pin keeps it
   driving, which is why row 6 has to be one of GPIO 0–21 — `IO14` is.

3. **Three keys held at once can wake it, and that is fine.** With rows 0 to 5
   floating they still conduct, so a chain can reach row 6: `SHIFT` joins
   column 0 to row 5, `1` joins row 5 to column 1, `0` joins column 1 to row 6.
   Hold all three and column 0 goes low. Two keys cannot do it, and three
   specific keys at once is a pocket, not a user. The scan on wake sees that
   `EXIT/ON` is not down and goes back to sleep in a few milliseconds.

While `EXIT/ON` is held the internal pull-up — about 45 kΩ — passes roughly
70 µA. Only while held.

---

## What this gains

**The clock keeps running.** The slider took the RTC down with the rail, so
Plus42's `TIME` and `DATE` needed setting after every power-up unless a backup
cell was added. Deep sleep keeps the RTC alive, so they survive.

With a caveat worth writing down: there is no 32.768 kHz crystal on this board,
so the RTC runs on the internal RC oscillator. ESP-IDF calibrates it against the
main crystal at boot, but it drifts with temperature and nothing recalibrates it
during a sleep. **Expect minutes a day, not seconds.** Better than a clock that
stops, worse than a watch.

If that is not good enough, the fix is a 32.768 kHz crystal and two load caps on
the S3's `XTAL_32K` pair. Confirm the pin numbers against the S3 datasheet
before drawing anything; on this board the obstacle is that one of that pair is
already carrying `LED_RED`, and the clean swap is to move `LED_RED` to `IO40`,
which `docs/top-edge.md` records as free. Three parts and a pin shuffle.

**There is no power-fail-save problem any more.** `docs/top-edge.md` used to
list "unsaved state is lost" as a cost of the slider, because the rail collapsed
in milliseconds with no warning. Deep sleep is entered deliberately, so the
state is saved before it. Persisting after every completed operation is still
the right thing to do — it covers a flat cell and a reset — but it is no longer
load-bearing.

---

## What this loses

**There is no way to take the rail away.** That mattered for one case: firmware
that has hung.

- `RESET` still works. It is a hardware reset of the chip, wired from the
  module's `EN` to ground, and it goes nowhere near the firmware.
- `BOOT` held with a tap of `RESET` still brings up the ROM bootloader whatever
  is in flash.
- Firmware that hangs *drawing current* is reachable by `RESET`. Firmware that
  boot-loops will flatten the cell, and the answer to that is `BOOT` and a
  reflash.

**For shipping, or a long drawer, pull the cell connector.** `BT1` is the hard
off, and at 21 µA against self-discharge there is no other reason to want one.
The MAX17048 also has a `SLEEP` bit in its `MODE` register if its 4 µA ever
needs to go — software, no hardware.

---

## What changed in the files

- `elec/src/power.ato` — `sw_power` and `r_reg_en` deleted, `reg.EN ~ sys`, and
  the fuel gauge's comment rewritten: its I²C pull-ups are on a rail that never
  goes away now, so it never shuts down and never loses what ModelGauge has
  learned. That is 4 µA standing and a better reading out of a drawer.
- `elec/src/parts.ato` — `component SlideSwitch` kept but not instantiated.
- `tools/place_board.py`, `tools/place_keypad.py` — `SW39` gone from the top
  edge, which frees board X 6 to 16 on that edge. Nothing has claimed it.
- `docs/top-edge.md` — five parts on the edge, not six.

Nothing in `keypad.ato` or `connections.md` changed. The hardware for this was
already there; only the firmware knew it was not.
