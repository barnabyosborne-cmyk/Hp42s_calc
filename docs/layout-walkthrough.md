# Laying out this board in KiCad, step by step

This is the click-by-click version, written for someone who has not done a PCB
layout before. It assumes nothing except that KiCad 10 is installed and this
repo is on your machine.

`docs/pcb-process.md` is the map of the whole job, from netlist to boards in
your hand. **This file is steps 2 to 7 of that map, in detail.** When you are
done here you will have a finished board file, and you go back there for the
fabrication outputs, the ordering and the bring-up.

Everything below was checked against KiCad 10's own source, so the menu paths
and the keyboard shortcuts are the real ones, not remembered ones.

---

## What you are actually about to do

The netlist already says what connects to what. It says nothing about *where*.
Layout is the job of deciding where each of the 119 parts sits on a 76 × 144 mm
rectangle, and then drawing the copper that makes the 83 connections real.

There are five distinct activities and they are not equally hard:

| | What | How long |
|---|---|---|
| A | Set the project up | 30 minutes, once |
| B | Import and place the parts | an evening, and you will redo it |
| C | Route the copper | two or three evenings |
| D | Pour the ground planes | an hour |
| E | Check it | an hour, and worth two |

B is the one that matters. A good placement makes the routing almost draw
itself; a bad one makes it impossible, and you find out four hours in. This is
why the placement order in step 7 is an order and not a list.

### Two rules before you start

**Commit after every numbered step.** The board file is text and git will diff
it. When something goes wrong at step 9 you want to be able to go back to the
end of step 8, not to the beginning.

```bash
cd "/Users/barnaby osborne/Documents/Personal/02 Projects/Calculator/Hp42s_calc1"
git add -A && git commit -m "layout: step N done"
```

**Quote the path in every shell command.** The checkout lives at

```
/Users/barnaby osborne/Documents/Personal/02 Projects/Calculator/Hp42s_calc1
```

which has spaces in it in three places. Unquoted, bash reads
`cd /Users/barnaby osborne/...` as *cd to `/Users/barnaby`, with `osborne/...`
as a second argument*, and you get "No such file or directory" pointing at a
path that plainly exists. The shell commands below are already written with the
quotes in. Python is not affected — `open('...')` takes the whole string — so
the scripting console in step 6 needs no special treatment.

**Do not fight the software.** If a step does not behave the way this file says
it will, stop and say so rather than working around it. Everything here is
checked, but it is checked against source code, not against your screen.

---

## Step 1 — Learn six keys and one panel

Five minutes here saves an evening later. KiCad is modal and hover-driven in a
way that is unusual, and fighting it is most of a beginner's pain.

### The thing that trips everyone up

**KiCad acts on whatever the mouse is hovering over, not on what you clicked.**
Hover a footprint and press `M` and it starts moving — no click needed. If you
click first and then move the mouse away, the key still applies to the thing
under the cursor. Keep the pointer on the thing you mean.

### The six keys

| Key | Does |
|---|---|
| `M` | Move the thing under the cursor. Click to drop it. |
| `R` | Rotate 90° anticlockwise. `Shift+R` goes the other way. |
| `F` | Flip to the other side of the board. |
| `E` | Open its properties dialog. |
| `Esc` | Cancel whatever you are in the middle of. |
| `Ctrl+Z` | Undo. Works on everything, including a whole script run. |

`Delete` or `Backspace` deletes. `Ctrl+0` zooms to fit the board, which is how
you find things you have lost.

### The panel on the right

It is called the **Appearance** panel. If it is not showing, **View → Panels →
Appearance**. It has tabs across the top; the one you live in is **Layers**.

Two different things happen in that tab and it is worth knowing they are
different:

- **Clicking a layer's name makes it the active layer**, and the active layer
  is where new tracks go. This is the single most common source of "why is my
  track on the wrong side of the board".
- **The checkbox beside it hides or shows that layer.** Hiding is not deleting.
  Turning off `B.Cu` while you work on the front is normal practice and changes
  nothing about the board.

### Two more worth knowing now

- `Ctrl+U` switches between mm and inches. **Work in mm.** Everything in this
  repo is mm. If a dialog shows inches, press it.
- `Ctrl+Shift+M` is the measuring tape. Use it constantly.

---

## Step 2 — Make the project

KiCad needs a project file to hang a board off. It does not exist in this repo
yet.

Neither does the folder it goes in, in a fresh clone: git cannot store an empty
directory, so `elec/layout/` only appears once something is in it. Make it
first:

```bash
cd "/Users/barnaby osborne/Documents/Personal/02 Projects/Calculator/Hp42s_calc1"
mkdir -p elec/layout
```

1. Open **KiCad** (the project manager, the one with the workflow icons).
2. **File → New Project…**
3. Navigate into this repo, to `elec/layout/`.
4. Name it `default`. Leave "Create a new folder for the project" **ticked**.
5. Save.

You now have `elec/layout/default/default.kicad_pro` and a `.kicad_pcb` beside
it. That exact path matters — the footprint library path in step 3 is written
relative to it.

6. In the project manager, double-click **`default.kicad_pcb`** to open the PCB
   editor. This is the window you will live in.

You will never open the schematic editor. atopile is the schematic; the `.ato`
files in `elec/src/` are the drawing, and `build/default.net` is what comes out
of them.

**Done looks like:** an empty PCB editor with a blank sheet, and the title bar
saying `default.kicad_pcb`.

```bash
git add -A && git commit -m "layout: empty KiCad project"
```

---

## Step 3 — Point KiCad at this repo's own footprints

Seven of the 28 footprints on this board do not exist in KiCad's libraries —
the two dome sites, the two TI leadless packages, the side-looking IR emitter,
the status LED and the side-push recovery button. They live in
`elec/footprints/hp42s.pretty/`, generated by `tools/gen_dome_footprints.py`
and `tools/gen_ic_footprints.py` from the vendors' own drawings.

Without this step the netlist import fails on 44 of the 119 parts.

1. In the **PCB editor**, **Preferences → Manage Footprint Libraries…**
2. Choose the **Project Specific Libraries** tab, not Global. The path below
   only makes sense inside this project.
3. Add a row. There are two buttons under the table and either will do: the one
   whose tooltip reads **"Add empty row to table"** gives you a blank line to
   type into, and **"Add Existing"** opens a file picker you can point at
   `elec/footprints/hp42s.pretty` and let KiCad fill in for you.

   Whichever you use, the row has to end up reading:

   | Column | Value |
   |---|---|
   | Nickname | `hp42s` |
   | Library Path | `${KIPRJMOD}/../../footprints/hp42s.pretty` |
   | Library Format | `KiCad` |

   `${KIPRJMOD}` is KiCad's variable for "the folder this project is in", so
   the path means *up two levels from `elec/layout/default/`, then into
   `elec/footprints/`*. If you used the file picker and it filled in an
   absolute path like `/Users/barnaby/…`, click the cell and retype it as
   above. The absolute one works on your machine today and nowhere else.

4. **OK**.

**Check it before moving on: View → Footprint Library Browser.** A window opens
with every library listed down the left. Click `hp42s` and you should see
**nine** entries:

```
Alps_SKRTLAE010_SidePush
Dialight_599_BiColor_1208_RA
Dialight_599_White_1208_RA
Dome_4Leg_10mm
Dome_4Leg_8.5mm
SameSky_UJ20-C-H-G-SMT-1A-P16_USB-C
TI_DQA0010A_USON-10_2.5x1mm_P0.5mm
TI_DSK0010A_WSON-10-1EP_2.5x2.5mm_P0.5mm_EP2x1.2mm
Vishay_VSMB2943SLX01_SideView
```

Nine, but only seven get used. `Dialight_599_White` belongs to the frontlight
LEDs, which sit on a separate sliver of FR4 and are not on this board.
`SameSky_UJ20` is the USB-C receptacle this board used to have before it moved
to the GCT part on 22 September 2026; it is kept only so old board files still
open.

If `hp42s` is not in the list at all, or is there but empty, the path is wrong.
Check that `elec/footprints/hp42s.pretty/` really is two levels up from your
project folder — from `elec/layout/default/`, `../../footprints/` should land
you in `elec/footprints/`.

---

## Step 4 — Board Setup, before there is anything on the board

Do this now rather than later. Changing the layer count after you have routed
is possible but unpleasant, and the net classes decide how wide your tracks
come out, so setting them first means you never have to go back and widen
anything.

**File → Board Setup…** opens a dialog with a tree down the left side.

### 4a. Layers

Go to **Board Stackup → Physical Stackup**. At the top, set **Copper Layers:
4**. (Some builds put that selector on the **Board Editor Layers** page just
above it instead; either is the same setting.)

Leave the **board thickness at 1.6 mm**, which is KiCad's default.

It was 1.0 mm until 23 September 2026, on the reasoning that a 15 mm case with
a cell on the back of it could use the 0.6 mm. Barnaby asked whether that would
flex under 37 dome switches. It would: a 1.0 mm board supported only at its
edges moves about 0.28 mm under a firm press, against 0.5 mm of dome travel,
which would make every key feel dead. 1.6 mm is 4.1× stiffer, the stack-up had
2.6 mm of slack to pay for it, and the panel's fold geometry had assumed
1.6 mm all along. The working is in `docs/board-thickness.md`.

The case stays at 15 mm.

You will now have four copper layers: `F.Cu`, `In1.Cu`, `In2.Cu`, `B.Cu`.

What each is for on this board:

| Layer | Use |
|---|---|
| `F.Cu` | dome pads, the panel's connector, short signal runs |
| `In1.Cu` | **solid ground.** Do not cut it up. |
| `In2.Cu` | 3.3 V pour, plus the keypad column and row nets |
| `B.Cu` | everything else, and a second ground pour |

The keypad matrix has to live on an inner layer because nothing can route
between the numeric dome sites on the front: they clear each other by 1.6 mm
and their courtyards by 0.6 mm. Each dome ring gets a via placed outside its
courtyard and drops to `In2.Cu`.

### 4b. Constraints

Go to **Design Rules → Constraints**.

Everything on this page is a **floor**, not a value. Nothing here decides how
wide your tracks come out — that is the net classes in 4c. These exist only to
make DRC shout when you draw something the fab cannot make, so the right
numbers are your fab's capabilities, not your preferences.

Four to set, in the **Copper** and **Holes** groups on the left:

| Setting | Value | Why |
|---|---|---|
| Minimum clearance | `0.2 mm` | every cheap fab beats this comfortably |
| Minimum track width | `0.15 mm` | you will not go this thin; it is the floor |
| Minimum via diameter | `0.5 mm` | see below — this one has to agree with the next two |
| Minimum drill size | `0.3 mm` | the smallest hole a cheap fab will drill without a surcharge |

And **leave "Minimum annular width" at KiCad's `0.1 mm`.**

**Those three numbers have to agree with each other**, which is the part that
is easy to get wrong. The annular ring is the copper left around a hole, so

```
annular width = (via diameter − drill) / 2
```

At a 0.5 mm via on a 0.3 mm drill that is exactly 0.1 mm, which is what the
annular rule asks for and what a cheap fab quotes. A 0.45 mm via on the same
drill gives only 0.075 mm, so a via drawn at the minimum diameter would fail
the annular rule — an internally inconsistent set of limits, which is worth
avoiding even though nothing on this board is drawn anywhere near these floors.
(The net classes in 4c use 0.6/0.3 and 0.8/0.4, so 0.15 and 0.2 mm of ring.)

**Leave every other field on the page alone.** KiCad's defaults are right for
this board and several of them matter:

- **Copper to edge clearance `0.5 mm`** keeps the pours back from the outline,
  which matters here because the left edge is notched and the module's antenna
  hangs off the bottom.
- **uVias** are microvias and there are none on this board.
- **Silk minimum text height `0.8 mm`** is about the smallest a fab will print
  legibly, and you have 38 dome sites to label.

These are all deliberately loose. A board this dense does not need fine-pitch
rules anywhere except under the module, and paying for tighter tolerances would
be paying for nothing.

### 4c. Net classes

*These* are the numbers that decide what gets drawn, as opposed to 4b's floors.
Each class says how wide a track on its nets comes out and how big its vias
are, and you can change a class later and have every net on it follow.

Go to **Design Rules → Net Classes**. The columns are `Name`, `Clearance`,
`Track Width`, `Via Size`, `Via Hole`, then `uVia Size`, `uVia Hole`,
`DP Width`, `DP Gap`, `Tuning Profile` and a `PCB Color` swatch. Only the first
five and the colour matter here; the microvia and differential-pair columns are
for things this board does not have.

There is a `Default` class already. Set it to `0.2` clearance, `0.2` track,
`0.6` via size, `0.3` via hole. Then add two more with the **+** button under
the table:

| Class | Clearance | Track Width | Via Size | Via Hole | For |
|---|---|---|---|---|---|
| `Default` | `0.2` | `0.2` | `0.6` | `0.3` | everything not named below |
| `power` | *blank* | `0.5` | `0.8` | `0.4` | the rails |
| `keypad` | *blank* | `0.2` | `0.6` | `0.3` | the 13 matrix nets |

**Leave a cell blank when you want Default's value.** These fields are optional
in KiCad 10, and the effective rules for a net are built by starting from
`Default` and letting the assigned class overwrite only the fields it actually
has set. So a blank `Clearance` on `power` is not "no clearance", it is
"whatever `Default` says" — and it stays right if you ever change `Default`.
Typing `0.2` into all three works too; it is just three places to remember
instead of one.

**`keypad` is deliberately identical to `Default`, and that is not a mistake.**
The matrix carries no current worth the name — a dome contact against a
pull-up, microamps — so there is nothing to make its tracks wider for, and
nothing about it that wants a different via.

It exists for a different reason, and you will be glad of it in step 7. In the
**Appearance** panel there is a **Nets** tab with a **Netclasses** section, and
right-clicking a class there gives you **Set Netclass Color** and **Hide All
Other Netclasses**. The keypad matrix is 13 nets across 38 dome sites, which is
most of the ratsnest on this board; being able to colour it, or switch it off
entirely while you place the power parts, is the difference between a readable
ratsnest and a grey fog. A class is the only handle KiCad gives you for that.

So set a colour on it while you are here — anything that stands out — and one
on `power` too.

### The half that actually does something

**The classes above apply to nothing until you assign nets to them.** That is
the **Netclass Assignments** table in the lower half of the same page, and it
starts empty. Add rows with its own **+** button — the one under *that* table,
not the one under the class list. Patterns use `*` as a wildcard:

| Pattern | Net class |
|---|---|
| `sys` | `power` |
| `bat` | `power` |
| `cell` | `power` |
| `v3v3` | `power` |
| `vbus` | `power` |
| `lx1` | `power` |
| `lx2` | `power` |
| `row*` | `keypad` |
| `col*` | `keypad` |

`gnd` stays on `Default` because it is going to be a poured plane, not tracks,
and the class width would only apply to the stubs.

Nine rows. If that table is empty when you close the dialog, `power` and
`keypad` exist and do nothing, every net is `Default`, and the rails come out
at 0.2 mm.

**The "Nets matching" panel on the right will be empty, and that is correct
right now.** It lists the nets on the board that a pattern catches, and the
board has no nets yet — they arrive with the netlist in step 5. Come back to
this page once they do; it turns into the cheapest check in this whole file.
Click each pattern in turn and you should see:

| Pattern | Nets | |
|---|---|---|
| `sys`, `bat`, `cell`, `v3v3`, `vbus`, `lx1`, `lx2` | 1 each | 7 |
| `row*` | `row0`–`row6` | 7 |
| `col*` | `col0`–`col5` | 6 |

**20 nets assigned, 63 left on `Default`.** A pattern showing 0 after the
import is a typo in the pattern, and a typo here is silent: the net simply
stays on `Default` and you find out when a 3 A rail turns out to be 0.2 mm
wide.

### 4d. Pre-defined sizes

Go to **Design Rules → Pre-defined Sizes** and add a couple of track widths you
will want to reach for by hand: `0.25 mm` and `0.8 mm`. During routing these
appear in a dropdown on the toolbar, so you can fatten a specific run without
editing its net class.

**OK** to close Board Setup.

```bash
git add -A && git commit -m "layout: 4-layer 1.6 mm stackup, net classes"
```

---

## Step 5 — Import the netlist

This is where the 119 parts arrive.

**First you have to build the netlist, because it is not in the repo.**
`build/` is in `.gitignore` — generated output does not belong in git — so
after a clone or a pull there is no `build/default.net` on your machine at all.
Run this before you go looking for it:

```bash
conda activate ato
cd "/Users/barnaby osborne/Documents/Personal/02 Projects/Calculator/Hp42s_calc1"
ato --non-interactive build
```

**The `conda activate ato` is not optional.** atopile lives in a conda
environment called `ato`, not in `base`, so a fresh terminal gives you
`-bash: ato: command not found`. `conda env list` shows the environments if the
name ever changes.

Note also that `--non-interactive` goes **before** `build`, not after. It is a
flag on the `ato` command itself, and putting it after gives you
`No such option: '--non-interactive'`.

It takes two to four minutes and ends with `Build complete!`. You now have
`build/default.net` and `build/default.csv`, the BOM.

Re-run it any time `elec/src/` changes, and re-import into KiCad afterwards.
That import is not a one-time operation and it does not disturb placement or
routing you have already done.

Now, in the PCB editor:

1. **File → Import → Netlist…**
2. **Netlist file:** browse to `build/default.net` at the repo root. Note that
   it is at the *repo* root, not under `elec/`.
3. **Link Method: "Link footprints using component tstamps (unique ids)".**

   **This one matters, and it is the opposite of what you might guess.** The
   other option links by reference designator. Do not use it.

   Here is why. atopile hands out designators in the order it meets components
   in the source. Add a resistor in the middle of `hp42s.ato` and everything
   after it shifts up one — I tested this on 22 September 2026 by inserting one
   resistor near the top of the file, and eleven resistors downstream of it got
   renumbered, `R14` through `R24` becoming `R15` through `R25`. The unique ids
   did not move at all. So designator linking would silently reassign eleven
   of your carefully placed parts to each other's positions, and tstamp linking
   just renames them in place.

4. **Options.** Leave **"Delete footprints with no components in netlist"** and
   **"Replace footprints with those specified in netlist"** ticked, and
   **"Group footprints based on symbol group"** and **"Delete tracks shorting
   multiple nets"** unticked. All four are already that way.

   **Untick "Delete/replace footprints even if locked".** KiCad ships it
   *ticked*, so this is an active change rather than something to leave alone.
   It costs nothing today, because nothing is locked yet, but the setting
   sticks: you lock the placed keypad at the end of step 6, and a re-import
   after that would walk straight through the lock and put all 38 dome sites
   back in the heap.

   Changing any option re-runs the preview on its own, so the list refreshes as
   you click.

5. **Press "Update PCB".** Not "Load and Test Netlist".

   Both read the netlist and fill the panel with the same list, but only
   `Update PCB` applies it; the other is a dry run, and it is the highlighted
   default button, so it is the easy one to press and feel finished. **The
   panel's own heading tells you which you are looking at**: it says *Changes
   to Be Applied* after a test, and *Changes Applied to PCB* after the real
   thing.

Read the message pane. **Expect `Total warnings: 9, errors: 0`.** Errors are
what matter, and there should be none. Every footprint resolves: 21 of the 28
from KiCad's own libraries, 7 from `hp42s`.

All nine warnings read `No net found for component <ref> pad <n>`, and all nine
are pins deliberately left unconnected:

| Part | Pads | Why |
|---|---|---|
| `U1` TPD4E05U06 | 6, 7, 9, 10 | TI marks them NC in table 4-2 of SLVSBO7O. Nothing inside the package touches them. |
| `U5` ESP32-S3-MINI-1 | 7, 26, 38, 41, 44 | `IO3`, `IO26`, `IO42`, `IO45`, `IO46` — spare GPIOs this design does not use. All 24 of the module's ground pins are connected. |

A warning naming any *other* reference or pad is not on this list and is worth
stopping for. If you imported before 23 September 2026 you will see 11 rather
than 9: the extra two are `J2 pad MP`, the display connector's metal hold-downs,
which are now tied to ground in `elec/src/display.ato`. Rebuild and re-import
and they go away.

If you see `Cannot add <ref> (footprint "hp42s:..." not found)`, step 3 did not
take — go back and fix the library path before doing anything else.

6. Close the dialog. All 119 footprints land in a heap near the origin,
   overlapping, with a dense cloud of thin lines between them. That cloud is
   the **ratsnest**: one line per connection that is not yet copper. It is
   supposed to look terrible.

**Done looks like:** 119 footprints on the sheet and no errors in the import
log. You can confirm the count with **Inspect → Show Board Statistics**.

```bash
git add -A && git commit -m "layout: import 119 footprints"
```

---

## Step 6 — Run the placement script

37 keys on a measured, non-uniform grid, plus a board outline with a notch in
it, plus seven parts whose positions were worked out to a hundredth of a
millimetre against case drawings. None of that should be done by dragging.

`tools/place_keypad.py` does it. It is a KiCad Python script and it runs
*inside* KiCad.

1. **Tools → Scripting Console.** A Python prompt opens in a panel.

   If that entry is not in the Tools menu, this KiCad was built without Python
   scripting — unusual for an official build, but it happens with some Linux
   distribution packages. Tell me and I will convert the script to something
   that edits the `.kicad_pcb` file directly instead.
2. Paste this, with the path adjusted to wherever the repo actually is:

```python
exec(open('/Users/barnaby osborne/Documents/Personal/02 Projects/Calculator/Hp42s_calc1/tools/place_keypad.py').read())
```

That is the real path on this machine, spaces and all; Python's quotes handle
them, so it needs no escaping. Use the **full absolute path** — the console's
working directory is not necessarily the project folder, and a relative path
here is the most common reason this step appears to do nothing.

3. Press Enter. It prints what it did:

```
top edge:
  SW39  power slider  -> front, (11.0, 3.0)
  D4    IR emitter    -> front, (22.0, 1.6)
  J1    USB-C         -> front, (36.0, 3.675)
  D5    status LED    -> front, (48.0, 1.8)
  SW40  reset         -> front, (66.0, 1.5)
  SW41  boot          -> front, (57.0, 1.5)
panel:
  J2    panel FPC     -> back, (9.0, 30.15), 90 deg -- check the mouth faces the left edge
  drew glass 71.82 x 36.30 on Cmts.User
  ...
drew a 76.0 x 144.0 mm outline on Edge.Cuts, with a 0.55 x 16.0 mm notch ...
placed 38 dome sites
```

If it throws a Python traceback, paste the whole thing back to me. The script's
arithmetic is checked but its KiCad API calls have never been run — that is
what the `UNTESTED IN KICAD` banner at the top of the file means, and the first
run is the test.

4. **Ctrl+0** to zoom to fit. You should now see the board rectangle, a 6 × 7
   grid of dome sites in the lower two thirds, a dashed outline of the display
   glass on `Cmts.User`, and the top-edge parts along the top.

### Two things to check by eye right now

**The FPC connector's mouth.** Hover `J2`, look at which way its opening
points. It must face the **notched left edge** of the board. If it points into
the middle of the board, open `tools/place_keypad.py`, change
`FPC_ANGLE = 90.0` to `270.0`, and run the script again. It is idempotent —
running it twice just puts everything back.

**The keyboard's position.** The dome grid should span board Y 59 to 137, with
about 7 mm of clear board below the bottom row and the display area above it.
Measure it with `Ctrl+Shift+M` if it looks off.

5. Now **lock the keypad** so you cannot nudge it by accident. Drag a selection
   box around the dome grid only, then press **`L`** (Toggle Lock) — it is also
   on the right-click menu. Locked footprints refuse to move until you unlock
   them, which is `L` again.

```bash
git add -A && git commit -m "layout: keypad grid, top edge, panel, outline"
```

---

## Step 7 — Place everything else

This is the judgement part of the job, and it is the part worth being slow
about. Roughly 60 parts are still in a heap at the origin.

### How to find a part

Do not hunt for it. **Ctrl+F**, type the reference designator, Enter — KiCad
selects it and centres the view on it. Press `M` with the cursor over it and it
comes with you.

(**Place → Place Footprints**, hotkey `A`, is the tool for adding a *new* part
from a library. You do not want it on this board — every part you need is
already on the sheet, put there by the netlist import.)

To see a whole circuit at once, hover anything on the net and press `` ` `` —
that is **Highlight Net**, and everything on it lights up. `U` is
**Select/Expand Connection**, which selects what is connected rather than just
colouring it. The **Net Inspector** panel (**View → Panels → Net Inspector**)
lists every net by name if you would rather go at it from that end.

**Turn the keypad matrix off while you do this.** Appearance panel → **Nets**
tab → **Netclasses**, right-click `keypad` → **Hide All Other Netclasses**, or
just untick it. Those 13 nets across 38 dome sites are most of the ratsnest on
the board and none of it is your problem until step 9.5. This is what the
`keypad` class in 4c was for.

### The rule that governs all of it

**Parts that belong to one circuit go together, and circuits that hate each
other go apart.** This board has three switching converters on it, each of
which is a small radio transmitter, and one radio receiver which is the
module's antenna. The whole of the placement below is the consequence.

### Where things go

Two decisions from 21 September 2026 shape this. The **cell goes at the top of
the back**, which pushes the electronics into the space behind the keyboard.
And the **top bezel is 14 mm**, which is what let the six top-edge parts move
to the front. See `docs/top-edge.md` and `docs/display-mounting.md`.

So the back of the board, top to bottom, is: battery bay (board Y 5 to 59),
then the FPC connector and the panel booster crammed into the top left of that
same region because the ribbon gives them nowhere else, then the keyboard from
Y 59 down, with the electronics tucked behind it.

### Place in this order

Each one constrains the next, which is why it is an order.

**7.1 — The panel's FPC connector (`J2`).** Already placed by the script, on
the back at board X 9.00, Y 30.15. **Do not move it.** The panel's tail is
14.30 mm long and after the fold there is 11.00 mm of reach; the connector's
pad row has to fall in the last 3 mm of that. Two millimetres to the right and
the flex pulls out of the contacts. Measure the real panel's tail before you
commit the board, because the drawing only gives it to ±0.3 mm.

**7.2 — The module (`U5`).** Back side, behind the keyboard, low on the board.

The antenna end must **overhang the board outline** with all copper cleared
beneath it. This is not optional and it is not a suggestion in the datasheet —
ground plane under a chip antenna detunes it into uselessness. The module's
footprint has a keepout area marked; put it past the edge.

The bottom edge of the board does this as well as the top used to, and it is
diagonally opposite the USB connector, which is what you want: USB is the
noisiest thing on the board and the antenna is the most sensitive.

**7.3 — The panel's booster (`L2`, `Q1`, `C3`, `D1`, `D2`, `D3`).** One tight
cluster right next to `J2`. This is a switching loop and every millimetre of
it is inductance you do not want. Keep the loop `L2` → `Q1` → ground → back to
`L2` as small as you physically can, and make sure its ground return runs
directly underneath it on `In1.Cu` rather than wandering off.

These two — `J2` and the booster — are the only things still pinned to the top
left of the back. The cell has to come down past them.

**7.4 — The buck-boost (`U3`, `L1`) and its capacitors.** Same discipline,
equally tight, and **far from 7.3**. Behind the keyboard. Two switchers close
together beat against each other and you hear it through the buzzer.

`U3` is a WSON-10 with a thermal pad that the datasheet says explicitly must be
connected to ground for correct operation. It is not optional and it is not
just heat.

**7.5 — The charger (`U2`) and the cell connector (`BT1`).** Near the USB-C at
`J1`, with the cell connection running away from the signal side of the board.

This is the one part of the design that *gained* from the 14 mm bezel. USB-C is
on the front now, so the charge current no longer has to run the length of the
board to reach a cell at the top.

`U2`'s TS/MR pin cannot float — it has 10 kΩ to ground in the netlist already.
Just make sure that resistor lands next to the pin and not across the board.

**7.6 — The fuel gauge (`U4`).** Anywhere convenient on the cell net. It draws
3 µA and it is not fussy.

**7.7 — The frontlight driver (`U6`, `L3`, `D6`, and its capacitors).** Only if
this unit is getting a light guide. Front side, in the strip between the panel
and the keyboard — board Y 48.3 to 59.0 — at the **right-hand end**, as far as
the board allows from `J2` and the panel booster at X 7–20.

It is a third switching node and it wants to be nowhere near the panel's SPI.

**7.8 — The test pads (`TP1`–`TP11`).** Put them somewhere you can get a probe
on with the board out of the case. `TP3` is the chassis ground bond for the
metal faceplate and belongs on the **front**, near the USB-C shield's ground
stitch — not near the module.

**7.9 — The decoupling capacitors.** Last, and deliberately.

Every 100 nF goes **hard against the pin it serves**, on the same side of the
board, with its ground end straight down a via into `In1.Cu`. A 100 nF placed
10 mm from its pin is decoration: at 100 MHz the track to it has more impedance
than the capacitor does.

The way to do this is one IC at a time. Find the IC, find its decoupling caps
by net, and tuck each one in. It is tedious and it is the difference between a
board that works and a board that mostly works.

### Leave room for the case to hold the board up

New on 23 September 2026, and it belongs here rather than at the end, because
it is a placement constraint and not a routing one.

37 dome switches need something behind the board taking the push, or the board
bends instead of the dome snapping. Board thickness only gets you so far —
`docs/board-thickness.md` has the numbers — and the rest has to come from the
case bearing on the board *inside* the keyboard area, not just around its edge.

The 14 mm bezel put the electronics behind the keyboard, so parts and support
posts now want the same space. As you place the back side, keep three or four
clear patches spread through the keyboard region for the case to push on. The
gaps between key columns are the natural place, since nothing routes there on
the front anyway. It does not have to be a regular grid and it does not have to
be perfect; going from edge-support-only to a few bearing points is worth as
much as the thickness change was.

### Done looks like

- Nothing overlaps. Run DRC (step 11) now if you want — courtyard overlaps show
  up as errors and it is a cheap check.
- No ratsnest line crosses the whole board. A long line means two things that
  belong together are not together. Fix the placement, not the routing.
- The battery bay on the back is clear from about board Y 5 to Y 59. Y 5 rather
  than Y 0 because the USB-C receptacle's four through-hole shield legs have
  their solder fillets there now, on the back, and a pouch cell resting on four
  solder fillets is not a risk worth taking.
- The module's antenna hangs off the board with nothing under it.

Expect to redo this once after you see how the routing goes. That is normal and
it is not wasted time.

```bash
git add -A && git commit -m "layout: place the electronics"
```

---

## Step 8 — Pour the ground planes

Do this before routing, not after. A poured plane gives every ground connection
a short return path, and routing on top of one is very different from routing
on bare board.

### 8.1 — The inner ground plane

1. In the **Layers** panel on the right, click **`In1.Cu`** to select it.
2. Press **`Alt+Z`**, or **Place → Draw Filled Zones**.
3. Click once on the board — a dialog opens.
4. Set **Net:** `gnd`. Layer should already be `In1.Cu`.
5. Leave **Pad Connections: Thermal reliefs** for now.
6. **OK**, then draw a rectangle a little *outside* the board outline by
   clicking each corner and double-clicking to finish. KiCad clips zones to the
   board edge automatically, so overshooting is correct.
7. Press **`B`** to fill all zones.

`In1.Cu` should go solid copper. **Leave it that way.** Every signal on this
board returns through it, and a slot cut in it forces a return current to go
the long way round, which is how a board that looks fine radiates.

### 8.2 — The back ground pour

Same again on **`B.Cu`**, net `gnd`. This one will be broken up by tracks and
that is fine; it is a supplement, not the plane.

### 8.3 — The 3.3 V pour

On **`In2.Cu`**, net `v3v3`, but **not** the whole board — draw it only over
the region where the ICs are, behind the keyboard. The rest of `In2.Cu` is
needed for the keypad matrix.

### 8.4 — The antenna keepout

The module's antenna must have no copper under it on any layer.

This is a different tool from the zone above, not an option on it:
**Place → Draw Rule Areas**, or `Ctrl+Shift+K`. In its dialog, select all four
copper layers and tick **"Keep out copper pours"** (and "Keep out tracks" and
"Keep out vias" while you are there). Then draw it over the antenna's overhang.

The zones will refuse to fill inside it, and DRC will complain if you route
through it, which is the point.

Press **`B`** again to refill everything.

```bash
git add -A && git commit -m "layout: ground planes and antenna keepout"
```

---

## Step 9 — Route, in this order

Routing is drawing copper. `X` starts a track from wherever you are hovering,
clicks place corners, double-click or `Enter` ends it, `Esc` abandons it,
`Backspace` undoes the last segment.

While routing, **`V` places a via and switches layer** in one action — this is
how you get from front to back mid-track. `+` and `-` step through layers.

### The order

**9.1 — The two switching loops, first.** The panel booster (`L2`/`Q1`) and the
buck-boost (`U3`/`L1`). Short, fat — use the `power` class or reach for the
0.8 mm predefined width — and returning to ground directly beneath themselves.
Do these while the board is empty and you have complete freedom, because they
are the two that cannot be compromised. If they end up long you will hear it
through the buzzer and see it on the panel.

**9.2 — Power distribution.** `sys`, `bat`, `v3v3`. Fat tracks, short paths.
`vbus` from the USB connector to the charger.

**9.3 — The panel's SPI** — `epd_sck`, `epd_mosi`, `epd_cs`, `epd_dc`,
`epd_rst`, `epd_busy`. Keep them away from both switch nodes. They are the only
fast signals on the board.

**9.4 — USB `usb_dp` and `usb_dm`.** As a pair, the same length, no stubs,
straight from `J1` through the ESD array `U1` to the module.

**KiCad's differential pair router will not recognise this pair, and you should
not waste time trying to make it.** KiCad decides what is a differential pair
by looking at the end of the net name, and it accepts exactly three spellings:
`+`/`-`, or an uppercase `P`/`N`. Ours are `usb_dp` and `usb_dm`, which match
none of them — and they cannot be renamed into a matching pair, because atopile
lowercases every net name on its way into the netlist. I checked both halves of
that: KiCad's matcher in `board.cpp`, and all 83 net names in `default.net`,
every one of which is lowercase even where the signal was declared in capitals.

So route them by hand with `X`, as two tracks side by side with a constant gap,
roughly the same length, on the same layer, over unbroken ground. That is all
the differential pair router would have done for you anyway.

They carry full-speed USB here, 12 Mbit/s over about 30 mm, so the length
matching is a formality. Keeping them together over solid ground is not.

**9.5 — The keypad matrix, last, on `In2.Cu`.** 13 nets, `row0`–`row6` and
`col0`–`col5`. It is slow, it is forgiving, and it is most of the copper on the
board.

Each dome ring gets a via placed **outside its courtyard** — there is 0.6 mm of
clearance between adjacent numeric domes' courtyards and nothing at all routes
between them on the front — and drops to `In2.Cu`, where there is room.

There are no diodes in this matrix, which means the firmware is responsible for
ghosting. That is already handled; see `docs/connections.md`.

**Done looks like:** DRC reports zero unrouted nets.

```bash
git add -A && git commit -m "layout: routing complete"
```

---

## Step 10 — The dome pads

This is the part that is specific to this board and that gets it wrong quietly.
It is not really a KiCad step — it is a thing to check and a thing to tell the
fab.

- **Solder mask must be open over the whole contact area** of every dome pad,
  ring and centre both. The generated footprints do this already; check one in
  the footprint editor so you know what right looks like.
- **Each dome site needs a vent** — a via, or a channel in the dome array —
  or trapped air mushes the click.
- **Plating.** ENIG is fine for rev A. For the final board, specify selective
  hard gold on the 37 dome sites: 0.38–0.76 µm gold over 1.27–5.0 µm nickel.
  ENIG typically fails before 200,000 cycles and a flaky `0` key ruins the
  object. Get a quote before designing around it — it costs more than the rest
  of the board.

---

## Step 11 — Design rule check

**Inspect → Design Rules Checker.**

In the dialog, before you run it:

- **Untick "Test for parity between PCB and schematic".** There is no schematic
  — atopile is the schematic — so the test has nothing to compare against and
  will report every part as missing. The **Schematic Parity** tab stays empty
  and that is correct.
- **Tick "Refill all zones before performing DRC".** Otherwise you can pass a
  check against a stale pour.

Then run it. Two numbers have to reach zero: the **Violations** tab's error
count, and the **Unconnected Items** tab's count.

Warnings are worth reading once each but not all of them are worth fixing.
Silkscreen overlapping a pad is a warning and it is usually real; "footprint
has no courtyard" on a test pad is a warning and it is noise.

The two categories that are always real:

- **Clearance violations.** Copper too close to copper. Fix them.
- **Unconnected items.** A connection in the netlist with no copper. This is
  the one that costs you a board, and it is why the number has to be zero and
  not nearly zero.

---

## Step 12 — Look at it in 3D

**`Alt+3`** opens the 3D viewer.

This catches things no rule check will: a connector facing inward, a part
straddling the board edge, the module overlapping the cell, silkscreen where
the faceplate has to sit flat. Spin it, look at the back, look along the top
edge.

Specifically, on this board: check that the six top-edge parts all face *out*,
that `J2`'s mouth faces the notch, and that nothing on the front is tall enough
to hit the faceplate — there is about 1.7 mm of air up there now.

---

## Then what

Go back to **`docs/pcb-process.md`, step 8**, for the fabrication outputs, what
to order, and how to bring the board up without destroying it.

---

## When it goes wrong

**"I can't select anything."** There is a selection filter, bottom right of the
window. If someone unticked "Footprints" you can see them but not grab them.

**"My track went on the wrong layer."** The active layer is whatever is
highlighted in the Layers panel. Select the layer *first*, then press `X`.

**"The zone disappeared."** Zones show as outlines until they are filled. Press
`B`.

**"A part won't move."** It is locked. Select it and press `L`. You locked
the keypad deliberately in step 6.

**"I imported the netlist again and everything moved."** You used reference
designator linking instead of tstamps. Revert to your last commit and re-import
with the right Link Method. This is exactly why step 5 makes a point of it.

**"The script did nothing."** Relative path. Use the absolute one.

**`git add` fails with "'…/.history/' does not have a commit checked out".**
Some editors — VS Code's "Local History" extension is the usual one — keep
timestamped copies of your files in a `.history/` folder next to them, and
some of those run `git init` inside it. Git then finds a repository with no
commits in it, refuses to work out what to record, and aborts the whole `git
add`, so nothing at all gets staged.

`.history/` is in this repo's `.gitignore`, so a current clone will not hit
this. If you do, pull, and it goes away. Nothing is lost either way: that
folder is your editor's own backups and git was never going to store it.

**`build/default.net` is not there after a pull.** It is not supposed to be —
`build/` is gitignored because it is generated. Run `ato --non-interactive
build`. See step 5.

**Anything else** — paste the error or describe what you see. Do not work
around it; a layout problem worked around is a board problem later.
