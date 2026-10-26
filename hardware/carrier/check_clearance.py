#!/usr/bin/env python3
"""Geometric clearance check for the routed carrier.

KiCad 7's CLI has no DRC, so this measures the board directly. For every pair
of copper features on the same layer that belong to DIFFERENT nets, it
computes the real edge-to-edge distance and requires it to be at least the
design clearance. Unconnected pads are each treated as their own net, because
floating copper still has to clear everything.

This is my own arithmetic, so it is only trustworthy on inputs that something
else has confirmed: check_pads_vs_kicad.py verifies independently that the
copper really is where this reads it from. Run both.

Covered: trace-trace, trace-pad, trace-via, pad-pad, via-anything, copper to
board edge, copper into the antenna keep-out.
NOT covered: zone fills (there are none), soldermask, silkscreen, drill
spacing. A DRC pass in the KiCad editor is still required before ordering.
"""
import math, pathlib, re, sys
import netlist as N
import gen_pcb as G
import route as R

HERE = pathlib.Path(__file__).resolve().parent
CLEAR = R.CLEAR

def seg_seg(p, q, r, s):
    def d_pt_seg(px, py, ax, ay, bx, by):
        vx, vy = bx - ax, by - ay
        L = vx * vx + vy * vy
        t = 0.0 if L == 0 else max(0.0, min(1.0, ((px-ax)*vx + (py-ay)*vy) / L))
        return math.hypot(px - (ax + t*vx), py - (ay + t*vy))
    d1 = (q[0]-p[0], q[1]-p[1]); d2 = (s[0]-r[0], s[1]-r[1])
    den = d1[0]*d2[1] - d1[1]*d2[0]
    if abs(den) > 1e-12:
        t = ((r[0]-p[0])*d2[1] - (r[1]-p[1])*d2[0]) / den
        u = ((r[0]-p[0])*d1[1] - (r[1]-p[1])*d1[0]) / den
        if 0 <= t <= 1 and 0 <= u <= 1:
            return 0.0
    return min(d_pt_seg(*p, *r, *s), d_pt_seg(*q, *r, *s),
               d_pt_seg(*r, *p, *q), d_pt_seg(*s, *p, *q))

def seg_rect(p, q, cx, cy, w, h):
    x0, x1, y0, y1 = cx-w/2, cx+w/2, cy-h/2, cy+h/2
    edges = (((x0,y0),(x1,y0)), ((x1,y0),(x1,y1)),
             ((x1,y1),(x0,y1)), ((x0,y1),(x0,y0)))
    inside = lambda a: x0 <= a[0] <= x1 and y0 <= a[1] <= y1
    if inside(p) or inside(q):
        return 0.0
    return min(seg_seg(p, q, a, b) for a, b in edges)

def rect_rect(a, b):
    dx = max(0.0, max(a[0]-a[2]/2 - (b[0]+b[2]/2), b[0]-b[2]/2 - (a[0]+a[2]/2)))
    dy = max(0.0, max(a[1]-a[3]/2 - (b[1]+b[3]/2), b[1]-b[3]/2 - (a[1]+a[3]/2)))
    return math.hypot(dx, dy)

def load():
    txt = (HERE / "carrier.kicad_pcb").read_text()
    netname = {int(i): n for i, n in re.findall(r'\(net (\d+) "([^"]*)"\)', txt)}
    segs = [((float(a), float(b)), (float(c), float(d)), float(w), L,
             netname.get(int(n), f"?{n}"))
            for a, b, c, d, w, L, n in re.findall(
                r'\(segment \(start (-?[\d.]+) (-?[\d.]+)\) \(end (-?[\d.]+) (-?[\d.]+)\)'
                r' \(width ([\d.]+)\) \(layer "([^"]+)"\) \(net (\d+)\)\)', txt)]
    vias = [(float(x), float(y), float(s)) for x, y, s in re.findall(
        r'\(via \(at (-?[\d.]+) (-?[\d.]+)\) \(size ([\d.]+)\)', txt)]
    return segs, vias

def main():
    segs, vias = load()
    pd = R.pads()
    nets = N.resolved_nets()
    padnet = {}
    for net, nodes in nets.items():
        for ref, num in nodes:
            padnet[(ref, str(num))] = net

    # objects: (kind, layer, net, geometry)
    objs = []
    for (ref, num), (x, y, w, h) in pd.items():
        if not num:
            continue
        net = padnet.get((ref, num), f"<float {ref}.{num}>")
        layers = ("F.Cu", "B.Cu") if R._is_tht(ref) else ("F.Cu",)
        for L in layers:
            objs.append(("pad", L, net, (x, y, w, h), f"{ref}.{num}"))
    for p, q, w, L, net in segs:
        objs.append(("seg", L, net, (p, q, w), net))
    for i, (x, y, s) in enumerate(vias):
        # vias carry net 0 in the file; attribute them by the traces they join
        touching = {n for p, q, w, LL, n in segs
                    if min(math.dist(p, (x, y)), math.dist(q, (x, y))) < 1e-6}
        net = touching.pop() if len(touching) == 1 else (
            "/".join(sorted(touching)) if touching else f"<via{i}>")
        for L in ("F.Cu", "B.Cu"):
            objs.append(("pad", L, net, (x, y, s, s), f"via{i}"))

    fails = []
    for i in range(len(objs)):
        ka, La, na, ga, ia = objs[i]
        for j in range(i + 1, len(objs)):
            kb, Lb, nb, gb, ib = objs[j]
            if La != Lb or na == nb:
                continue
            if "/" in na and nb in na.split("/"):  continue
            if "/" in nb and na in nb.split("/"):  continue
            if ka == "seg" and kb == "seg":
                d = seg_seg(ga[0], ga[1], gb[0], gb[1]) - ga[2]/2 - gb[2]/2
            elif ka == "seg":
                d = seg_rect(ga[0], ga[1], *gb) - ga[2]/2
            elif kb == "seg":
                d = seg_rect(gb[0], gb[1], *ga) - gb[2]/2
            else:
                d = rect_rect(ga, gb)
            if d < CLEAR - 1e-6:
                fails.append((d, La, na, ia, nb, ib))

    # board edge and antenna keep-out
    ax0, ay0, ax1, ay1 = G.W - 10.0, 39.0, G.W, 67.0
    for p, q, w, L, net in segs:
        for pt in (p, q):
            m = min(pt[0], pt[1], G.W - pt[0], G.H - pt[1]) - w/2
            if m < 0.2:
                fails.append((m, L, net, "board edge", "", ""))
            if ax0 <= pt[0] <= ax1 and ay0 <= pt[1] <= ay1:
                fails.append((0.0, L, net, "antenna keep-out", "", ""))

    print(f"{len(segs)} segments, {len(vias)} vias, {len([o for o in objs if o[0]=='pad'])} pad instances")
    print(f"checked every same-layer pair of different nets at {CLEAR} mm")
    if fails:
        fails.sort()
        print(f"\nFAIL: {len(fails)} violations, worst first")
        for d, L, na, ia, nb, ib in fails[:15]:
            print(f"  - {d:+.3f} mm on {L}: {na} ({ia}) vs {nb} ({ib})")
        sys.exit(1)
    print("\nOK: no clearance violation, nothing in the keep-out, nothing off the edge")

if __name__ == "__main__":
    main()
