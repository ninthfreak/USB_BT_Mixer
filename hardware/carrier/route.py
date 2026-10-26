#!/usr/bin/env python3
"""Route carrier.kicad_pcb: a grid A* router over two layers.

Design rules, deliberately loose for a cheap fab (JLCPCB allows 0.127 mm):
    trace 0.40 mm, clearance 0.25 mm, via 0.8 mm pad on a 0.4 mm drill.

Everything is routed as copper TRACES, including ground. A ground pour would
be better for clock return paths, but a zone's filled shape is computed by
KiCad and I cannot verify it here, so the board is left fully routed without
one. Adding a B.Cu ground pour in the editor afterwards is one action and
KiCad will DRC it.

Obstacles are stamped into a grid with the clearance already inflated, so a
path that exists is a path that fits. check_clearance.py re-measures the
result rather than trusting this.
"""
import heapq, pathlib, re, sys
import numpy as np
import netlist as N
import gen_pcb as G

GRID   = 0.2      # mm per cell
TRACE  = 0.40
CLEAR  = 0.25
VIA_D  = 0.80     # annular pad
VIA_DR = 0.40     # drill
EDGE_K = 0.60     # keep copper this far inside the board edge
LAYERS = ("F.Cu", "B.Cu")

W, H = G.W, G.H
NX, NY = int(round(W / GRID)) + 1, int(round(H / GRID)) + 1

def cells(mm):          # clearance in whole cells, always rounded up
    return int(np.ceil(mm / GRID - 1e-9))

# A via may land next to an existing trace, so everything is stamped at the
# larger of the two separations. Routing one at TRACE+CLEAR and then dropping
# a via there left 0.05 mm violations.
TT = cells(max(TRACE + CLEAR, VIA_D / 2 + CLEAR + TRACE / 2))
PAD_K = CLEAR + max(TRACE, VIA_D) / 2

def pads():
    """(ref, padname) -> (x, y, w, h) in board mm, F.Cu only."""
    out = {}
    for ref in G.PLACE:
        fpid = N.FOOTPRINTS[ref]
        ox, oy, rot = G.origin(ref, fpid)
        for num, x, y, pr, w, h in re.findall(
                r'\(pad\s+"([^"]*)"\s+\S+\s+\S+\s+\(at (-?[\d.]+) (-?[\d.]+)(?:\s+(-?[\d.]+))?\)'
                r'\s+\(size ([\d.]+) ([\d.]+)\)', G.load_fp(fpid)):
            dx, dy = G.xform(float(x), float(y), rot)
            pw, ph = float(w), float(h)
            if (rot + float(pr or 0)) % 180 == 90:
                pw, ph = ph, pw
            out[(ref, num)] = (ox + dx, oy + dy, pw, ph)
    return out

def stamp_rect(grid, x, y, w, h, pad_mm):
    x0 = max(0, int((x - w / 2 - pad_mm) / GRID))
    x1 = min(NX, int(np.ceil((x + w / 2 + pad_mm) / GRID)) + 1)
    y0 = max(0, int((y - h / 2 - pad_mm) / GRID))
    y1 = min(NY, int(np.ceil((y + h / 2 + pad_mm) / GRID)) + 1)
    grid[y0:y1, x0:x1] = True

def stamp_seg(grid, p, q, r_cells):
    """Block every cell within r_cells of the segment p-q."""
    n = max(2, int(np.hypot(q[0]-p[0], q[1]-p[1]) / GRID) + 1)
    for t in np.linspace(0, 1, n):
        cx, cy = int(round((p[0]+(q[0]-p[0])*t)/GRID)), int(round((p[1]+(q[1]-p[1])*t)/GRID))
        x0, x1 = max(0, cx-r_cells), min(NX, cx+r_cells+1)
        y0, y1 = max(0, cy-r_cells), min(NY, cy+r_cells+1)
        grid[y0:y1, x0:x1] = True

def static_grid():
    """Blocked regardless of net: board edge, antenna keep-out, drilled holes."""
    g = np.zeros((2, NY, NX), dtype=bool)
    m = cells(EDGE_K)
    g[:, :m, :] = g[:, -m:, :] = g[:, :, :m] = g[:, :, -m:] = True
    ax0, ay0, ax1, ay1 = W - 10.0, 39.0, W, 67.0
    g[:, int(ay0/GRID):int(np.ceil(ay1/GRID))+1,
         int(ax0/GRID):int(np.ceil(ax1/GRID))+1] = True
    for hx, hy in G.MOUNT:
        for L in (0, 1):
            stamp_rect(g[L], hx, hy, G.MOUNT_D, G.MOUNT_D, PAD_K)
    ox, oy, rot = G.origin("U3", N.FOOTPRINTS["U3"])
    for x, y, d in re.findall(r'\(pad "" np_thru_hole circle \(at (-?[\d.]+) (-?[\d.]+)\)'
                              r'\s+\(size ([\d.]+)', G.load_fp(N.FOOTPRINTS["U3"])):
        dx, dy = G.xform(float(x), float(y), rot)
        for L in (0, 1):
            stamp_rect(g[L], ox+dx, oy+dy, float(d), float(d), PAD_K)
    return g

def pad_grid(pd, own):
    """Pads of every OTHER net. Built fresh per net: the previous version
    cleared a box around each of the net's own pads, which also erased any
    already-routed trace passing through that box."""
    g = np.zeros((2, NY, NX), dtype=bool)
    for (ref, num), (x, y, w, h) in pd.items():
        if not num or (ref, num) in own:
            continue
        stamp_rect(g[0], x, y, w, h, PAD_K)
        if _is_tht(ref):
            stamp_rect(g[1], x, y, w, h, PAD_K)
    return g

def _is_tht(ref):
    return N.PARTS[ref]["kind"] in ("r", "c", "cpol", "d", "hdr", "sj", "tp")

NB = [(1,0,1.0),(-1,0,1.0),(0,1,1.0),(0,-1,1.0),
      (1,1,1.4142),(1,-1,1.4142),(-1,1,1.4142),(-1,-1,1.4142)]

def astar(blocked, starts, goals, via_cost=14.0):
    """Route from any start cell to any goal cell across 2 layers."""
    goalset = set(goals)
    dist = {}
    pq = []
    for s in starts:
        dist[s] = 0.0
        heapq.heappush(pq, (0.0, s, None))
    gx = np.array([g[1] for g in goals]); gy = np.array([g[2] for g in goals])
    came = {}
    while pq:
        d, cur, prev = heapq.heappop(pq)
        if cur in came:
            continue
        came[cur] = prev
        if cur in goalset:
            path = []
            while cur is not None:
                path.append(cur); cur = came[cur]
            return path[::-1]
        L, x, y = cur
        for dx, dy, w in NB:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < NX and 0 <= ny < NY) or blocked[L, ny, nx]:
                continue
            nd = d + w
            k = (L, nx, ny)
            if nd < dist.get(k, 1e18):
                dist[k] = nd
                h = float(np.min(np.hypot(gx - nx, gy - ny)))
                heapq.heappush(pq, (nd + h, k, cur))
        o = 1 - L
        if not blocked[o, y, x]:
            nd = d + via_cost
            k = (o, x, y)
            if nd < dist.get(k, 1e18):
                dist[k] = nd
                h = float(np.min(np.hypot(gx - x, gy - y)))
                heapq.heappush(pq, (nd + h, k, cur))
    return None

def pad_cells(x, y, w, h):
    x0, x1 = int((x - w/2)/GRID) + 1, int((x + w/2)/GRID)
    y0, y1 = int((y - h/2)/GRID) + 1, int((y + h/2)/GRID)
    out = [(0, cx, cy) for cx in range(max(0,x0), min(NX, x1+1))
                       for cy in range(max(0,y0), min(NY, y1+1))]
    return out or [(0, int(round(x/GRID)), int(round(y/GRID)))]

def simplify(path):
    """Collapse a cell path into straight runs."""
    pts = [path[0]]
    for i in range(1, len(path) - 1):
        a, b, c = path[i-1], path[i], path[i+1]
        if a[0] != b[0] or b[0] != c[0]:
            pts.append(b); continue
        if (b[1]-a[1], b[2]-a[2]) != (c[1]-b[1], c[2]-b[2]):
            pts.append(b)
    pts.append(path[-1])
    return pts

def main():
    pd = pads()
    nets = N.resolved_nets()
    padnet = {}
    for net, nodes in nets.items():
        for ref, num in nodes:
            padnet[(ref, str(num))] = net

    static = static_grid()
    obstacle = np.zeros((2, NY, NX), dtype=bool)   # accumulated copper
    tracks, vias, failed = [], [], []

    # Hardest first. Input 2's power pads face the 2.2 mm gap between the two
    # modules, so VBUS2 gets the channel before anything else can take it.
    # GND goes last: it has 13 pads and tolerates any detour.
    def rank(name):
        if name.startswith("VBUS"):           return (0, name)
        if name.startswith(("BCLK", "LRCK")): return (1, name)
        if name.startswith("AUD"):            return (2, name)
        if name.startswith(("U1_", "U2_")):   return (3, name)
        if name == "RAIL":                    return (4, name)
        if name == "GND":                     return (6, name)
        return (5, name)

    for net in sorted(nets, key=rank):
        nodes = [(r, str(p)) for r, p in nets[net]]
        grid = static | obstacle | pad_grid(pd, set(nodes))
        # Each island is (pads, routable cells). A net must be able to T into
        # its own earlier traces -- stamping them as obstacles against itself
        # is what stranded the last GND pad.
        groups = [([n], set(pad_cells(*pd[n]))) for n in nodes]

        while len(groups) > 1:
            pairs = sorted(
                ((min(np.hypot(pd[a][0]-pd[b][0], pd[a][1]-pd[b][1])
                      for a in groups[i][0] for b in groups[j][0]), i, j)
                 for i in range(len(groups)) for j in range(i+1, len(groups))))
            path = None
            for _, i, j in pairs:
                starts = [c for c in groups[i][1] if not grid[c[0], c[2], c[1]]]
                goals = [c for c in groups[j][1] if not grid[c[0], c[2], c[1]]]
                if not starts or not goals:
                    continue
                path = astar(grid, starts, goals)
                if path is not None:
                    gi, gj = i, j
                    break
            if path is None:
                failed.append((net, groups[0][0][0], groups[1][0][0]))
                break
            pts = simplify(path)
            for a, b in zip(pts, pts[1:]):
                if a[0] != b[0]:
                    vx, vy = a[1]*GRID, a[2]*GRID
                    vias.append((vx, vy))
                    for t in (grid, obstacle[0], obstacle[1]):
                        pass
                    stamp_rect(obstacle[0], vx, vy, VIA_D, VIA_D, PAD_K)
                    stamp_rect(obstacle[1], vx, vy, VIA_D, VIA_D, PAD_K)
                else:
                    p = (a[1]*GRID, a[2]*GRID); q = (b[1]*GRID, b[2]*GRID)
                    tracks.append((p, q, LAYERS[a[0]], net))
                    stamp_seg(obstacle[a[0]], p, q, TT)
            merged = (groups[gi][0] + groups[gj][0],
                      groups[gi][1] | groups[gj][1] | set(path))
            groups = [merged] + [g for k, g in enumerate(groups)
                                 if k not in (gi, gj)]

    emit(tracks, vias)
    tot = sum(np.hypot(q[0]-p[0], q[1]-p[1]) for p, q, _, _ in tracks)
    print(f"routed {len(nets) - len({f[0] for f in failed})}/{len(nets)} nets, "
          f"{len(tracks)} segments, {len(vias)} vias, {tot:.0f} mm of track")
    if failed:
        print("\nUNROUTED")
        for net, a, b in failed:
            print(f"  - {net}: {a[0]}.{a[1]} to {b[0]}.{b[1]}")
        sys.exit(1)

def emit(tracks, vias):
    src = pathlib.Path(__file__).resolve().parent / "carrier.kicad_pcb"
    txt = src.read_text().rstrip()
    assert txt.endswith(")")
    body = txt[:-1].rstrip()
    body = re.sub(r'\n\s*\(segment .*?\)\n', '\n', body, flags=re.S)
    out = [body]
    nets = sorted({t[3] for t in tracks})
    idx = {n: i + 1 for i, n in enumerate(nets)}
    for n, i in idx.items():
        out.append(f'  (net {i} "{n}")')
    for p, q, layer, net in tracks:
        out.append(f'  (segment (start {p[0]:.3f} {p[1]:.3f}) '
                   f'(end {q[0]:.3f} {q[1]:.3f}) (width {TRACE}) '
                   f'(layer "{layer}") (net {idx[net]}))')
    for x, y in vias:
        out.append(f'  (via (at {x:.3f} {y:.3f}) (size {VIA_D}) (drill {VIA_DR}) '
                   f'(layers "F.Cu" "B.Cu") (net 0))')
    out.append(')')
    src.write_text("\n".join(out) + "\n")

if __name__ == "__main__":
    main()
