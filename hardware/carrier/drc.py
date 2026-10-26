#!/usr/bin/python3
"""KiCad's own DRC on carrier.kicad_pcb -- the gate for this board.

Must run under the SYSTEM python (/usr/bin/python3), which carries KiCad 7's
pcbnew bindings. kicad-cli in KiCad 7 has no DRC subcommand, but
pcbnew.WriteDRCReport has existed since 7.0; for a long time this project
said no DRC was available because only the CLI had been checked.

Two things happen here that KiCad's DRC cannot do by itself:

1. Every pad's net is compared with netlist.py. The board is checked AS
   GENERATED -- nothing is patched onto it first -- so a generator that drops
   nets fails here instead of being papered over.
2. The design rules are set to this board's own, which are stricter than
   KiCad's defaults: 0.25 mm clearance, 0.5 mm copper to edge, 0.5 mm between
   drilled holes (most fabs want that between plated holes).

    /usr/bin/python3 drc.py              # routed board: everything must pass
    /usr/bin/python3 drc.py --unrouted   # placement stage: ignore missing tracks
"""
import collections, pathlib, re, sys, tempfile
import pcbnew

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import netlist as N

mm = pcbnew.FromMM
RULES = dict(clearance=0.25, track=0.40, via=0.80, drill=0.40,
             edge=0.50, hole_clear=0.25, hole_to_hole=0.50)

# Library linkage: footprints name stock libraries this container has no
# global table for. Says nothing about the copper.
ENV_ONLY = re.compile(r"does not include the library")
UNROUTED_OK = {"unconnected_items", "track_dangling"}

def check_nets(board):
    want = {(r, str(p)): n for n, nodes in N.resolved_nets().items() for r, p in nodes}
    bad, seen = [], set()
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if ref not in N.PARTS:
            continue
        for p in fp.Pads():
            key = (ref, p.GetNumber())
            got = p.GetNetname() or None
            exp = want.get(key)
            seen.add(key)
            if got != exp:
                bad.append(f"{ref}.{p.GetNumber()}: board has {got!r}, netlist says {exp!r}")
    for key in want:
        if key not in seen:
            bad.append(f"{key[0]}.{key[1]}: in the netlist but not on the board")
    return bad

def apply_rules(board):
    ds = board.GetDesignSettings()
    nc = ds.m_NetSettings.m_DefaultNetClass
    nc.SetClearance(mm(RULES["clearance"]))
    nc.SetTrackWidth(mm(RULES["track"]))
    nc.SetViaDiameter(mm(RULES["via"]))
    nc.SetViaDrill(mm(RULES["drill"]))
    ds.m_CopperEdgeClearance = mm(RULES["edge"])
    ds.m_HoleClearance = mm(RULES["hole_clear"])
    ds.m_HoleToHoleMin = mm(RULES["hole_to_hole"])

def main():
    unrouted = "--unrouted" in sys.argv
    board = pcbnew.LoadBoard(str(HERE / "carrier.kicad_pcb"))

    net_errors = check_nets(board)
    apply_rules(board)
    board.BuildConnectivity()

    rpt = pathlib.Path(tempfile.mkdtemp()) / "drc.rpt"
    pcbnew.WriteDRCReport(board, str(rpt), pcbnew.EDA_UNITS_MILLIMETRES, True)
    txt = rpt.read_text()
    (HERE / "drc-report.txt").write_text(txt)

    blocks = [x for x in re.split(r"\n(?=\[)", txt) if x.startswith("[")]
    counted, skipped = collections.Counter(), collections.Counter()
    for x in blocks:
        kind = re.match(r"\[(\w+)\]", x).group(1)
        if ENV_ONLY.search(x) or (unrouted and kind in UNROUTED_OK):
            skipped[kind] += 1
        else:
            counted[kind] += 1

    stage = "placement (unrouted)" if unrouted else "routed"
    print(f"KiCad {pcbnew.Version()} DRC, {stage}, rules {RULES}")
    print(f"pad nets vs netlist.py: {'OK' if not net_errors else f'{len(net_errors)} wrong'}")
    for e in net_errors[:10]:
        print("  -", e)
    for k, v in counted.most_common():
        print(f"  {v:4}  {k}")
    for k, v in skipped.most_common():
        print(f"  {v:4}  {k}  (not counted: {'stage' if k in UNROUTED_OK else 'library linkage'})")
    print("full report: drc-report.txt")

    if net_errors or counted:
        print(f"\nFAIL: {len(net_errors)} net errors, {sum(counted.values())} DRC findings")
        sys.exit(1)
    print("\nOK: KiCad DRC is clean and every pad carries its netlist net")

if __name__ == "__main__":
    main()
