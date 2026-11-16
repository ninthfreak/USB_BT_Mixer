"""Single source of truth for the carrier board's connections.

Everything downstream is generated from this file: the KiCad schematic, the
human-readable connection table, and the check that the two agree. Nothing
here is copied from another file -- hardware/wiring.md is prose ABOUT this,
and check_netlist.py verifies the generated schematic matches.

Pin numbering (ours, since we draw both symbol and footprint). Each is
written against a picture of the real board that is committed in docs/sources,
because "left" and "right" mean nothing without one: for five weeks the input
boards' land pattern was the mirror image of the real board, and every check
agreed with it (docs/project-review-2026-11.md #1).

  RP2350-USB-C (U1, U2), 18 pads. docs/sources/rp2350-usb-c-pinout.png:
  component side up, NATIVE USB port (the proud one, beside BOOT and RST) at
  the TOP of the picture:
      1..9   LEFT edge, top to bottom:  5V GND 3V3 GP29 GP28 GP27 GP26 GP10 GP9
      10..18 RIGHT edge, top to bottom: GP0 GP1 GP2 GP3 GP4 GP5 GP6 GP7 GP8

  ESP32-DEV-KIT (U3), 38 pads. docs/sources/esp32-dev-kit-drawing.png:
  component side up, USB-C at the LEFT, antenna at the RIGHT:
      1..19  header J3, the TOP row, numbered from the ANTENNA end:
             pad 1 = 3V3 (far right) ... pad 19 = 5V (far left)
      20..38 header J4, the BOTTOM row, also from the antenna end:
             pad 20 = GND (far right) ... pad 38 = CLK (far left)
             (so J4 pin n == our pad 19 + n)

check_pcb.py holds both pictures against the placed board.
"""

# ── Module pin maps ──────────────────────────────────────────────────────
RP_LEFT  = ["5V", "GND", "3V3", "GP29", "GP28", "GP27", "GP26", "GP10", "GP9"]
RP_RIGHT = ["GP0", "GP1", "GP2", "GP3", "GP4", "GP5", "GP6", "GP7", "GP8"]

ESP_J3 = ["3V3", "EN", "IO36", "IO39", "IO34", "IO35", "IO32", "IO33", "IO25",
          "IO26", "IO27", "IO14", "IO12", "GND", "IO13", "SD2", "SD3", "CMD", "5V"]
ESP_J4 = ["GND", "IO23", "IO22", "TX0", "RX0", "IO21", "GND", "IO19", "IO18",
          "IO5", "IO17", "IO16", "IO4", "IO0", "IO2", "IO15", "SD1", "SD0", "CLK"]

# ── Parts ────────────────────────────────────────────────────────────────
# kind: "module" | "r" | "c" | "cpol" | "d" | "hdr" | "tp"
PARTS = {
    "U1": dict(kind="module", value="RP2350-USB-C", desc="Input 1",
               left=RP_LEFT, right=RP_RIGHT),
    "U2": dict(kind="module", value="RP2350-USB-C", desc="Input 2",
               left=RP_LEFT, right=RP_RIGHT),
    "U3": dict(kind="module", value="ESP32-DEV-KIT", desc="Mixer / Bluetooth",
               left=ESP_J3, right=ESP_J4),

    "D1": dict(kind="d", value="1N5817", desc="Input 1 supply isolation"),
    "D2": dict(kind="d", value="1N5817", desc="Input 2 supply isolation"),

    # 1k in series with every line the ESP32 drives into an input board.
    # With one host connected the other input board is unpowered and the
    # ESP32 keeps driving these lines into it. The clocks land on GP9/GP10
    # and the UART on GP5, which are the RP2350's fault-tolerant pads: with
    # the chip unpowered "very little current flows into the pin whilst it
    # is below 3.63 V" (RP2350 datasheet), so nothing is back-fed and these
    # are no longer what protects the chip. They stay as edge-rate control
    # beside a 2.4 GHz radio (22 ns edges into ~10 pF at 2.8 MHz, against a
    # 177 ns half-period) and to limit the current if firmware ever turns a
    # pin the wrong way round.
    "R1": dict(kind="r", value="1k", desc="BCLK series to input 1"),
    "R2": dict(kind="r", value="1k", desc="BCLK series to input 2"),
    "R3": dict(kind="r", value="1k", desc="LRCK series to input 1"),
    "R4": dict(kind="r", value="1k", desc="LRCK series to input 2"),
    "R5": dict(kind="r", value="1k", desc="UART TX series to input 1"),
    "R6": dict(kind="r", value="1k", desc="UART TX series to input 2"),
    # R7 (AUD2 pull-down), R8/R9 (GP29 pull-downs), C2-C4 (0.1 uF bypasses):
    # retired 2026-11-16, not needed (docs/project-review-2026-11.md #5).
    # The designators are not reused.
    #
    # Bleed: an input board with no host is fed its own diode's reverse
    # leakage from the rail. With nothing to drain it, its VBUS floats up,
    # and a USB-C host will not switch a port on until VBUS is below 0.8 V
    # (vSafe0V). 1k holds it there against up to 0.8 mA; it costs 5 mA
    # while that host is connected.
    "R10": dict(kind="r", value="1k", desc="Input 1 VBUS bleed: holds it at 0 V with no host"),
    "R11": dict(kind="r", value="1k", desc="Input 2 VBUS bleed: holds it at 0 V with no host"),

    "C1": dict(kind="cpol", value="22uF", desc="Rail bulk, at the ESP32"),

    # One 2-pin header beside each input board's GP3, not one shared 3-pin:
    # a shared header meant a debug line crossing under input 2.
    "J1": dict(kind="hdr", value="1x2", desc="Input 1 debug serial (optional)",
               pins=["GND", "DBG1"]),
    "J2": dict(kind="hdr", value="1x2", desc="Input 2 debug serial (optional)",
               pins=["GND", "DBG2"]),
    "TP1": dict(kind="tp", value="RAIL", desc="Rail test point -- MEASURE here"),
    "TP2": dict(kind="tp", value="GND", desc="Ground test point"),
}

# ── Nets ─────────────────────────────────────────────────────────────────
# "REF.PINNAME", or "REF.#n" to pick a pad by number where the name repeats.
NETS = {
    # Power. Each input board's raw VBUS reaches the rail only through its
    # own diode, so the two hosts' 5 V supplies are never tied together.
    "VBUS1": ["U1.5V", "D1.A", "R10.1"],
    "VBUS2": ["U2.5V", "D2.A", "R11.1"],
    "RAIL":  ["D1.K", "D2.K", "U3.5V", "C1.+", "TP1.1"],
    # U3 pad 20 (a third GND) is off the board under the antenna overhang;
    # pads 14 and 26 carry the ESP32's ground.
    "GND":   ["U1.GND", "U2.GND", "U3.GND", "U3.#26",
              "C1.-", "R10.2", "R11.2", "J1.GND", "J2.GND", "TP2.1"],

    # I2S. The ESP32 is clock master on both; each clock has an output pin
    # (I2S0 master) and a loop-back input pin (I2S1 slave) joined under the
    # ESP32, on its side of the series resistors. Never IO36/IO39: they
    # glitch low for ~80 ns whenever the SAR ADC powers up -- reported as
    # tracking A2DP streaming (AUDIT.md #4).
    #
    # On the input boards the clocks go to GP9 and GP10, not GP26/GP27. Only
    # GP26-GP29 are ADC-capable, and those four are the pads with a diode to
    # the board's 3V3 rail; a clock driven into one while that board has no
    # host would power its rail through the pin. GP9/GP10 are consecutive
    # (one PIO "in" group) and sit next along the same edge.
    #
    # The ESP32 pins are chosen for the PCB layout. Along its front row,
    # west to east: input 1's audio (IO13), LRCK out (IO14), BCLK out
    # (IO26), input 1's UART (IO25, IO33), BCLK in (IO32), LRCK in (IO35).
    # The clocks' output pins face input 1 and their loop-back pins face
    # input 2, so the two links under the ESP32 nest instead of crossing,
    # and input 1's UART ends on the two pads between them. Input 2's audio
    # and UART pass through the gaps east of IO35 to the rear row. The I2S
    # and UART signals go through the GPIO matrix, so any of these pins can
    # carry them; IO35 is input-only, which a loop-back input may be. IO14
    # is a JTAG pin that some sources say emits PWM at boot; harmless on a
    # clock output nothing reads yet.
    "BCLK":  ["U3.IO26", "U3.IO32", "R1.1", "R2.1"],
    "BCLK1": ["R1.2", "U1.GP9"],
    "BCLK2": ["R2.2", "U2.GP9"],
    "LRCK":  ["U3.IO14", "U3.IO35", "R3.1", "R4.1"],
    "LRCK1": ["R3.2", "U1.GP10"],
    "LRCK2": ["R4.2", "U2.GP10"],
    # Both audio inputs are on pins with an internal pull-down, which
    # firmware must switch on: an input board with no host leaves its line
    # floating, and a floating line is noise in the mix.
    "AUD1":  ["U1.GP28", "U3.IO13"],
    "AUD2":  ["U2.GP28", "U3.IO18"],

    # UART, one pair per input board. Every net joins a TX to an RX.
    # Firmware must switch on the pull-ups on the ESP32's RX pins (IO33,
    # IO19): an input board with no host leaves its TX floating.
    "U1_TX":   ["U1.GP4", "U3.IO33"],
    "ESP_TX1": ["U3.IO25", "R5.1"],
    "U1_RX":   ["R5.2", "U1.GP5"],
    "U2_TX":   ["U2.GP4", "U3.IO19"],
    "ESP_TX2": ["U3.IO21", "R6.1"],
    "U2_RX":   ["R6.2", "U2.GP5"],

    # Breakout: PIO debug serial from each input board.
    "DBG1": ["U1.GP3", "J1.DBG1"],
    "DBG2": ["U2.GP3", "J2.DBG2"],
}

# Deliberately NOT connected, with the reason. Asserted by check_netlist.py.
NO_CONNECT = {
    "U1.3V3": "Each board has its own regulator. Never tie the 3V3 rails.",
    "U2.3V3": "Each board has its own regulator. Never tie the 3V3 rails.",
    "U3.IO36": "Erratum: pulled low ~80 ns when the SAR ADC powers up. Never a clock.",
    "U3.IO39": "Erratum: pulled low ~80 ns when the SAR ADC powers up. Never a clock.",
    "U3.IO34": "Battery-sense divider through R28 on the ESP32 board.",
    "U3.IO27": "Drives the ESP32 board's RGB LED through R1.",
    "U3.IO12": "Strapping pin (MTDI).",
    "U3.IO15": "Strapping pin.",
    "U3.IO0":  "Strapping pin and auto-download circuit.",
    "U3.IO2":  "Strapping pin.",
    "U3.IO5":  "Strapping pin.",
    "U3.TX0":  "Console UART to the CH343P. Keep free for logs and flashing.",
    "U3.RX0":  "Console UART to the CH343P. Keep free for logs and flashing.",
    "U3.SD0":  "Module flash.", "U3.SD1": "Module flash.",
    "U3.SD2":  "Module flash.", "U3.SD3": "Module flash.",
    "U3.CMD":  "Module flash.", "U3.CLK": "Module flash.",
}

# ESP32 pads with NO land on the carrier. The antenna end of the ESP32
# overhangs the carrier edge, which is Espressif's preferred arrangement, and
# these four sit on that overhang (AUDIT.md #6). None is needed: EN and IO23
# were unused, 3V3 is never connected, and GND has two other pads.
OFF_BOARD = {
    "U3.3V3": "On the antenna overhang.",
    "U3.EN":  "On the antenna overhang.",
    "U3.#20": "On the antenna overhang (a third GND; pads 14 and 26 remain).",
    "U3.IO23": "On the antenna overhang.",
}

# Spare pads: nothing wrong with them, this design just has no use for them.
# Listed so check_netlist.py can insist every floating pad is accounted for.
UNUSED = {f"{u}.{p}": "Spare GPIO"
          for u in ("U1", "U2")
          for p in ("GP0", "GP1", "GP2", "GP6", "GP7", "GP8")}
# The four ADC-capable pads. GP28 carries the audio out; these three stay
# free, which also leaves analogue inputs for a volume knob one day. GP29
# was a chain input with a pull-down; nothing reads it, so it needs neither.
UNUSED.update({f"{u}.{p}": "Spare GPIO, ADC-capable" for u in ("U1", "U2")
               for p in ("GP26", "GP27", "GP29")})
UNUSED.update({f"U3.{p}": "Spare GPIO" for p in ("IO22", "IO17", "IO16", "IO4")})

# Footprints. The two modules are generated by gen_fp.py into carrier.pretty/;
# everything else is a stock KiCad 7 library part. Axial parts use P7.62 since
# leads bend to suit.
_R = "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal"
_RV = "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical"
FOOTPRINTS = {
    "U1": "carrier:RP2350-USB-C",
    "U2": "carrier:RP2350-USB-C",
    "U3": "carrier:ESP32-DEV-KIT",
    "D1": "Diode_THT:D_DO-41_SOD81_P7.62mm_Horizontal",
    "D2": "Diode_THT:D_DO-41_SOD81_P7.62mm_Horizontal",
    "R10": _R, "R11": _R,
    # Standing: inline on a lane at the ESP32's own pin, where a lying
    # resistor's 7.62 mm would force the lane sideways.
    **{f"R{i}": _RV for i in range(1, 7)},
    "C1": "Capacitor_THT:CP_Radial_D5.0mm_P2.50mm",
    "J1": "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
    "J2": "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
    "TP1": "TestPoint:TestPoint_Pad_D1.5mm",
    "TP2": "TestPoint:TestPoint_Pad_D1.5mm",
}

# Pads to solder for MECHANICAL reasons only -- they carry no net. The owner
# solders the connected pads plus these; the rest of the land pattern stays
# bare. Each module's pad field has a corner here so it cannot peel from one
# end. Every one must be electrically floating on the carrier, which
# check_netlist.py asserts: several are the ESP32's flash and strapping pins
# and tying them anywhere would be actively harmful.
SOLDER_MECHANICAL = {
    # The 5V and GP9 pads hold the left edge's two corners and carry nets.
    "U1.GP0":  "corner beside the native port, right edge",
    "U1.GP8":  "far corner, right edge",
    "U2.GP0":  "corner beside the native port, right edge",
    "U2.GP8":  "far corner, right edge",
    "U3.IO36": "last pad on the carrier, antenna end of J3",
    "U3.IO22": "last pad on the carrier, antenna end of J4",
    "U3.CLK":  "corner, USB-C end of J4",
}

PASSIVE_PINS = {   # ref -> {pin name: pad number}
    "r":    {"1": 1, "2": 2},
    "c":    {"1": 1, "2": 2},
    "cpol": {"+": 1, "-": 2},
    # Pin 1 is the CATHODE. KiCad's diode footprints put the band and the "K"
    # on pad 1; this once said A=1, which reversed both Schottkys on the board
    # and would have left the rail unpowered (AUDIT.md #1).
    "d":    {"K": 1, "A": 2},
    "tp":   {"1": 1},
}


def pin_table():
    """ref -> {pin name: pad number} for every part."""
    out = {}
    for ref, p in PARTS.items():
        if p["kind"] == "module":
            t = {}
            for i, n in enumerate(p["left"]):
                t.setdefault(n, i + 1)
            for i, n in enumerate(p["right"]):
                t.setdefault(n, len(p["left"]) + i + 1)
            out[ref] = t
        elif p["kind"] == "hdr":
            out[ref] = {n: i + 1 for i, n in enumerate(p["pins"])}
        else:
            out[ref] = dict(PASSIVE_PINS[p["kind"]])
    return out


def pad_names():
    """ref -> {pad number: pin name}, lossless. pin_table() collapses repeated
    names (the ESP32 has three GND pads), so anything that must visit EVERY
    physical pad has to use this instead."""
    out = {}
    for ref, p in PARTS.items():
        if p["kind"] == "module":
            names = list(p["left"]) + list(p["right"])
        elif p["kind"] == "hdr":
            names = list(p["pins"])
        else:
            names = [n for n, _ in sorted(PASSIVE_PINS[p["kind"]].items(),
                                          key=lambda kv: kv[1])]
        out[ref] = {i + 1: n for i, n in enumerate(names)}
    return out


def resolve(node, table):
    """'U3.IO25' or 'U3.#20' -> (ref, pad number)."""
    ref, pin = node.split(".", 1)
    assert ref in PARTS, f"unknown part {ref} in {node}"
    if pin.startswith("#"):
        return ref, int(pin[1:])
    assert pin in table[ref], f"{ref} has no pin named {pin!r} ({node})"
    return ref, table[ref][pin]


def resolved_nets():
    """net name -> sorted list of (ref, pad number)."""
    t = pin_table()
    out = {}
    for net, nodes in NETS.items():
        seen = set()
        for n in nodes:
            rp = resolve(n, t)
            assert rp not in seen, f"{n} listed twice on net {net}"
            seen.add(rp)
        out[net] = sorted(seen)
    # no pad may appear on two nets
    owner = {}
    for net, nodes in out.items():
        for rp in nodes:
            assert rp not in owner, f"{rp} is on both {owner[rp]} and {net}"
            owner[rp] = net
    return out
