# Carrier board connections

Generated from `netlist.py` by `gen_table.py`. Do not edit by hand.

`check_netlist.py` reads the netlist back out of `carrier.kicad_sch`
and proves it matches the same source, so this table and the schematic
cannot disagree.

**23 nets, 67 pads, 18 parts.**

## Power

| Net | Connects |
|---|---|
| **VBUS1** | `C3.1`, `D1.A`, `U1.5V` |
| **VBUS2** | `C4.1`, `D2.A`, `U2.5V` |
| **RAIL** | `C1.+`, `C2.1`, `D1.K`, `D2.K`, `TP1.1`, `U3.5V` |
| **GND** | `C1.-`, `C2.2`, `C3.2`, `C4.2`, `J1.GND`, `SJ1.2`, `SJ2.2`, `TP2.1`, `U1.GND`, `U2.GND`, `U3.GND #14`, `U3.GND #20`, `U3.GND #26` |

## Chain input, grounded through a cuttable bridge

| Net | Connects |
|---|---|
| **GP29_1** | `SJ1.1`, `U1.GP29` |
| **GP29_2** | `SJ2.1`, `U2.GP29` |

## I2S clocks (ESP32 is master)

| Net | Connects |
|---|---|
| **BCLK** | `R1.1`, `R2.1`, `U3.IO36`, `U3.IO25` |
| **BCLK1** | `R1.2`, `U1.GP26` |
| **BCLK2** | `R2.2`, `U2.GP26` |
| **LRCK** | `R3.1`, `R4.1`, `U3.IO39`, `U3.IO33` |
| **LRCK1** | `R3.2`, `U1.GP27` |
| **LRCK2** | `R4.2`, `U2.GP27` |

## I2S audio (returns to the ESP32)

| Net | Connects |
|---|---|
| **AUD1** | `U1.GP28`, `U3.IO35` |
| **AUD2** | `U2.GP28`, `U3.IO26` |

## UART, one pair per input board

| Net | Connects |
|---|---|
| **U1_TX** | `U1.GP4`, `U3.IO16` |
| **U1_RX** | `U1.GP5`, `U3.IO17` |
| **U2_TX** | `U2.GP4`, `U3.IO18` |
| **U2_RX** | `U2.GP5`, `U3.IO19` |

## Breakout header

| Net | Connects |
|---|---|
| **DBG1** | `J1.DBG1`, `U1.GP3` |
| **DBG2** | `J1.DBG2`, `U2.GP3` |
| **SP1** | `J1.SP1`, `U3.IO32` |
| **SP2** | `J1.SP2`, `U3.IO21` |
| **SP3** | `J1.SP3`, `U3.IO22` |

## Parts

| Ref | Value | Purpose |
|---|---|---|
| U1 | RP2350-USB-C | Input 1 |
| U2 | RP2350-USB-C | Input 2 |
| U3 | ESP32-DEV-KIT | Mixer / Bluetooth |
| D1 | 1N5817 | Input 1 supply isolation |
| D2 | 1N5817 | Input 2 supply isolation |
| R1 | 33R | BCLK series, to input 1 |
| R2 | 33R | BCLK series, to input 2 |
| R3 | 33R | LRCK series, to input 1 |
| R4 | 33R | LRCK series, to input 2 |
| C1 | 22uF | Rail bulk, at the ESP32 |
| C2 | 100nF | Rail bypass, at the ESP32 |
| C3 | 100nF | Input 1 supply bypass |
| C4 | 100nF | Input 2 supply bypass |
| J1 | 1x6 | Debug + spare GPIO breakout |
| TP1 | RAIL | Rail test point -- MEASURE here |
| TP2 | GND | Ground test point |
| SJ1 | closed | Input 1 GP29 to GND, cut to free |
| SJ2 | closed | Input 2 GP29 to GND, cut to free |

## Deliberately not connected

| Pin | Why |
|---|---|
| `U1.3V3` | Each board has its own regulator. Never tie the 3V3 rails. |
| `U2.3V3` | Each board has its own regulator. Never tie the 3V3 rails. |
| `U3.3V3` | ESP32 regulator output. Nothing on this board runs from it. |
| `U3.IO34` | Battery-sense divider through R28 on the ESP32 board. |
| `U3.IO27` | Drives the ESP32 board's RGB LED through R1. |
| `U3.IO12` | Strapping pin (MTDI). |
| `U3.IO15` | Strapping pin. |
| `U3.IO0` | Strapping pin and auto-download circuit. |
| `U3.IO2` | Strapping pin. |
| `U3.IO5` | Strapping pin. |
| `U3.TX0` | Console UART to the CH343P. Keep free for logs and flashing. |
| `U3.RX0` | Console UART to the CH343P. Keep free for logs and flashing. |
| `U3.EN` | Chip enable, pulled up on the ESP32 board. Leave it alone. |
| `U3.SD0` | Module flash. |
| `U3.SD1` | Module flash. |
| `U3.SD2` | Module flash. |
| `U3.SD3` | Module flash. |
| `U3.CMD` | Module flash. |
| `U3.CLK` | Module flash. |

Spare pads, free for later use: `U1.GP0`, `U1.GP1`, `U1.GP2`, `U1.GP6`, `U1.GP7`, `U1.GP8`, `U1.GP9`, `U1.GP10`, `U2.GP0`, `U2.GP1`, `U2.GP2`, `U2.GP6`, `U2.GP7`, `U2.GP8`, `U2.GP9`, `U2.GP10`, `U3.IO14`, `U3.IO13`, `U3.IO23`, `U3.IO4`.
