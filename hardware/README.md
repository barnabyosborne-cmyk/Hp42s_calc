# Hardware — case and keycaps

Barnaby's own CAD. Nothing generated here.

Constraints the electronics impose:

- Case **148 × 80 × 15 mm**, board about **144 × 76 mm**, 4 layer.
- Face budget, from Barnaby's measurements of a real 42S rather than a
  reconstruction: the keyboard area is **70 × 78 mm**, its datum 5 mm in from
  the left and 9 mm up from the bottom. That leaves **61 mm** above it for the
  bezel and display, and a **9 mm chin** below.
- Key pitch: rows **12.0 mm** throughout; columns **12.5 mm** on rows 1–3 and
  **15.0 mm** on the numeric block of rows 4–7, with the left column staying
  on the 8.75 mm centre. Full table in `docs/keypad-geometry.md`.
- Keycaps 6.0 mm tall: 7.5 mm wide on rows 1–3 and in the left column,
  10 mm wide on the numeric block, and ENTER 20 mm wide.
- Keycap actuator must be **≤ 25 % of dome diameter**, centred. That is a
  Snaptron rule and it is why the centre pad in the footprint is small.
- Battery bay behind the keyboard: one clean **50 × 60 mm** rectangle, 5 mm
  deep, ≥ 15 mm clear of the module antenna.
- Panel mounts on the front of the board; its tail folds through a slot to a
  connector on the back, so the connector height stays out of the front stack.
