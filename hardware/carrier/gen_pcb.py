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
port wall. Each input board is turned 180 degrees so its NATIVE USB port (the
"programming" port, proud of the board edge) faces the hosts and hangs over
that edge; its PIO-USB port faces inward, unused (review-notes #25).

Layout rules, so the board reads the way it works (owner, 2026-10-27):
  * top layer: every signal; no signal changes layer
  * bottom layer: a solid ground plane, plus power (the rail runs round the
    front and left edges, behind the port ends, where no signal crosses it)
  * related lines run together: each board's I2S group and UART pair

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
# The strip and the ESP32's position below were sized when the native port
# faced inward (RP_COURT behind the module). Kept: the rotated boards leave
# the strip 1 mm deeper, and the owner accepted the 70 x 79.6 outline.

# ESP32: turned 180 deg so header J3 (power + I2S) faces the input boards.
# Its USB-C end overhangs the LEFT edge by 1 mm so a flashing cable's overmold
# hangs in free air instead of meeting the carrier (AUDIT.md #9). Its antenna
# end overhangs a notch by ANT_OVERHANG, Espressif's preferred arrangement
# for a module on a carrier (AUDIT.md #6): the whole antenna (esp_ant_l,
# measured off Waveshare's drawing) plus 0.7 mm hangs past the notch edge.
USB_OVERHANG = 1.0
ANT_OVERHANG = round(B["esp_ant_l"] + 0.7, 2)     # 7.5
ESP_HW, ESP_HD = B["esp_w"] / 2, B["esp_d"] / 2
ESP_CX = -USB_OVERHANG + ESP_HW
X_NOTCH = ESP_CX + ESP_HW - ANT_OVERHANG

# Service strip between the input boards and the ESP32: room for two rows of
# 3 mm parts with 0.6 mm between everything.
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

MODULES = {"U1": (17.55, RP_HL, 180), "U2": (52.45, RP_HL, 180),
           "U3": (ESP_CX, ESP_CY, 180)}

# Everything else is placed by PAD 1 position (x, y, rotation), laid out by
# signal flow. Seen from the ESP32, west to east the board carries: input 1's
# UART pair, input 1's I2S group, input 2's UART pair, input 2's I2S group.
# Input 2's clock branches cross its UART pair by passing between the pads of
# R2 and R4, so no signal needs the bottom layer.
PLACE_PAD = {
    # Strip, west end: rail bulk and bypass at the ESP32's 5V pad; test points.
    "C1": (2.15, 38.7, 0), "C2": (7.7, 40.7, 90),
    "TP1": (5.0, 33.0, 0), "TP2": (5.0, 30.0, 0),
    # Strip: input 1's clock resistors, standing, inline on their lanes.
    "R3": (20.82, 40.3, 90), "R1": (25.9, 40.3, 90),
    # Strip: input 2's clock resistors, lying across input 2's UART lanes.
    "R4": (35.5, 35.8, 0), "R2": (32.3, 38.8, 0),
    # Channel, front: input 1's supply diode and bypass at its power pads.
    "D1": (37.4, 2.4, 180), "C3": (34.4, 6.4, 180),
    # Channel: input 1's GP29 pull-down, debug header, input 2's RX resistor.
    "R8": (29.6, 11.6, 270), "J1": (34.5, 11.0, 0), "R6": (40.5, 30.0, 90),
    # Right margin: input 2's supply diode and bypass at its power pads.
    "D2": (68.0, 8.0, 270), "C4": (68.0, 18.3, 270),
    # Behind input 2: its GP29 and audio pull-downs, fed down the margin.
    "R9": (60.3, 35.0, 0), "R7": (60.3, 38.2, 0),
    # Behind the ESP32: input 1's RX resistor, at the ESP32's TX pin.
    "R5": (17.5, 75.6, 180),
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

    for ref, (px, py, rot) in PLACE_PAD.items():
        fp = load(N.FOOTPRINTS[ref])
        fp.SetOrientationDegrees(rot)
        fp.SetPosition(V(0, 0))
        finish(fp, ref)
        p1 = [q for q in fp.Pads() if q.GetNumber() == "1"][0].GetPosition()
        fp.SetPosition(V(px - MM(p1.x), py - MM(p1.y)))

    # Refdes on silkscreen, centred on each part's body and running along it,
    # so it neither overlaps a neighbour nor sits on copper. Test points and
    # J1 carry their own labels instead.
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        kind = N.PARTS.get(ref, {}).get("kind")
        r = fp.Reference()
        if kind in ("r", "c", "d") and "Vertical" in N.FOOTPRINTS[ref]:
            # standing resistor: the body is a circle over pad 1; label beside it
            p1 = [q for q in fp.Pads() if q.GetNumber() == "1"][0].GetPosition()
            r.SetPosition(V(MM(p1.x) - 2.2, MM(p1.y) - 1.27))
            r.SetTextAngleDegrees(90)
        elif kind in ("r", "c", "d"):
            pads = list(fp.Pads())
            mx = (pads[0].GetPosition().x + pads[1].GetPosition().x) // 2
            my = (pads[0].GetPosition().y + pads[1].GetPosition().y) // 2
            r.SetPosition(pcbnew.VECTOR2I(mx, my))
            r.SetTextAngleDegrees(fp.GetOrientationDegrees())
        if kind == "d":
            # keep the cathode "K" on the board: if rotation put it past the
            # edge, mirror it to the other side of pad 1
            p1 = [q for q in fp.Pads() if q.GetNumber() == "1"][0].GetPosition()
            for g in fp.GraphicalItems():
                if g.GetClass() in ("MTEXT", "FP_TEXT", "PCB_TEXT") and g.GetText() == "K":
                    t = g.GetPosition()
                    if MM(t.x) > W - 1.0 or MM(t.x) < 1.0:
                        g.SetPosition(pcbnew.VECTOR2I(2 * p1.x - t.x, 2 * p1.y - t.y))
        elif kind == "cpol":
            # The can's outline and its negative-side hatching leave no room
            # for the refdes inside; it is labelled just below instead.
            r.SetVisible(False)
            c = fp.GetPosition()
            text(board, ref, MM(c.x) + 1.25, MM(c.y) - 3.6, 0.8)
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
    zone(board, OUTLINE, pcbnew.B_Cu, gnd, name="GND bottom")
    zone(board, KEEPOUT, pcbnew.F_Cu, rule=True, name="ANTENNA KEEPOUT")

    # Labels the builder and the debugger will want.
    text(board, "RAIL", 6.4, 33.0, 0.8, just="left")
    text(board, "GND", 3.6, 30.0, 0.8, just="right")
    for i, lab in enumerate(["G", "D1", "D2"]):
        text(board, lab, 32.9, 11.0 + i * 2.54, 0.8, just="right")
    text(board, "IN 1", 17.55, 27.5, 1.0)
    text(board, "IN 2", 52.45, 27.5, 1.0)
    text(board, "USB_BT_Mixer v0.3", 63.6, 41.0, 0.8)
    text(board, "ANTENNA OVERHANGS HERE", X_NOTCH - 1.2, (Y_STEP + H) / 2,
         0.8, layer=pcbnew.Cmts_User, rot=90)

    import drc
    drc.apply_rules(board)      # stored in carrier.kicad_pro for KiCad's GUI
    out = HERE / "carrier.kicad_pcb"
    pcbnew.SaveBoard(str(out), board)
    print(f"wrote carrier.kicad_pcb: {W} x {H} mm (notch from x {X_NOTCH:.1f}, "
          f"y {Y_STEP}), {len(MODULES) + len(PLACE_PAD)} parts, {len(MOUNT)} holes, unrouted")

if __name__ == "__main__":
    main()
