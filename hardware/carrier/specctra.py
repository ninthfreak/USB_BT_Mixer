"""Specctra plumbing between KiCad and Freerouting.

KiCad 7 exports a Specctra design (.dsn) from a script, but its session
import (.ses) only works on the GUI's board, so read_session() lays
Freerouting's wires and vias onto a scripted board itself. The edit_*
helpers adjust the exported design before Freerouting sees it.
"""
import re
import pcbnew

POWER = ["RAIL", "VBUS1", "VBUS2"]
POWER_WIDTH_UM = 800


def edit_power_class(d, nets=POWER, width_um=POWER_WIDTH_UM):
    """Move the power nets out of the default class into one routed wide."""
    m = re.search(r'\(class kicad_default ""([^(]*)', d)
    rest = [n for n in m.group(1).split() if n not in nets]
    d = d.replace(m.group(0), '(class kicad_default "" ' + " ".join(rest) + "\n      ", 1)
    via = re.search(r"\(use_via ([^)]*)\)", d).group(1)
    cls = (f"    (class Power {' '.join(nets)}\n      (circuit\n        (use_via {via})\n      )\n"
           f"      (rule\n        (width {width_um})\n        (clearance 250.1)\n      )\n    )\n")
    k = d.rindex("  )\n", 0, d.index("  (wiring"))
    return d[:k] + cls + d[k:]


def edit_drop_nets(d, nets):
    """Hide finished nets (pre-routed, or a pour) from Freerouting. Their pads
    stay as obstacles and their wires stay as fixed copper with no net, so the
    router neither moves them nor tries to complete them."""
    for n in nets:
        e = re.escape(n)
        d = re.sub(r"\n    \(net %s\n      \(pins[^)]*\)\n    \)" % e, "", d)
        d = re.sub(r"\n\s*\(plane %s \(polygon[^\n]*\n[^\n]*\)\)" % e, "", d)
        d = re.sub(r"(\(class [^\n(]*?)(?<=\s)%s(?=\s)" % e, r"\1", d)
        d = d.replace("(net %s)" % n, "")
    return d


def edit_protect(d):
    """KiCad writes locked copper as 'fix', which Freerouting will still rip
    up; 'protect' it cannot touch."""
    return d.replace("(type fix)", "(type protect)")


def edit_bottom_power_layer(d):
    """Declare B.Cu a power plane: Freerouting then routes signals on F.Cu
    only. (Per-layer costs in the design file crash Freerouting 2.1.)"""
    return d.replace("    (layer B.Cu\n      (type signal)", "    (layer B.Cu\n      (type power)", 1)


def inset_outline(outline, d_mm):
    """Move every edge of an axis-aligned polygon inward by d_mm."""
    n = len(outline)
    def inside(x, y):
        c = False
        for (ax, ay), (bx, by) in zip(outline, outline[1:] + outline[:1]):
            if (ay > y) != (by > y) and x < ax + (y - ay) * (bx - ax) / (by - ay):
                c = not c
        return c
    normals = []
    for (ax, ay), (bx, by) in zip(outline, outline[1:] + outline[:1]):
        L = ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5
        nx, ny = -(by - ay) / L, (bx - ax) / L
        mx, my = (ax + bx) / 2, (ay + by) / 2
        if not inside(mx + 0.01 * nx, my + 0.01 * ny):
            nx, ny = -nx, -ny
        normals.append((nx, ny))
    return [(x + d_mm * (normals[i - 1][0] + normals[i][0]),
             y + d_mm * (normals[i - 1][1] + normals[i][1]))
            for i, (x, y) in enumerate(outline)]


def edit_boundary(d, outline_mm):
    """Replace the routing boundary. Freerouting keeps only its ordinary
    clearance from the board edge, so it is handed an outline inset by the
    difference between the board's edge rule and that clearance."""
    pts = "  ".join(f"{x * 1000:.1f} {-y * 1000:.1f}" for x, y in outline_mm + outline_mm[:1])
    new = f"    (boundary\n      (path pcb 0  {pts})\n    )"
    d2, k = re.subn(r"    \(boundary\n      \(path pcb 0[^)]*\)\n    \)", new, d, count=1)
    assert k == 1, "no boundary in the design file"
    return d2


# ── Session (.ses) reading ───────────────────────────────────────────────
def _parse(text):
    stack, cur = [], []
    for t in re.findall(r'"[^"]*"|\(|\)|[^\s()]+', text):
        if t == "(":
            stack.append(cur); cur = []
        elif t == ")":
            done = cur; cur = stack.pop(); cur.append(done)
        else:
            cur.append(t.strip('"'))
    if not cur:
        raise ValueError("empty session file")
    return cur[0]


def _find(node, key):
    for c in node:
        if isinstance(c, list) and c and c[0] == key:
            yield c


def read_session(board, path, via_d=0.8, via_drill=0.4):
    """Lay a Freerouting session's wires and vias onto board. Returns
    (tracks, vias) added."""
    routes = next(_find(_parse(open(path).read()), "routes"))
    res = next(_find(routes, "resolution"))
    unit = {"um": 1e-3, "mil": 0.0254, "mm": 1.0}[res[1]] / float(res[2])
    mm = lambda v: pcbnew.FromMM(float(v) * unit)
    layers = {"F.Cu": pcbnew.F_Cu, "B.Cu": pcbnew.B_Cu}
    n_tr = n_via = 0
    for net in _find(next(_find(routes, "network_out")), "net"):
        ni = board.FindNet(net[1])
        for wire in _find(net, "wire"):
            for p in _find(wire, "path"):
                xy = [v for v in p[3:] if not isinstance(v, list)]
                pts = [(mm(xy[k]), -mm(xy[k + 1])) for k in range(0, len(xy) - 1, 2)]
                for a, b in zip(pts, pts[1:]):
                    t = pcbnew.PCB_TRACK(board)
                    t.SetStart(pcbnew.VECTOR2I(*a)); t.SetEnd(pcbnew.VECTOR2I(*b))
                    t.SetWidth(mm(p[2])); t.SetLayer(layers[p[1]]); t.SetNet(ni)
                    board.Add(t); n_tr += 1
        for v in _find(net, "via"):
            via = pcbnew.PCB_VIA(board)
            via.SetPosition(pcbnew.VECTOR2I(mm(v[2]), -mm(v[3])))
            via.SetWidth(pcbnew.FromMM(via_d)); via.SetDrill(pcbnew.FromMM(via_drill))
            via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); via.SetViaType(pcbnew.VIATYPE_THROUGH)
            via.SetNet(ni); board.Add(via); n_via += 1
    return n_tr, n_via


def unrouted(log):
    """Connections left open by Freerouting's last pass, from its log."""
    passes = [l for l in log.splitlines() if "pass #" in l]
    if not passes:
        raise RuntimeError("Freerouting ran no passes:\n" + log[-2000:])
    m = re.search(r"\((\d+) unrouted\)", passes[-1])
    return int(m.group(1)) if m else 0
