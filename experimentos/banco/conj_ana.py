import json, glob, numpy as np, sys
# Análisis de conj.py (10/11/2026): python conj_ana.py en la carpeta con los res_conj_*.json
rows = []
for f in sorted(glob.glob("res_conj_*_0.json")): rows += json.load(open(f))
V = ["base", "f3", "f5", "h3", "h5"]
print(len(rows), "agentes")
for per in ("tr", "y22", "y23"):
    for v in V:
        ret = np.array([r[v][per]["ret"] for r in rows]); ve = np.array([r[v][per]["verde"] for r in rows]); dd = np.array([r[v][per]["dd"] for r in rows])
        n = np.array([r[v][per]["n"] for r in rows])
        extra = ""
        if v != "base":
            d = ve - np.array([r["base"][per]["verde"] for r in rows]); dr = ret - np.array([r["base"][per]["ret"] for r in rows])
            extra = f" | dverde {d.mean():+.3f} mej {np.mean(d>0):.2f} emp {np.mean(d<0):.2f} | dret mej {np.mean(dr>0):.2f}"
        print(f"{per} {v:4s} ret med {np.median(ret):+.3f} verde {ve.mean():.3f} >50% {np.mean(ve>0.5):.2f} dd med {np.median(dd):.3f} ops {np.median(n):.0f} ret/dd {np.median(ret/np.maximum(dd,.01)):+.2f}{extra}")
combos = sorted({(r["activo"], r["tf"]) for r in rows})
for c in combos:
    rr = [r for r in rows if (r["activo"], r["tf"]) == c]
    s = " ".join(f"{v}:" + "/".join(f"{np.median([r[v][p]['ret'] for r in rr]):+.2f},{np.mean([r[v][p]['verde'] for r in rr]):.3f}" for p in ("y22", "y23")) for v in V)
    print(c, len(rr), s)
