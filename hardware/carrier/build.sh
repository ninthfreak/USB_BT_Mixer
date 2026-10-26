#!/usr/bin/env bash
# Regenerate everything from netlist.py and verify the result.
set -euo pipefail
cd "$(dirname "$0")"
python3 gen_sch.py
python3 gen_table.py
python3 check_netlist.py
xvfb-run -a kicad-cli sch export pdf -o carrier.pdf carrier.kicad_sch >/dev/null
echo "carrier.pdf refreshed"
