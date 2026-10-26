#!/usr/bin/env bash
# Regenerate everything from netlist.py + enclosure/boards.scad, then verify.
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
python3 check_routing.py
python3 check_pads_vs_kicad.py
xvfb-run -a kicad-cli sch export pdf -o carrier.pdf carrier.kicad_sch >/dev/null
echo "carrier.pdf refreshed"
