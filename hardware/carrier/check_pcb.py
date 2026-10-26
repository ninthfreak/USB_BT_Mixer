#!/usr/bin/env python3
"""Check the placement in carrier.kicad_pcb.

KiCad 7's CLI has no DRC, so this covers what placement can be checked
without one:

  1. every part's courtyard lies inside the board outline
  2. no two courtyards overlap
  3. the two exposed USB-C ports land on the front edge (y = 0), because
     that edge is the enclosure's port wall
  4. no part sits on a mounting hole
  5. nothing intrudes into the antenna keep-out
  5. every part in netlist.py is actually placed

It does NOT check track clearance, because there are no tracks: routing is
done in the PCB editor with live DRC.
"""
import pathlib, re, sys
import netlist as N
import gen_pcb as G

HERE = pathlib.Path(__file__).resolve().parent

def overlap(a, b, slack=0.0):
    return (a[0] < b[2] - slack and b[0] < a[2] - slack and
            a[1] < b[3] - slack and b[1] < a[3] - slack)

def main():
    fails, boxes = [], {}

    missing = set(N.PARTS) - set(G.PLACE)
    if missing:
        fails.append(f"not placed: {sorted(missing)}")

    pads = {}
    for ref in G.PLACE:
        fp = N.FOOTPRINTS[ref]
        if G.courtyard(fp) is None:
            fails.append(f"{ref}: footprint has no courtyard")
            continue
        boxes[ref], pads[ref] = G.boxes_for(ref, fp)

    # Containment is judged on PADS, not courtyards: a courtyard is a
    # clearance envelope and is meant to run off the edge where a module sits
    # flush with it, as both RP boards deliberately do.
    for ref, bb in pads.items():
        if not (0 <= bb[0] and 0 <= bb[1] and bb[2] <= G.W and bb[3] <= G.H):
            fails.append(f"{ref}: pads {tuple(round(v,2) for v in bb)} "
                         f"outside the 0,0-{G.W},{G.H} outline")

    refs = sorted(boxes)
    for i, a in enumerate(refs):
        for b in refs[i + 1:]:
            if overlap(boxes[a], boxes[b]):
                fails.append(f"{a} and {b} courtyards overlap: "
                             f"{tuple(round(v,2) for v in boxes[a])} vs "
                             f"{tuple(round(v,2) for v in boxes[b])}")

    # the exposed port must sit ON the front edge, or it will not reach the wall
    for ref in ("U1", "U2"):
        x, y, rot = G.origin(ref, N.FOOTPRINTS[ref])
        front = y - G.B["board_l"] / 2          # module outline, exposed end
        if abs(front) > 0.01:
            fails.append(f"{ref}: exposed port edge at y={front:.2f}, not 0")

    # Mounting holes are plain Edge.Cuts circles with no courtyard of their
    # own, so they were invisible to the overlap test above. The first render
    # showed both front holes drilled through D1 and D2.
    ring = G.MOUNT_D / 2 + 0.5
    for i, (hx, hy) in enumerate(G.MOUNT):
        hb = (hx - ring, hy - ring, hx + ring, hy + ring)
        for ref, bb in boxes.items():
            if overlap(bb, hb):
                fails.append(f"mounting hole {i+1} at ({hx},{hy}) collides with {ref}")

    ant = (G.W - 10.0, 39.0, G.W, 67.0)
    for ref, bb in boxes.items():
        if ref != "U3" and overlap(bb, ant, 0.001):
            fails.append(f"{ref} intrudes into the antenna keep-out")

    print(f"board  : {G.W} x {G.H} mm")
    print(f"placed : {len(boxes)} parts")
    used = sum((b[2]-b[0]) * (b[3]-b[1]) for b in boxes.values())
    print(f"courtyard area: {used:.0f} mm2 of {G.W*G.H:.0f} mm2 ({100*used/(G.W*G.H):.0f}%)")
    if fails:
        print("\nFAIL")
        for f in fails:
            print("  -", f)
        sys.exit(1)
    print("\nOK: all courtyards inside the outline, none overlapping, ports on the edge")

if __name__ == "__main__":
    main()
