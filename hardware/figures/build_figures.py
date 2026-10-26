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
b.append(wire(c,[P1("29"),(-12.8,10.50),(-12.8,5.42)],GND,lw=0.9))             # GP29 -> R8 -> GND
b.append(wire(c,[P2("29"),(23.0,10.50),(23.0,5.42)],GND,lw=0.9))               # GP29 -> R9 -> GND
for x,y in ((20,RY),(22,GY),(34.06,GY),(-12.8,5.42),(23.0,5.42)): b.append(dot(c,x,y))
b += [resistor(c,-4.6,10.5,False,"4k7"), resistor(c,26.6,10.5,False,"4k7")]
b += [diode(c,-8,-6), diode(c,20,-6)]                                            # bodies sit on the wire
b += [wire(c,[(36,RY),(36,GY)],RAIL,lw=0.8), wire(c,[(42,RY),(42,GY)],RAIL,lw=0.8)]
b += [ecap(c,36,-20.5), dcap(c,42,-20.5)]
b += [wire(c,[(-6.5,2.88),(-6.5,5.42)],RAIL,lw=0.8), wire(c,[(24,2.88),(24,5.42)],RAIL,lw=0.8)]
b += [dcap(c,-6.5,4.15), dcap(c,24,4.15)]
b += [tag(c,-6.0,-7.6,"D1",RAIL), tag(c,22.0,-7.6,"D2",RAIL),
      tag(c,36,-15.4,"C1",RAIL,"middle"), tag(c,42,-15.4,"C2",RAIL,"middle"),
      tag(c,-6.5,0.4,"C3",RAIL,"middle"), tag(c,24.0,0.4,"C4",RAIL,"middle"),
      tag(c,-15.5,-20.0,"GND",GND), tag(c,-7.5,-16.4,"rail",RAIL),
      tag(c,-4.6,12.6,"R8 4k7",GND,"middle"), tag(c,26.6,12.6,"R9 4k7",GND,"middle")]
F2=svg(c,"".join(b),"Power wiring drawn pictorially: an orange wire leaves each input board's 5V pad, passes down through a black Schottky diode whose silver band faces the rail, and joins a shared rail bus that feeds the ESP32's 5V pad at the right. A dark ground bus runs below it. A can capacitor and a disc capacitor bridge the two buses near the ESP32, and a disc capacitor sits across each input board's 5V and GND pads. On each input board a 4.7 kilohm resistor runs from the GP29 pad to ground.")

# ── Figure 3: I2S ─────────────────────────────────────────────────────────
c=C(-24.5,53,-58,37,7.0)
BY_, LY_ = -25.5, -19.5                    # bit-clock and word-clock buses
b=[boards(c)]
b.append(wire(c,[E3(9),(21.36,BY_),(-19,BY_),(-19,18.12),P1("26")],BCLK))        # GPIO25 -> R1 -> board 1
b.append(wire(c,[(21.36,BY_),(28.8,BY_),(28.8,18.12),P2("26")],BCLK))            #        -> R2 -> board 2
b.append(wire(c,[E3(8),(18.82,LY_),(-16.6,LY_),(-16.6,15.58),P1("27")],LRCK))    # GPIO33 -> R3 -> board 1
b.append(wire(c,[(18.82,LY_),(26.4,LY_),(26.4,15.58),P2("27")],LRCK))            #        -> R4 -> board 2
LB = J3Y - 2.2                                                                   # jumpers run just inside the header row
b.append(wire(c,[E3(9),(E3(9)[0],LB),(E3(15)[0],LB),E3(15)],BCLK,lw=0.85))       # loop-back 25 -> 13
b.append(wire(c,[E3(8),(E3(8)[0],LB),(E3(7)[0],LB),E3(7)],LRCK,lw=0.85))         # loop-back 33 -> 32
b.append(wire(c,[P1("28"),(-14.2,13.04),(-14.2,-15),(E3(6)[0],-15),E3(6)],AUD))  # input 1 -> GPIO35
b.append(wire(c,[(-11.0,13.04),(-11.0,5.42),P1("GND")],GND,lw=0.9))             # R7 pull-down at input 1
b.append(dot(c,-11.0,13.04))
b.append(resistor(c,-11.0,9.23,True,"100k"))
b.append(wire(c,[P2("28"),(23.9,13.04),(23.9,J3Y)],AUD))
for x,y in ((21.36,BY_),(18.82,LY_)): b.append(dot(c,x,y))
b += [resistor(c,0.5,BY_,False), resistor(c,25.5,BY_,False),
      resistor(c,3.0,LY_,False), resistor(c,23.0,LY_,False)]
b += [tag(c,0.5,-23.2,"R1 1k",BCLK,"middle"), tag(c,26.6,-23.2,"R2 1k",BCLK,"middle"),
      tag(c,3.0,-17.2,"R3 1k",LRCK,"middle"), tag(c,20.5,-17.2,"R4 1k",LRCK,"middle"),
      tag(c,-9.4,8.7,"R7 100k",GND),
      tag(c,-24.0,19.6,"BCLK",BCLK), tag(c,-24.0,16.6,"LRCK",LRCK), tag(c,-24.0,13.6,"audio",AUD)]
F3=svg(c,"".join(b),"I2S wiring drawn pictorially: a blue bit-clock wire and an amber word-clock wire each rise from one ESP32 pad, split left and right along a bus, and pass through a 1 kilohm resistor before reaching the matching pad on each input board. Two short jumpers on the ESP32's own header row are the clock loop-backs, GPIO25 to GPIO13 and GPIO33 to GPIO32. Violet wires carry audio from each input board's GP28 pad down to the ESP32; a 100 kilohm resistor at input 1 pulls its audio line to ground.")

# ── Figure 4: UART ────────────────────────────────────────────────────────
c=C(-9,65,-73.5,37,6.3)
b=[boards(c)]
b.append(wire(c,[E4(11),(26.44,-59),(54,-59),(54,-6),(19.0,-6),(19.0,15.58),P1("5","R")],TX))
b.append(wire(c,[E4(12),(28.98,-62),(56.5,-62),(56.5,-3),(21.5,-3),(21.5,13.04),P1("4","R")],RX))
b.append(wire(c,[E4(8),(21.36,-65),(59,-65),(59,15.58),P2("5","R")],TX))
b.append(wire(c,[E4(9),(23.90,-68),(61.5,-68),(61.5,13.04),P2("4","R")],RX))
b += [resistor(c,36.0,-59,False), resistor(c,44.0,-65,False)]                    # R5, R6 at the ESP32 end
b += [tag(c,18,-58.4,"GPIO17 → R5",TX,"end"), tag(c,18,-61.4,"GPIO16",RX,"end"),
      tag(c,18,-64.4,"GPIO19 → R6",TX,"end"), tag(c,18,-67.4,"GPIO18",RX,"end")]
F4=svg(c,"".join(b),"UART wiring drawn pictorially: four wires leave the ESP32's far header row, route around its USB-C end on the right, and reach the right-hand pads of the two input boards. Orange wires carry data from the ESP32, each through a 1 kilohm resistor near the ESP32, to each board's GP5 input; teal wires carry data from each board's GP4 output back to the ESP32.")

pathlib.Path(HERE+"/figs.txt").write_text("\n@@SPLIT@@\n".join([F1,F2,F3,F4]))
print("sizes:",[len(x) for x in (F1,F2,F3,F4)])
