#!/usr/bin/python3
"""Route carrier.kicad_pcb.

    /usr/bin/python3 route.py            # lay the committed route (build.sh)
    /usr/bin/python3 route.py --reroute  # run Freerouting, rewrite carrier.ses

Copper comes from two places:

1. PATHS and VIAS below, placed by hand: the rail on the BOTTOM layer, and
   short ground stubs from the surface GND pads to a via. These nets are
   hidden from the router.

   The rail crosses the front IN FRONT of input 1's ground pad (y 4.2,
   between its 5V and GND pads) and then hugs the left edge, so every
   module's ground via lands in the one main ground plane and no signal
   runs along the rail. It once ran behind the input boards' ground pads,
   which left both boards' only ground connections on a strip of plane
   joined to the rest by two 0.5 mm slivers
   (docs/project-review-2026-11.md #2). check_routing.py measures that path.

   LINKS are signal copper placed by hand as well: the two clock loop-backs
   under the ESP32, each joining a clock's output pin to its loop-back pin.
   The router is given them as finished copper it must keep. Left to itself
   it ran input 2's audio through the gap between those pins, which left one
   link impossible and sent the other the whole way round the ESP32.

2. Every other signal, by Freerouting (https://github.com/freerouting/freerouting),
   in up to two stages:
     stage 1  B.Cu is declared a power plane, so every signal goes on top
     stage 2  only if stage 1 leaves connections open: B.Cu opens, vias are
              expensive, and the stage-1 copper is locked
   On this placement stage 1 routes everything: no signal changes layer.

Freerouting's output varies from run to run, so its result is committed as
carrier.ses and the build lays that file. carrier-route.json records a hash
of the design the route was made for -- outline, rules, placement, pads and
nets -- and if any of that changes, the build stops and asks for a reroute
rather than laying stale copper. The hand copper in (1) is not part of the
hash: moving it does not make the signal route stale, and KiCad's DRC
catches any clash between the two.

The router never sees the board's 0.5 mm edge rule (it keeps only its 0.25 mm
clearance from the outline), so it is handed an outline inset by 0.3 mm.
KiCad's DRC (drc.py) then checks the result against the real rules.

Freerouting 2.1.0 is downloaded once, checked against its SHA-256, and run
with its usage analytics switched off. It needs Java 17 or later.
"""
import hashlib, json, os, pathlib, shutil, subprocess, sys, tempfile, time, urllib.request
import pcbnew

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_pcb as G
import drc
import specctra as S

mm = pcbnew.FromMM
def V(x, y): return pcbnew.VECTOR2I(mm(x), mm(y))
F, B = pcbnew.F_Cu, pcbnew.B_Cu

BOARD = HERE / "carrier.kicad_pcb"
SESSION = HERE / "carrier.ses"
META = HERE / "carrier-route.json"

FR_VERSION = "2.1.0"
FR_URL = f"https://github.com/freerouting/freerouting/releases/download/v{FR_VERSION}/freerouting-{FR_VERSION}.jar"
FR_SHA256 = "2c07d58f75dac03782664081e7a58b41c25400d871a9fcf166a2ea6fe60d5def"
FR_CACHE = pathlib.Path(os.environ.get("XDG_CACHE_HOME", pathlib.Path.home() / ".cache")) / "usb_bt_mixer"
STAGE_TIMEOUT = "00:01:00"
STAGE2_VIA_COST = 200
EDGE_INSET = drc.RULES["edge"] - drc.RULES["clearance"] + 0.05     # 0.30 mm

HIDDEN = ["GND", "RAIL"]          # finished by hand or by the pour

PATHS = [
    # RAIL, bottom: D2.K, across the front between input 1's 5V and GND
    # pads, D1.K, then down the left edge to C1+.
    ("RAIL", B, 0.8, [(32.58, 2.4), (32.58, 4.2), (5.5, 4.2), (5.5, 6.0), (3.5, 8.2)]),
    ("RAIL", B, 0.8, [(3.5, 8.2), (1.3, 10.4), (1.3, 35.6), (2.15, 37.0), (2.15, 38.7)]),
    # RAIL, top: the ESP32's 5V pad and the test point to C1+.
    ("RAIL", F, 0.8, [(3.04, 43.0), (2.15, 38.7)]),
    ("RAIL", F, 0.8, [(2.15, 38.7), (2.6, 34.3)]),
    # GND, top: surface GND pads to a via.
    ("GND", F, 0.4, [(2.6, 31.3), (4.0, 31.3)]),          # TP2
    ("GND", F, 0.4, [(10.4, 5.42), (11.7, 5.42)]),        # input 1 GND, under it
    ("GND", F, 0.4, [(45.3, 5.42), (46.6, 5.42)]),        # input 2 GND, under it
    ("GND", F, 0.4, [(15.74, 43.2), (16.0, 41.4)]),       # ESP32 J3 GND
    ("GND", F, 0.4, [(33.52, 72.2), (33.52, 73.9)]),      # ESP32 J4 GND
]
VIAS = [("GND", 4.0, 31.3), ("GND", 11.7, 5.42), ("GND", 46.6, 5.42),
        ("GND", 16.0, 41.4), ("GND", 33.52, 73.9)]


# Signal copper placed by hand; the router keeps it.
#  * The clock loop-backs, nested under the ESP32 just behind its front row:
#    BCLK IO26 <-> IO32 inside, LRCK IO14 <-> IO35 outside. Input 1's UART
#    ends on the two pads between. Each starts and ends on a pad centre.
#  * R6's first few millimetres, straight through the gap below it. Without
#    it the router gave that gap to input 2's TX and then had to take the
#    line right round the back of the ESP32 to reach its pin.
J3_Y = 44.05                         # centre line of the ESP32's front pads
LINKS = [
    ("BCLK", F, 0.4, [(25.9, J3_Y), (25.9, 46.1), (26.4, 46.6), (33.02, 46.6), (33.52, 46.1), (33.52, J3_Y)]),
    ("LRCK", F, 0.4, [(20.82, J3_Y), (20.82, 47.1), (21.32, 47.6), (35.56, 47.6), (36.06, 47.1), (36.06, J3_Y)]),
    ("ESP_TX2", F, 0.4, [(42.41, 40.3), (42.41, 46.6)]),
]


def add_hand_copper(board, locked):
    """Add PATHS, LINKS and VIAS. Segments already on the board are skipped:
    the router's session hands the LINKS back as part of their nets."""
    have = set()
    for t in board.GetTracks():
        if t.GetClass() == "PCB_TRACK":
            a, c = t.GetStart(), t.GetEnd()
            have.add((t.GetNetname(), t.GetLayer(), frozenset([(a.x, a.y), (c.x, c.y)])))
    for net, layer, w, pts in PATHS + LINKS:
        ni = board.FindNet(net)
        for a, c in zip(pts, pts[1:]):
            if (net, layer, frozenset([(mm(a[0]), mm(a[1])), (mm(c[0]), mm(c[1]))])) in have:
                continue
            t = pcbnew.PCB_TRACK(board); t.SetStart(V(*a)); t.SetEnd(V(*c))
            t.SetWidth(mm(w)); t.SetLayer(layer); t.SetNet(ni); t.SetLocked(locked)
            board.Add(t)
    for net, x, y in VIAS:
        v = pcbnew.PCB_VIA(board); v.SetPosition(V(x, y))
        v.SetWidth(mm(drc.RULES["via"])); v.SetDrill(mm(drc.RULES["drill"]))
        v.SetLayerPair(F, B); v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetNet(board.FindNet(net)); v.SetLocked(locked); board.Add(v)


def design(board, path, stage):
    """Export the board for Freerouting, edited for the given stage."""
    pcbnew.ExportSpecctraDSN(board, str(path))
    d = path.read_text()
    d = S.edit_drop_nets(S.edit_power_class(d), HIDDEN)
    d = S.edit_boundary(S.edit_protect(d), S.inset_outline(G.OUTLINE, EDGE_INSET))
    if stage == 1:
        d = S.edit_bottom_power_layer(d)
    path.write_text(d)
    return d


def fingerprint(d):
    """Hash of the stage-1 design: everything before the wiring section (the
    hand copper), minus anything that names the run."""
    d = d[:d.index("  (wiring")]
    body = "\n".join(l for l in d.splitlines() if "host_version" not in l and "(pcb " not in l)
    return hashlib.sha256(body.encode()).hexdigest()


def freerouting():
    jar = FR_CACHE / f"freerouting-{FR_VERSION}.jar"
    if not jar.exists():
        FR_CACHE.mkdir(parents=True, exist_ok=True)
        print(f"downloading Freerouting {FR_VERSION} ...", flush=True)
        tmp = jar.with_suffix(".part")
        with urllib.request.urlopen(FR_URL) as r, open(tmp, "wb") as f:
            shutil.copyfileobj(r, f)
        tmp.rename(jar)
    digest = hashlib.sha256(jar.read_bytes()).hexdigest()
    if digest != FR_SHA256:
        sys.exit(f"{jar}: SHA-256 {digest} is not the published {FR_SHA256}")
    return jar


def run_stage(jar, dsn, ses, extra=()):
    t = time.time()
    r = subprocess.run(["java", "-jar", str(jar), "--gui.enabled=false",
                        "--usage_and_diagnostic_data.disable_analytics=true",
                        f"--router.job_timeout={STAGE_TIMEOUT}", *extra,
                        "-de", str(dsn), "-do", str(ses)],
                       capture_output=True, text=True, timeout=900)
    dsn.with_suffix(".log").write_text(r.stdout + r.stderr)
    left = S.unrouted(r.stdout + r.stderr)
    print(f"  {dsn.name}: {time.time() - t:.0f} s, Freerouting counts {left} open", flush=True)
    return left


def fresh_board():
    pcbnew.KIID.SeedGenerator(2)          # reproducible output, as in gen_pcb
    board = pcbnew.LoadBoard(str(BOARD))
    for t in list(board.GetTracks()):
        board.Delete(t)
    return board


def open_connections(session):
    """Connections KiCad finds open with this session laid. Freerouting's
    own count is not used to decide anything: with hand-placed LINKS in the
    design it has reported connections open on a board KiCad finds complete."""
    board = fresh_board()
    S.read_session(board, session)
    add_hand_copper(board, locked=False)
    drc.apply_rules(board)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.BuildConnectivity()
    return board.GetConnectivity().GetUnconnectedCount(False)


def reroute():
    jar = freerouting()
    board = fresh_board()
    add_hand_copper(board, locked=True)
    work = pathlib.Path(tempfile.mkdtemp(prefix="route-"))
    d1 = design(board, work / "stage1.dsn", 1)
    run_stage(jar, work / "stage1.dsn", work / "stage1.ses")
    left = open_connections(work / "stage1.ses")
    print(f"  KiCad: {left} connection(s) open after stage 1", flush=True)
    if left:
        S.read_session(board, work / "stage1.ses")
        for t in board.GetTracks():
            t.SetLocked(True)
        design(board, work / "stage2.dsn", 2)
        run_stage(jar, work / "stage2.dsn", work / "stage2.ses",
                  (f"--router.scoring.via_costs={STAGE2_VIA_COST}",))
        left = open_connections(work / "stage2.ses")
        if left:
            sys.exit(f"{left} connection(s) still open after stage 2; see {work}")
        final, stages = work / "stage2.ses", 2
    else:
        final, stages = work / "stage1.ses", 1
    shutil.copyfile(final, SESSION)
    META.write_text(json.dumps({"freerouting": FR_VERSION, "stages": stages,
                                "design_sha256": fingerprint(d1)}, indent=2) + "\n")
    print(f"wrote {SESSION.name} ({stages} stage{'s' if stages > 1 else ''})")


def lay():
    board = fresh_board()
    # The design the committed route was made for must be the design we have.
    add_hand_copper(board, locked=True)
    work = pathlib.Path(tempfile.mkdtemp(prefix="route-"))
    want = json.loads(META.read_text())["design_sha256"]
    got = fingerprint(design(board, work / "stage1.dsn", 1))
    if got != want:
        sys.exit("carrier.ses was routed for a different placement or netlist.\n"
                 "Run: /usr/bin/python3 route.py --reroute   (then rebuild)")
    for t in list(board.GetTracks()):
        board.Delete(t)
    tracks, vias = S.read_session(board, SESSION)
    add_hand_copper(board, locked=False)
    drc.apply_rules(board)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(str(BOARD), board)
    segs = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK"]
    length = sum(pcbnew.ToMM(t.GetLength()) for t in segs)
    print(f"laid {SESSION.name}: {tracks} signal segments, {vias} signal vias; "
          f"{len(PATHS)} hand paths, {len(LINKS)} hand links, {len(VIAS)} GND vias; "
          f"{length:.0f} mm of track")


if __name__ == "__main__":
    if "--reroute" in sys.argv:
        reroute()
    lay()
