#!/usr/bin/env python3
"""Pre-routing feasibility estimate for the placement in gen_pcb.py.

There is no DRC in KiCad 7's CLI and no autorouter, so this does not prove
routability. What it does measure, from the real placement:

  * minimum spanning length of every net (a lower bound on trace length)
  * the I2S runs against the <10 cm rule in hardware/wiring.md
  * whether any CONNECTED pad falls inside the antenna keep-out
  * how much copper area is actually available

Module pads are exact (U1/U2 at 0 deg, U3 at 180 deg). Two-pin passives are
approximated by their courtyard centre, so net lengths are underestimates by
up to the lead pitch of each passive on the net -- stated, not hidden.
"""
import sys, itertools, math
import netlist as N
import gen_pcb as G

def module_pads(ref):
    """Exact global pad positions for a 0/180-degree part."""
    fpid = N.FOOTPRINTS[ref]
    ox, oy, rot = G.origin(ref, fpid)
    out = {}
    import re
    for num, x, y in re.findall(
            r'\(pad\s+"(\d+)"\s+\S+\s+\S+\s+\(at (-?[\d.]+) (-?[\d.]+)', G.load_fp(fpid)):
        px, py = float(x), float(y)
        if rot == 180:
            px, py = -px, -py
        elif rot != 0:
            return None
        out[int(num)] = (ox + px, oy + py)
    return out

def points():
    """(ref, pad) -> (x, y), exact where possible, centre otherwise."""
    pts, approx = {}, set()
    for ref in G.PLACE:
        mp = module_pads(ref)
        if mp is not None:
            for num, xy in mp.items():
                pts[(ref, num)] = xy
        else:
            cx, cy, _ = G.PLACE[ref]
            for num in N.pad_names()[ref]:
                pts[(ref, num)] = (cx, cy)
                approx.add(ref)
    return pts, approx

def mst_len(ps):
    if len(ps) < 2:
        return 0.0
    unused, used, total = list(ps[1:]), [ps[0]], 0.0
    while unused:
        d, i, p = min((math.dist(u, v), i, u)
                      for i, u in enumerate(unused) for v in used)
        total += d; used.append(p); unused.pop(i)
    return total

def main():
    pts, approx = points()
    nets = N.resolved_nets()
    ant = (G.W - 10.0, 39.0, G.W, 67.0)
    fails, rows = [], []

    for name, nodes in sorted(nets.items()):
        ps = [pts[n] for n in nodes if n in pts]
        L = mst_len(ps)
        rough = any(r in approx for r, _ in nodes)
        rows.append((name, len(nodes), L, rough))
        for (r, pad), (x, y) in zip(nodes, ps):
            if ant[0] <= x <= ant[2] and ant[1] <= y <= ant[3]:
                fails.append(f"net {name}: {r}.{pad} at ({x:.1f},{y:.1f}) is "
                             f"inside the antenna keep-out")

    print(f"{'net':8} {'pads':>4} {'min length':>11}")
    for name, n, L, rough in rows:
        print(f"{name:8} {n:>4} {L:>9.1f} mm {'~' if rough else ''}")
    total = sum(r[2] for r in rows)
    longest = max(rows, key=lambda r: r[2])
    print(f"\ntotal {total:.0f} mm over {len(rows)} nets; "
          f"longest {longest[0]} at {longest[2]:.1f} mm")
    print("(~ = includes a passive approximated by its centre; real length is longer)")

    i2s = [r for r in rows if r[0].startswith(("BCLK", "LRCK", "AUD"))]
    worst = max(i2s, key=lambda r: r[2])
    print(f"\nI2S: worst net {worst[0]} at {worst[2]:.1f} mm "
          f"(wiring.md asks for <100 mm) -> {'OK' if worst[2] < 100 else 'TOO LONG'}")
    if worst[2] >= 100:
        fails.append(f"I2S net {worst[0]} exceeds 100 mm")

    area = G.W * G.H
    print(f"\ncopper available: {area:.0f} mm2 per layer, {2*area:.0f} mm2 over two layers")
    print(f"the module areas are free for routing on BOTH layers: the modules")
    print(f"touch only their edge pads and are flat underneath (review-notes #23)")
    # 0.4 mm trace on 0.4 mm clearance is a conservative hobby-fab default
    used = total * 0.8
    print(f"at 0.4 mm trace / 0.4 mm clearance that is ~{used:.0f} mm2, "
          f"{100*used/(2*area):.0f}% of the copper")

    if fails:
        print("\nFAIL")
        for f in fails:
            print("  -", f)
        sys.exit(1)
    print("\nOK: no connected pad in the keep-out, I2S within budget")

if __name__ == "__main__":
    main()
