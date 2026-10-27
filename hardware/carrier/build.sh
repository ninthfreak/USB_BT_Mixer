#!/usr/bin/env bash
# Regenerate the whole carrier from netlist.py + enclosure/boards.scad, then
# verify it. Every step must pass; KiCad's own DRC (drc.py) is the gate.
#
# Everything runs under the SYSTEM python, which carries KiCad 7's pcbnew
# bindings. A python from /usr/local or a venv will not find pcbnew.
set -euo pipefail
cd "$(dirname "$0")"
PY=/usr/bin/python3
# Python keys its bytecode cache on mtime+size. Restoring a file to its
# original size within the same second can hand a check the OLD module and
# make it report on code that is no longer there. Seen in this project.
rm -rf __pycache__

$PY gen_fp.py
$PY gen_sch.py
$PY gen_table.py
$PY gen_pcb.py

$PY check_footprints.py
$PY check_netlist.py
$PY check_pcb.py
$PY drc.py --unrouted          # placement: courtyards, holes, silk, pad nets

$PY route.py                   # lays the committed route (carrier.ses);
                               # after a placement change: route.py --reroute
$PY drc.py                     # routed: everything, connectivity included
$PY check_routing.py

xvfb-run -a kicad-cli sch export pdf -o carrier.pdf carrier.kicad_sch >/dev/null
xvfb-run -a kicad-cli pcb export pdf --layers F.Cu,B.Cu,Edge.Cuts \
  --exclude-refdes --exclude-value -o carrier-pcb.pdf carrier.kicad_pcb >/dev/null
echo "carrier.pdf and carrier-pcb.pdf refreshed"
