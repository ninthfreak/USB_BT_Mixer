#!/usr/bin/env python3
"""Write CONNECTIONS.md from netlist.py -- the same source the schematic uses.

A schematic is the engineering artifact; this is the reviewable one. Both come
from netlist.py and check_netlist.py proves the schematic matches it, so
checking this table is equivalent to checking the schematic.
"""
import pathlib
import netlist as N

GROUPS = [
    ("Power", ["VBUS1", "VBUS2", "RAIL", "GND"]),
    ("Chain input, grounded through a cuttable bridge", ["GP29_1", "GP29_2"]),
    ("I2S clocks (ESP32 is master)", ["BCLK", "BCLK1", "BCLK2", "LRCK", "LRCK1", "LRCK2"]),
    ("I2S audio (returns to the ESP32)", ["AUD1", "AUD2"]),
    ("UART, one pair per input board", ["U1_TX", "U1_RX", "U2_TX", "U2_RX"]),
    ("Breakout header", ["DBG1", "DBG2", "SP1", "SP2", "SP3"]),
]

def cell(pads, ref, pad):
    """`U1.GP26`, or `U3.GND #26` where the part repeats that pin name."""
    name = pads[ref][pad]
    repeats = sum(1 for v in pads[ref].values() if v == name) > 1
    return f"`{ref}.{name} #{pad}`" if repeats else f"`{ref}.{name}`"


def main():
    pads, nets = N.pad_names(), N.resolved_nets()
    seen = set()
    L = ["# Carrier board connections", "",
         "Generated from `netlist.py` by `gen_table.py`. Do not edit by hand.",
         "", "`check_netlist.py` reads the netlist back out of `carrier.kicad_sch`",
         "and proves it matches the same source, so this table and the schematic",
         "cannot disagree.", "",
         f"**{len(nets)} nets, {sum(len(v) for v in nets.values())} pads, "
         f"{len(N.PARTS)} parts.**", ""]

    for title, names in GROUPS:
        L += [f"## {title}", "", "| Net | Connects |", "|---|---|"]
        for n in names:
            seen.add(n)
            cells = ", ".join(cell(pads, r, p) for r, p in nets[n])
            L.append(f"| **{n}** | {cells} |")
        L.append("")
    assert seen == set(nets), f"ungrouped nets: {set(nets) - seen}"

    L += ["## Parts", "", "| Ref | Value | Purpose |", "|---|---|---|"]
    for ref, p in N.PARTS.items():
        L.append(f"| {ref} | {p['value']} | {p['desc']} |")

    # Soldering map: the owner solders only what is needed.
    conn = {}
    for net, nodes in nets.items():
        for ref, pad in nodes:
            conn.setdefault(ref, {})[pad] = net
    mech = {}
    for node, why in N.SOLDER_MECHANICAL.items():
        ref, pad = N.resolve(node, N.pin_table())
        mech.setdefault(ref, {})[pad] = why

    L += ["## What to solder", "",
          "Only the pads that carry a net, plus a few corners so a module",
          "cannot peel from one end. Everything else is left bare: the land",
          "pattern is there if you ever want it.", "",
          "The port end of each input board has **no pads at all** -- the",
          "nearest joint is 9.8 mm from the USB-C shell -- so plug forces were",
          "never going to be held by solder. The enclosure lid's press posts",
          "take that load, as they already do today.", ""]
    tot_s = tot_a = 0
    for ref in ("U1", "U2", "U3"):
        allp = pads[ref]
        cs = sorted(conn.get(ref, {}))
        ms = sorted(mech.get(ref, {}))
        skip = [p for p in sorted(allp) if p not in cs and p not in ms]
        tot_s += len(cs) + len(ms); tot_a += len(allp)
        L += [f"### {ref} ({N.PARTS[ref]['value']}) — solder "
              f"{len(cs) + len(ms)} of {len(allp)}", "",
              "| | Pads |", "|---|---|",
              "| **Net** | " + ", ".join(f"`{p} {allp[p]}`" for p in cs) + " |",
              "| **Mechanical** | " + ", ".join(f"`{p} {allp[p]}`" for p in ms) + " |",
              "| Leave bare | " + ", ".join(f"{p} {allp[p]}" for p in skip) + " |", ""]
    L += [f"**{tot_s} joints instead of {tot_a}.**", ""]

    L += ["", "## Deliberately not connected", "",
          "| Pin | Why |", "|---|---|"]
    for node, why in N.NO_CONNECT.items():
        L.append(f"| `{node}` | {why} |")
    L += ["", "Spare pads, free for later use: " +
          ", ".join(f"`{k}`" for k in N.UNUSED) + ".", ""]

    pathlib.Path("CONNECTIONS.md").write_text("\n".join(L))
    print(f"wrote CONNECTIONS.md ({len(nets)} nets)")

if __name__ == "__main__":
    main()
