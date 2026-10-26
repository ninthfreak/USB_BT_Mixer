#!/usr/bin/env bash
# Regenerate the whole carrier from netlist.py + enclosure/boards.scad, then
# verify it. Order matters: check_pads_vs_kicad runs on the UNROUTED board,
# where every pad is its own copper blob and the comparison is strongest.
# Once traces are down, pads merge into larger blobs and the check weakens to
# "copper exists here" rather than "the centroid is here".
set -euo pipefail
cd "$(dirname "$0")"
# Python keys its bytecode cache on mtime+size. Restoring a file to its
# original size within the same second can hand a check the OLD module and
# make it report on code that is no longer there. Seen in this project.
rm -rf __pycache__

python3 gen_fp.py
python3 gen_sch.py
python3 gen_table.py
python3 gen_pcb.py

python3 check_footprints.py
python3 check_netlist.py
python3 check_pcb.py
python3 check_pads_vs_kicad.py      # unrouted: strongest form

python3 route.py
python3 check_clearance.py
python3 check_routing.py

xvfb-run -a kicad-cli sch export pdf -o carrier.pdf carrier.kicad_sch >/dev/null
xvfb-run -a kicad-cli pcb export pdf --layers F.Cu,B.Cu,Edge.Cuts \
  --exclude-refdes --exclude-value -o carrier-pcb.pdf carrier.kicad_pcb >/dev/null
echo "carrier.pdf and carrier-pcb.pdf refreshed"
