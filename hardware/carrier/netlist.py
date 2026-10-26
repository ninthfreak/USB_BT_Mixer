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

    # 1k, not 33R. With one host connected the other input board is
    # unpowered, and the ESP32 keeps driving clocks into it; these limit the
    # current through its protection diodes to ~3 mA (AUDIT.md #3). At 2.8 MHz
    # into ~10 pF they still give ~22 ns edges against a 177 ns half-period.
    "R1": dict(kind="r", value="1k", desc="BCLK series to input 1; limits back-feed"),
    "R2": dict(kind="r", value="1k", desc="BCLK series to input 2; limits back-feed"),
    "R3": dict(kind="r", value="1k", desc="LRCK series to input 1; limits back-feed"),
    "R4": dict(kind="r", value="1k", desc="LRCK series to input 2; limits back-feed"),
    "R5": dict(kind="r", value="1k", desc="UART TX series to input 1; limits back-feed"),
    "R6": dict(kind="r", value="1k", desc="UART TX series to input 2; limits back-feed"),
    "R7": dict(kind="r", value="100k", desc="AUD1 pull-down: GPIO35 has no internal pull"),
    # 4.7k rather than a solder bridge: a bridge is a dead short if firmware
    # ever drives GP29 high. 4.7k holds it firmly low against the RP2350-E9
    # input leakage (up to ~120 uA, 0.56 V). Leave unfitted to free the pin.
    "R8": dict(kind="r", value="4k7", desc="Input 1 GP29 pull-down; omit to free the pin"),
    "R9": dict(kind="r", value="4k7", desc="Input 2 GP29 pull-down; omit to free the pin"),

    "C1": dict(kind="cpol", value="22uF", desc="Rail bulk, at the ESP32"),
    "C2": dict(kind="c", value="100nF", desc="Rail bypass, at the ESP32"),
    "C3": dict(kind="c", value="100nF", desc="Input 1 supply bypass"),
    "C4": dict(kind="c", value="100nF", desc="Input 2 supply bypass"),

    "J1": dict(kind="hdr", value="1x6", desc="Debug + spare GPIO breakout",
               pins=["GND", "DBG1", "DBG2", "SP1", "SP2", "SP3"]),
    "TP1": dict(kind="tp", value="RAIL", desc="Rail test point -- MEASURE here"),
    "TP2": dict(kind="tp", value="GND", desc="Ground test point"),
}

# ── Nets ─────────────────────────────────────────────────────────────────
# "REF.PINNAME", or "REF.#n" to pick a pad by number where the name repeats.
NETS = {
    # Power. Each input board's raw VBUS reaches the rail only through its
    # own diode, so the two hosts' 5 V supplies are never tied together.
    "VBUS1": ["U1.5V", "D1.A", "C3.1"],
    "VBUS2": ["U2.5V", "D2.A", "C4.1"],
    "RAIL":  ["D1.K", "D2.K", "U3.5V", "C1.+", "C2.1", "TP1.1"],
    # U3 pad 20 (a third GND) is off the board under the antenna overhang;
    # pads 14 and 26 carry the ESP32's ground.
    "GND":   ["U1.GND", "U2.GND", "U3.GND", "U3.#26",
              "C1.-", "C2.2", "C3.2", "C4.2", "R7.2", "R8.2", "R9.2",
              "J1.GND", "TP2.1"],

    # GP29 is the unused chain input, held low until something uses it.
    "GP29_1": ["U1.GP29", "R8.1"],
    "GP29_2": ["U2.GP29", "R9.1"],

    # I2S. The ESP32 is clock master on both; the loop-backs must tap the pin
    # DIRECTLY, on the ESP32 side of the series resistors. They use IO13 and
    # IO32, not IO36/IO39, which glitch low for ~80 ns whenever the SAR ADC
    # powers up -- reported as tracking A2DP streaming (AUDIT.md #4).
    "BCLK":  ["U3.IO25", "U3.IO13", "R1.1", "R2.1"],
    "BCLK1": ["R1.2", "U1.GP26"],
    "BCLK2": ["R2.2", "U2.GP26"],
    "LRCK":  ["U3.IO33", "U3.IO32", "R3.1", "R4.1"],
    "LRCK1": ["R3.2", "U1.GP27"],
    "LRCK2": ["R4.2", "U2.GP27"],
    "AUD1":  ["U1.GP28", "U3.IO35", "R7.1"],
    "AUD2":  ["U2.GP28", "U3.IO26"],

    # UART, one pair per input board. Every net joins a TX to an RX. The
    # ESP32's TX reaches each board through 1k for the same back-feed reason
    # as the clocks; the boards' TX lines drive the always-powered ESP32.
    "U1_TX":   ["U1.GP4", "U3.IO16"],
    "ESP_TX1": ["U3.IO17", "R5.1"],
    "U1_RX":   ["R5.2", "U1.GP5"],
    "U2_TX":   ["U2.GP4", "U3.IO18"],
    "ESP_TX2": ["U3.IO19", "R6.1"],
    "U2_RX":   ["R6.2", "U2.GP5"],

    # Breakout: PIO debug serial from each input board, three spare ESP32 pins.
    "DBG1": ["U1.GP3", "J1.DBG1"],
    "DBG2": ["U2.GP3", "J1.DBG2"],
    "SP1":  ["U3.IO4", "J1.SP1"],
    "SP2":  ["U3.IO21", "J1.SP2"],
    # IO14 is a JTAG pin and some sources say it emits PWM at boot; harmless
    # on a breakout pin, worth knowing before using it.
    "SP3":  ["U3.IO14", "J1.SP3"],
}

# Deliberately NOT connected, with the reason. Asserted by check_netlist.py.
NO_CONNECT = {
    "U1.3V3": "Each board has its own regulator. Never tie the 3V3 rails.",
    "U2.3V3": "Each board has its own regulator. Never tie the 3V3 rails.",
    "U3.IO36": "Erratum: pulled low ~80 ns when the SAR ADC powers up. Was the BCLK loop-back.",
    "U3.IO39": "Erratum: pulled low ~80 ns when the SAR ADC powers up. Was the LRCK loop-back.",
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
          for p in ("GP0", "GP1", "GP2", "GP6", "GP7", "GP8", "GP9", "GP10")}
UNUSED.update({"U3.IO22": "Spare GPIO"})

# Footprints. The two modules are generated by gen_fp.py into carrier.pretty/;
# everything else is a stock KiCad 7 library part. Axial parts use P7.62 since
# leads bend to suit; the disc caps use P5.08 because splaying a 2.54 mm part
# out is easy while squeezing a 5.08 mm one in is not.
_R = "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal"
_C = "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm"
FOOTPRINTS = {
    "U1": "carrier:RP2350-USB-C",
    "U2": "carrier:RP2350-USB-C",
    "U3": "carrier:ESP32-DEV-KIT",
    "D1": "Diode_THT:D_DO-41_SOD81_P7.62mm_Horizontal",
    "D2": "Diode_THT:D_DO-41_SOD81_P7.62mm_Horizontal",
    **{f"R{i}": _R for i in range(1, 10)},
    "C1": "Capacitor_THT:CP_Radial_D5.0mm_P2.50mm",
    "C2": _C, "C3": _C, "C4": _C,
    "J1": "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical",
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
    "U1.GP9":  "far corner, left column", "U1.GP0": "near corner, right column",
    "U1.GP8":  "far corner, right column",
    "U2.GP9":  "far corner, left column", "U2.GP0": "near corner, right column",
    "U2.GP8":  "far corner, right column",
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
