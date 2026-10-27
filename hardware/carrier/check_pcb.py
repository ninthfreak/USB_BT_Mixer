#!/usr/bin/python3
"""Check the board's mechanical intent -- things KiCad's DRC cannot know.

DRC (drc.py) owns clearances, courtyard overlaps, holes and connectivity.
This checks the decisions behind the layout, read from the board KiCad
actually built:

  1. both input boards face the hosts with their NATIVE USB port: turned
     180 degrees, board edge on the front edge, the proud shell hanging past
     it by at least 0.5 mm (review-notes #25)
  2. the ESP32's USB-C end overhangs the left edge, so a flashing cable's
     overmold hangs in free air (AUDIT.md #9)
  3. the ESP32's antenna end overhangs the notch by the whole antenna
     (esp_ant_l in boards.scad) plus 0.5 mm, with no carrier under it
     (AUDIT.md #6)
  4. every mounting hole leaves at least 1.5 mm of FR4 to the edge
     (AUDIT.md #11 -- the old rear holes left 0.5 mm)
"""
import pathlib, sys
import pcbnew

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_pcb as G

MM = pcbnew.ToMM

def module_box(fp):
    """Module outline from its F.Fab drawing, which gen_fp draws at the real
    board edges."""
    xs, ys = [], []
    for g in fp.GraphicalItems():
        if g.GetLayer() == pcbnew.F_Fab and g.GetClass() in ("MGRAPHIC", "FP_SHAPE", "PCB_SHAPE"):
            for p in (g.GetStart(), g.GetEnd()):
                xs.append(MM(p.x)); ys.append(MM(p.y))
    return min(xs), min(ys), max(xs), max(ys)

def main():
    b = pcbnew.LoadBoard(str(HERE / "carrier.kicad_pcb"))
    fp = {f.GetReference(): f for f in b.GetFootprints()}
    fails = []

    for ref in ("U1", "U2"):
        rot = fp[ref].GetOrientationDegrees() % 360
        edge = MM(fp[ref].GetPosition().y) - G.B["board_l"] / 2
        shell = module_box(fp[ref])[1]          # fab drawing includes the shells
        print(f"{ref}: turned {rot:.0f} deg, board edge at y = {edge:+.3f}, "
              f"native USB shell overhangs the front edge by {-shell:.2f} mm")
        if abs(rot - 180) > 0.01:
            fails.append(f"{ref}: turned {rot:.0f} deg; the native USB port must face the front (180)")
        if abs(edge) > 0.01:
            fails.append(f"{ref}: board edge at y={edge:.3f}, not on the front edge")
        if -shell < 0.5:
            fails.append(f"{ref}: native USB shell overhangs only {-shell:.2f} mm (want >= 0.5)")

    x0, y0, x1, y1 = module_box(fp["U3"])
    usb = -x0
    ant = x1 - G.X_NOTCH
    print(f"U3 USB-C end overhangs the left edge by {usb:.2f} mm")
    print(f"U3 antenna end overhangs the notch by {ant:.2f} mm "
          f"(module front edge y {y0:.2f}, notch starts y {G.Y_STEP})")
    if usb < 0.5:
        fails.append(f"U3 USB-C end overhangs only {usb:.2f} mm (want >= 0.5)")
    want = G.B["esp_ant_l"] + 0.5
    if ant < want:
        fails.append(f"U3 antenna overhang {ant:.2f} mm (want >= {want:.2f}: "
                     f"the {G.B['esp_ant_l']} mm antenna plus 0.5)")
    if y0 <= G.Y_STEP:
        fails.append("carrier extends under the antenna end: the notch starts behind the module")

    edges = list(zip(G.OUTLINE, G.OUTLINE[1:] + G.OUTLINE[:1]))
    def dist(px, py, a, c):
        (ax, ay), (cx, cy) = a, c
        vx, vy = cx - ax, cy - ay
        t = max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / (vx * vx + vy * vy)))
        return ((px - ax - t * vx) ** 2 + (py - ay - t * vy) ** 2) ** 0.5
    for i in range(1, 5):
        h = fp[f"H{i}"]
        x, y = MM(h.GetPosition().x), MM(h.GetPosition().y)
        r = MM(list(h.Pads())[0].GetDrillSize().x) / 2
        web = min(dist(x, y, a, c) for a, c in edges) - r
        print(f"H{i} at ({x:.1f},{y:.1f}): {web:.2f} mm of FR4 to the edge")
        if web < 1.5:
            fails.append(f"H{i}: only {web:.2f} mm to the edge (want >= 1.5)")

    if fails:
        print("\nFAIL")
        for f in fails:
            print("  -", f)
        sys.exit(1)
    print("\nOK: native USB ports over the front edge, ESP32 overhangs both ends, holes have proper webs")

if __name__ == "__main__":
    main()
