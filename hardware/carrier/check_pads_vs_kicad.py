#!/usr/bin/env python3
"""Verify our pad positions against KiCad's own rendering of the board.

check_pcb.py deliberately reuses gen_pcb's geometry so the generator and the
check cannot drift apart. The cost is that a bug in the SHARED code is
invisible to both -- which is exactly what happened: the 90-degree rotation
transform was wrong, five parts were up to 7.6 mm out of place, and every
check agreed with the generator.

This closes that hole by letting KiCad do the transform. It exports F.Cu to
SVG, reads the centroid of every filled pad shape, and matches them against
the positions we compute. KiCad's answer is the authority.
"""
import pathlib, re, subprocess, sys, tempfile
import numpy as np
import netlist as N
import gen_pcb as G

HERE = pathlib.Path(__file__).resolve().parent
TOL = 0.15          # mm; one 400-dpi pixel is 0.064 mm

def kicad_pads():
    """Centroid of every copper blob KiCad renders on F.Cu, in board mm.

    Parsing the SVG was a mistake: path data carries arc radii and flags that
    are not coordinates, so averaging them gives nonsense. Rasterising cannot
    be misparsed -- KiCad decides where the copper goes, we only measure it.
    Edge.Cuts is rendered too and self-calibrates the pixel-to-mm mapping, so
    no assumption about page size or margins enters.
    """
    tmp = pathlib.Path(tempfile.mkdtemp())
    pdf = tmp / "f.pdf"
    r = subprocess.run(["xvfb-run", "-a", "kicad-cli", "pcb", "export", "pdf",
                        "--layers", "F.Cu,Edge.Cuts", "--black-and-white",
                        "--exclude-refdes", "--exclude-value",
                        "--drill-shape-opt", "0",
                        "-o", str(pdf), str(HERE / "carrier.kicad_pcb")],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"kicad-cli failed:\n{r.stdout}\n{r.stderr}")
    subprocess.run(["pdftoppm", "-r", "400", "-gray", "-singlefile",
                    str(pdf), str(tmp / "f")], check=True)
    img = _pgm(tmp / "f.pgm")
    blobs = _components(img < 128)
    if not blobs:
        sys.exit("nothing rendered")
    # the board outline is the blob with the largest bounding box
    outline = max(blobs, key=lambda b: (b[3] - b[1]) * (b[4] - b[2]))
    _, ox0, oy0, ox1, oy1, _ = outline
    sx, sy = G.W / (ox1 - ox0), G.H / (oy1 - oy0)
    if abs(sx - sy) > 0.002:
        sys.exit(f"non-uniform scale {sx:.5f} vs {sy:.5f}")
    pads = [((b[0][0] - ox0) * sx, (b[0][1] - oy0) * sy,
             (b[1] - ox0) * sx, (b[2] - oy0) * sy,
             (b[3] - ox0) * sx, (b[4] - oy0) * sy)
            for b in blobs if b is not outline]
    return pads, sx

def _pgm(path):
    raw = path.read_bytes()
    assert raw[:2] == b"P5", raw[:2]
    tok, i = [], 2
    while len(tok) < 3:
        while raw[i:i+1].isspace(): i += 1
        if raw[i:i+1] == b"#":
            while raw[i:i+1] != b"\n": i += 1
            continue
        j = i
        while not raw[j:j+1].isspace(): j += 1
        tok.append(int(raw[i:j])); i = j
    i += 1
    w, h, _ = tok
    return np.frombuffer(raw[i:i+w*h], dtype=np.uint8).reshape(h, w)

def _components(mask):
    """(centroid, x0, y0, x1, y1, n) for each 4-connected True region."""
    h, w = mask.shape
    seen = np.zeros_like(mask)
    out = []
    ys, xs = np.nonzero(mask)
    for sy, sx in zip(ys, xs):
        if seen[sy, sx]:
            continue
        stack = [(sy, sx)]; seen[sy, sx] = True
        px = py = n = 0
        x0 = x1 = sx; y0 = y1 = sy
        while stack:
            y, x = stack.pop()
            px += x; py += y; n += 1
            x0, x1 = min(x0, x), max(x1, x)
            y0, y1 = min(y0, y), max(y1, y)
            for dy, dx in ((1,0),(-1,0),(0,1),(0,-1)):
                a, b = y+dy, x+dx
                if 0 <= a < h and 0 <= b < w and mask[a,b] and not seen[a,b]:
                    seen[a,b] = True; stack.append((a,b))
        if n >= 30:
            out.append(((px/n, py/n), x0, y0, x1, y1, n))
    return out

def ours():
    pts = {}
    for ref in G.PLACE:
        fpid = N.FOOTPRINTS[ref]
        ox, oy, rot = G.origin(ref, fpid)
        for num, x, y in re.findall(
                r'\(pad\s+"([^"]*)"\s+\S+\s+\S+\s+\(at (-?[\d.]+) (-?[\d.]+)',
                G.load_fp(fpid)):
            if not num:          # unnamed = NPTH mounting hole, no copper
                continue
            dx, dy = G.xform(float(x), float(y), rot)
            pts[(ref, num)] = (ox + dx, oy + dy)
    return pts

def main():
    kic, scale = kicad_pads()
    mine = ours()

    unmatched, matched, merged = [], 0, 0
    for (ref, num), (x, y) in sorted(mine.items()):
        if any(abs(k[0] - x) < TOL and abs(k[1] - y) < TOL for k in kic):
            matched += 1
        # a Bridged solder jumper renders as ONE blob spanning both pads, so
        # fall back to "inside a blob" before calling it a miss
        elif any(k[2] - TOL <= x <= k[4] + TOL and k[3] - TOL <= y <= k[5] + TOL
                 for k in kic):
            matched += 1; merged += 1
        else:
            near = min(kic, key=lambda k: (k[0]-x)**2 + (k[1]-y)**2) if kic else None
            unmatched.append((ref, num, x, y, near))

    print(f"KiCad drew {len(kic)} copper blobs on F.Cu")
    print(f"we predict {len(mine)} pad positions; {matched} agree within {TOL} mm"
          + (f" ({merged} inside a merged blob, e.g. a bridged jumper)" if merged else ""))
    if unmatched:
        print("\nFAIL -- KiCad put these somewhere we did not predict")
        for ref, num, x, y, near in unmatched[:12]:
            d = f"nearest KiCad shape ({near[0]:.2f},{near[1]:.2f})" if near else "none"
            print(f"  - {ref}.{num} we say ({x:.2f},{y:.2f}); {d}")
        sys.exit(1)
    print("\nOK: every pad is where KiCad puts it")

if __name__ == "__main__":
    main()
