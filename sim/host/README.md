# Plus42 on a PC, drawing the real panel layout

`hp42s_host` is Plus42 and `firmware/main/shell.cc` compiled for this
computer, with a stand-in for `epd.c` that keeps the same framebuffer layout
and saves every panel update as a picture. It shows what the calculator draws
and where `shell_blitter` puts it on the 296 x 152 panel, including the columns
the case hides (grey) and the annunciator strip along the bottom.

It does not test the keypad scan or the SSD1680 protocol; that is what
`sim/wokwi/` is for. It costs no Wokwi minutes and runs in about a second.

```bash
bash ../../firmware/vendor/setup.sh      # once: lays out Intel's decimal library
make                                     # builds /tmp/hp42s-host/hp42s_host
make frames KEYS="2 ENTER 3 ADD SQRT"    # PNGs and sheet.png in /tmp/hp42s-host/frames
```

Keys are named by their legend in `host_main.cc` (`SHIFT`, `ENTER`, `ADD`,
`SIN`, `7`, ...) or given as core key numbers 1 to 37. It prints the X
register after each key, and the frame each key produced.

`frames.py` also reads a Wokwi run's output: `python3 frames.py run.log DIR`.
