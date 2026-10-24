import pathlib, re
HERE=str(__import__("pathlib").Path(__file__).resolve().parent)
figs=pathlib.Path(HERE+"/figs.txt").read_text().split("\n@@SPLIT@@\n")
p=pathlib.Path(HERE).parent/"wiring-guide.html"; s=p.read_text()
blocks=list(re.finditer(r'<svg\b.*?</svg>', s, re.S))
assert len(blocks)==len(figs)==4, (len(blocks), len(figs))
for m,new in zip(reversed(blocks), reversed(figs)):
    s = s[:m.start()] + new + s[m.end():]
p.write_text(s); print("spliced")
