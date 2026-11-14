import json, glob, numpy as np, sys
# Análisis de multimer.py (14/11/2026): python mm_ana.py en la carpeta con los res_mm_*.json
rows = []
for f in sorted(glob.glob("res_mm_[0-5]_0.json")): rows += json.load(open(f))
V = [v for v in ("base", "pool", "media", "min") if v in rows[0]]
print(len(rows), "agentes")
for per in ("tr", "y22", "y23", "o1_y22", "o1_y23", "o2_y22", "o2_y23"):
    for v in V:
        g = lambda k, vv=v: np.array([r[vv][per][k] for r in rows])
        ret, ve, dd = g("ret"), g("verde"), g("dd")
        extra = ""
        if v != "base":
            d = ve - g("verde", "base"); dr = ret - g("ret", "base")
            extra = f" | dverde {d.mean():+.3f} mej {np.mean(d>0):.2f} emp {np.mean(d<0):.2f} | dret med {np.median(dr):+.3f} mej {np.mean(dr>0):.2f}"
        print(f"{per:7s} {v:5s} ret med {np.median(ret):+.3f} verde {ve.mean():.3f} >50% {np.mean(ve>0.5):.2f} dd med {np.median(dd):.3f} ret>0 {np.mean(ret>0):.2f}{extra}")
combos = sorted({(r["activo"], r["tf"]) for r in rows})
for c in combos:
    rr = [r for r in rows if (r["activo"], r["tf"]) == c]
    print(c, len(rr), " ".join(f"{v}:" + "/".join(f"{np.median([r[v][p]['ret'] for r in rr]):+.2f},{np.mean([r[v][p]['verde'] for r in rr]):.3f}" for p in ("y22", "y23")) for v in V))
