#!/usr/bin/env python3
"""Generate carrier.kicad_pcb: board outline and component placement.

PLACEMENT ONLY -- nothing is routed. KiCad 7's kicad-cli has no DRC
subcommand (it arrived in 8), so a generated layout cannot be machine
checked for clearance here, and this board has a 2.4 GHz antenna and clock
traces where layout quality is a judgement call. Routing belongs in the KiCad
PCB editor with live DRC. What IS checked, by check_pcb.py: every courtyard
inside the outline, no courtyard overlapping another, and the exposed USB-C
ports landing exactly on the front edge.

Frame: origin at the carrier's front-left corner, +X right, +Y back
(KiCad draws +Y downward, so the front edge is at the TOP of the view).
y = 0 is the port wall: the two exposed USB-C ports sit on it.

The frame maps to enclosure/box.scad by  pcb_y = 33.0 - box_y  and
pcb_x = box_x + 8.8.
"""
import pathlib, re

HERE = pathlib.Path(__file__).resolve().parent
SCAD = HERE.parents[1] / "enclosure" / "boards.scad"
B = {n: float(v) for n, v in
     re.findall(r"^\s*(\w+)\s*=\s*(-?[\d.]+)\s*;", SCAD.read_text(), re.M)}

# 64 mm wide, not 58. At 58 the two input boards left only a 2.2 mm channel
# between them, and SIX of input 2's nets need access from that side because
# both modules face the same way. The router could not fit them and nor could
# a person. The box is ours to size (the owner said so), so the board grew
# rather than the route getting cleverer. The enclosure needs ~5 mm more width.
W, H = 64.0, 74.0
EDGE, LINE = 0.10, 0.12

# Module centres. The RP boards span y 0..33 so their EXPOSED ports land on
# the front edge; the ESP32 is turned 180 deg so header J3 (power + I2S)
# faces them, which puts the antenna at the back RIGHT corner.
# Desired COURTYARD CENTRE of each part, and its rotation.
# Desired COURTYARD CENTRE of each part, and its rotation.
PLACE = {
    "U1": (17.55, 17.00, 0),
    "U2": (46.45, 17.00, 0),      # 11.4 mm clear between the two modules
    "U3": (32.00, 53.80, 180),
    # Service strip: only parts under ~4 mm tall fit, and the four series
    # resistors belong here anyway, against the ESP32's J3 row.
    "C2": (5.00, 36.4, 0),
    "R1": (15.00, 36.4, 0), "R2": (26.00, 36.4, 0),
    "R3": (37.00, 36.4, 0), "R4": (48.00, 36.4, 0),
    # Left column, below the front mounting hole.
    "D1": (3.40, 10.76, 90), "C3": (3.40, 20.07, 90),
    "C1": (3.40, 26.37, 90), "TP1": (3.40, 30.97, 0),
    # Right column.
    "D2": (60.45, 10.76, 90), "C4": (60.45, 20.07, 90),
    "TP2": (60.45, 24.87, 0), "SJ1": (60.45, 27.97, 0), "SJ2": (60.45, 31.07, 0),
    # Behind the ESP32, reachable with the lid off.
    "J1": (32.00, 72.10, 90),
}
MOUNT = [(3.0, 3.0), (W - 3.0, 3.0), (3.0, 72.1), (W - 3.0, 72.1)]
MOUNT_D = 2.8   # M2.5 clearance

LAYERS = """  (layers
    (0 "F.Cu" signal) (31 "B.Cu" signal)
    (32 "B.Adhes" user "B.Adhesive") (33 "F.Adhes" user "F.Adhesive")
    (34 "B.Paste" user) (35 "F.Paste" user)
    (36 "B.SilkS" user "B.Silkscreen") (37 "F.SilkS" user "F.Silkscreen")
    (38 "B.Mask" user) (39 "F.Mask" user)
    (40 "Dwgs.User" user "User.Drawings") (41 "Cmts.User" user "User.Comments")
    (42 "Eco1.User" user "User.Eco1") (43 "Eco2.User" user "User.Eco2")
    (44 "Edge.Cuts" user) (45 "Margin" user)
    (46 "B.CrtYd" user "B.Courtyard") (47 "F.CrtYd" user "F.Courtyard")
    (48 "B.Fab" user) (49 "F.Fab" user)
  )"""

def seg(x0, y0, x1, y1, layer, w):
    return (f'  (gr_line (start {x0:.3f} {y0:.3f}) (end {x1:.3f} {y1:.3f})'
            f' (stroke (width {w}) (type solid)) (layer "{layer}"))')

def box(x0, y0, x1, y1, layer, w):
    return [seg(x0, y0, x1, y0, layer, w), seg(x1, y0, x1, y1, layer, w),
            seg(x1, y1, x0, y1, layer, w), seg(x0, y1, x0, y0, layer, w)]

def _bbox(xs, ys):
    return (min(xs), min(ys), max(xs), max(ys)) if xs else None

def courtyard(fpid):
    """Local AABB of F.CrtYd. Stock footprints use poly, circle and arc as
    well as line."""
    txt, xs, ys = load_fp(fpid), [], []
    for m in re.finditer(r'\(fp_(line|poly|circle|arc|rect)\b(.*?)\(layer "([^"]+)"\)',
                         txt, re.S):
        if m.group(3) != "F.CrtYd":
            continue
        nums = [float(v) for v in re.findall(r'-?\d+\.?\d*', m.group(2))]
        if m.group(1) == "circle" and len(nums) >= 4:
            cx, cy, ex, ey = nums[:4]
            r = ((ex - cx) ** 2 + (ey - cy) ** 2) ** 0.5
            xs += [cx - r, cx + r]; ys += [cy - r, cy + r]
        else:
            xs += nums[0::2]; ys += nums[1::2]
    return _bbox(xs, ys)

def pad_box(fpid):
    """Local AABB covering every pad."""
    txt, xs, ys = load_fp(fpid), [], []
    for x, y, w, h in re.findall(
            r'\(pad\s+"[^"]*"\s+\S+\s+\S+\s+\(at (-?[\d.]+) (-?[\d.]+)(?:\s+-?[\d.]+)?\)'
            r'\s+\(size ([\d.]+) ([\d.]+)\)', txt):
        x, y, w, h = float(x), float(y), float(w), float(h)
        xs += [x - w / 2, x + w / 2]; ys += [y - h / 2, y + h / 2]
    return _bbox(xs, ys)

def xform(x, y, rot):
    """KiCad places a local point at angle `rot`. The angle is CCW on screen
    and screen Y points down, so in file coordinates:
        x' =  x*cos + y*sin,   y' = -x*sin + y*cos
    Getting this wrong is invisible when the generator and the check share it,
    which is exactly what happened: five 90-degree parts were up to 7.6 mm out
    and both agreed."""
    if rot == 0:   return x, y
    if rot == 90:  return y, -x
    if rot == 180: return -x, -y
    if rot == 270: return -y, x
    raise AssertionError(f"unsupported rotation {rot}")

def rotate(aabb, rot):
    x0, y0, x1, y1 = aabb
    xs, ys = zip(*(xform(x, y, rot)
                   for x in (x0, x1) for y in (y0, y1)))
    return min(xs), min(ys), max(xs), max(ys)

def origin(ref, fpid):
    """Footprint origin that puts the courtyard centre on PLACE[ref]."""
    cx, cy, rot = PLACE[ref]
    x0, y0, x1, y1 = rotate(courtyard(fpid), rot)
    return cx - (x0 + x1) / 2, cy - (y0 + y1) / 2, rot

def boxes_for(ref, fpid):
    """Placed (courtyard, pads) AABBs."""
    ox, oy, rot = origin(ref, fpid)
    def put(a):
        x0, y0, x1, y1 = rotate(a, rot)
        return ox + x0, oy + y0, ox + x1, oy + y1
    return put(courtyard(fpid)), put(pad_box(fpid))

def load_fp(fpid):
    lib, name = fpid.split(":", 1)
    for root in (HERE, pathlib.Path("/usr/share/kicad/footprints")):
        f = root / f"{lib}.pretty" / f"{name}.kicad_mod"
        if f.exists():
            return f.read_text().rstrip()
    raise SystemExit(f"footprint not found: {fpid}")

def main():
    import netlist as N
    out = ['(kicad_pcb (version 20221018) (generator gen_pcb.py)',
           '  (general (thickness 1.6))', '  (paper "A4")', LAYERS,
           '  (setup (pad_to_mask_clearance 0))']

    out += box(0, 0, W, H, "Edge.Cuts", EDGE)
    for x, y in MOUNT:
        out.append(f'  (gr_circle (center {x} {y}) (end {x + MOUNT_D/2} {y})'
                   f' (stroke (width {EDGE}) (type solid)) (fill none)'
                   f' (layer "Edge.Cuts"))')

    for ref in PLACE:
        t = load_fp(N.FOOTPRINTS[ref])
        x, y, rot = origin(ref, N.FOOTPRINTS[ref])
        at = (f'  (at {x:.3f} {y:.3f})' if rot == 0
              else f'  (at {x:.3f} {y:.3f} {rot})')
        t = t.replace('  (layer "F.Cu")', f'  (layer "F.Cu")\n{at}', 1)
        t = t.replace('(fp_text reference "REF**"', f'(fp_text reference "{ref}"', 1)
        t = re.sub(r'\(fp_text value "[^"]*"',
                   f'(fp_text value "{N.PARTS[ref]["value"]}"', t, count=1)
        out.append("  " + t.replace("\n", "\n  "))

    # The ESP32's PCB antenna sits over the carrier. Copper under it detunes
    # and attenuates 2.4 GHz, so the pour and routing are kept out. Cutting
    # the board away here would be better still if range disappoints.
    ax0, ay0, ax1, ay1 = W - 10.0, 39.0, W, 67.0
    out.append(f'''  (zone (net 0) (net_name "") (layers "F&B.Cu") (name "ANTENNA KEEPOUT")
    (hatch edge 0.5) (connect_pads (clearance 0))
    (min_thickness 0.25) (filled_areas_thickness no)
    (keepout (tracks not_allowed) (vias not_allowed) (pads allowed)
             (copperpour not_allowed) (footprints allowed))
    (fill (thermal_gap 0.5) (thermal_bridge_width 0.5))
    (polygon (pts (xy {ax0} {ay0}) (xy {ax1} {ay0}) (xy {ax1} {ay1}) (xy {ax0} {ay1}))))''')
    out.append(seg(ax0, ay0, ax1, ay0, "Cmts.User", LINE))
    out.append(f'  (gr_text "ANTENNA - no copper" (at {ax0 + 5} {ay0 + 3} 90)'
               f' (layer "Cmts.User")'
               f' (effects (font (size 1.2 1.2) (thickness 0.2))))')
    out.append(')')
    (HERE / "carrier.kicad_pcb").write_text("\n".join(out) + "\n")
    print(f"wrote carrier.kicad_pcb: {W} x {H} mm, {len(PLACE)} parts placed, unrouted")

if __name__ == "__main__":
    main()
