import sys, pathlib
HERE=str(__import__("pathlib").Path(__file__).resolve().parent)
sys.path.insert(0,HERE)
from pictorial import *

# ── Exploded placement (mm), shared by figures 2-4 ────────────────────────
# RP boards sit at the top with their exposed ports up, exactly as in fig 1.
# The ESP32 sits below, leaving a 28 mm routing channel between the two.
R1X, R2X, BY = 0.0, 30.0, 0.0
EX, EY = -3.0, -56.0                 # ESP32: x -3.0..50.8, y -56.0..-28.06
J3Y = EY + ED - 1.5                  # -29.56, the header row facing the channel
J4Y = EY + 1.5                       # -54.50, the far row (UART)

def P1(n, s="L"):                    # input board 1 pad, by silkscreen name
    i = (LEFT if s=="L" else RIGHT).index(n); x,y = rp_pad(R1X,i,s); return (x, y+BY)
def P2(n, s="L"):
    i = (LEFT if s=="L" else RIGHT).index(n); x,y = rp_pad(R2X,i,s); return (x, y+BY)
def E3(pin): return esp_pad(EX,EY,pin-1,"J3")
def E4(pin): return esp_pad(EX,EY,pin-1,"J4")

def boards(c): return esp_board(c,EX,EY)+rp_board(c,R1X,BY,"INPUT 1")+rp_board(c,R2X,BY,"INPUT 2")
def svg(c,body,aria): return f'<svg viewBox="0 0 {c.w} {c.h}" role="img" aria-label="{esc(aria)}">{body}</svg>'
def dot(c,x,y):                      # T-junction: two wires joined at one point
    return (f'<circle cx="{c.X(x)}" cy="{c.Y(y)}" r="{c.L(1.05)}" fill="#D9DCE0" '
            f'stroke="#55595F" stroke-width="1.1"/>')

# ── Figure 1: true-scale placement ────────────────────────────────────────
c1=C(-14,55,-48,40,7.6)
b=[f'<rect x="{c1.X(-12.1)}" y="{c1.Y(35.4)}" width="{c1.L(64.6)}" height="{c1.L(79.74)}" rx="{c1.L(2)}" fill="var(--sunk)" stroke="var(--board-edge)" stroke-width="1.4"/>',
   f'<rect x="{c1.X(-9.7)}" y="{c1.Y(33)}" width="{c1.L(59.8)}" height="{c1.L(74.94)}" rx="{c1.L(1)}" fill="var(--surface)" stroke="var(--rule)"/>',
   esp_board(c1,-6.7,-33.94), rp_board(c1,0,0,"INPUT 1"), rp_board(c1,22.9,0,"INPUT 2"),
   f'<text x="{c1.X(20.2)}" y="{c1.Y(-39)}" text-anchor="middle" font-size="11" font-family="var(--f-mono)" fill="var(--dim)">antenna end — keep the loom away</text>',
   f'<text x="{c1.X(20.2)}" y="{c1.Y(-3)}" text-anchor="middle" font-size="11" font-family="var(--f-mono)" fill="var(--dim)">6 mm service gap — the loom lives here</text>',
   f'<text x="{c1.X(20.2)}" y="{c1.Y(37.5)}" text-anchor="middle" font-size="11" font-family="var(--f-mono)" fill="var(--fg)">host cables plug in here</text>']
F1=svg(c1,"".join(b),"The real boards seen from above in their box positions: two RP2350-USB-C input boards side by side at the front with their exposed USB-C ports facing the port wall, and the ESP32 dev kit across the back with its antenna at the left.")

# ── Figure 2: power ───────────────────────────────────────────────────────
c=C(-18,53,-58,37,7.0)
RY, GY = -18.0, -23.0                      # rail bus and ground bus
b=[boards(c)]
b.append(wire(c,[P1("5V"),(-8,2.88),(-8,RY),(46.76,RY),(46.76,J3Y)],RAIL))      # board 1 -> D1 -> rail -> ESP 5V
b.append(wire(c,[P2("5V"),(20,2.88),(20,RY)],RAIL))                             # board 2 -> D2 -> rail
b.append(wire(c,[P1("GND"),(-15,5.42),(-15,GY),(44,GY)],GND))                   # ground bus
b.append(wire(c,[P2("GND"),(22,5.42),(22,GY)],GND))
b.append(wire(c,[(34.06,GY),(34.06,J3Y)],GND))                                  # bus -> ESP GND
b.append(wire(c,[P1("29"),(-3,10.50),(-3,5.42),P1("GND")],GND,lw=0.9))          # GP29 tied to GND
b.append(wire(c,[P2("29"),(27,10.50),(27,5.42),P2("GND")],GND,lw=0.9))
for x,y in ((20,RY),(22,GY),(34.06,GY)): b.append(dot(c,x,y))
b += [diode(c,-8,-6), diode(c,20,-6)]                                            # bodies sit on the wire
b += [wire(c,[(36,RY),(36,GY)],RAIL,lw=0.8), wire(c,[(42,RY),(42,GY)],RAIL,lw=0.8)]
b += [ecap(c,36,-20.5), dcap(c,42,-20.5)]
b += [wire(c,[(-6.5,2.88),(-6.5,5.42)],RAIL,lw=0.8), wire(c,[(24,2.88),(24,5.42)],RAIL,lw=0.8)]
b += [dcap(c,-6.5,4.15), dcap(c,24,4.15)]
b += [tag(c,-6.0,-7.6,"D1",RAIL), tag(c,22.0,-7.6,"D2",RAIL),
      tag(c,36,-15.4,"C1",RAIL,"middle"), tag(c,42,-15.4,"C2",RAIL,"middle"),
      tag(c,-9.2,4.9,"C3",RAIL,"end"), tag(c,21.3,4.9,"C4",RAIL,"end"),
      tag(c,-15.5,-20.0,"GND",GND), tag(c,-7.5,-16.4,"rail",RAIL),
      tag(c,-3.6,11.1,"GP29",GND,"end"), tag(c,26.4,11.1,"GP29",GND,"end")]
F2=svg(c,"".join(b),"Power wiring drawn pictorially: an orange wire leaves each input board's 5V pad, passes down through a black Schottky diode whose silver band faces the rail, and joins a shared rail bus that feeds the ESP32's 5V pad at the right. A dark ground bus runs below it. A can capacitor and a disc capacitor bridge the two buses near the ESP32, and a disc capacitor sits across each input board's own 5V and GND pads. A thin ground wire ties each board's GP29 pad to its GND pad.")

# ── Figure 3: I2S ─────────────────────────────────────────────────────────
c=C(-24.5,53,-58,37,7.0)
BY_, LY_ = -25.5, -19.5                    # bit-clock and word-clock buses
b=[boards(c)]
b.append(wire(c,[E3(9),(21.36,BY_),(-19,BY_),(-19,18.12),P1("26")],BCLK))        # GPIO25 -> R1 -> board 1
b.append(wire(c,[(21.36,BY_),(28.8,BY_),(28.8,18.12),P2("26")],BCLK))            #        -> R2 -> board 2
b.append(wire(c,[E3(8),(18.82,LY_),(-16.6,LY_),(-16.6,15.58),P1("27")],LRCK))    # GPIO33 -> R3 -> board 1
b.append(wire(c,[(18.82,LY_),(26.4,LY_),(26.4,15.58),P2("27")],LRCK))            #        -> R4 -> board 2
b.append(wire(c,[(4.12,BY_),(4.12,J3Y)],BCLK,lw=0.85))                           # loop-back 25 -> 36
b.append(wire(c,[(6.66,LY_),(6.66,J3Y)],LRCK,lw=0.85))                           # loop-back 33 -> 39
b.append(wire(c,[P1("28"),(-14.2,13.04),(-14.2,-15),(11.74,-15),(11.74,J3Y)],AUD))
b.append(wire(c,[P2("28"),(23.9,13.04),(23.9,J3Y)],AUD))
for x,y in ((21.36,BY_),(18.82,LY_),(4.12,BY_),(6.66,LY_)): b.append(dot(c,x,y))
b += [resistor(c,0.5,BY_,False), resistor(c,25.5,BY_,False),
      resistor(c,3.0,LY_,False), resistor(c,23.0,LY_,False)]
b += [tag(c,0.5,-23.2,"R1",BCLK,"middle"), tag(c,26.6,-23.2,"R2",BCLK,"middle"),
      tag(c,3.0,-17.2,"R3",LRCK,"middle"), tag(c,20.5,-17.2,"R4",LRCK,"middle"),
      tag(c,-24.0,19.6,"BCLK",BCLK), tag(c,-24.0,16.6,"LRCK",LRCK), tag(c,-24.0,13.6,"audio",AUD)]
F3=svg(c,"".join(b),"I2S wiring drawn pictorially: a blue bit-clock wire and an amber word-clock wire each rise from one ESP32 pad, split left and right along a bus, and pass through a beige 33 ohm resistor before reaching the matching pad on each input board. Two short branches drop off the same buses back into two nearby ESP32 pads as the clock loop-backs. Violet wires carry audio from each input board's GP28 pad down to the ESP32.")

# ── Figure 4: UART ────────────────────────────────────────────────────────
c=C(-9,65,-70,37,6.3)
b=[boards(c)]
b.append(wire(c,[E4(11),(26.44,-59),(54,-59),(54,-6),(19.0,-6),(19.0,15.58),P1("5","R")],TX))
b.append(wire(c,[E4(12),(28.98,-61.5),(56.5,-61.5),(56.5,-3),(21.5,-3),(21.5,13.04),P1("4","R")],RX))
b.append(wire(c,[E4(8),(21.36,-64),(59,-64),(59,15.58),P2("5","R")],TX))
b.append(wire(c,[E4(9),(23.90,-66.5),(61.5,-66.5),(61.5,13.04),P2("4","R")],RX))
b += [tag(c,18,-58.4,"GPIO17",TX,"end"), tag(c,18,-60.9,"GPIO16",RX,"end"),
      tag(c,18,-63.4,"GPIO19",TX,"end"), tag(c,18,-65.9,"GPIO18",RX,"end")]
F4=svg(c,"".join(b),"UART wiring drawn pictorially: four wires leave the ESP32's far header row, route around its USB-C end on the right, and reach the right-hand pads of the two input boards. Orange wires carry data from the ESP32 to each board's GP5 input; teal wires carry data from each board's GP4 output back to the ESP32.")

pathlib.Path(HERE+"/figs.txt").write_text("\n@@SPLIT@@\n".join([F1,F2,F3,F4]))
print("sizes:",[len(x) for x in (F1,F2,F3,F4)])
