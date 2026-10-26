#!/usr/bin/env python3
"""Verify carrier.kicad_sch really carries the connections netlist.py declares.

The schematic is generated, so "it generated" proves nothing -- this reads the
netlist back OUT of the KiCad file with kicad-cli and diffs it against the
source. Checks, in order:

  1. every net in netlist.py exists in the schematic with exactly its pads
  2. the schematic has no nets beyond those (bar KiCad's unconnected-* stubs)
  3. every pad in NO_CONNECT really is unconnected
  4. no pad is left floating that isn't named in NO_CONNECT
  5. every mechanical-only solder pad really is unconnected
  6. every part carries a footprint, that footprint file exists, and its pad
     numbers are exactly the symbol's pad numbers
"""
import subprocess, sys, pathlib, re, xml.etree.ElementTree as ET
import netlist as N

HERE = pathlib.Path(__file__).resolve().parent
SCH, XML = HERE / "carrier.kicad_sch", HERE / "carrier.xml"

def export():
    r = subprocess.run(["xvfb-run", "-a", "kicad-cli", "sch", "export", "netlist",
                        "--format", "kicadxml", "-o", str(XML), str(SCH)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"kicad-cli failed:\n{r.stdout}\n{r.stderr}")
    assert XML.exists() and XML.stat().st_size > 0, "kicad-cli produced no netlist"

def from_schematic():
    root = ET.parse(XML).getroot()
    nets = {}
    for net in root.findall("./nets/net"):
        name = net.get("name")
        pads = sorted((n.get("ref"), int(n.get("pin")))
                      for n in net.findall("node"))
        nets[name] = pads
    pads_in_sch = set()
    for c in root.findall("./components/comp"):
        pads_in_sch.add(c.get("ref"))
    return nets, pads_in_sch

LIBS = [pathlib.Path("/usr/share/kicad/footprints")]

def footprint_file(fpid):
    lib, name = fpid.split(":", 1)
    local = HERE / f"{lib}.pretty" / f"{name}.kicad_mod"
    if local.exists():
        return local
    for root in LIBS:
        c = root / f"{lib}.pretty" / f"{name}.kicad_mod"
        if c.exists():
            return c
    return None

def check_footprints(fails):
    pads = N.pad_names()
    for ref in N.PARTS:
        fpid = N.FOOTPRINTS.get(ref)
        if not fpid:
            fails.append(f"{ref}: no footprint assigned")
            continue
        f = footprint_file(fpid)
        if f is None:
            fails.append(f"{ref}: footprint {fpid} not found in any library")
            continue
        nums = set(re.findall(r'\(pad\s+"([^"]+)"', f.read_text()))
        nums.discard("")                       # NPTH mounting holes
        want = {str(n) for n in pads[ref]}
        if nums != want:
            fails.append(f"{ref}: {fpid} pads {sorted(nums)} != symbol pads "
                         f"{sorted(want)}")

def main():
    export()
    sch, refs = from_schematic()
    want = N.resolved_nets()
    table = N.pin_table()
    fails = []

    real = {k: v for k, v in sch.items() if not k.startswith("unconnected-")}
    floating = {k: v for k, v in sch.items() if k.startswith("unconnected-")}

    for name, pads in want.items():
        if name not in real:
            fails.append(f"net {name}: missing from the schematic")
        elif real[name] != pads:
            miss = set(pads) - set(real[name])
            extra = set(real[name]) - set(pads)
            fails.append(f"net {name}: missing {sorted(miss)} extra {sorted(extra)}")
    for name in real:
        if name not in want:
            fails.append(f"net {name}: in the schematic but not in netlist.py")

    if set(refs) != set(N.PARTS):
        fails.append(f"parts differ: {set(refs) ^ set(N.PARTS)}")

    # which pads float, per the schematic
    float_pads = set()
    for pads in floating.values():
        float_pads |= set(pads)
    declared = set()
    for node in list(N.NO_CONNECT) + list(N.UNUSED):
        declared.add(N.resolve(node, table))

    for node in N.NO_CONNECT:
        rp = N.resolve(node, table)
        if rp not in float_pads:
            fails.append(f"{node} is in NO_CONNECT but IS connected")
    undeclared = sorted(float_pads - declared)
    if undeclared:
        names = {}
        for ref, num in undeclared:
            nm = next((k for k, v in table[ref].items() if v == num), str(num))
            names.setdefault(ref, []).append(f"{nm}(#{num})")
        fails.append("floating pads declared nowhere: " +
                     "; ".join(f"{r}: {', '.join(v)}" for r, v in sorted(names.items())))

    # A pad listed as mechanical must carry no net. Soldering the ESP32's
    # flash or strapping pins to live copper would be worse than not
    # soldering them at all.
    owner = {}
    for net, nodes in want.items():
        for rp in nodes:
            owner[rp] = net
    for node, why in N.SOLDER_MECHANICAL.items():
        rp = N.resolve(node, table)
        if rp in owner:
            fails.append(f"{node} is listed as mechanical-only but is on net "
                         f"{owner[rp]}")

    check_footprints(fails)

    print(f"source : {len(want)} nets, {sum(len(v) for v in want.values())} pads")
    print(f"schema : {len(real)} nets, {len(float_pads)} floating pads")
    if fails:
        print("\nFAIL")
        for f in fails:
            print("  -", f)
        sys.exit(1)
    print("OK: schematic matches netlist.py, and every footprint resolves")

if __name__ == "__main__":
    main()
