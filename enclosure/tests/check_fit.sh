#!/usr/bin/env bash
# Collision checks for the two-port USB-C wall test coupon.
# Needs openscad and python3 + trimesh.
set -u
cd "$(dirname "$0")"
tmp=$(mktemp -d)
fail=0
vol() { python3 -c "import trimesh,sys; print(abs(trimesh.load(sys.argv[1]).volume))" "$1"; }

guards=([10]="outer shell solid" [11]="coupon solid" [13]="inner shell solid" \
        [14]="wall web between the two pockets" [17]="nub A reaches into the notch" \
        [18]="board has notches" [19]="nub B reaches into the notch")
for w in 10 11 13 14 17 18 19; do
  if ! openscad -q -o "$tmp/$w.stl" -D "which=$w" fit_checks.scad 2>/dev/null || [ ! -s "$tmp/$w.stl" ]; then
    echo "GUARD $w (${guards[$w]}): EMPTY"; fail=1
  else echo "guard $w (${guards[$w]}): ok"; fi
done

names=([1]="coupon vs board A" [2]="coupon vs board A outer shell" \
       [7]="coupon vs board B" [8]="coupon vs board B outer shell" \
       [15]="coupon vs board A inner shell" \
       [24]="board A drops straight in" [25]="board B drops straight in")
for w in 1 2 7 8 15 24 25; do
  if openscad -q -o "$tmp/$w.stl" -D "which=$w" fit_checks.scad 2>/dev/null && [ -s "$tmp/$w.stl" ]; then
    v=$(vol "$tmp/$w.stl" 2>/dev/null)
    if python3 -c "import sys; sys.exit(0 if float('$v') < 1e-6 else 1)"; then
      echo "check $w (${names[$w]}): contact only"
    else echo "CHECK $w (${names[$w]}): OVERLAP ${v} mm3"; fail=1; fi
  else echo "check $w (${names[$w]}): clear"; fi
done
rm -rf "$tmp"
exit $fail
