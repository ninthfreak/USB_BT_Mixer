#!/usr/bin/env bash
# Collision checks for the USB-C wall test coupon. Needs openscad and python3 + trimesh.
set -u
cd "$(dirname "$0")"
tmp=$(mktemp -d)
fail=0
vol() { python3 -c "import trimesh,sys; print(abs(trimesh.load(sys.argv[1]).volume))" "$1"; }
for w in 10 11 12; do
  if ! openscad -q -o "$tmp/$w.stl" -D "which=$w" fit_checks.scad 2>/dev/null || [ ! -s "$tmp/$w.stl" ]; then
    echo "GUARD $w: EMPTY (test solid missing)"; fail=1
  else echo "guard $w: ok"; fi
done
names=([1]="coupon vs board" [2]="coupon vs USB shell" [3]="coupon vs key" [4]="key vs board" [5]="key vs STEMMA connector" [6]="coupon vs board during install")
for w in 1 2 3 4 5 6; do
  if openscad -q -o "$tmp/$w.stl" -D "which=$w" fit_checks.scad 2>/dev/null && [ -s "$tmp/$w.stl" ]; then
    v=$(vol "$tmp/$w.stl" 2>/dev/null)
    if python3 -c "import sys; sys.exit(0 if float('$v') < 1e-6 else 1)"; then echo "check $w (${names[$w]}): contact only"
    else echo "CHECK $w (${names[$w]}): OVERLAP ${v} mm3"; fail=1; fi
  else echo "check $w (${names[$w]}): clear"; fi
done
rm -rf "$tmp"
exit $fail
