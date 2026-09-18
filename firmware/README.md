# Firmware — porting Plus42

Nothing here yet.

Plus42 is Thomas Okken's extension of Free42: algebraic expressions, units,
directories, TVM, function plotting. Same GPLv2, same author, same repo
shape — a portable `common/` core plus a thin per-platform shell. Porting
means writing a new shell, not touching the core.

Source: <https://codeberg.org/thomasokken/plus42desktop>. The GTK shell is the
closest reference for a bare-metal port; the iOS and Android shells carry
platform baggage that does not help.

## The shell API

About 22 functions the platform has to supply. The ones that carry real work:

- `shell_blitter` — the whole display. **Must not assume a fixed size.**
  Plus42 resizes the display at runtime (`ROW±`, `COL±`, `SETDS`, `WIDTH`,
  `HEIGHT` in the DISP menu), 2–99 rows and 22–999 columns. Cells are 6 × 8 px.
- `shell_annunciators` — the status strip.
- `shell_request_timeout3`, `shell_delay`, `shell_milliseconds` — timing.
- `shell_read_saved_state` / `shell_write_saved_state` — state to flash.
- `shell_get_mem`, `shell_low_battery`, `shell_powerdown`.
- `shell_print`, `shell_write`, `shell_read` — printing and file transfer.
- `shell_get_acceleration` / `_location` / `_heading` — stub these out.

## Power state machine

Three states, and two rules that matter more than the rest:

| State | Trigger | Cell current |
|---|---|---|
| Active | key or timer | ~24 mA |
| Idle | 0.5 s quiet, light sleep (SRAM retained) | ~265 µA |
| Off | 5 min quiet, deep sleep, state flushed to flash | ~25 µA |

1. **Never deep-sleep with a core timeout pending.** `core_keytimeout1` fires
   at 0.25 s and `core_keytimeout2` 2 s later; losing them loses keystrokes.
2. **Light-sleep through the panel refresh, waking on BUSY.** Spinning through
   a 400 ms partial update instead costs about 5× the energy per keystroke —
   0.70 µAh becomes 3.8 µAh. This one decision is the difference between
   15 months and 3.

A naive always-active port gets about 40 hours.
