#!/usr/bin/env bash
# Regenerate everything from netlist.py + enclosure/boards.scad, then verify.
set -euo pipefail
cd "$(dirname "$0")"
python3 gen_fp.py
python3 gen_sch.py
python3 gen_table.py
python3 gen_pcb.py
python3 check_footprints.py
python3 check_netlist.py
python3 check_pcb.py
python3 check_routing.py
xvfb-run -a kicad-cli sch export pdf -o carrier.pdf carrier.kicad_sch >/dev/null
echo "carrier.pdf refreshed"
