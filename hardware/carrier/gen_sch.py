#!/usr/bin/env python3
"""Generate carrier.kicad_sch from netlist.py.

Connectivity is carried entirely by global labels, not by drawn wires: every
connected pad gets a short stub and a label naming its net. For a carrier
board that is both easier to read than a rat's nest and far easier to verify
-- check_netlist.py re-extracts the netlist from the generated file and
compares it back to netlist.py.
"""
import pathlib, uuid
import netlist as N

NS = uuid.UUID("6f1a9c2e-4b7d-5e8f-9a0b-1c2d3e4f5a6b")
def uid(key): return str(uuid.uuid5(NS, key))

FONT = "(effects (font (size 1.27 1.27)))"
STROKE = "(stroke (width 0.254) (type default))"
P = 2.54

# ── Symbol bodies, in local coordinates ──────────────────────────────────
def pin(x, y, ang, length, name, num, typ="passive"):
    return (f'(pin {typ} line (at {x} {y} {ang}) (length {length})\n'
            f'  (name "{name}" {FONT}) (number "{num}" {FONT}))')

def rect(x0, y0, x1, y1, fill="background"):
    return f'(rectangle (start {x0} {y0}) (end {x1} {y1}) {STROKE} (fill (type {fill})))'

def poly(pts, fill="none"):
    s = " ".join(f"(xy {x} {y})" for x, y in pts)
    return f'(polyline (pts {s}) {STROKE} (fill (type {fill})))'

def module_body(left, right):
    n = max(len(left), len(right))
    span = (n - 1) * P
    hy = span / 2 + P
    hx = 12.7 if n > 12 else 10.16
    g = [rect(-hx, hy, hx, -hy)]
    for i, nm in enumerate(left):
        g.append(pin(-hx - P, span / 2 - i * P, 0, P, nm, i + 1))
    for i, nm in enumerate(right):
        g.append(pin(hx + P, span / 2 - i * P, 180, P, nm, len(left) + i + 1))
    return g

def body_for(kind, part):
    if kind == "module":
        return module_body(part["left"], part["right"])
    if kind == "r":
        return [rect(-2.54, 1.016, 2.54, -1.016),
                pin(-5.08, 0, 0, 2.54, "1", 1), pin(5.08, 0, 180, 2.54, "2", 2)]
    if kind == "c":
        return [poly([(-0.635, 1.905), (-0.635, -1.905)]),
                poly([(0.635, 1.905), (0.635, -1.905)]),
                pin(-5.08, 0, 0, 4.445, "1", 1), pin(5.08, 0, 180, 4.445, "2", 2)]
    if kind == "cpol":
        return [poly([(-0.635, 1.905), (-0.635, -1.905)]),
                f'(arc (start 0.635 1.905) (mid 1.905 0) (end 0.635 -1.905) '
                f'{STROKE} (fill (type none)))',
                poly([(-2.2, 2.6), (-1.2, 2.6)]), poly([(-1.7, 3.1), (-1.7, 2.1)]),
                pin(-5.08, 0, 0, 4.445, "+", 1), pin(5.08, 0, 180, 3.175, "-", 2)]
    if kind == "d":
        return [poly([(-1.27, 1.27), (-1.27, -1.27), (1.27, 0), (-1.27, 1.27)],
                     fill="outline"),
                poly([(1.27, 1.905), (1.27, -1.905)]),
                pin(-5.08, 0, 0, 3.81, "A", 1), pin(5.08, 0, 180, 3.81, "K", 2)]
    if kind == "sj":
        return [rect(-2.54, 1.27, -0.635, -1.27, "outline"),
                rect(0.635, 1.27, 2.54, -1.27, "outline"),
                poly([(-0.635, 0), (0.635, 0)]),
                pin(-5.08, 0, 0, 2.54, "1", 1), pin(5.08, 0, 180, 2.54, "2", 2)]
    if kind == "tp":
        return [f'(circle (center 0 0) (radius 0.762) {STROKE} (fill (type none)))',
                pin(-5.08, 0, 0, 4.318, "1", 1)]
    if kind == "hdr":
        names = part["pins"]
        span = (len(names) - 1) * P
        hy = span / 2 + P
        g = [rect(-3.81, hy, 3.81, -hy)]
        for i, nm in enumerate(names):
            g.append(pin(-6.35, span / 2 - i * P, 0, P, nm, i + 1))
        return g
    raise AssertionError(kind)

def lib_symbol(sym, kind, part):
    pref = {"module": "U", "r": "R", "c": "C", "cpol": "C", "d": "D",
            "hdr": "J", "tp": "TP", "sj": "SJ"}[kind]
    body = "\n".join(body_for(kind, part))
    hide = "" if kind != "tp" else " hide"
    return (f'(symbol "carrier:{sym}" (pin_names (offset 0.254)) (in_bom yes) (on_board yes)\n'
            f'  (property "Reference" "{pref}" (at 0 0 0) {FONT})\n'
            f'  (property "Value" "{sym}" (at 0 0 0) {FONT})\n'
            f'  (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))\n'
            f'  (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))\n'
            f'  (symbol "{sym}_1_1"\n{body}\n  )\n)')

# ── Placement (mm on A3) ─────────────────────────────────────────────────
POS = {
    "U1": (78, 72), "U2": (78, 190), "U3": (332, 130),
    "D1": (196, 40), "D2": (196, 60), "C3": (196, 80), "C4": (196, 100),
    "C1": (196, 120), "C2": (196, 140),
    "R1": (262, 40), "R2": (262, 60), "R3": (262, 80), "R4": (262, 100),
    "SJ1": (262, 120), "SJ2": (262, 140),
    "TP1": (196, 162), "TP2": (262, 162),
    "J1": (210, 215),
}

def main():
    t = N.pin_table()
    pads = N.pad_names()
    nets = N.resolved_nets()
    # pad -> net name
    padnet = {}
    for net, nodes in nets.items():
        for rp in nodes:
            padnet[rp] = net

    # one lib_symbol per distinct shape
    symname = {}
    libs = {}
    for ref, part in N.PARTS.items():
        k = part["kind"]
        s = {"module": f"MOD_{len(part.get('left',[]))}", "hdr": f"HDR_{len(part.get('pins',[]))}"}.get(k, k.upper())
        symname[ref] = s
        libs.setdefault(s, lib_symbol(s, k, part))

    out = ['(kicad_sch (version 20230121) (generator gen_sch.py)',
           f'  (uuid {uid("sheet")})', '  (paper "A3")',
           '  (title_block (title "USB_BT_Mixer carrier") '
           '(comment 1 "GENERATED by hardware/carrier/gen_sch.py from netlist.py -- do not edit by hand"))',
           '  (lib_symbols']
    out += ["    " + libs[s].replace("\n", "\n    ") for s in sorted(libs)]
    out.append('  )')

    inst = []
    for ref, part in N.PARTS.items():
        cx, cy = POS[ref]
        s = symname[ref]
        kind = part["kind"]
        out.append(f'  (symbol (lib_id "carrier:{s}") (at {cx} {cy} 0) (unit 1)')
        out.append(f'    (in_bom yes) (on_board yes) (dnp no) (uuid {uid(ref)})')
        # reference above, value below the body
        if kind in ("module", "hdr"):
            n = max(len(part.get("left", part.get("pins", []))),
                    len(part.get("right", [])))
            off = (n - 1) * P / 2 + P + 3
        else:
            off = 5
        out.append(f'    (property "Reference" "{ref}" (at {cx} {cy-off} 0) {FONT})')
        out.append(f'    (property "Value" "{part["value"]}" (at {cx} {cy+off} 0) {FONT})')
        out.append(f'    (property "Footprint" "{N.FOOTPRINTS[ref]}" (at {cx} {cy} 0) '
                   f'(effects (font (size 1.27 1.27)) hide))')
        for num in sorted(pads[ref]):
            out.append(f'    (pin "{num}" (uuid {uid(f"{ref}.{num}")}))')
        out.append('  )')
        inst.append(f'    (path "/{uid(ref)}" (reference "{ref}") (unit 1) '
                    f'(value "{part["value"]}") (footprint "{N.FOOTPRINTS[ref]}"))')

        # stubs + labels for connected pads
        for num in sorted(pads[ref]):
            net = padnet.get((ref, num))
            if net is None:
                continue
            px, py, side = pin_xy(part, kind, num, cx, cy)
            if side == "L":
                wx = px - P
                out.append(wire(px, py, wx, py, f"{ref}.{num}.w"))
                out.append(glabel(net, wx, py, 180, "right", f"{ref}.{num}.l"))
            else:
                wx = px + P
                out.append(wire(px, py, wx, py, f"{ref}.{num}.w"))
                out.append(glabel(net, wx, py, 0, "left", f"{ref}.{num}.l"))

    out.append('  (sheet_instances (path "/" (page "1")))')
    out.append('  (symbol_instances')
    out += inst
    out.append('  )')
    out.append(')')
    pathlib.Path("carrier.kicad_sch").write_text("\n".join(out) + "\n")
    print(f"wrote carrier.kicad_sch: {len(N.PARTS)} parts, {len(nets)} nets, "
          f"{sum(len(v) for v in nets.values())} pads")

def pin_xy(part, kind, num, cx, cy):
    """Connection point of pad `num`, and which side it leaves on."""
    if kind == "module":
        left, right = part["left"], part["right"]
        n = max(len(left), len(right))
        span = (n - 1) * P
        hx = 12.7 if n > 12 else 10.16
        if num <= len(left):
            return cx - hx - P, cy - (span / 2 - (num - 1) * P), "L"
        i = num - len(left) - 1
        return cx + hx + P, cy - (span / 2 - i * P), "R"
    if kind == "hdr":
        span = (len(part["pins"]) - 1) * P
        return cx - 6.35, cy - (span / 2 - (num - 1) * P), "L"
    if kind == "tp":
        return cx - 5.08, cy, "L"
    return (cx - 5.08, cy, "L") if num == 1 else (cx + 5.08, cy, "R")

def wire(x0, y0, x1, y1, key):
    return (f'  (wire (pts (xy {x0} {y0}) (xy {x1} {y1})) '
            f'(stroke (width 0) (type default)) (uuid {uid(key)}))')

def glabel(name, x, y, ang, just, key):
    return (f'  (global_label "{name}" (shape bidirectional) (at {x} {y} {ang}) '
            f'(fields_autoplaced) (effects (font (size 1.27 1.27)) (justify {just})) '
            f'(uuid {uid(key)}))')

if __name__ == "__main__":
    main()
