#!/usr/bin/env bash
# Collision checks for the two-port USB-C wall test coupon.
# Needs openscad and python3 + trimesh.
set -u
cd "$(dirname "$0")"
tmp=$(mktemp -d)
fail=0
vol() { python3 -c "import trimesh,sys; print(abs(trimesh.load(sys.argv[1]).volume))" "$1"; }

guards=([10]="outer shell solid" [11]="coupon solid" [12]="key solid" \
        [13]="inner shell solid" [14]="wall web between the two pockets" \
        [16]="staple solid" [17]="peg reaches into the notch" [18]="board has notches")
for w in 10 11 12 13 14 16 17 18; do
  if ! openscad -q -o "$tmp/$w.stl" -D "which=$w" fit_checks.scad 2>/dev/null || [ ! -s "$tmp/$w.stl" ]; then
    echo "GUARD $w (${guards[$w]}): EMPTY"; fail=1
  else echo "guard $w (${guards[$w]}): ok"; fi
done

names=([1]="coupon vs board A" [2]="coupon vs board A outer shell" [3]="coupon vs key A" \
       [4]="key A vs board A" [5]="key A vs board A inner shell" \
       [6]="coupon vs board A during install" [7]="coupon vs board B" \
       [8]="coupon vs board B outer shell" [9]="key A vs board B assembly" \
       [15]="coupon vs board A inner shell" [20]="staple A vs board A" \
       [21]="staple A vs board A outer shell" [22]="staple A vs key A" \
       [23]="staple A vs board B assembly")
for w in 1 2 3 4 5 6 7 8 9 15 20 21 22 23; do
  if openscad -q -o "$tmp/$w.stl" -D "which=$w" fit_checks.scad 2>/dev/null && [ -s "$tmp/$w.stl" ]; then
    v=$(vol "$tmp/$w.stl" 2>/dev/null)
    if python3 -c "import sys; sys.exit(0 if float('$v') < 1e-6 else 1)"; then
      echo "check $w (${names[$w]}): contact only"
    else echo "CHECK $w (${names[$w]}): OVERLAP ${v} mm3"; fail=1; fi
  else echo "check $w (${names[$w]}): clear"; fi
done
rm -rf "$tmp"
exit $fail
