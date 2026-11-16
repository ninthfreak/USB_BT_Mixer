#!/usr/bin/python3
"""Write carrier-fit-check.pdf: the carrier at 1:1, every module pad named.

Print it at 100 % ("actual size"), check the 50 mm bar with a ruler, then lay
the three real modules on the paper. It answers, before any money is spent:

  * do the modules' edge pads land on the printed lands?
  * does each pad's SILKSCREEN LABEL on the real module match the name
    printed beside it? (A land pattern that is mirrored or turned end for
    end fits perfectly and is completely wrong; only the labels show it.)
  * do the USB-C shells hang over the edges as drawn?

It also doubles as the soldering map: filled lands carry a net, lands marked
M are soldered for strength only, hollow lands are left bare.

Read from carrier.kicad_pcb (what will actually be made) and netlist.py (the
names). The PDF is written by hand -- no library, and the same board gives
the same bytes.
"""
import pathlib, sys
import pcbnew

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import netlist as N
import gen_pcb as G

MM = pcbnew.ToMM
PT = 72 / 25.4                       # points per mm
PAGE_W, PAGE_H = 210.0, 297.0        # A4 portrait
OX, OY = 70.0, 84.0                  # where the board's front-left corner goes
FONT = 1.9                           # pad label height, mm

# Helvetica advance widths (1/1000 em) for the characters used here.
_W = dict(zip("0123456789", [556] * 10))
_W.update({c: 667 for c in "ABEKPSVXY"}); _W.update({c: 722 for c in "CDHNRU"})
_W.update({"G": 778, "O": 778, "Q": 778, "M": 833, "W": 944, "I": 278, "J": 500,
           "L": 556, "T": 611, "F": 611, "Z": 611, " ": 278, ".": 278, ",": 278,
           ":": 278, "-": 333, "(": 333, ")": 333, "/": 278, "%": 889, "+": 584,
           "=": 584, "'": 191, "#": 556})
for c, w in zip("abcdefghijklmnopqrstuvwxyz",
                [556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833,
                 556, 556, 556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500]):
    _W[c] = w

def width(s, size):                  # mm
    return sum(_W.get(c, 556) for c in s) * size / 1000


class Page:
    """Just enough PDF: lines, rectangles, circles, Helvetica text. Units are
    mm, origin top-left, +y down, to match the board's own frame."""
    def __init__(self):
        self.ops = []

    def _p(self, x, y):
        return f"{x * PT:.2f} {(PAGE_H - y) * PT:.2f}"

    def stroke(self, w=0.15, gray=0.0, dash=None):
        d = f"[{dash[0] * PT:.2f} {dash[1] * PT:.2f}] 0 d" if dash else "[] 0 d"
        self.ops.append(f"{w * PT:.2f} w {gray:.2f} G {d}")

    def line(self, pts, close=False):
        self.ops.append(" ".join(f"{self._p(*p)} {'m' if i == 0 else 'l'}" for i, p in enumerate(pts))
                        + (" s" if close else " S"))

    def rect(self, x0, y0, x1, y1, fill=None):
        op = "S" if fill is None else f"{fill:.2f} g B"
        self.ops.append(f"{x0 * PT:.2f} {(PAGE_H - y1) * PT:.2f} {(x1 - x0) * PT:.2f} {(y1 - y0) * PT:.2f} re {op}")

    def circle(self, x, y, r, fill=None):
        k = 0.5523 * r
        c = [(x + r, y), (x + r, y + k, x + k, y + r, x, y + r), (x - k, y + r, x - r, y + k, x - r, y),
             (x - r, y - k, x - k, y - r, x, y - r), (x + k, y - r, x + r, y - k, x + r, y)]
        s = f"{self._p(*c[0])} m " + " ".join(
            f"{self._p(a, b)} {self._p(e, f)} {self._p(g, h)} c" for a, b, e, f, g, h in c[1:])
        self.ops.append(s + (" S" if fill is None else f" {fill:.2f} g B"))

    def text(self, s, x, y, size=FONT, align="left", up=False, bold=False, gray=0.0):
        """Baseline starts at (x, y). up=True turns it to read bottom-to-top."""
        w = width(s, size)
        off = {"left": 0, "right": -w, "centre": -w / 2}[align]
        esc = s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        px, py = x * PT, (PAGE_H - y) * PT
        m = f"0 1 -1 0 {px:.2f} {py:.2f}" if up else f"1 0 0 1 {px:.2f} {py:.2f}"
        self.ops.append(f"q {gray:.2f} g BT /F{2 if bold else 1} {size * PT:.2f} Tf {m} Tm "
                        f"{off * PT:.2f} 0 Td ({esc}) Tj ET Q")

    def save(self, path):
        body = "\n".join(self.ops).encode("latin-1")
        objs = [b"<< /Type /Catalog /Pages 2 0 R >>",
                b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
                (f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_W * PT:.2f} {PAGE_H * PT:.2f}] "
                 f"/Contents 4 0 R /Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> >>").encode(),
                b"<< /Length %d >>\nstream\n" % len(body) + body + b"\nendstream",
                b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
                b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>"]
        out, offs = b"%PDF-1.4\n", []
        for i, o in enumerate(objs, 1):
            offs.append(len(out))
            out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
        xref = len(out)
        out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
        out += b"".join(b"%010d 00000 n \n" % o for o in offs)
        out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
        path.write_bytes(out)


def main():
    b = pcbnew.LoadBoard(str(HERE / "carrier.kicad_pcb"))
    fps = {f.GetReference(): f for f in b.GetFootprints()}
    names = N.pad_names()
    table = N.pin_table()
    netted = {(r, p) for nodes in N.resolved_nets().values() for r, p in nodes}
    mech = {N.resolve(n, table) for n in N.SOLDER_MECHANICAL}
    B = G.B
    pg = Page()
    X = lambda x: OX + x
    Y = lambda y: OY + y

    # ── header ──
    pg.text("USB_BT_Mixer carrier: 1:1 fit check", 15, 14, 4.2, bold=True)
    pg.text("Print at 100 % (actual size, no 'fit to page'). The bar below must measure 50.0 mm.", 15, 21, 2.9)
    pg.stroke(0.3)
    pg.line([(15, 29), (65, 29)])
    for i in range(6):
        pg.line([(15 + 10 * i, 27.2), (15 + 10 * i, 30.8)])
        pg.text(str(10 * i), 15 + 10 * i, 34.2, 2.3, "centre")
    pg.text("mm", 68, 30, 2.3)
    for i, line in enumerate([
            "1. Lay each module on its outline, component side up, as drawn.",
            "2. Its edge pads must sit on the printed lands, all along both edges.",
            "3. Read the label printed on the module beside each pad. It must match the name printed here beside",
            "    the same land. A mismatch anywhere means STOP: do not order the board.",
            "4. USB-C shells: the input boards' hang past the FRONT edge, the ESP32's past the LEFT edge.",
            "Lands:  filled = solder (carries a net)      M = solder (for strength only)      hollow = leave bare"]):
        pg.text(line, 15, 43 + i * 4.4, 2.7)

    # ── board outline, holes ──
    pg.stroke(0.35)
    pg.line([(X(x), Y(y)) for x, y in G.OUTLINE], close=True)
    pg.stroke(0.15)
    for x, y in G.MOUNT:
        pg.circle(X(x), Y(y), 1.35)
        pg.line([(X(x) - 0.8, Y(y)), (X(x) + 0.8, Y(y))]); pg.line([(X(x), Y(y) - 0.8), (X(x), Y(y) + 0.8)])

    # ── through-hole parts and test pads: faint, only to show where they sit ──
    pg.stroke(0.1, 0.6)
    for ref in sorted(fps):
        if N.PARTS.get(ref, {}).get("kind") in ("r", "c", "cpol", "d", "hdr", "tp"):
            for p in fps[ref].Pads():
                bb = p.GetBoundingBox()
                pg.circle(X(MM(p.GetPosition().x)), Y(MM(p.GetPosition().y)),
                          min(MM(bb.GetWidth()), MM(bb.GetHeight())) / 2, 0.88)

    # ── module outlines (real board edges, and what overhangs) ──
    pg.stroke(0.2, 0.0, (1.2, 0.8))
    hw, hl = B["board_w"] / 2, B["board_l"] / 2
    for ref in ("U1", "U2"):
        cx, cy, _ = G.MODULES[ref]
        pg.rect(X(cx - hw), Y(cy - hl), X(cx + hw), Y(cy + hl))
        uw = B["usb_w"] / 2
        pg.rect(X(cx - uw), Y(cy - hl - B["usb_over_in"]), X(cx + uw), Y(cy - hl - B["usb_over_in"] + B["usb_depth"]))
        pg.rect(X(cx - uw), Y(cy + hl - B["usb_depth"]), X(cx + uw), Y(cy + hl))
        pg.text(f"INPUT {ref[1]}", X(cx), Y(cy + 2.0), 2.6, "centre", bold=True)
        pg.text("native USB", X(cx), Y(cy - hl + 3.6), 1.8, "centre")
        pg.text("(proud shell)", X(cx), Y(cy - hl + 5.8), 1.8, "centre")
        pg.text("PIO-USB, unused", X(cx), Y(cy + hl - 3.2), 1.8, "centre")
    ew, ed = G.ESP_HW, G.ESP_HD
    cx, cy = G.ESP_CX, G.ESP_CY
    pg.rect(X(cx - ew), Y(cy - ed), X(cx + ew), Y(cy + ed))
    pg.rect(X(cx - ew), Y(cy - B["esp_usb_w"] / 2), X(cx - ew + 7.5), Y(cy + B["esp_usb_w"] / 2))
    pg.rect(X(cx + ew - B["esp_ant_l"]), Y(cy - B["esp_ant_w"] / 2), X(cx + ew), Y(cy + B["esp_ant_w"] / 2))
    pg.text("ESP32-DEV-KIT", X(cx + 4), Y(cy + 1.0), 2.6, "centre", bold=True)
    pg.text("USB-C", X(cx - ew + 3.7), Y(cy + 0.7), 1.8, "centre")
    pg.text("ANT", X(cx + ew - B["esp_ant_l"] / 2), Y(cy + 0.7), 1.8, "centre")

    # ── every module land, named ──
    pg.stroke(0.15)
    for ref in ("U1", "U2", "U3"):
        fp = fps[ref]
        for p in fp.Pads():
            bb = p.GetBoundingBox()
            x0, y0, x1, y1 = MM(bb.GetLeft()), MM(bb.GetTop()), MM(bb.GetRight()), MM(bb.GetBottom())
            px, py = MM(p.GetPosition().x), MM(p.GetPosition().y)
            key = (ref, int(p.GetNumber()))
            pg.rect(X(x0), Y(y0), X(x1), Y(y1), 0.35 if key in netted else 1.0)
            name = names[ref][key[1]]
            if ref == "U3":
                front = py < G.ESP_CY                    # J3 row faces the input boards
                if key in mech:
                    pg.text("M", X(px), Y(py + 0.6), 1.5, "centre", bold=True)
                pg.text(name, X(px + FONT * 0.36), Y(y0 - 0.5) if front else Y(y1 + 0.5),
                        align="left" if front else "right", up=True)
            else:
                left = px < G.MODULES[ref][0]
                if key in mech:
                    pg.text("M", X(px), Y(py + 0.55), 1.5, "centre", bold=True)
                pg.text(name, X(x0 - 0.5) if left else X(x1 + 0.5), Y(py + FONT * 0.36),
                        align="right" if left else "left")
    # the four ESP32 pads that have no land: name them where they would be
    off = {N.resolve(n, table)[1]: n.split(".")[1] for n in N.OFF_BOARD}
    pitch = 2.54
    for num, _ in sorted(off.items()):
        i = (num - 1) % 19
        x = G.ESP_CX + 9 * pitch - i * pitch                 # U3 is turned 180 degrees
        front = num <= 19
        y = G.ESP_CY - G.ESP_HD if front else G.ESP_CY + G.ESP_HD
        pg.text(f"({names['U3'][num]})", X(x + FONT * 0.36), Y(y - 1.6) if front else Y(y + 1.6),
                align="left" if front else "right", up=True, gray=0.45)

    # ── the edges, and what to expect ──
    pg.text("FRONT: the hosts' cables plug in along this edge", X(G.W / 2), Y(-3.5), 2.6, "centre", bold=True)
    pg.text("LEFT: ESP32 flashing cable", X(-3.0), Y(G.ESP_CY + 16), 2.3, up=True, bold=True)
    pg.text("no carrier under the antenna", X(G.X_NOTCH + 1.5), Y(G.H - 2.0), 2.0)
    p1 = [q for q in fps["U1"].Pads() if q.GetNumber() == "1"][0].GetPosition()
    side = "left" if MM(p1.x) < G.MODULES["U1"][0] else "right"
    for i, line in enumerate([
            "Names in brackets: ESP32 pads past the notch, which have no land. Grey dots: through-hole parts. "
            "Crossed circles: M2.5 mounting holes.",
            "ESP32, antenna to the right as drawn: the row nearest the input boards reads 5V at the USB-C end "
            "... IO36, EN, 3V3 at the antenna end.",
            f"Each input board, native USB port (proud shell, beside BOOT and RST) at the front: 5V is the pad "
            f"nearest that port on the {side}-hand edge.",
            "The same views are Waveshare's own pictures: docs/sources/rp2350-usb-c-pinout.png and "
            "esp32-dev-kit-drawing.png."]):
        pg.text(line, 15, Y(G.H) + 16 + i * 4.4, 2.5)

    out = HERE / "carrier-fit-check.pdf"
    pg.save(out)
    print(f"wrote {out.name}: A4, 1:1, {sum(len(list(f.Pads())) for r, f in fps.items() if r in N.PARTS and N.PARTS[r]['kind'] == 'module')} module lands named")

if __name__ == "__main__":
    main()
