#!/usr/bin/python3
"""Run KiCad's own DRC on carrier.kicad_pcb.

Must run under the SYSTEM python (/usr/bin/python3), which carries KiCad 7's
pcbnew bindings. kicad-cli in KiCad 7 has no DRC subcommand, but
pcbnew.WriteDRCReport has existed since 7.0 -- for a long time this project
claimed no DRC was available because only the CLI had been checked.

gen_pcb.py does not yet write nets onto pads, and an un-netted pad touching a
netted track reads as a short. So this works on a temporary copy with pad nets
assigned from netlist.py, exactly as "Update PCB from Schematic" would. The
repository board is not modified.

lib_footprint_issues is reported but not counted: it means the footprints
carry no library link and this container has no global library table, which
says nothing about the copper.
"""
import collections, pathlib, re, shutil, sys, tempfile
import pcbnew

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import netlist as N

IGNORE = {"lib_footprint_issues"}

def main():
    tmp = pathlib.Path(tempfile.mkdtemp())
    shutil.copy(HERE / "carrier.kicad_pcb", tmp / "b.kicad_pcb")
    b = pcbnew.LoadBoard(str(tmp / "b.kicad_pcb"))

    nets = N.resolved_nets()
    info = {}
    for name in nets:
        ni = b.FindNet(name)
        if ni is None:
            ni = pcbnew.NETINFO_ITEM(b, name); b.Add(ni)
        info[name] = ni
    padnet = {(r, str(p)): n for n, nodes in nets.items() for r, p in nodes}
    for fp in b.GetFootprints():
        for p in fp.Pads():
            n = padnet.get((fp.GetReference(), p.GetNumber()))
            if n:
                p.SetNet(info[n])
    b.BuildConnectivity()

    rpt = tmp / "drc.rpt"
    pcbnew.WriteDRCReport(b, str(rpt), pcbnew.EDA_UNITS_MILLIMETRES, True)
    txt = rpt.read_text()
    blocks = [x for x in re.split(r'\n(?=\[)', txt) if x.startswith('[')]
    kinds = collections.Counter(re.match(r'\[(\w+)\]', x).group(1) for x in blocks)
    real = {k: v for k, v in kinds.items() if k not in IGNORE}
    errors = sum(v for k, v in real.items()
                 if any(f"[{k}]" in x and "Severity: error" in x for x in blocks))

    print(f"KiCad {pcbnew.Version()} DRC, pad nets assigned from netlist.py")
    for k, v in sorted(kinds.items(), key=lambda kv: -kv[1]):
        print(f"  {v:4}  {k}" + ("   (library linkage, ignored)" if k in IGNORE else ""))
    shutil.copy(rpt, HERE / "drc-report.txt")
    print(f"\nfull report: drc-report.txt")
    if real:
        print(f"FAIL: {sum(real.values())} findings")
        sys.exit(1)
    print("OK: KiCad DRC is clean")

if __name__ == "__main__":
    main()
