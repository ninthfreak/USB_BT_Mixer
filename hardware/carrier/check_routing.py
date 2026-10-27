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
"""
import collections, pathlib, sys
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

    if fails:
        print("\nFAIL")
        for f in fails:
            print("  -", f)
        sys.exit(1)
    print("\nOK: power nets full width, I2S within budget, bottom pour solid, every signal on top")

if __name__ == "__main__":
    main()
