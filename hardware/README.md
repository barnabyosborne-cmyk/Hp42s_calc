# Hardware — case and keycaps

Barnaby's own CAD. Nothing generated here.

Constraints the electronics impose:

- Case **148 × 80 × 15 mm**, board about **144 × 76 mm**, 4 layer.
- Face budget that makes 148 mm close: 8.0 top bezel + 36.3 display outline +
  6.0 gap + 84.0 keyboard (7 rows × 12.0 mm) + 13.7 chin. The chin is the only
  free number — protect the row pitch over it. Below about 8 mm of chin a
  taller shell becomes the honest answer.
- Key pitch **11.8 mm across × 12.0 mm down**.
- Keycap actuator must be **≤ 25 % of dome diameter**, centred. That is a
  Snaptron rule and it is why the centre pad in the footprint is small.
- Battery bay behind the keyboard: one clean **50 × 60 mm** rectangle, 5 mm
  deep, ≥ 15 mm clear of the module antenna.
- Panel mounts on the front of the board; its tail folds through a slot to a
  connector on the back, so the connector height stays out of the front stack.
