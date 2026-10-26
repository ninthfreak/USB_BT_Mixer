#!/usr/bin/python3
"""Route carrier.kicad_pcb: grid A* over two layers, then KiCad fills the pours.

Runs under the SYSTEM python with KiCad's pcbnew bindings, and takes all
geometry from KiCad rather than from our own arithmetic. The previous router
modelled every pad as its bounding rectangle -- tracks ended in the corners of
round pads, outside the copper, and nine connections were open while it
reported success (AUDIT.md #2). Here:

  * pad shapes come from KiCad's own PAD.HitTest, inflated for clearance, so
    circles and ovals are circles and ovals
  * a track may start or end only where KiCad says the point is well inside
    the pad
  * through-hole pads exist on both layers, so a net changes layer AT its
    pad instead of drilling a via beside it (AUDIT.md #5)
  * vias keep 0.5 mm drill-to-drill from every hole of every net, their own
    included
  * clearance is stamped as a true distance, plus a margin for the grid: a
    path between two allowed cell centres can pass up to GRID*sqrt(2)/2 closer
    to an obstacle than either centre

Ground is not routed as traces. Both layers carry a GND pour; surface GND
pads get a short stub to a via, and a lattice of stitching vias ties the two
pours together. KiCad fills the pours at the end and drc.py confirms every
GND pad actually reaches one.

The bottom layer costs three times as much as the top, so signals stay on
top and the bottom pour stays whole under the clocks.
"""
import heapq, math, pathlib, sys
import numpy as np
import pcbnew

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import netlist as N
import gen_pcb as G
import drc

mm, MM = pcbnew.FromMM, pcbnew.ToMM
def V(x, y): return pcbnew.VECTOR2I(mm(float(x)), mm(float(y)))

R = drc.RULES               # the router works to the rules DRC enforces
GRID = 0.2
TRACE, POWER = R["track"], 0.80
CLEAR = R["clearance"]
VIA_D, VIA_DR = R["via"], R["drill"]
EDGE = R["edge"]            # copper to board edge
HOLE_GAP = R["hole_to_hole"]  # drill edge to drill edge, any nets
MARGIN = 0.15               # > GRID*sqrt(2)/2, see docstring
B_COST, VIA_COST = 3.0, 12.0
POWER_NETS = {"RAIL", "VBUS1", "VBUS2"}
STITCH = 6.0                # stitching-via lattice pitch

NX = int(math.ceil(G.W / GRID)) + 1
NY = int(math.ceil(G.H / GRID)) + 1
XS = np.arange(NX) * GRID
YS = np.arange(NY) * GRID
GX, GY = np.meshgrid(XS, YS)          # [j, i] -> mm

# Obstacle inflation, measured from an obstacle's COPPER EDGE to the centre
# line of what is being placed:
INF_T = {TRACE: CLEAR + TRACE / 2 + MARGIN,      # 0.60
         POWER: CLEAR + POWER / 2 + MARGIN}      # 0.80
INF_V = CLEAR + VIA_D / 2 + MARGIN               # 0.80

# ── Static obstacles: edge, keep-out, holes ──────────────────────────────
def seg_dist(ax, ay, bx, by):
    vx, vy = bx - ax, by - ay
    L = vx * vx + vy * vy
    t = np.clip(((GX - ax) * vx + (GY - ay) * vy) / L, 0, 1)
    return np.hypot(GX - (ax + t * vx), GY - (ay + t * vy))

def inside_outline():
    return (((GX >= 0) & (GX <= G.W) & (GY >= 0) & (GY <= G.Y_STEP)) |
            ((GX >= 0) & (GX <= G.X_NOTCH) & (GY >= 0) & (GY <= G.H)))

def edge_distance():
    pts = G.OUTLINE
    d = np.full(GX.shape, np.inf)
    for (ax, ay), (bx, by) in zip(pts, pts[1:] + pts[:1]):
        d = np.minimum(d, seg_dist(ax, ay, bx, by))
    d[~inside_outline()] = -1.0
    return d

def rect_distance(x0, y0, x1, y1):
    dx = np.maximum(np.maximum(x0 - GX, 0), GX - x1)
    dy = np.maximum(np.maximum(y0 - GY, 0), GY - y1)
    return np.hypot(np.maximum(dx, 0), np.maximum(dy, 0))

def window(x0, y0, x1, y1):
    i0, i1 = max(0, int((x0) / GRID)), min(NX, int(math.ceil(x1 / GRID)) + 1)
    j0, j1 = max(0, int((y0) / GRID)), min(NY, int(math.ceil(y1 / GRID)) + 1)
    return slice(j0, j1), slice(i0, i1)

def stamp_disc_seg(mask, a, b, r):
    """True distance stamp: every cell within r of segment a-b."""
    sj, si = window(min(a[0], b[0]) - r, min(a[1], b[1]) - r,
                    max(a[0], b[0]) + r, max(a[1], b[1]) + r)
    gx, gy = GX[sj, si], GY[sj, si]
    vx, vy = b[0] - a[0], b[1] - a[1]
    L = vx * vx + vy * vy
    t = np.zeros_like(gx) if L == 0 else np.clip(((gx - a[0]) * vx + (gy - a[1]) * vy) / L, 0, 1)
    mask[sj, si] |= np.hypot(gx - (a[0] + t * vx), gy - (a[1] + t * vy)) <= r

# ── Pads ─────────────────────────────────────────────────────────────────
class Pad:
    def __init__(self, fp, p):
        self.ref, self.num = fp.GetReference(), p.GetNumber()
        self.net = p.GetNetname() or None
        self.pad = p
        self.tht = p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH
        self.npth = p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH
        self.layers = [L for L, lid in ((0, pcbnew.F_Cu), (1, pcbnew.B_Cu)) if p.IsOnLayer(lid)]
        bb = p.GetBoundingBox()
        self.box = (MM(bb.GetLeft()), MM(bb.GetTop()), MM(bb.GetRight()), MM(bb.GetBottom()))
        c = p.GetPosition()
        self.x, self.y = MM(c.x), MM(c.y)
        self.drill = MM(p.GetDrillSize().x) if (self.tht or self.npth) else 0.0

    def mask(self, inflate):
        """Cells whose centre lies within `inflate` mm of the pad copper."""
        x0, y0, x1, y1 = self.box
        sj, si = window(x0 - inflate, y0 - inflate, x1 + inflate, y1 + inflate)
        m = np.zeros((NY, NX), dtype=bool)
        acc = mm(inflate)
        for j in range(sj.start, sj.stop):
            for i in range(si.start, si.stop):
                if self.pad.HitTest(V(XS[i], YS[j]), acc):
                    m[j, i] = True
        return m

    def inside_cells(self):
        """Cells KiCad agrees are well inside the copper: the centre and four
        points 0.12 mm away all hit. A track ending here is connected."""
        x0, y0, x1, y1 = self.box
        sj, si = window(x0, y0, x1, y1)
        out, d = [], 0.12
        for j in range(sj.start, sj.stop):
            for i in range(si.start, si.stop):
                x, y = XS[i], YS[j]
                if all(self.pad.HitTest(V(x + ox, y + oy))
                       for ox, oy in ((0, 0), (d, 0), (-d, 0), (0, d), (0, -d))):
                    out.append((i, j))
        if not out:   # tiny pad: fall back to the nearest cell to its centre
            out = [(int(round(self.x / GRID)), int(round(self.y / GRID)))]
        return [(L, i, j) for L in self.layers for i, j in out]

# ── A* ───────────────────────────────────────────────────────────────────
NB = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
      (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142)]

def astar(blockT, blockV, starts, goal_test, goal_box):
    gx0, gy0, gx1, gy1 = goal_box
    def h(i, j):
        dx = max(gx0 - i, 0, i - gx1); dy = max(gy0 - j, 0, j - gy1)
        return math.hypot(dx, dy)
    pq, dist, came = [], {}, {}
    for s in starts:
        dist[s] = 0.0
        heapq.heappush(pq, (h(s[1], s[2]), 0.0, s, None))
    while pq:
        f, d, cur, prev = heapq.heappop(pq)
        if cur in came:
            continue
        came[cur] = prev
        if goal_test(cur):
            path = []
            while cur is not None:
                path.append(cur); cur = came[cur]
            return path[::-1]
        L, i, j = cur
        step = 1.0 if L == 0 else B_COST
        for di, dj, w in NB:
            ni, nj = i + di, j + dj
            if 0 <= ni < NX and 0 <= nj < NY and not blockT[L, nj, ni]:
                k = (L, ni, nj); nd = d + w * step
                if nd < dist.get(k, 1e18):
                    dist[k] = nd
                    heapq.heappush(pq, (nd + h(ni, nj), nd, k, cur))
        if not blockV[j, i]:
            k = (1 - L, i, j); nd = d + VIA_COST
            if nd < dist.get(k, 1e18):
                dist[k] = nd
                heapq.heappush(pq, (nd + h(i, j), nd, k, cur))
    return None

def cells_on(a, b):
    """Grid cells whose square the segment a-b crosses (a, b in cells).
    Sampled every 0.01 mm: a crossing missed by sampling is shorter than
    that, so every point on the segment lies within 0.1414 + 0.005 mm of a
    returned cell centre -- inside MARGIN, which is what makes a segment
    over free cells legal."""
    n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) * GRID / 0.01))
    t = np.linspace(0, 1, n + 1)
    i = np.rint(a[0] + t * (b[0] - a[0])).astype(int)
    j = np.rint(a[1] + t * (b[1] - a[1])).astype(int)
    return set(zip(i.tolist(), j.tolist()))

def pull(path, blockT):
    """String-pull a grid path: on each same-layer run, jump straight to the
    furthest later point that has a clear line of sight. Turns the A*
    staircase into a few straight segments. Layer changes stay put."""
    out = [path[0]]
    k = 0
    while k < len(path) - 1:
        L = path[k][0]
        if path[k + 1][0] != L:                 # via: keep both ends
            out.append(path[k + 1]); k += 1; continue
        end = k + 1
        while end + 1 < len(path) and path[end + 1][0] == L:
            end += 1
        best = k + 1
        for m in range(end, k + 1, -1):
            a, b = path[k][1:], path[m][1:]
            if not any(blockT[L, j, i] for i, j in cells_on(a, b)):
                best = m; break
        out.append(path[best]); k = best
    return out

# ── Main ─────────────────────────────────────────────────────────────────
def main():
    path = HERE / "carrier.kicad_pcb"
    pcbnew.KIID.SeedGenerator(2)            # reproducible output, as in gen_pcb
    board = pcbnew.LoadBoard(str(path))
    nets = {str(name): board.FindNet(str(name)) for name in N.resolved_nets()}
    old = list(board.GetTracks())               # idempotent: start from placement
    for t in old:
        board.Delete(t)

    # Sorted: KiCad's own item order follows UUIDs, and the route must not
    # depend on it.
    pads = sorted((Pad(fp, p) for fp in board.GetFootprints() for p in fp.Pads()),
                  key=lambda q: (q.ref, q.num))
    print(f"{len(pads)} pads; building obstacle maps ...", flush=True)

    ed = edge_distance()
    kx = [p[0] for p in G.KEEPOUT]; ky = [p[1] for p in G.KEEPOUT]
    kd = rect_distance(min(kx), min(ky), max(kx), max(ky))
    staticT = {w: (ed < EDGE + w / 2 + MARGIN) | (kd < w / 2 + MARGIN) for w in (TRACE, POWER)}
    staticV = (ed < EDGE + VIA_D / 2 + MARGIN) | (kd < VIA_D / 2 + MARGIN)

    # Drill-to-drill: a via keeps HOLE_GAP from every hole, any net.
    holes = np.zeros((NY, NX), dtype=bool)
    for p in pads:
        if p.drill:
            holes |= np.hypot(GX - p.x, GY - p.y) < p.drill / 2 + HOLE_GAP + VIA_DR / 2 + MARGIN
    # NPTH holes have no copper; tracks still keep clear of the drill.
    for p in pads:
        if p.npth:
            for w in (TRACE, POWER):
                staticT[w] |= np.hypot(GX - p.x, GY - p.y) < p.drill / 2 + CLEAR + w / 2 + MARGIN

    # Per-pad obstacle masks, per layer: T for each width, V for vias.
    pm = {}
    for k, p in enumerate(pads):
        if p.npth:
            continue
        mT4, mT8 = p.mask(INF_T[TRACE]), p.mask(INF_T[POWER])
        pm[k] = (mT4, mT8)          # INF_T[POWER] == INF_V
    print("obstacle maps done", flush=True)

    # Copper routed so far, per net: [T0.4 F, T0.4 B, T0.8 F, T0.8 B, V]
    routed = {}
    def blank(): return np.zeros((5, NY, NX), dtype=bool)

    def obstacles(net, width):
        bT = np.zeros((2, NY, NX), dtype=bool)
        bV = staticV | holes
        bT[0] |= staticT[width]; bT[1] |= staticT[width]
        wi = 0 if width == TRACE else 1
        for k, p in enumerate(pads):
            if p.npth or p.net == net and net is not None:
                continue
            m = pm[k][wi]; mv = pm[k][1]
            for L in p.layers:
                bT[L] |= m
            bV = bV | mv            # a via is on both layers
        for n, r in routed.items():
            if n == net:
                continue
            bT[0] |= r[2 * wi]; bT[1] |= r[2 * wi + 1]
            bV = bV | r[4]
        return bT, bV

    def add_track(net, a, b, L, width):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(V(*a)); t.SetEnd(V(*b)); t.SetWidth(mm(width))
        t.SetLayer(pcbnew.F_Cu if L == 0 else pcbnew.B_Cu)
        t.SetNet(nets[net]); board.Add(t)
        r = routed.setdefault(net, blank())
        stamp_disc_seg(r[2 * 0 + L], a, b, width / 2 + CLEAR + TRACE / 2 + MARGIN)
        stamp_disc_seg(r[2 * 1 + L], a, b, width / 2 + CLEAR + POWER / 2 + MARGIN)
        stamp_disc_seg(r[4], a, b, width / 2 + CLEAR + VIA_D / 2 + MARGIN)

    def add_via(net, x, y):
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(V(x, y)); v.SetWidth(mm(VIA_D)); v.SetDrill(mm(VIA_DR))
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetNet(nets[net]); board.Add(v)
        r = routed.setdefault(net, blank())
        for L in (0, 1):
            stamp_disc_seg(r[L], (x, y), (x, y), VIA_D / 2 + CLEAR + TRACE / 2 + MARGIN)
            stamp_disc_seg(r[2 + L], (x, y), (x, y), VIA_D / 2 + CLEAR + POWER / 2 + MARGIN)
        stamp_disc_seg(r[4], (x, y), (x, y), VIA_D / 2 + CLEAR + VIA_D / 2 + MARGIN)
        holes[np.hypot(GX - x, GY - y) < VIA_DR + HOLE_GAP + MARGIN] = True

    def emit(net, cells, blockT, width):
        """Lay the path as copper; return (vias, cells now under our copper).
        The copper follows the pulled path, not the raw A* cells, so only
        cells along the pulled segments may seed this net's later links."""
        pts = pull(cells, blockT)
        n_via, covered = 0, set()
        for a, b in zip(pts, pts[1:]):
            if a[0] != b[0]:
                add_via(net, a[1] * GRID, a[2] * GRID); n_via += 1
                covered |= {(0, a[1], a[2]), (1, a[1], a[2])}
            else:
                add_track(net, (a[1] * GRID, a[2] * GRID), (b[1] * GRID, b[2] * GRID), a[0], width)
                covered |= {(a[0], i, j) for i, j in cells_on(a[1:], b[1:])}
        return n_via, covered

    order = (["VBUS2", "VBUS1"] +
             [n for n in ("BCLK", "BCLK1", "BCLK2", "LRCK", "LRCK1", "LRCK2")] +
             ["AUD1", "AUD2"] +
             ["U1_TX", "ESP_TX1", "U1_RX", "U2_TX", "ESP_TX2", "U2_RX"] +
             ["RAIL"] +
             ["GP29_1", "GP29_2", "DBG1", "DBG2", "SP1", "SP2", "SP3"])
    assert set(order) == set(N.resolved_nets()) - {"GND"}, set(N.resolved_nets()) ^ set(order)

    failed, vias = [], 0
    for net in order:
        width = POWER if net in POWER_NETS else TRACE
        own = [p for p in pads if p.net == net]
        bT, bV = obstacles(net, width)
        islands = [set(c for c in p.inside_cells() if not bT[c[0], c[2], c[1]]) for p in own]
        names = [[f"{p.ref}.{p.num}"] for p in own]
        while len(islands) > 1:
            best = None
            order_pairs = sorted(((i, j) for i in range(len(islands))
                                  for j in range(i + 1, len(islands))),
                                 key=lambda ij: min(math.dist((a[1], a[2]), (b[1], b[2]))
                                                    for a in list(islands[ij[0]])[:40]
                                                    for b in list(islands[ij[1]])[:40]))
            for i, j in order_pairs:
                goals = islands[j]
                if not islands[i] or not goals:
                    continue
                gi = [c[1] for c in goals]; gj = [c[2] for c in goals]
                cells = astar(bT, bV, list(islands[i]), lambda c: c in goals,
                              (min(gi), min(gj), max(gi), max(gj)))
                if cells:
                    best = (i, j, cells); break
            if best is None:
                failed.append((net, names[0][0], names[1][0])); break
            i, j, cells = best
            nv, covered = emit(net, cells, bT, width)
            vias += nv
            islands[i] |= islands[j] | {c for c in covered if not bT[c[0], c[2], c[1]]}
            names[i] += names[j]
            del islands[j], names[j]
            bT, bV = obstacles(net, width)     # our own copper never blocks us
        print(f"  {net:8} {'routed' if not failed or failed[-1][0] != net else 'FAILED'}", flush=True)

    # Ground: surface GND pads get a stub to the nearest place a via fits;
    # through-hole GND pads already reach both pours.
    bT, bV = obstacles("GND", TRACE)
    stubs = 0
    for p in pads:
        if p.net != "GND" or p.tht:
            continue
        starts = [c for c in p.inside_cells() if not bT[c[0], c[2], c[1]]]
        cells = astar(bT, bV, starts, lambda c: c[0] == 1, (0, 0, NX, NY))
        if cells is None:
            failed.append(("GND", f"{p.ref}.{p.num}", "via")); continue
        vias += emit("GND", cells, bT, TRACE)[0]; stubs += 1
        bT, bV = obstacles("GND", TRACE)

    # Stitching vias tie the two pours together on a lattice.
    stitched = 0
    for y in np.arange(STITCH / 2, G.H, STITCH):
        for x in np.arange(STITCH / 2, G.W, STITCH):
            i, j = int(round(x / GRID)), int(round(y / GRID))
            if 0 <= i < NX and 0 <= j < NY and not bV[j, i] and not bT[0, j, i] and not bT[1, j, i]:
                add_via("GND", i * GRID, j * GRID); stitched += 1
                bT, bV = obstacles("GND", TRACE)

    print("filling pours ...", flush=True)
    drc.apply_rules(board)      # so the board opens in KiCad with these rules
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(str(path), board)

    tracks = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK"]
    length = sum(MM(t.GetLength()) for t in tracks)
    print(f"\n{len(order) - len({f[0] for f in failed if f[0] != 'GND'})}/{len(order)} signal nets routed, "
          f"{len(tracks)} segments, {vias} routed vias, {stubs} GND stubs, "
          f"{stitched} stitching vias, {length:.0f} mm of track")
    if failed:
        print("UNROUTED")
        for f in failed:
            print("  -", f)
        sys.exit(1)

if __name__ == "__main__":
    main()
