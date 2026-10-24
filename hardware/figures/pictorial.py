import pathlib, re

# ---- geometry, READ FROM enclosure/boards.scad ----------------------------
# Not copied. boards.scad is the single source for every board number, and a
# second copy here is what let the figures draw both USB-C shells proud when
# the model had said for weeks that only the inner one is.
_SCAD = pathlib.Path(__file__).resolve().parents[2] / "enclosure" / "boards.scad"

def _scad_numbers(path):
    out = {}
    for name, val in re.findall(r"^\s*(\w+)\s*=\s*(-?[\d.]+)\s*;", path.read_text(), re.M):
        out[name] = float(val)
    return out

_B = _scad_numbers(_SCAD)
_NEED = ["board_w", "board_l", "pcb_t", "usb_w", "usb_over_out", "usb_over_in",
         "usb_depth", "notch_d", "notch_len", "notch_dep", "pad_first",
         "pad_pitch", "pad_inset", "esp_w", "esp_d"]
_missing = [k for k in _NEED if k not in _B]
assert not _missing, f"{_SCAD} no longer defines: {_missing}"

BW, BL, PCB = _B["board_w"], _B["board_l"], _B["pcb_t"]
USBW = _B["usb_w"]
# The two receptacles differ. The EXPOSED port (notch end, the one the host
# cable reaches) is flush with the PCB edge; the inner PROGRAMMING port is
# proud. Owner, boards in hand.
USB_OVER_OUT, USB_OVER_IN = _B["usb_over_out"], _B["usb_over_in"]
USB_DEPTH = _B["usb_depth"]
NOTCH_D, NOTCH_L, NOTCH_DEP = _B["notch_d"], _B["notch_len"], _B["notch_dep"]
PAD1, PITCH = _B["pad_first"], _B["pad_pitch"]
PAD_IN = _B["pad_inset"]
EW, ED = _B["esp_w"], _B["esp_d"]
EH_DX, EH_DY = _B["esp_hole_dx"], _B["esp_hole_dy"]
EPAD0, EPITCH = (EW - 45.72) / 2, 2.54   # 19 pads, 45.72 mm span (wiring.md)

LEFT  = ["5V","GND","3V3","29","28","27","26","10","9"]
RIGHT = ["0","1","2","3","4","5","6","7","8"]
# J3 front row, box left -> right (schematic pin 1..19)
J3 = ["3V3","EN","36","39","34","35","32","33","25","26","27","14","12","GND","13","SD2","SD3","CMD","5V"]
# J4 back row, box left -> right
J4 = ["GND","23","22","TX0","RX0","21","GND","19","18","5","17","16","4","0","2","15","SD1","SD0","CLK"]

PCB_BLUE="var(--pcb-rp)"; PCB_EDGE="var(--pcb-rp-edge)"; GOLD="#C9A227"; SIL="#BFC4CA"
SIL_D="#8C9198"; DARK="#17191C"; BTN="#30343A"; MOD="#9AA0A6"

def esc(s): return s.replace("&","&amp;").replace("<","&lt;")

class C:
    def __init__(s,x0,x1,y0,y1,scale):
        s.x0,s.y1,s.s = x0,y1,scale
        s.w=round((x1-x0)*scale,1); s.h=round((y1-y0)*scale,1)
    def X(s,x): return round((x-s.x0)*s.s,2)
    def Y(s,y): return round((s.y1-y)*s.s,2)
    def L(s,v): return round(v*s.s,2)

def rp_pad(bx,i,side):
    x = bx + (PAD_IN if side=="L" else BW-PAD_IN)
    return x, PAD1 + i*PITCH
def esp_pad(ex,ey,i,row):
    return ex+EPAD0+i*EPITCH, (ey+ED-1.5) if row=="J3" else (ey+1.5)

def rp_board(c,bx,by,name):
    o=[]; X,Y,L=c.X,c.Y,c.L
    nb=by+BL-NOTCH_D-NOTCH_L
    o.append(f'<path d="M{X(bx+2)} {Y(by)} H{X(bx+BW-2)} A{L(2)} {L(2)} 0 0 0 {X(bx+BW)} {Y(by+2)} '
             f'V{Y(nb)} H{X(bx+BW-NOTCH_DEP)} V{Y(nb+NOTCH_L)} H{X(bx+BW)} V{Y(by+BL-2)} '
             f'A{L(2)} {L(2)} 0 0 0 {X(bx+BW-2)} {Y(by+BL)} H{X(bx+2)} '
             f'A{L(2)} {L(2)} 0 0 0 {X(bx)} {Y(by+BL-2)} V{Y(nb+NOTCH_L)} H{X(bx+NOTCH_DEP)} '
             f'V{Y(nb)} H{X(bx)} V{Y(by+2)} A{L(2)} {L(2)} 0 0 0 {X(bx+2)} {Y(by)} Z" '
             f'fill="{PCB_BLUE}" stroke="{PCB_EDGE}" stroke-width="1.2"/>')
    # Same rule as rp_shell() in boards.scad: the exposed port's face sits at
    # board_l + usb_over_out (0.00 = flush), the programming port's at
    # -usb_over_in (proud). Each reaches usb_depth back along the board.
    for yy, mouth in ((by + BL + USB_OVER_OUT - USB_DEPTH, "out"),
                      (by - USB_OVER_IN, "in")):
        o.append(f'<rect x="{X(bx+(BW-USBW)/2)}" y="{Y(yy+USB_DEPTH)}" width="{L(USBW)}" height="{L(USB_DEPTH)}" rx="{L(0.5)}" '
                 f'fill="{SIL}" stroke="{SIL_D}" stroke-width="1"/>')
        # the slot, drawn at the open mouth end
        sy = yy + USB_DEPTH - 0.9 if mouth == "out" else yy + 0.9
        o.append(f'<rect x="{X(bx+(BW-USBW)/2+1.2)}" y="{Y(sy)}" width="{L(USBW-2.4)}" height="{L(1.1)}" rx="{L(0.5)}" fill="{SIL_D}" opacity="0.55"/>')
    o.append(f'<rect x="{X(bx+5.4)}" y="{Y(by+19.0)}" width="{L(6.6)}" height="{L(6.6)}" rx="{L(0.4)}" fill="{DARK}"/>')
    for bxx in (bx+3.4,bx+10.6):
        o.append(f'<rect x="{X(bxx)}" y="{Y(by+9.2)}" width="{L(3.2)}" height="{L(3.2)}" rx="{L(0.4)}" fill="{BTN}"/>'
                 f'<circle cx="{X(bxx+1.6)}" cy="{Y(by+7.6)}" r="{L(1.0)}" fill="#55595F"/>')
    for i in range(9):
        for side,labs in (("L",LEFT),("R",RIGHT)):
            px,py=rp_pad(bx,i,side); py+=by
            o.append(f'<rect x="{X(px-0.85)}" y="{Y(py+0.8)}" width="{L(1.7)}" height="{L(1.6)}" rx="{L(0.4)}" fill="{GOLD}"/>')
            tx = X(px)+(L(1.6) if side=="L" else -L(1.6))
            o.append(f'<text x="{tx}" y="{Y(py)+3.4}" font-size="{max(7,L(1.35))}" fill="#CFE0F2" '
                     f'text-anchor="{"start" if side=="L" else "end"}" font-family="var(--f-mono)">{labs[i]}</text>')
    o.append(f'<text x="{X(bx+BW/2)}" y="{Y(by+14.5)}" text-anchor="middle" font-size="{max(8,L(1.9))}" '
             f'fill="#9FC3E8" font-family="var(--f-mono)">{name}</text>')
    return "".join(o)

def esp_board(c,ex,ey):
    o=[]; X,Y,L=c.X,c.Y,c.L
    o.append(f'<rect x="{X(ex)}" y="{Y(ey+ED)}" width="{L(EW)}" height="{L(ED)}" rx="{L(1.5)}" fill="var(--pcb-esp)" stroke="var(--pcb-esp-edge)" stroke-width="1.2"/>')
    o.append(f'<rect x="{X(ex+1)}" y="{Y(ey+25.7)}" width="{L(18)}" height="{L(23.5)}" rx="{L(0.8)}" fill="{MOD}" stroke="#70757A" stroke-width="1"/>')
    for k in range(7):
        yy=ey+4.0+k*3.0
        o.append(f'<path d="M{X(ex+1.6)} {Y(yy)} H{X(ex+6.2)}" stroke="#6F7479" stroke-width="2" fill="none"/>')
    o.append(f'<text x="{X(ex+13)}" y="{Y(ey+14)}" text-anchor="middle" font-size="{max(7,L(1.6))}" fill="#3C4044" font-family="var(--f-mono)">WROOM-32E</text>')
    o.append(f'<rect x="{X(ex+EW-3.2)}" y="{Y(ey+ED/2+4.45)}" width="{L(6)}" height="{L(8.9)}" rx="{L(0.6)}" fill="{SIL}" stroke="{SIL_D}" stroke-width="1"/>')
    o.append(f'<rect x="{X(ex+29)}" y="{Y(ey+16)}" width="{L(5.5)}" height="{L(4.5)}" rx="{L(0.4)}" fill="#D8DCE0"/>')
    for bxx in (ex+40,ex+45.5):
        o.append(f'<rect x="{X(bxx)}" y="{Y(ey+9.5)}" width="{L(3.2)}" height="{L(3.2)}" rx="{L(0.4)}" fill="{BTN}"/>')
    for hx,hy in ((1.88,1.27),(EW-1.88,1.27),(1.88,ED-1.27),(EW-1.88,ED-1.27)):
        o.append(f'<circle cx="{X(ex+hx)}" cy="{Y(ey+hy)}" r="{L(1.3)}" fill="var(--pcb-esp-edge)" stroke="var(--dim)" stroke-width="0.8"/>')
    for row,labs in (("J3",J3),("J4",J4)):
        for i,lab in enumerate(labs):
            px,py=esp_pad(ex,ey,i,row)
            o.append(f'<rect x="{X(px-0.85)}" y="{Y(py+0.85)}" width="{L(1.7)}" height="{L(1.7)}" rx="{L(0.3)}" fill="{GOLD}"/>')
    return "".join(o)

def wire(c,pts,col,label=None,lw=1.15):
    X,Y=c.X,c.Y
    d="M"+" L".join(f"{X(x)} {Y(y)}" for x,y in pts)
    s=(f'<path d="{d}" fill="none" stroke="#0007" stroke-width="{c.L(lw)+2.6}" stroke-linecap="round" stroke-linejoin="round"/>'
       f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{c.L(lw)}" stroke-linecap="round" stroke-linejoin="round"/>')
    for x,y in (pts[0],pts[-1]):
        s+=f'<circle cx="{X(x)}" cy="{Y(y)}" r="{c.L(0.95)}" fill="#D9DCE0" stroke="#7A7F85" stroke-width="0.8"/>'
    return s

def diode(c,x,y,vert=True):
    X,Y,L=c.X,c.Y,c.L; w,h=(2.2,4.3) if vert else (4.3,2.2)
    s=f'<rect x="{X(x-w/2)}" y="{Y(y+h/2)}" width="{L(w)}" height="{L(h)}" rx="{L(0.7)}" fill="var(--part-body)" stroke="var(--part-edge)" stroke-width="0.8"/>'
    if vert: s+=f'<rect x="{X(x-w/2)}" y="{Y(y-h/2+0.55)}" width="{L(w)}" height="{L(0.55)}" fill="#E6E8EA"/>'
    else:    s+=f'<rect x="{X(x+w/2-0.55)}" y="{Y(y+h/2)}" width="{L(0.55)}" height="{L(h)}" fill="#E6E8EA"/>'
    return s

def resistor(c,x,y,vert=True):
    X,Y,L=c.X,c.Y,c.L; w,h=(2.4,6.4) if vert else (6.4,2.4)
    s=f'<rect x="{X(x-w/2)}" y="{Y(y+h/2)}" width="{L(w)}" height="{L(h)}" rx="{L(1.0)}" fill="#D6C3A0" stroke="#9C8A68" stroke-width="0.8"/>'
    for k,col in enumerate(("#E07B29","#E07B29","#222","#C9A227")):
        off=h/2-1.2-k*1.0
        if vert: s+=f'<rect x="{X(x-w/2)}" y="{Y(y+off)}" width="{L(w)}" height="{L(0.55)}" fill="{col}"/>'
        else:    s+=f'<rect x="{X(x+off-0.55)}" y="{Y(y+h/2)}" width="{L(0.55)}" height="{L(h)}" fill="{col}"/>'
    return s

def ecap(c,x,y):
    X,Y,L=c.X,c.Y,c.L
    return (f'<circle cx="{X(x)}" cy="{Y(y)}" r="{L(2.6)}" fill="var(--part-body)" stroke="var(--part-edge)" stroke-width="0.9"/>'
            f'<path d="M{X(x)} {Y(y+2.6)} A{L(2.6)} {L(2.6)} 0 0 0 {X(x)} {Y(y-2.6)} Z" fill="#9AA0A6" opacity="0.85"/>')
def dcap(c,x,y):
    X,Y,L=c.X,c.Y,c.L
    return f'<circle cx="{X(x)}" cy="{Y(y)}" r="{L(1.9)}" fill="#C8A24A" stroke="#8C7030" stroke-width="0.9"/>'

def tag(c,x,y,txt,col,anchor="start"):
    return (f'<text x="{c.X(x)}" y="{c.Y(y)}" font-size="11" font-family="var(--f-mono)" font-weight="600" '
            f'fill="{col}" text-anchor="{anchor}" paint-order="stroke" stroke="var(--surface)" stroke-width="3">{esc(txt)}</text>')

RAIL="var(--w-pwr)"; GND="var(--w-gnd)"; BCLK="var(--w-clk)"; LRCK="var(--w-clk2)"
AUD="var(--w-dat)"; TX="var(--w-pwr)"; RX="var(--w-uart)"
