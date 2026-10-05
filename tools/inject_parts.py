#!/usr/bin/env python3
"""Add netlist parts that are not on the board yet, the way KiCad's
"Update PCB from Netlist" would, so they can be placed and routed here.

    python3 tools/inject_parts.py            # after `ato build`

Each new footprint is copied from its library (elec/footprints/hp42s.pretty,
or the upstream copy tools/check_netlist.py caches in build/fpcache), put on
the FRONT at (0, -10), off the board, with its netlist path, reference,
value and pad nets. place_board.py then moves and flips it, and fix_pads.py
(with --libdir pointing at a library tree) rewrites its pads. Its path is the
netlist's, so a later "Update PCB from Netlist" in KiCad, linking by unique
ids, finds it already there and leaves it where it is.
"""
import re
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PCB = ROOT / "elec/layout/default/default.kicad_pcb"
NET = ROOT / "build/default.net"
LOCAL = ROOT / "elec/footprints/hp42s.pretty"
CACHE = ROOT / "build/fpcache"
NS = uuid.UUID("1b7e0c27-0000-4000-8000-000000000019")


def children(text):
    """Top-level parenthesised groups in text, in order."""
    out, d, start = [], 0, None
    for i, ch in enumerate(text):
        if ch == "(":
            if d == 0:
                start = i
            d += 1
        elif ch == ")":
            d -= 1
            if d == 0:
                out.append(text[start:i + 1])
    return out


def blocks(text, head):
    i = 0
    while True:
        i = text.find(head, i)
        if i < 0:
            return
        d, j = 0, i
        while True:
            c = text[j]
            d += (c == "(") - (c == ")")
            j += 1
            if d == 0:
                break
        yield text[i:j]
        i = j


def netlist():
    t = NET.read_text()
    comps, nets = {}, {}
    for b in blocks(t, "(comp "):
        ref = re.search(r'\(ref "([^"]+)"\)', b).group(1)
        fp = re.search(r'\(footprint "([^"]+)"\)', b).group(1)
        names = re.search(r'\(sheetpath \(names "([^"]+)"\)', b).group(1)
        ts = re.search(r'\(tstamps "([^"]+)"\)\)\s*$', b) or re.findall(r'\(tstamps "([^"]+)"\)', b)
        ts = ts[-1] if isinstance(ts, list) else ts.group(1)
        val = re.search(r'\(value "([^"]*)"\)', b).group(1)
        comps[ref] = dict(fp=fp, names=names, ts=ts, value=val)
    for b in blocks(t, "(net "):
        m = re.search(r'\(name "([^"]+)"\)', b)
        if not m:
            continue
        for n in re.finditer(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', b):
            nets[(n.group(1), n.group(2))] = m.group(1)
    return comps, nets


def library(fp):
    lib, name = fp.split(":")
    p = LOCAL / f"{name}.kicad_mod" if lib == "hp42s" else CACHE / f"{lib}__{name}.kicad_mod"
    return p.read_text()


def u(*k):
    return str(uuid.uuid5(NS, "/".join(k)))


def convert(ref, c, nets):
    src = library(c["fp"])
    body = src[src.index("\n") + 1:src.rindex(")")]
    # drop the library-only header lines
    body = re.sub(r'\n\t\((version|generator|generator_version) [^\n]*', "", "\n" + body)
    lines = [f'\t(footprint "{c["fp"]}"', f'\t\t(uuid "{u(ref, "fp")}")', '\t\t(at 0 -10)']
    for it in children(body):
        k = re.match(r"\((\w+)", it).group(1)
        if k == "layer":
            lines.insert(1, "\t\t" + it)
            continue
        if k == "fp_text" and re.match(r'\(fp_text (reference|value) ', it):
            kind = "Reference" if " reference " in it[:20] else "Value"
            txt = ref if kind == "Reference" else c["value"]
            it = re.sub(r'^\(fp_text (reference|value) "[^"]*"', f'(property "{kind}" "{txt}"', it)
            it = it.replace("(at ", "(at ", 1)
            it = it[:-1] + f' (uuid "{u(ref, kind)}"))'
        elif k == "property":
            name = re.match(r'\(property "([^"]+)"', it).group(1)
            if name == "Reference":
                it = re.sub(r'^\(property "Reference" "[^"]*"', f'(property "Reference" "{ref}"', it)
            elif name == "Value":
                it = re.sub(r'^\(property "Value" "[^"]*"', f'(property "Value" "{c["value"]}"', it)
            it = it[:-1] + f' (uuid "{u(ref, "prop", name)}"))'
        elif k == "pad":
            num = re.match(r'\(pad "([^"]*)"', it).group(1)
            net = nets.get((ref, num))
            extra = (f' (net "{net}")' if net else "") + f' (uuid "{u(ref, "pad", num, it[:60])}")'
            it = it[:-1] + extra + ")"
        elif k in ("fp_line", "fp_rect", "fp_circle", "fp_poly", "fp_arc", "fp_text"):
            it = it[:-1] + f' (uuid "{u(ref, k, it)}"))'
        elif k == "model":
            pass
        lines.append("\t\t" + it.replace("\n", "\n\t"))
    path = f'/{c["ts"]}/{c["ts"]}'
    lines.append(f'\t\t(path "{path}")')
    lines.append('\t\t(sheetname "")')        # as KiCad's own import writes it
    lines.append("\t)")
    return "\n".join(lines) + "\n"


def main():
    comps, nets = netlist()
    text = PCB.read_text()
    have = set(re.findall(r'\(property "Reference" "([^"]+)"', text))
    new = [r for r in comps if r not in have]
    if not new:
        print("nothing to add")
        return
    add = "".join(convert(r, comps[r], nets) for r in new)
    i = text.rindex("\n)")
    PCB.write_text(text[:i + 1] + add + text[i + 1:])
    print("added", " ".join(new))


if __name__ == "__main__":
    main()
