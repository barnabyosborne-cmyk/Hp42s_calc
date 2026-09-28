#!/usr/bin/env python3
"""Write a JLCPCB assembly BOM for the main board.

    python3 tools/jlc_bom.py [out.csv]

JLC's columns are Comment, Designator, Footprint and LCSC Part #. The board
file carries no values (atopile writes "?"), so the values come from the
source, keyed by each footprint's instance path, and the part numbers from
the comments in elec/src/parts.ato.

LCSC numbers were chosen on 28 September 2026 from JLC's own parts search
(the endpoint behind jlcpcb.com/parts), preferring Basic parts; stock moves,
so re-check anything JLC flags.

Left out: the 38 domes (attr exclude_from_pos_files, fitted by hand), the
test pads and the two sliver lands (bare copper, nothing to place).
Where a capacitor's voltage is not in the source, the rating below is a
choice made here, marked with *.
"""

import csv
import re
import sys
from collections import OrderedDict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import route_power as rp            # noqa: E402

# instance path -> (comment, manufacturer part or "")
PARTS = {
    "power.usb": ("USB-C receptacle 16P", "GCT USB4105-GF-A"),
    "power.esd": ("TPD4E05U06 USB ESD", "TPD4E05U06DQAR"),
    "power.chg": ("BQ25185 charger", "BQ25185DLHR"),
    "power.reg": ("TPS63900 buck-boost", "TPS63900DSKR"),
    "power.gauge": ("MAX17048 fuel gauge", "MAX17048G+T10"),
    "power.l_sw": ("2.2uH XFL4020", "Coilcraft XFL4020-222MEC"),
    "power.cell": ("JST PH 2-pin SMD right angle", "JST S2B-PH-SM4-TB"),
    "mcu": ("ESP32-S3-MINI-1-N8", "ESP32-S3-MINI-1-N8"),
    "sw_reset": ("Side tact switch", "Alps SKRTLAE010"),
    "sw_boot": ("Side tact switch", "Alps SKRTLAE010"),
    "display.epd": ("24P 0.5mm FPC connector", "Amphenol F32Q-1A7H1-11024"),
    "display.l_boost": ("47uH SRN4018", "Bourns SRN4018-470M"),
    "display.q_boost": ("Si1308EDL N-MOSFET", "Si1308EDL-T1-GE3"),
    "ls": ("Piezo buzzer", "Murata PKLCS1212E4001-R1"),
    "ir": ("940nm IR LED side view", "Vishay VSMB2943SLX01"),
    "q_ir": ("2N7002 N-MOSFET", "2N7002"),
    "led_status": ("Red/green LED 1208 RA", "Dialight 599-0Q70-247F"),
    "frontlight.u": ("TPS61165 LED driver", "TPS61165DBVR"),
    "frontlight.l_fl": ("22uH NR3015", "Taiyo Yuden NR3015T220M"),
}
DIODE = ("B5819W Schottky 40V 1A", "CJ B5819W SL")

# JLC's substitutes, 28 September 2026, from JLC's own parts search. The
# design's part is kept in the source; these are what JLC can place.
#   L1  XFL4020-222MEC had 1 in stock. XEL4020-222MEC is the same Coilcraft
#       4020 family on the same XxL4020 land: 2.2 uH, 35 mOhm, 4 A.
#   L2  SRN4018-470M had none. Sunlord SWPA4018S470MT is 47 uH in the same
#       4 x 4 x 1.8 body, 845 mOhm, 420 mA -- the panel boost draws tens of mA.
#       Different maker's land: check it sits on the pads in JLC's preview.
#   L3  NR3015T220M had 30. ANR3015T220M is the APV part the footprint is
#       named after.
#   D5  The Dialight 599-0Q70-247F is not in JLC's catalogue at all. The
#       Lite-On LTST-S326KGJRKT is the same thing: side-looking, 3.0 x 2.0 x
#       1.0 mm, red + yellow-green on a common anode, anode and red on the end
#       pads and green on the back one. Its land (datasheet section 6.2) sits
#       inside the Dialight pads; a footprint of its own waits for the next
#       netlist re-import. Check its polarity in JLC's preview.
SUBS = {
    "led_status": ("Red/green LED side view, common anode", "Lite-On LTST-S326KGJRKT"),
    "power.l_sw": ("2.2uH XEL4020", "Coilcraft XEL4020-222MEC"),
    "display.l_boost": ("47uH 4018 shielded", "Sunlord SWPA4018S470MT"),
    "frontlight.l_fl": ("22uH 3015", "ANR3015T220M"),
    "power.cell": ("JST PH 2-pin SMD right angle", "JST S2B-PH-SM4-TB(LF)(SN)"),
}
LCSC = {
    "power.usb": "C3020560", "power.esd": "C138714", "power.chg": "C19725033",
    "power.reg": "C1518762", "power.gauge": "C2682616", "power.l_sw": "C5369025",
    "power.cell": "C295747", "mcu": "C2913206", "sw_reset": "C110293",
    "sw_boot": "C110293", "display.epd": "C3168917",
    "display.l_boost": "C83445", "display.q_boost": "C469327", "ls": "C113159",
    "ir": "C511094", "q_ir": "C8545", "frontlight.u": "C58756",
    "frontlight.l_fl": "C6364792", "diode": "C8598", "led_status": "C125116",
}
# by Comment; Basic parts where JLC has one, else the best-stocked Extended
PASSIVE_LCSC = {
    "1uF 25V* X7R/X5R": "C15849", "10uF 10V* X7R/X5R": "C15850",
    "22uF 10V* X7R/X5R": "C45783", "100nF 16V* X7R/X5R": "C1525",
    "1uF 10V* X7R/X5R": "C52923", "1uF 25V X7R/X5R": "C15849",
    "4.7uF 16V X7R/X5R": "C19666", "1uF 50V X7R/X5R": "C28323",
    "4.7uF 10V* X7R/X5R": "C19666", "220nF 16V* X7R/X5R": "C16772",
    "5.1k 5%": "C25905", "18k 1%": "C25762",
    "10k 5%": "C25744", "100k 5%": "C25741", "15k 1%": "C25756",
    "1.2k 1%": "C22765", "820R 1%": "C23253",
    "4.7k 5%": "C25900",
    "1M 5%": "C26083", "2R2 1%": "C22939", "1k 5%": "C11702",
    "22R 5%": "C25092", "10R 5%": "C25077", "0R 5%": "C17168",
}
# where the Basic part is one size only, by (Comment, footprint)
PASSIVE_FP_LCSC = {
    ("4.7uF 25V X7R/X5R", "C_0805_2012Metric"): "C1779",
}

# values not given a voltage in the source get the * rating
CAP_V = {
    "power.c_vbus": "1uF 25V*", "power.c_bat": "10uF 10V*",
    "power.c_sys": "22uF 10V*", "power.c_out": "22uF 10V*",
    "power.c_out_hf": "100nF 16V*", "power.c_gauge": "100nF 16V*",
    "c_en": "1uF 10V*", "c_mcu_bulk": "22uF 10V*", "c_mcu": "100nF 16V*",
    "frontlight.c_out": "1uF 50V", "frontlight.c_in": "4.7uF 10V*",
    "frontlight.c_comp": "220nF 16V*",
}
SKIP_PREFIX = ("SW",)            # domes; the two tact switches are kept below


def source_values():
    """instance path -> value, from the .ato files."""
    src = Path(__file__).resolve().parent.parent / "elec/src"
    mods = {"display.ato": "display.", "frontlight.ato": "frontlight.",
            "power.ato": "power.", "hp42s.ato": ""}
    out = {}
    for f, prefix in mods.items():
        for m in re.finditer(r'^\s+(\w+)\.value = "([^"]*)"',
                             (src / f).read_text(), re.M):
            out[prefix + m.group(1)] = m.group(2)
    return out


def pretty(v):
    v = re.sub(r"^(\d+)u(\d)\b", r"\1.\2u", v)
    v = re.sub(r"(\d)u\b", r"\1uF", v).replace("uF", "uF")
    v = re.sub(r"(\d)n\b", r"\1nF", v)
    return v


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("hp42s-bom-jlc.csv")
    text = rp.PCB.read_text()
    vals = source_values()
    groups = OrderedDict()
    on_board = set()
    for m in re.finditer(r'\n\t\(footprint "([^"]+)"', text):
        blk = rp.block_at(text, m.start() + 1)
        ref = re.search(r'\(property "Reference" "([^"]*)"', blk).group(1)
        path = re.search(r'\(sheetname "[^"]*::([^"]*)"', blk)
        path = path.group(1) if path else ""
        fp = m.group(1).split(":")[-1]
        on_board.add(path)
        if ref.startswith("TP"):
            continue
        if ref.startswith(SKIP_PREFIX) and path not in PARTS:
            continue
        lcsc = LCSC.get(path, "")
        if path in SUBS:
            comment, mpn = SUBS[path]
        elif path in PARTS:
            comment, mpn = PARTS[path]
        elif ref.startswith("D"):
            comment, mpn = DIODE
            lcsc = LCSC["diode"]
        elif ref.startswith("C"):
            v = CAP_V.get(path) or pretty(vals[path])
            if "V" not in v:
                v += " 25V" if path.startswith("display.") else ""
            comment, mpn = f"{v} X7R/X5R", ""
        elif ref.startswith("R"):
            v = vals[path]
            tol = "1%" if "1%" in v else "5%"
            ohms = v.split()[0]
            if re.fullmatch(r"[\d.]+", ohms):
                ohms += "R"             # a bare "10" is 10 ohms, not 10k
            comment, mpn = f"{ohms} {tol}", ""
        else:
            raise SystemExit(f"{ref} ({path}) has no BOM entry")
        lcsc = lcsc or PASSIVE_FP_LCSC.get((comment, fp)) or PASSIVE_LCSC.get(comment, "")
        key = (comment, fp, lcsc, mpn)
        groups.setdefault(key, []).append(ref)

    # FrontlightStrip is in frontlight.ato but built as its own board
    sliver = {"frontlight.wire_a", "frontlight.wire_k"}
    missing = sorted(p for p in vals if p not in on_board | sliver)
    if missing:
        raise SystemExit("in the source but not on the board, so re-import the "
                         "netlist first: " + ", ".join(missing))

    def refkey(r):
        return (re.sub(r"\d", "", r), int(re.sub(r"\D", "", r)))

    with out.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #",
                    "Manufacturer Part", "Qty"])
        for (comment, fp, lcsc, mpn), refs in sorted(
                groups.items(), key=lambda kv: refkey(min(kv[1], key=refkey))):
            refs.sort(key=refkey)
            w.writerow([comment, ",".join(refs), fp, lcsc, mpn, len(refs)])
    n = sum(len(r) for r in groups.values())
    print(f"wrote {out}: {len(groups)} lines, {n} parts")


if __name__ == "__main__":
    main()
