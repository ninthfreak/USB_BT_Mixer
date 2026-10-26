#!/usr/bin/python3
"""Generate carrier.kicad_pcb with KiCad's own API: outline, placement, nets.

Runs under the SYSTEM python, which carries KiCad 7's pcbnew bindings. KiCad
places every footprint, applies every rotation, and writes the file, so no
rotation arithmetic of ours decides where copper ends up. An earlier
text-based generator got the 90-degree transform wrong and its own check
agreed with it (AUDIT.md); this cannot happen the same way.

Every pad carries its net, every footprint is linked to its schematic symbol
by UUID path and to its library by ID, so the board opens in KiCad without
the 305 bookkeeping violations the old file produced.

Frame: origin at the carrier's front-left corner, +X right, +Y back (KiCad
draws +Y downward, so the front edge is at the TOP of the view). y = 0 is the
port wall: the two exposed USB-C ports sit on it.

Board dimensions come from enclosure/boards.scad; nothing is restated here.
"""
import pathlib, re, sys
import pcbnew

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import netlist as N
import gen_sch

SCAD = HERE.parents[1] / "enclosure" / "boards.scad"
B = {n: float(v) for n, v in
     re.findall(r"^\s*(\w+)\s*=\s*(-?[\d.]+)\s*;", SCAD.read_text(), re.M)}
STOCK = pathlib.Path("/usr/share/kicad/footprints")

mm, MM = pcbnew.FromMM, pcbnew.ToMM
def V(x, y): return pcbnew.VECTOR2I(mm(x), mm(y))

# ── Geometry ─────────────────────────────────────────────────────────────
# 70 mm wide. At 58 the gap between the input boards could not carry input
# 2's six nets; at 64 it routed but left nowhere to put input 2's diode,
# bypass cap and pull-down beside its pads (AUDIT.md #10).
W = 70.0

RP_HL = B["board_l"] / 2
RP_COURT = RP_HL + B["usb_over_in"] + 0.25      # courtyard past the module centre, +Y

# ESP32: turned 180 deg so header J3 (power + I2S) faces the input boards.
# Its USB-C end overhangs the LEFT edge by 1 mm so a flashing cable's overmold
# hangs in free air instead of meeting the carrier (AUDIT.md #9). Its antenna
# end overhangs a notch by ANT_OVERHANG, Espressif's preferred arrangement
# for a module on a carrier (AUDIT.md #6). ASSUMPTION to check on the real
# board: the PCB antenna lies within the last ~7 mm of the dev kit.
USB_OVERHANG = 1.0
ANT_OVERHANG = 7.5
ESP_HW, ESP_HD = B["esp_w"] / 2, B["esp_d"] / 2
ESP_CX = -USB_OVERHANG + ESP_HW
X_NOTCH = ESP_CX + ESP_HW - ANT_OVERHANG

# Service strip between the input boards and the ESP32: two rows of 3 mm
# parts with 0.6 mm between everything.
ROW_A = RP_COURT + 16.5 + 0.6 + 1.5               # 36.35
ROW_B = ROW_A + 3.0 + 0.6                         # 39.95
ESP_COURT = ESP_HD + 1.10 + 0.5                   # land pads + 0.5 margin
ESP_CY = ROW_B + 1.5 + 0.6 + ESP_COURT            # 57.62
Y_STEP = 42.5                                     # notch starts here
assert ROW_B + 1.5 < Y_STEP < ESP_CY - ESP_HD, "notch must clear the strip and the module"

MH_COURT = 2.95                                   # MountingHole_2.7mm_M2.5 courtyard
MH_REAR = ESP_CY + ESP_COURT + 0.5 + MH_COURT
H = round(MH_REAR + 1.35 + 1.6, 1)                # 1.6 mm FR4 web behind the hole

OUTLINE = [(0, 0), (W, 0), (W, Y_STEP), (X_NOTCH, Y_STEP), (X_NOTCH, H), (0, H)]

MODULES = {"U1": (17.55, RP_HL, 0), "U2": (52.45, RP_HL, 0),
           "U3": (ESP_CX, ESP_CY, 180)}

# Everything else is placed by COURTYARD CENTRE: KiCad computes the courtyard
# after rotation and we shift the part to put its centre here.
PLACE = {
    # Left column, beside input 1's power edge.
    "D1": (3.60, 28.49, 90),
    "C3": (1.90, 19.18, 90), "R8": (5.50, 17.87, 90),
    # Channel, beside input 2's power edge: diode, bypass and GP29 pull-down
    # within a few mm of the pads they serve. R5 sits by input 1's GP5.
    "D2": (36.90, 28.49, 90), "C4": (40.40, 30.10, 90),
    "R9": (40.40, 17.87, 90), "R5": (29.60, 17.40, 90),
    # Right column, beside input 2's UART edge.
    "R6": (66.40, 17.40, 90), "J1": (66.40, 31.00, 0),
    # Strip row A: rail test points side by side, AUD1 pull-down.
    "TP1": (8.50, ROW_A, 0), "TP2": (12.30, ROW_A, 0), "R7": (48.86, ROW_A, 0),
    # Strip row B, against the ESP32's J3 row: rail bypass beside its 5V pad,
    # then the four clock resistors at the driving end.
    "C1": (3.25, (ROW_A + ROW_B) / 2 - 0.55, 0),
    "C2": (10.15, ROW_B, 0),
    "R3": (19.16, ROW_B, 0), "R1": (29.48, ROW_B, 0),
    "R2": (39.80, ROW_B, 0), "R4": (50.12, ROW_B, 0),
}
MOUNT = [(3.0, 3.0), (W - 3.0, 3.0), (3.0, MH_REAR), (X_NOTCH - 3.0, MH_REAR)]
MOUNT_FP = "MountingHole:MountingHole_2.7mm_M2.5"

# Copper keep-out on the strip of carrier nearest the antenna overhang.
KEEPOUT = [(X_NOTCH - 2.3, Y_STEP), (X_NOTCH, Y_STEP),
           (X_NOTCH, ESP_CY + ESP_HD + 1.6), (X_NOTCH - 2.3, ESP_CY + ESP_HD + 1.6)]

def lib_path(fpid):
    lib, name = fpid.split(":", 1)
    p = HERE / f"{lib}.pretty"
    return (p if p.exists() else STOCK / f"{lib}.pretty"), lib, name

def load(fpid):
    path, lib, name = lib_path(fpid)
    fp = pcbnew.FootprintLoad(str(path), name)
    assert fp is not None, f"cannot load {fpid}"
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp

def courtyard_box(fp):
    fp.BuildCourtyardCaches()
    c = fp.GetCourtyard(pcbnew.F_CrtYd)
    assert c.OutlineCount(), f"{fp.GetReference()} has no courtyard"
    b = c.BBox()
    return MM(b.GetLeft()), MM(b.GetTop()), MM(b.GetRight()), MM(b.GetBottom())

def segment(board, a, b, layer, width):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(V(*a)); s.SetEnd(V(*b))
    s.SetLayer(layer); s.SetWidth(mm(width))
    board.Add(s)

def text(board, s, x, y, size=1.0, layer=pcbnew.F_SilkS, rot=0, just=None):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(s); t.SetPosition(V(x, y)); t.SetLayer(layer)
    t.SetTextSize(V(size, size)); t.SetTextThickness(mm(size * 0.15))
    if rot: t.SetTextAngleDegrees(rot)
    if just == "right": t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_RIGHT)
    if just == "left":  t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
    board.Add(t)

def zone(board, pts, layer, net=None, rule=False, name=""):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    if rule:
        z.SetIsRuleArea(True)
        z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(True)
        z.SetDoNotAllowCopperPour(True)
        z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False)
        z.SetLayerSet(pcbnew.LSET(pcbnew.F_Cu).addLayer(pcbnew.B_Cu))
    else:
        z.SetNet(net)
        z.SetLocalClearance(mm(0.30))
        z.SetMinThickness(mm(0.25))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(mm(0.40))
        z.SetThermalReliefSpokeWidth(mm(0.40))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    if name: z.SetZoneName(name)
    o = z.Outline(); o.NewOutline()
    for x, y in pts:
        o.Append(mm(x), mm(y))
    board.Add(z)
    return z

def main():
    # Fixed UUID seed: the same inputs give a byte-identical board, so a
    # rebuild shows no diff unless something really changed.
    pcbnew.KIID.SeedGenerator(1)
    board = pcbnew.CreateEmptyBoard()
    board.GetDesignSettings().SetBoardThickness(mm(1.6))

    # nets, in a stable order
    nets = N.resolved_nets()
    info = {}
    for name in sorted(nets):
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        info[name] = ni
    padnet = {(r, str(p)): n for n, nodes in nets.items() for r, p in nodes}

    for a, b in zip(OUTLINE, OUTLINE[1:] + OUTLINE[:1]):
        segment(board, a, b, pcbnew.Edge_Cuts, 0.1)

    def finish(fp, ref):
        fp.SetReference(ref)
        fp.SetValue(N.PARTS[ref]["value"])
        fp.Value().SetLayer(pcbnew.F_Fab)
        fp.SetPath(pcbnew.KIID_PATH("/" + gen_sch.uid(ref)))
        for p in fp.Pads():
            n = padnet.get((ref, p.GetNumber()))
            if n:
                p.SetNet(info[n])
        board.Add(fp)

    for ref, (x, y, rot) in MODULES.items():
        fp = load(N.FOOTPRINTS[ref])
        fp.SetOrientationDegrees(rot)
        fp.SetPosition(V(x, y))
        finish(fp, ref)

    for ref, (cx, cy, rot) in PLACE.items():
        fp = load(N.FOOTPRINTS[ref])
        fp.SetOrientationDegrees(rot)
        fp.SetPosition(V(0, 0))
        finish(fp, ref)          # must belong to the board before its
        x0, y0, x1, y1 = courtyard_box(fp)   # courtyard can be computed
        fp.SetPosition(V(cx - (x0 + x1) / 2, cy - (y0 + y1) / 2))

    # Refdes on silkscreen, centred on each part's body and running along it,
    # so it neither overlaps a neighbour nor sits on copper. Test points and
    # J1 carry their own labels instead.
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        kind = N.PARTS.get(ref, {}).get("kind")
        r = fp.Reference()
        if kind in ("r", "c", "d"):
            pads = list(fp.Pads())
            mx = (pads[0].GetPosition().x + pads[1].GetPosition().x) // 2
            my = (pads[0].GetPosition().y + pads[1].GetPosition().y) // 2
            r.SetPosition(pcbnew.VECTOR2I(mx, my))
            r.SetTextAngleDegrees(fp.GetOrientationDegrees())
        elif kind == "cpol":
            # The can's outline and its negative-side hatching leave no room
            # for the refdes inside; it is labelled just below instead.
            r.SetVisible(False)
            c = fp.GetPosition()
            text(board, ref, MM(c.x) + 1.25, MM(c.y) + 3.75, 0.8)
        elif kind in ("tp", "hdr"):
            r.SetVisible(False)
        if kind in ("r", "c", "d"):
            r.SetTextSize(V(0.8, 0.8)); r.SetTextThickness(mm(0.12))

    for i, (x, y) in enumerate(MOUNT, 1):
        fp = load(MOUNT_FP)
        fp.SetPosition(V(x, y))
        fp.SetReference(f"H{i}")
        fp.Reference().SetVisible(False)
        board.Add(fp)

    # Ground pours on both layers. KiCad fills them in route.py, after the
    # tracks exist; drc.py then confirms every GND pad reaches the pour.
    gnd = info["GND"]
    zone(board, OUTLINE, pcbnew.F_Cu, gnd, name="GND top")
    zone(board, OUTLINE, pcbnew.B_Cu, gnd, name="GND bottom")
    zone(board, KEEPOUT, pcbnew.F_Cu, rule=True, name="ANTENNA KEEPOUT")

    # Labels the builder and the debugger will want.
    text(board, "< IN 1", 31.4, 3.2, 1.0)
    text(board, "IN 2 >", 38.6, 3.2, 1.0)
    text(board, "RAIL", PLACE["TP1"][0], ROW_A - 1.8, 0.8)
    text(board, "GND", PLACE["TP2"][0] + 0.5, ROW_A - 1.8, 0.8)
    jx, jy = PLACE["J1"][0], PLACE["J1"][1]
    for i, lab in enumerate(["G", "D1", "D2", "S1", "S2", "S3"]):
        text(board, lab, jx - 1.6, jy - 6.35 + i * 2.54, 0.8, just="right")
    # kept between the rear screw heads (their courtyards end ~6 mm in)
    text(board, "USB_BT_Mixer carrier v0.2", X_NOTCH / 2, H - 5.0, 1.0)
    text(board, "J1  G=GND  D1/D2=debug TX in1/in2", X_NOTCH / 2, H - 3.3, 0.8)
    text(board, "S1=IO4  S2=IO21  S3=IO14", X_NOTCH / 2, H - 1.9, 0.8)
    text(board, "ANTENNA OVERHANGS HERE", X_NOTCH - 1.2, (Y_STEP + H) / 2,
         0.8, layer=pcbnew.Cmts_User, rot=90)

    import drc
    drc.apply_rules(board)      # stored in carrier.kicad_pro for KiCad's GUI
    out = HERE / "carrier.kicad_pcb"
    pcbnew.SaveBoard(str(out), board)
    print(f"wrote carrier.kicad_pcb: {W} x {H} mm (notch from x {X_NOTCH:.1f}, "
          f"y {Y_STEP}), {len(MODULES) + len(PLACE)} parts, {len(MOUNT)} holes, unrouted")

if __name__ == "__main__":
    main()
