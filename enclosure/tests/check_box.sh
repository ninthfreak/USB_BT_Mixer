#!/usr/bin/env bash
# Collision checks for the full enclosure (base + lid).
# Needs openscad and python3 + trimesh.
set -u
cd "$(dirname "$0")"
tmp=$(mktemp -d)
fail=0
vol() { python3 -c "import trimesh,sys; print(abs(trimesh.load(sys.argv[1]).volume))" "$1"; }

guards=([1]="base solid" [2]="lid solid" [3]="nub in board A's left notch" \
        [4]="lid presses on board A" [5]="ESP32 part envelope solid" \
        [6]="pad zone solid" [7]="lid presses on board B" \
        [8]="nub in board A's right notch" [9]="nub in board B's left notch")
for w in 1 2 3 4 5 6 7 8 9; do
  if ! openscad -q -o "$tmp/g$w.stl" -D "which=$w" box_checks.scad 2>/dev/null || [ ! -s "$tmp/g$w.stl" ]; then
    echo "GUARD $w (${guards[$w]}): EMPTY"; fail=1
  else echo "guard $w (${guards[$w]}): ok"; fi
done

names=([10]="base vs board A" [11]="base vs board B" \
       [12]="base vs board A outer shell" [13]="base vs board A inner shell" \
       [14]="base vs board B outer shell" \
       [15]="base vs ESP32 PCB" [16]="base vs ESP32 parts" \
       [17]="board A drops straight in" [18]="board B drops straight in" \
       [19]="lid vs board A" [20]="lid vs board B" \
       [21]="lid vs board A outer shell" [22]="lid vs board A inner shell" \
       [23]="lid vs board B outer shell" [24]="lid vs board B inner shell" \
       [25]="lid vs ESP32 parts" [26]="lid vs base" \
       [27]="lid vs board A pad zone" [28]="lid vs board B pad zone")
for w in 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28; do
  if openscad -q -o "$tmp/$w.stl" -D "which=$w" box_checks.scad 2>/dev/null && [ -s "$tmp/$w.stl" ]; then
    v=$(vol "$tmp/$w.stl" 2>/dev/null)
    if python3 -c "import sys; sys.exit(0 if float('$v') < 1e-6 else 1)"; then
      echo "check $w (${names[$w]}): contact only"
    else echo "CHECK $w (${names[$w]}): OVERLAP ${v} mm3"; fail=1; fi
  else echo "check $w (${names[$w]}): clear"; fi
done
rm -rf "$tmp"
exit $fail
