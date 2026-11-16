#!/usr/bin/python3
"""Check the ROUTED board for design intent that KiCad's DRC cannot know.

drc.py owns clearance, connectivity, keep-outs and holes. This reads the
tracks route.py actually laid and checks what the rules alone would pass:

  1. power nets (VBUS1, VBUS2, RAIL) are 0.8 mm wide everywhere -- the DRC
     minimum is 0.4 mm, which would let a thin neck through
  2. every I2S chain, ESP32 pin to input-board pin, is under 100 mm.
     Measured as the total copper of the nets in the chain, which is an
     upper bound on any one path through it
  3. the bottom pour stays a ground plane: at least 80 % of the board area
     is filled GND copper on B.Cu, so the clocks on top have a return path
  4. the layout rule (gen_pcb.py): every signal stays on the top layer --
     no signal track on B.Cu and no signal via. Only power runs on the
     bottom, and the only vias are ground's
  5. the plane is one piece where it matters: each input board's ground via
     reaches both of the ESP32's ground vias through pour at least 2 mm wide
     all the way. Fill percentage (3) cannot see this: the rail once ran
     between the boards' ground pads and the rest of the plane, leaving two
     0.5 mm slivers as their only ground, at 89 % fill and a clean DRC
     (docs/project-review-2026-11.md #2)
"""
import collections, math, pathlib, sys
import pcbnew

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_pcb as G

MM = pcbnew.ToMM
POWER = {"VBUS1": 0.8, "VBUS2": 0.8, "RAIL": 0.8}
I2S_BUDGET = 100.0
# ESP32 pin -> series resistor -> input board pin. AUD nets have no resistor.
CHAINS = {"BCLK to in 1": ("BCLK", "BCLK1"), "BCLK to in 2": ("BCLK", "BCLK2"),
          "LRCK to in 1": ("LRCK", "LRCK1"), "LRCK to in 2": ("LRCK", "LRCK2"),
          "AUD1": ("AUD1",), "AUD2": ("AUD2",)}
B_FILL_MIN = 0.80
GND = "GND"
GND_NECK_MIN = 2.0                  # mm of pour, module ground to ESP32 ground
GND_PADS = {"U1": ["2"], "U2": ["2"], "U3": ["14", "26"]}
PM = pcbnew.SHAPE_POLY_SET.PM_STRICTLY_SIMPLE


def P(x, y): return pcbnew.VECTOR2I(pcbnew.FromMM(float(x)), pcbnew.FromMM(float(y)))


def ground_vias(b):
    """ref -> [(x, y)]: for each module ground pad, the nearest GND via."""
    vias = [(MM(t.GetPosition().x), MM(t.GetPosition().y)) for t in b.GetTracks()
            if t.GetClass() == "PCB_VIA" and t.GetNetname() == GND]
    out = {}
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNumber() in GND_PADS.get(fp.GetReference(), ()):
                x, y = MM(pad.GetPosition().x), MM(pad.GetPosition().y)
                d, v = min((math.hypot(vx - x, vy - y), (vx, vy)) for vx, vy in vias) if vias else (99, None)
                if d <= 3.0:
                    out.setdefault(fp.GetReference(), []).append(v)
    return out


def pieces_near(full, eroded, x, y, reach):
    """The pieces of the eroded pour that (x, y) sits on: any piece a straight
    line of at most `reach` from the point gets to without leaving copper.
    (A via beside a track is closer to the pour's edge than the erosion.)"""
    out = set()
    for i in range(int(reach / 0.1) + 1):
        for a in range(0, 360, 10):
            px = x + i * 0.1 * math.cos(math.radians(a))
            py = y + i * 0.1 * math.sin(math.radians(a))
            if all(full.Contains(P(x + (px - x) * t / 20, y + (py - y) * t / 20)) for t in range(21)):
                out |= {k for k in range(eroded.OutlineCount()) if eroded.Contains(P(px, py), k)}
    return out


def ground_necks(b, width):
    """Pairs (input board, ESP32 via) NOT joined by pour at least `width` wide."""
    z = [z for z in b.Zones() if not z.GetIsRuleArea() and z.IsOnLayer(pcbnew.B_Cu)][0]
    full = pcbnew.SHAPE_POLY_SET(z.GetFilledPolysList(pcbnew.B_Cu))
    full.Unfracture(PM)                     # KiCad stores fills with keyhole slits
    eroded = pcbnew.SHAPE_POLY_SET(full)
    eroded.Deflate(pcbnew.FromMM(width / 2), 32)
    eroded.Simplify(PM)
    gv = ground_vias(b)
    bad = [f"{ref}: no ground via within 3 mm of its GND pad" for ref in GND_PADS if not gv.get(ref)]
    near = lambda v: pieces_near(full, eroded, v[0], v[1], width / 2 + 0.7)
    for ref in ("U1", "U2"):
        for v in gv.get(ref, []):
            for e in gv.get("U3", []):
                if not near(v) & near(e):
                    bad.append(f"{ref} ground via ({v[0]:.1f}, {v[1]:.1f}) to the ESP32's at "
                               f"({e[0]:.1f}, {e[1]:.1f}): pour narrower than {width} mm on the way")
    return bad, gv

def main():
    b = pcbnew.LoadBoard(str(HERE / "carrier.kicad_pcb"))
    fails = []
    length = collections.Counter()
    bottom = collections.Counter()
    vias = collections.Counter()
    for t in b.GetTracks():
        net = t.GetNetname()
        if t.GetClass() == "PCB_VIA":
            vias[net] += 1
            continue
        L = MM(t.GetLength())
        length[net] += L
        if t.GetLayer() == pcbnew.B_Cu:
            bottom[net] += L
        if net in POWER and MM(t.GetWidth()) < POWER[net] - 1e-6:
            fails.append(f"{net}: a {MM(t.GetWidth()):.2f} mm segment (want {POWER[net]})")

    print(f"{'net':8} {'track mm':>9} {'on B.Cu':>8} {'vias':>5}")
    for net in sorted(length):
        print(f"{net:8} {length[net]:9.1f} {bottom[net]:8.1f} {vias[net]:5}")
    total = sum(length.values())
    print(f"total {total:.0f} mm, {sum(bottom.values()):.0f} mm of it on B.Cu")

    print(f"\nI2S chains (upper bound, budget {I2S_BUDGET:.0f} mm):")
    for name, nets in CHAINS.items():
        L = sum(length[n] for n in nets)
        print(f"  {name:13} {L:6.1f} mm  {'ok' if L < I2S_BUDGET else 'TOO LONG'}")
        if L >= I2S_BUDGET:
            fails.append(f"I2S chain {name}: {L:.1f} mm")

    area = G.W * G.Y_STEP + G.X_NOTCH * (G.H - G.Y_STEP)
    fill = {}
    for z in b.Zones():
        if z.GetIsRuleArea():
            continue
        for lid, key in ((pcbnew.F_Cu, "F"), (pcbnew.B_Cu, "B")):
            if z.IsOnLayer(lid):
                fill[key] = fill.get(key, 0) + MM(MM(z.GetFilledPolysList(lid).Area()))
    print(f"\nGND pour fill: top {fill.get('F', 0) / area:.0%}, "
          f"bottom {fill.get('B', 0) / area:.0%} of {area:.0f} mm2")
    if fill.get("B", 0) / area < B_FILL_MIN:
        fails.append(f"bottom GND pour covers {fill.get('B', 0) / area:.0%} (want >= {B_FILL_MIN:.0%})")
    sig_bottom = {n: L for n, L in bottom.items() if n not in POWER and n != GND and L > 0}
    sig_vias = {n: k for n, k in vias.items() if n != GND}
    print(f"signals on B.Cu: {sig_bottom or 'none'}; signal vias: {sig_vias or 'none'}; "
          f"GND vias: {vias[GND]}")
    for n, L in sig_bottom.items():
        fails.append(f"{n}: {L:.1f} mm on the bottom layer (signals stay on top)")
    for n, k in sig_vias.items():
        fails.append(f"{n}: {k} via(s) (signals never change layer)")

    necks, gv = ground_necks(b, GND_NECK_MIN)
    print(f"ground path, each input board's via to the ESP32's {len(gv.get('U3', []))} vias, "
          f"at least {GND_NECK_MIN} mm of pour: {'ok' if not necks else 'NO'}")
    fails += necks

    if fails:
        print("\nFAIL")
        for f in fails:
            print("  -", f)
        sys.exit(1)
    print("\nOK: power nets full width, I2S within budget, bottom pour solid and in one piece "
          "between the modules, every signal on top")

if __name__ == "__main__":
    main()
