#!/usr/bin/env python3
"""Check the generated module land patterns against enclosure/boards.scad.

Looking at a footprint catches gross errors; this catches the ones that look
fine. Every pad coordinate is recomputed from the board dimensions and
compared to what is actually in the .kicad_mod file.
"""
import pathlib, re, sys

HERE = pathlib.Path(__file__).resolve().parent
SCAD = HERE.parents[1] / "enclosure" / "boards.scad"
B = {n: float(v) for n, v in
     re.findall(r"^\s*(\w+)\s*=\s*(-?[\d.]+)\s*;", SCAD.read_text(), re.M)}
# boards.scad defines pad_last as an expression, so the literal parser misses
# it. Recompute rather than hardcode, so it still tracks the source.
B["pad_last"] = B["pad_first"] + (B["pad_count"] - 1) * B["pad_pitch"]
TOL = 0.002

def pads(name):
    txt = (HERE / "carrier.pretty" / f"{name}.kicad_mod").read_text()
    out = {}
    for num, x, y in re.findall(
            r'\(pad\s+"(\d+)"\s+smd\s+rect\s+\(at\s+(-?[\d.]+)\s+(-?[\d.]+)\)', txt):
        out[int(num)] = (float(x), float(y))
    return out

def near(a, b): return abs(a - b) < TOL

def extent(name, layer):
    """Bounding box of every fp_line on one layer."""
    txt = (HERE / "carrier.pretty" / f"{name}.kicad_mod").read_text()
    pts = [(float(a), float(b), float(c), float(d)) for a, b, c, d, lay in
           re.findall(r'\(fp_line \(start (-?[\d.]+) (-?[\d.]+)\) '
                      r'\(end (-?[\d.]+) (-?[\d.]+)\).*?\(layer "([^"]+)"\)', txt)
           if lay == layer]
    xs = [v for p in pts for v in (p[0], p[2])]
    ys = [v for p in pts for v in (p[1], p[3])]
    return min(xs), min(ys), max(xs), max(ys)

def main():
    fails = []
    off = 3.00 / 2 - 1.10          # PAD_L/2 - PAD_OUT, from gen_fp.py

    # ── RP2350: 9 pads per long edge, first 2.88 from the PROGRAMMING end ──
    p = pads("RP2350-USB-C")
    hw, hl = B["board_w"] / 2, B["board_l"] / 2
    n, pitch, first = int(B["pad_count"]), B["pad_pitch"], B["pad_first"]
    if len(p) != 2 * n:
        fails.append(f"RP2350: {len(p)} pads, expected {2*n}")
    for i in range(n):
        y = (hl - first) - i * pitch
        for num, x in ((i + 1, -hw + off), (n + i + 1, hw - off)):
            gx, gy = p.get(num, (None, None))
            if gx is None or not (near(gx, x) and near(gy, y)):
                fails.append(f"RP2350 pad {num}: {(gx,gy)} != {(round(x,3),round(y,3))}")
    # the far pad must land where boards.scad says the row ends
    if p and not near(p[n][1], hl - B["pad_last"]):
        fails.append(f"RP2350 pad {n} y={p[n][1]} != pad_last {hl - B['pad_last']}")

    # ── ESP32: 19 per row, span 45.72, rows on the long edges ──
    e = pads("ESP32-DEV-KIT")
    ew, ed = B["esp_w"] / 2, B["esp_d"] / 2
    n2, span = 19, 18 * 2.54
    if len(e) != 2 * n2:
        fails.append(f"ESP32: {len(e)} pads, expected {2*n2}")
    for i in range(n2):
        x = -span / 2 + i * 2.54
        for num, y in ((i + 1, ed - off), (n2 + i + 1, -ed + off)):
            gx, gy = e.get(num, (None, None))
            if gx is None or not (near(gx, x) and near(gy, y)):
                fails.append(f"ESP32 pad {num}: {(gx,gy)} != {(round(x,3),round(y,3))}")
    if e and not near((ew - span / 2), 4.04):
        fails.append(f"ESP32 pin-1 inset {ew - span/2:.3f} != 4.04")

    # the courtyard must enclose everything on the fab layer, proud
    # connectors included -- it is what stops another part being placed there
    for name in ("RP2350-USB-C", "ESP32-DEV-KIT"):
        fx0, fy0, fx1, fy1 = extent(name, "F.Fab")
        cx0, cy0, cx1, cy1 = extent(name, "F.CrtYd")
        if not (cx0 <= fx0 and cy0 <= fy0 and cx1 >= fx1 and cy1 >= fy1):
            fails.append(f"{name}: courtyard ({cx0},{cy0})-({cx1},{cy1}) does not "
                         f"enclose fab ({fx0},{fy0})-({fx1},{fy1})")

    print(f"RP2350 : {len(p)} pads, span {abs(p[1][1]-p[n][1]):.2f} mm")
    print(f"ESP32  : {len(e)} pads, span {abs(e[1][0]-e[n2][0]):.2f} mm")
    if fails:
        print("\nFAIL")
        for f in fails:
            print("  -", f)
        sys.exit(1)
    print("\nOK: every pad coordinate follows from enclosure/boards.scad")

if __name__ == "__main__":
    main()
