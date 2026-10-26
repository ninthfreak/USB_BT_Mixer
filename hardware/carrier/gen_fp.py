#!/usr/bin/env python3
"""Generate land patterns for the two castellated modules into carrier.pretty/.

Both boards are through-hole AND castellated on the edge (owner, boards in
hand), so each solders flat with the iron reaching the OUTSIDE of every joint.
The land pattern is therefore referenced to the module's BOARD OUTLINE, not to
its hole centres -- which is why the one dimension still soft on the ESP32
(header row spacing) does not enter this file at all.

Board dimensions come from enclosure/boards.scad, parsed, never restated here.
Waveshare dimensions both boards; see hardware/wiring.md for provenance.

Origin is the module outline centre. +Y is:
  RP2350  -> the PROGRAMMING port end (the proud one)
  ESP32   -> header J3 (pads 1..19)
"""
import pathlib, re

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "carrier.pretty"
SCAD = HERE.parents[1] / "enclosure" / "boards.scad"

B = {n: float(v) for n, v in
     re.findall(r"^\s*(\w+)\s*=\s*(-?[\d.]+)\s*;", SCAD.read_text(), re.M)}

# ── Land geometry, shared by both modules ────────────────────────────────
PAD_W   = 1.30   # along the edge; 2.54 pitch leaves a 1.24 mm gap
PAD_L   = 3.00   # across the edge
PAD_OUT = 1.10   # how far the pad sticks out past the module outline
# so the pad centre sits this far INSIDE the outline:
PAD_IN_OFF = PAD_L / 2 - PAD_OUT          # 0.40

LINE, SILK, FAB, CRT = 0.12, "F.SilkS", "F.Fab", "F.CrtYd"

def hdr(name, descr, tags):
    return [f'(footprint "{name}" (version 20221018) (generator gen_fp.py)',
            '  (layer "F.Cu")', f'  (descr "{descr}")', f'  (tags "{tags}")',
            '  (attr smd)']

def text(kind, val, x, y, layer):
    return (f'  (fp_text {kind} "{val}" (at {x} {y}) (layer "{layer}")\n'
            f'    (effects (font (size 1 1) (thickness 0.15))))')

def line(x0, y0, x1, y1, layer, w=LINE):
    return (f'  (fp_line (start {x0:.3f} {y0:.3f}) (end {x1:.3f} {y1:.3f})'
            f' (stroke (width {w}) (type solid)) (layer "{layer}"))')

def polyline(pts, layer, w=LINE):
    return [line(pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1], layer, w)
            for i in range(len(pts) - 1)]

def rect(x0, y0, x1, y1, layer, w=LINE):
    return polyline([(x0,y0),(x1,y0),(x1,y1),(x0,y1),(x0,y0)], layer, w)

def pad(num, x, y, w, h):
    return (f'  (pad "{num}" smd rect (at {x:.3f} {y:.3f}) (size {w} {h})'
            f' (layers "F.Cu" "F.Paste" "F.Mask"))')

def npth(x, y, d):
    return (f'  (pad "" np_thru_hole circle (at {x:.3f} {y:.3f}) (size {d} {d})'
            f' (drill {d}) (layers "F&B.Cu" "*.Mask"))')

def circle(x, y, r, layer, w=LINE):
    return (f'  (fp_circle (center {x:.3f} {y:.3f}) (end {x+r:.3f} {y:.3f})'
            f' (stroke (width {w}) (type solid)) (fill none) (layer "{layer}"))')

# ── RP2350-USB-C ─────────────────────────────────────────────────────────
def rp2350():
    w, l = B["board_w"], B["board_l"]
    hw, hl = w / 2, l / 2
    first, pitch = B["pad_first"], B["pad_pitch"]
    n = int(B["pad_count"])
    nd, nl, ndep = B["notch_d"], B["notch_len"], B["notch_dep"]

    o = hdr("RP2350-USB-C",
            "Waveshare RP2350-USB-C, castellated, soldered flat. "
            "+Y is the PROGRAMMING (proud) port end; -Y is the EXPOSED port "
            "that must meet the enclosure wall.",
            "waveshare rp2350 castellated module")
    o.append(text("reference", "REF**", 0, -hl - 1.6, SILK))
    o.append(text("value", "RP2350-USB-C", 0, hl + 1.6, FAB))

    # pads: 1..9 left edge from the programming end, 10..18 right edge
    y0 = hl - first
    for i in range(n):
        y = y0 - i * pitch
        o.append(pad(i + 1, -hw + PAD_IN_OFF, y, PAD_L, PAD_W))
        o.append(pad(n + i + 1, hw - PAD_IN_OFF, y, PAD_L, PAD_W))

    # fab: real outline with the two retention notches cut (port end only)
    ny1 = -hl + nd
    ny0 = ny1 + nl
    o += polyline([(-hw, -hl), (-hw, ny1), (-hw + ndep, ny1),
                   (-hw + ndep, ny0), (-hw, ny0), (-hw, hl),
                   (hw, hl), (hw, ny0), (hw - ndep, ny0),
                   (hw - ndep, ny1), (hw, ny1), (hw, -hl), (-hw, -hl)], FAB)
    # USB-C shells on fab: exposed one flush, programming one proud
    uw, ud = B["usb_w"] / 2, B["usb_depth"]
    o += rect(-uw, -hl - B["usb_over_out"], uw, -hl - B["usb_over_out"] + ud, FAB)
    o += rect(-uw, hl + B["usb_over_in"], uw, hl + B["usb_over_in"] - ud, FAB)

    # silk: short ticks clear of the pads, plus a pin-1 dot
    for sx in (-1, 1):
        o.append(line(sx * hw, hl, sx * hw, y0 + 1.2, SILK))
        o.append(line(sx * hw, -hl, sx * hw, ny1 - 0.3, SILK))
    o.append(line(-hw, hl, hw, hl, SILK))
    o.append(line(-hw, -hl, hw, -hl, SILK))
    o.append(circle(-hw - PAD_OUT - 0.7, y0, 0.25, SILK))
    o += rect(-hw - PAD_OUT - 0.5, -hl - B["usb_over_out"] - 0.25,
              hw + PAD_OUT + 0.5, hl + B["usb_over_in"] + 0.25, CRT, 0.05)
    o.append(")")
    return "\n".join(o)

# ── ESP32-DEV-KIT ────────────────────────────────────────────────────────
def esp32():
    w, d = B["esp_w"], B["esp_d"]
    hw, hd = w / 2, d / 2
    n, pitch = 19, 2.54
    span = (n - 1) * pitch
    x0 = -span / 2                      # pin 1 at 4.04 from the short edge
    assert abs((w - span) / 2 - 4.04) < 0.01, "pin-1 inset moved"

    o = hdr("ESP32-DEV-KIT",
            "Waveshare ESP32-DEV-KIT-WROOM-32E-N4, castellated, soldered flat. "
            "Pads 1-19 are header J3 (+Y), pads 20-38 are J4 (-Y). "
            "ANTENNA at -X: keep copper away.",
            "waveshare esp32 wroom castellated module")
    o.append(text("reference", "REF**", 0, -hd - 1.6, SILK))
    o.append(text("value", "ESP32-DEV-KIT", 0, hd + 1.6, FAB))

    for i in range(n):
        x = x0 + i * pitch
        o.append(pad(i + 1, x, hd - PAD_IN_OFF, PAD_W, PAD_L))        # J3
        o.append(pad(n + i + 1, x, -hd + PAD_IN_OFF, PAD_W, PAD_L))   # J4

    o += rect(-hw, -hd, hw, hd, FAB)
    # optional clearance holes under the module's own mounting holes
    for sx in (-1, 1):
        for sy in (-1, 1):
            o.append(npth(sx * B["esp_hole_dx"] / 2, sy * B["esp_hole_dy"] / 2, 3.0))
    # USB-C at +X, antenna at -X
    uw = B["esp_usb_w"] / 2
    o += rect(hw - 7.5, -uw, hw, uw, FAB)
    o.append(text("user", "ANT", -hw + 4, 0, FAB))
    # antenna keep-out reminder on fab
    o += rect(-hw, -hd, -hw + 8, hd, FAB)

    o.append(line(-hw, hd, hw, hd, SILK))
    o.append(line(-hw, -hd, hw, -hd, SILK))
    for sy in (-1, 1):
        o.append(line(-hw, sy * hd, -hw, sy * (hd - 2), SILK))
        o.append(line(hw, sy * hd, hw, sy * (hd - 2), SILK))
    o.append(circle(x0, hd + PAD_OUT + 0.7, 0.25, SILK))
    o += rect(-hw - 0.25, -hd - PAD_OUT - 0.5, hw + 0.25, hd + PAD_OUT + 0.5,
              CRT, 0.05)
    o.append(")")
    return "\n".join(o)

def main():
    OUT.mkdir(exist_ok=True)
    for name, fn in (("RP2350-USB-C", rp2350), ("ESP32-DEV-KIT", esp32)):
        (OUT / f"{name}.kicad_mod").write_text(fn() + "\n")
        print(f"wrote carrier.pretty/{name}.kicad_mod")

if __name__ == "__main__":
    main()
