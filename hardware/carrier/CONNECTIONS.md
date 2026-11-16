# Carrier board connections

Generated from `netlist.py` by `gen_table.py`. Do not edit by hand.

`check_netlist.py` reads the netlist back out of `carrier.kicad_sch`
and proves it matches the same source, so this table and the schematic
cannot disagree.

**20 nets, 57 pads, 18 parts.**

## Power

| Net | Connects |
|---|---|
| **VBUS1** | `D1.A`, `R10.1`, `U1.5V` |
| **VBUS2** | `D2.A`, `R11.1`, `U2.5V` |
| **RAIL** | `C1.+`, `D1.K`, `D2.K`, `TP1.1`, `U3.5V` |
| **GND** | `C1.-`, `J1.GND`, `J2.GND`, `R10.2`, `R11.2`, `TP2.1`, `U1.GND`, `U2.GND`, `U3.GND #14`, `U3.GND #26` |

## I2S clocks (ESP32 is master)

| Net | Connects |
|---|---|
| **BCLK** | `R1.1`, `R2.1`, `U3.IO32`, `U3.IO26` |
| **BCLK1** | `R1.2`, `U1.GP9` |
| **BCLK2** | `R2.2`, `U2.GP9` |
| **LRCK** | `R3.1`, `R4.1`, `U3.IO35`, `U3.IO14` |
| **LRCK1** | `R3.2`, `U1.GP10` |
| **LRCK2** | `R4.2`, `U2.GP10` |

## I2S audio (returns to the ESP32)

| Net | Connects |
|---|---|
| **AUD1** | `U1.GP28`, `U3.IO13` |
| **AUD2** | `U2.GP28`, `U3.IO18` |

## UART, one pair per input board

| Net | Connects |
|---|---|
| **U1_TX** | `U1.GP4`, `U3.IO33` |
| **ESP_TX1** | `R5.1`, `U3.IO25` |
| **U1_RX** | `R5.2`, `U1.GP5` |
| **U2_TX** | `U2.GP4`, `U3.IO19` |
| **ESP_TX2** | `R6.1`, `U3.IO21` |
| **U2_RX** | `R6.2`, `U2.GP5` |

## Debug header

| Net | Connects |
|---|---|
| **DBG1** | `J1.DBG1`, `U1.GP3` |
| **DBG2** | `J2.DBG2`, `U2.GP3` |

## Parts

| Ref | Value | Purpose |
|---|---|---|
| U1 | RP2350-USB-C | Input 1 |
| U2 | RP2350-USB-C | Input 2 |
| U3 | ESP32-DEV-KIT | Mixer / Bluetooth |
| D1 | 1N5817 | Input 1 supply isolation |
| D2 | 1N5817 | Input 2 supply isolation |
| R1 | 1k | BCLK series to input 1 |
| R2 | 1k | BCLK series to input 2 |
| R3 | 1k | LRCK series to input 1 |
| R4 | 1k | LRCK series to input 2 |
| R5 | 1k | UART TX series to input 1 |
| R6 | 1k | UART TX series to input 2 |
| R10 | 1k | Input 1 VBUS bleed: holds it at 0 V with no host |
| R11 | 1k | Input 2 VBUS bleed: holds it at 0 V with no host |
| C1 | 22uF | Rail bulk, at the ESP32 |
| J1 | 1x2 | Input 1 debug serial (optional) |
| J2 | 1x2 | Input 2 debug serial (optional) |
| TP1 | RAIL | Rail test point -- MEASURE here |
| TP2 | GND | Ground test point |
## What to solder

Only the pads that carry a net, plus a few corners so a module
cannot peel from one end. Everything else is left bare: the land
pattern is there if you ever want it.

Each input board's first pads (5V and GP0) are 2.9 mm from its
native USB-C shell, so those joints see some of a cable's leverage.
Solder is still the wrong thing to hold a plug: the enclosure must
bear on the modules near the port.

`carrier-fit-check.pdf` shows the same map at 1:1.

### U1 (RP2350-USB-C) — solder 10 of 18 lands

| | Pads |
|---|---|
| **Net** | `1 5V`, `2 GND`, `5 GP28`, `8 GP10`, `9 GP9`, `13 GP3`, `14 GP4`, `15 GP5` |
| **Mechanical** | `10 GP0`, `18 GP8` |
| Leave bare | 3 3V3, 4 GP29, 6 GP27, 7 GP26, 11 GP1, 12 GP2, 16 GP6, 17 GP7 |

### U2 (RP2350-USB-C) — solder 10 of 18 lands

| | Pads |
|---|---|
| **Net** | `1 5V`, `2 GND`, `5 GP28`, `8 GP10`, `9 GP9`, `13 GP3`, `14 GP4`, `15 GP5` |
| **Mechanical** | `10 GP0`, `18 GP8` |
| Leave bare | 3 3V3, 4 GP29, 6 GP27, 7 GP26, 11 GP1, 12 GP2, 16 GP6, 17 GP7 |

### U3 (ESP32-DEV-KIT) — solder 16 of 34 lands

| | Pads |
|---|---|
| **Net** | `6 IO35`, `7 IO32`, `8 IO33`, `9 IO25`, `10 IO26`, `12 IO14`, `14 GND`, `15 IO13`, `19 5V`, `25 IO21`, `26 GND`, `27 IO19`, `28 IO18` |
| **Mechanical** | `3 IO36`, `22 IO22`, `38 CLK` |
| Leave bare | 4 IO39, 5 IO34, 11 IO27, 13 IO12, 16 SD2, 17 SD3, 18 CMD, 23 TX0, 24 RX0, 29 IO5, 30 IO17, 31 IO16, 32 IO4, 33 IO0, 34 IO2, 35 IO15, 36 SD1, 37 SD0 |
| No land (antenna overhang) | 1 3V3, 2 EN, 20 GND, 21 IO23 |

**36 joints instead of 70.**


## Deliberately not connected

| Pin | Why |
|---|---|
| `U1.3V3` | Each board has its own regulator. Never tie the 3V3 rails. |
| `U2.3V3` | Each board has its own regulator. Never tie the 3V3 rails. |
| `U3.IO36` | Erratum: pulled low ~80 ns when the SAR ADC powers up. Never a clock. |
| `U3.IO39` | Erratum: pulled low ~80 ns when the SAR ADC powers up. Never a clock. |
| `U3.IO34` | Battery-sense divider through R28 on the ESP32 board. |
| `U3.IO27` | Drives the ESP32 board's RGB LED through R1. |
| `U3.IO12` | Strapping pin (MTDI). |
| `U3.IO15` | Strapping pin. |
| `U3.IO0` | Strapping pin and auto-download circuit. |
| `U3.IO2` | Strapping pin. |
| `U3.IO5` | Strapping pin. |
| `U3.TX0` | Console UART to the CH343P. Keep free for logs and flashing. |
| `U3.RX0` | Console UART to the CH343P. Keep free for logs and flashing. |
| `U3.SD0` | Module flash. |
| `U3.SD1` | Module flash. |
| `U3.SD2` | Module flash. |
| `U3.SD3` | Module flash. |
| `U3.CMD` | Module flash. |
| `U3.CLK` | Module flash. |

Spare pads, free for later use: `U1.GP0`, `U1.GP1`, `U1.GP2`, `U1.GP6`, `U1.GP7`, `U1.GP8`, `U2.GP0`, `U2.GP1`, `U2.GP2`, `U2.GP6`, `U2.GP7`, `U2.GP8`, `U1.GP26`, `U1.GP27`, `U1.GP29`, `U2.GP26`, `U2.GP27`, `U2.GP29`, `U3.IO22`, `U3.IO17`, `U3.IO16`, `U3.IO4`.
