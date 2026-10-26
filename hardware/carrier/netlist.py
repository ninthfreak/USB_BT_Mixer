"""Single source of truth for the carrier board's connections.

Everything downstream is generated from this file: the KiCad schematic, the
human-readable connection table, and the check that the two agree. Nothing
here is copied from another file -- hardware/wiring.md is prose ABOUT this,
and check_netlist.py verifies the generated schematic matches.

Pin numbering (ours, since we draw both symbol and footprint):

  RP2350-USB-C (U1, U2), 18 pads, looking at the component side with the
  PROGRAMMING port (the proud one) at the top:
      1..9   left edge, top to bottom:  5V GND 3V3 GP29 GP28 GP27 GP26 GP10 GP9
      10..18 right edge, top to bottom: GP0 GP1 GP2 GP3 GP4 GP5 GP6 GP7 GP8

  ESP32-DEV-KIT (U3), 38 pads:
      1..19  header J3
      20..38 header J4  (so J4 pin n == our pin 19 + n)
"""

# ── Module pin maps ──────────────────────────────────────────────────────
RP_LEFT  = ["5V", "GND", "3V3", "GP29", "GP28", "GP27", "GP26", "GP10", "GP9"]
RP_RIGHT = ["GP0", "GP1", "GP2", "GP3", "GP4", "GP5", "GP6", "GP7", "GP8"]

ESP_J3 = ["3V3", "EN", "IO36", "IO39", "IO34", "IO35", "IO32", "IO33", "IO25",
          "IO26", "IO27", "IO14", "IO12", "GND", "IO13", "SD2", "SD3", "CMD", "5V"]
ESP_J4 = ["GND", "IO23", "IO22", "TX0", "RX0", "IO21", "GND", "IO19", "IO18",
          "IO5", "IO17", "IO16", "IO4", "IO0", "IO2", "IO15", "SD1", "SD0", "CLK"]

# ── Parts ────────────────────────────────────────────────────────────────
# kind: "module" | "r" | "c" | "cpol" | "d" | "hdr" | "tp" | "sj"
PARTS = {
    "U1": dict(kind="module", value="RP2350-USB-C", desc="Input 1",
               left=RP_LEFT, right=RP_RIGHT),
    "U2": dict(kind="module", value="RP2350-USB-C", desc="Input 2",
               left=RP_LEFT, right=RP_RIGHT),
    "U3": dict(kind="module", value="ESP32-DEV-KIT", desc="Mixer / Bluetooth",
               left=ESP_J3, right=ESP_J4),

    "D1": dict(kind="d", value="1N5817", desc="Input 1 supply isolation"),
    "D2": dict(kind="d", value="1N5817", desc="Input 2 supply isolation"),

    "R1": dict(kind="r", value="33R", desc="BCLK series, to input 1"),
    "R2": dict(kind="r", value="33R", desc="BCLK series, to input 2"),
    "R3": dict(kind="r", value="33R", desc="LRCK series, to input 1"),
    "R4": dict(kind="r", value="33R", desc="LRCK series, to input 2"),

    "C1": dict(kind="cpol", value="22uF", desc="Rail bulk, at the ESP32"),
    "C2": dict(kind="c", value="100nF", desc="Rail bypass, at the ESP32"),
    "C3": dict(kind="c", value="100nF", desc="Input 1 supply bypass"),
    "C4": dict(kind="c", value="100nF", desc="Input 2 supply bypass"),

    "J1": dict(kind="hdr", value="1x6", desc="Debug + spare GPIO breakout",
               pins=["GND", "DBG1", "DBG2", "SP1", "SP2", "SP3"]),
    "TP1": dict(kind="tp", value="RAIL", desc="Rail test point -- MEASURE here"),
    "TP2": dict(kind="tp", value="GND", desc="Ground test point"),
    "SJ1": dict(kind="sj", value="closed", desc="Input 1 GP29 to GND, cut to free"),
    "SJ2": dict(kind="sj", value="closed", desc="Input 2 GP29 to GND, cut to free"),
}

# ── Nets ─────────────────────────────────────────────────────────────────
# "REF.PINNAME", or "REF.#n" to pick a pad by number where the name repeats.
NETS = {
    # Power. Each input board's raw VBUS reaches the rail only through its
    # own diode, so the two hosts' 5 V supplies are never tied together.
    "VBUS1": ["U1.5V", "D1.A", "C3.1"],
    "VBUS2": ["U2.5V", "D2.A", "C4.1"],
    "RAIL":  ["D1.K", "D2.K", "U3.5V", "C1.+", "C2.1", "TP1.1"],
    "GND":   ["U1.GND", "U2.GND", "U3.GND", "U3.#20", "U3.#26",
              "C1.-", "C2.2", "C3.2", "C4.2",
              "SJ1.2", "SJ2.2", "J1.GND", "TP2.1"],

    # GP29 is the unused chain input. Grounded through a solder bridge so a
    # second input board or an ADC can take it later without cutting a trace.
    "GP29_1": ["U1.GP29", "SJ1.1"],
    "GP29_2": ["U2.GP29", "SJ2.1"],

    # I2S. The ESP32 is clock master on both; the loop-backs must tap the pin
    # DIRECTLY, on the ESP32 side of the series resistors.
    "BCLK":  ["U3.IO25", "U3.IO36", "R1.1", "R2.1"],
    "BCLK1": ["R1.2", "U1.GP26"],
    "BCLK2": ["R2.2", "U2.GP26"],
    "LRCK":  ["U3.IO33", "U3.IO39", "R3.1", "R4.1"],
    "LRCK1": ["R3.2", "U1.GP27"],
    "LRCK2": ["R4.2", "U2.GP27"],
    "AUD1":  ["U1.GP28", "U3.IO35"],
    "AUD2":  ["U2.GP28", "U3.IO26"],

    # UART, one pair per input board. Every net joins a TX to an RX.
    "U1_TX": ["U1.GP4", "U3.IO16"],
    "U1_RX": ["U1.GP5", "U3.IO17"],
    "U2_TX": ["U2.GP4", "U3.IO18"],
    "U2_RX": ["U2.GP5", "U3.IO19"],

    # Breakout: PIO debug serial from each input board, three spare ESP32 pins.
    "DBG1": ["U1.GP3", "J1.DBG1"],
    "DBG2": ["U2.GP3", "J1.DBG2"],
    "SP1":  ["U3.IO32", "J1.SP1"],
    "SP2":  ["U3.IO21", "J1.SP2"],
    "SP3":  ["U3.IO22", "J1.SP3"],
}

# Deliberately NOT connected, with the reason. Asserted by check_netlist.py.
NO_CONNECT = {
    "U1.3V3": "Each board has its own regulator. Never tie the 3V3 rails.",
    "U2.3V3": "Each board has its own regulator. Never tie the 3V3 rails.",
    "U3.3V3": "ESP32 regulator output. Nothing on this board runs from it.",
    "U3.IO34": "Battery-sense divider through R28 on the ESP32 board.",
    "U3.IO27": "Drives the ESP32 board's RGB LED through R1.",
    "U3.IO12": "Strapping pin (MTDI).",
    "U3.IO15": "Strapping pin.",
    "U3.IO0":  "Strapping pin and auto-download circuit.",
    "U3.IO2":  "Strapping pin.",
    "U3.IO5":  "Strapping pin.",
    "U3.TX0":  "Console UART to the CH343P. Keep free for logs and flashing.",
    "U3.RX0":  "Console UART to the CH343P. Keep free for logs and flashing.",
    "U3.EN":   "Chip enable, pulled up on the ESP32 board. Leave it alone.",
    "U3.SD0":  "Module flash.", "U3.SD1": "Module flash.",
    "U3.SD2":  "Module flash.", "U3.SD3": "Module flash.",
    "U3.CMD":  "Module flash.", "U3.CLK": "Module flash.",
}

# Spare pads: nothing wrong with them, this design just has no use for them.
# Listed so check_netlist.py can insist every floating pad is accounted for.
UNUSED = {f"{u}.{p}": "Spare GPIO"
          for u in ("U1", "U2")
          for p in ("GP0", "GP1", "GP2", "GP6", "GP7", "GP8", "GP9", "GP10")}
UNUSED.update({
    "U3.IO14": "Spare GPIO", "U3.IO13": "Spare GPIO",
    "U3.IO23": "Spare GPIO", "U3.IO4":  "Spare GPIO",
})

# Footprints. The two modules are generated by gen_fp.py into carrier.pretty/;
# everything else is a stock KiCad 7 library part. Axial parts use P7.62 since
# leads bend to suit; the disc caps use P5.08 because splaying a 2.54 mm part
# out is easy while squeezing a 5.08 mm one in is not.
FOOTPRINTS = {
    "U1": "carrier:RP2350-USB-C",
    "U2": "carrier:RP2350-USB-C",
    "U3": "carrier:ESP32-DEV-KIT",
    "D1": "Diode_THT:D_DO-41_SOD81_P7.62mm_Horizontal",
    "D2": "Diode_THT:D_DO-41_SOD81_P7.62mm_Horizontal",
    "R1": "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
    "R2": "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
    "R3": "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
    "R4": "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
    "C1": "Capacitor_THT:CP_Radial_D5.0mm_P2.50mm",
    "C2": "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm",
    "C3": "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm",
    "C4": "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm",
    "J1": "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical",
    "TP1": "TestPoint:TestPoint_Pad_D1.5mm",
    "TP2": "TestPoint:TestPoint_Pad_D1.5mm",
    # Bridged, not Open: GP29 is grounded by default and the bridge is CUT to
    # free the pin for a third input or an ADC.
    "SJ1": "Jumper:SolderJumper-2_P1.3mm_Bridged_Pad1.0x1.5mm",
    "SJ2": "Jumper:SolderJumper-2_P1.3mm_Bridged_Pad1.0x1.5mm",
}

PASSIVE_PINS = {   # ref -> {pin name: pad number}
    "r":    {"1": 1, "2": 2},
    "c":    {"1": 1, "2": 2},
    "cpol": {"+": 1, "-": 2},
    "d":    {"A": 1, "K": 2},
    "tp":   {"1": 1},
    "sj":   {"1": 1, "2": 2},
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
