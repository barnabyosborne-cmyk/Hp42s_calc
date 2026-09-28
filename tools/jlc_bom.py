#!/usr/bin/env python3
"""Write a JLCPCB assembly BOM for the main board.

    python3 tools/jlc_bom.py [out.csv]

JLC's columns are Comment, Designator, Footprint and LCSC Part #. The board
file carries no values (atopile writes "?"), so the values come from the
source, keyed by each footprint's instance path, and the part numbers from
the comments in elec/src/parts.ato.

The LCSC column is left empty on purpose: LCSC is not reachable from where
this was written, and a wrong LCSC number places the wrong part without
complaint. JLC's BOM step matches on Comment and the manufacturer part and
offers candidates; pick them there.

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
DIODE = ("1N5819HW Schottky 40V 1A", "1N5819HW")

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
    for m in re.finditer(r'\n\t\(footprint "([^"]+)"', text):
        blk = rp.block_at(text, m.start() + 1)
        ref = re.search(r'\(property "Reference" "([^"]*)"', blk).group(1)
        path = re.search(r'\(sheetname "[^"]*::([^"]*)"', blk)
        path = path.group(1) if path else ""
        fp = m.group(1).split(":")[-1]
        if ref.startswith("TP"):
            continue
        if ref.startswith(SKIP_PREFIX) and path not in PARTS:
            continue
        if path in PARTS:
            comment, mpn = PARTS[path]
        elif ref.startswith("D"):
            comment, mpn = DIODE
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
        key = (comment, fp, mpn)
        groups.setdefault(key, []).append(ref)

    def refkey(r):
        return (re.sub(r"\d", "", r), int(re.sub(r"\D", "", r)))

    with out.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #",
                    "Manufacturer Part", "Qty"])
        for (comment, fp, mpn), refs in sorted(
                groups.items(), key=lambda kv: refkey(min(kv[1], key=refkey))):
            refs.sort(key=refkey)
            w.writerow([comment, ",".join(refs), fp, "", mpn, len(refs)])
    n = sum(len(r) for r in groups.values())
    print(f"wrote {out}: {len(groups)} lines, {n} parts")


if __name__ == "__main__":
    main()
