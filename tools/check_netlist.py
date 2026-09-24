#!/usr/bin/env python3
"""Check every pin in the netlist against the pads that actually exist.

KiCad matches a netlist pin to a footprint pad BY NAME. Declare `pin IO33`
against a footprint whose pads are called 1..65 and the import is SILENTLY
UNCONNECTED -- no error, just a missing ratsnest line you will not notice
until the board comes back. This repo has been bitten by that twice, so it
is worth a script rather than an eye.

Run it after `ato build`, from the repo root:

    python3 tools/check_netlist.py

Local footprints come from elec/footprints/hp42s.pretty. KiCad's own are
fetched from the upstream library over https and cached, so this needs the
network the first time and nothing after that.

Exit status is 0 if every pin lands on a real pad, 1 otherwise.
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NET = os.path.join(ROOT, "build", "default.net")
LOCAL = os.path.join(ROOT, "elec", "footprints", "hp42s.pretty")
CACHE = os.path.join(ROOT, "build", "fpcache")
UPSTREAM = ("https://gitlab.com/kicad/libraries/kicad-footprints/-/raw/master/"
            "{lib}.pretty/{name}.kicad_mod")


def read_netlist(path):
    """-> ({ref: footprint_id}, {ref: {pin names used}})"""
    text = open(path).read()
    comps = {m.group(1): m.group(2) for m in re.finditer(
        r'\(comp \(ref "([^"]+)"\)\s*\(value "[^"]*"\)\s*\(footprint "([^"]+)"', text)}
    used = {}
    for m in re.finditer(r'\(node \(ref "([^"]+)"\)\s*\(pin "([^"]+)"', text):
        used.setdefault(m.group(1), set()).add(m.group(2))
    return comps, used


def pads_of(fpid):
    """Pad names in a footprint, or None if the footprint cannot be found."""
    lib, _, name = fpid.partition(":")
    if lib == "hp42s":
        path = os.path.join(LOCAL, name + ".kicad_mod")
        if not os.path.exists(path):
            return None
        text = open(path).read()
    else:
        os.makedirs(CACHE, exist_ok=True)
        path = os.path.join(CACHE, f"{lib}__{name}.kicad_mod")
        if not os.path.exists(path):
            r = subprocess.run(
                ["curl", "-sf", "-m", "40", UPSTREAM.format(lib=lib, name=name)],
                capture_output=True, text=True)
            if r.returncode != 0 or "(footprint" not in r.stdout:
                return None
            open(path, "w").write(r.stdout)
        text = open(path).read()
    # the empty name is KiCad's for a pad with no electrical identity, such as
    # a mounting boss or a keepout; it is never something the netlist connects
    return {p for p in re.findall(r'\(pad\s+"([^"]*)"', text) if p}


def stale_sources():
    """The .ato files modified since the netlist was built.

    build/ is gitignored, so a checkout carries whatever netlist the last
    `ato build` left behind -- or one from a different machine entirely. On
    24 September 2026 this script reported 119 components from a netlist two
    commits out of date while the real one had 117, which is exactly the sort
    of difference that costs an afternoon. Say so rather than counting a file
    nobody rebuilt.
    """
    built = os.path.getmtime(NET)
    src = os.path.join(ROOT, "elec", "src")
    late = []
    for dirpath, _dirs, names in os.walk(src):
        for name in names:
            if not name.endswith(".ato"):
                continue
            full = os.path.join(dirpath, name)
            if os.path.getmtime(full) > built:
                late.append(os.path.relpath(full, ROOT))
    return sorted(late)


def main():
    if not os.path.exists(NET):
        sys.exit(f"no netlist at {NET} -- run `ato build` in elec/ first")

    late = stale_sources()
    if late:
        print(f"WARNING: the netlist is older than {len(late)} source file(s):")
        for name in late[:6]:
            print(f"         {name}")
        if len(late) > 6:
            print(f"         ... and {len(late) - 6} more")
        print("         Everything below describes the OLD netlist. Run "
              "`ato --non-interactive build` first.\n")

    comps, used = read_netlist(NET)
    cache, problems = {}, []

    def sort_key(ref):
        return re.sub(r"\d", "", ref), int(re.sub(r"\D", "", ref) or 0)

    for ref in sorted(comps, key=sort_key):
        fpid = comps[ref]
        if fpid not in cache:
            cache[fpid] = pads_of(fpid)
        pads, pins = cache[fpid], used.get(ref, set())
        if pads is None:
            problems.append((ref, fpid, "footprint not found"))
            continue
        missing = sorted(pins - pads)
        if missing:
            problems.append((ref, fpid, f"pins with no pad: {', '.join(missing)}"))

    print(f"{len(comps)} components, {len(cache)} distinct footprints")
    if not problems:
        print("every pin lands on a real pad")
        return 0
    print(f"\n{len(problems)} problems:")
    for ref, fpid, why in problems:
        print(f"  {ref:6s} {fpid:60s} {why}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
