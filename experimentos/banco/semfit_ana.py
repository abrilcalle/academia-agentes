import json, sys, os, numpy as np
S = os.path.dirname(os.path.abspath(__file__))
base = json.load(open(os.path.join(S, "res_0_media.json")))
def key(r): return (r["activo"], r["tf"], r["sd"])
B = {key(r): r for r in base}
for f in sys.argv[1:]:
    X = {key(r): r for r in json.load(open(os.path.join(S, f)))}
    ks = [k for k in X if k in B]
    print(f"== {f} ({len(ks)} agentes)")
    for per in ("tr", "y22", "y23"):
        for nm, src in (("base", B), ("var", X)):
            ret = np.array([src[k][per]["ret"] for k in ks]); v = np.array([src[k][per]["verde"] for k in ks])
            dd = np.array([src[k][per]["dd"] for k in ks])
            print(f"  {per} {nm:4s} ret med {np.median(ret):+.3f}  verde med {np.median(v):.3f} media {v.mean():.3f}  >50% {np.mean(v>0.5):.2f}  dd med {np.median(dd):.3f}")
        dv = np.array([X[k][per]["verde"] - B[k][per]["verde"] for k in ks])
        print(f"  {per} Δverde media {dv.mean():+.3f}  mejoran {np.mean(dv>0):.2f} empeoran {np.mean(dv<0):.2f}")
    for c in sorted({k[:2] for k in ks}):
        kk = [k for k in ks if k[:2] == c]
        s = []
        for per in ("y22", "y23"):
            s.append(f"{per} verde {np.mean([B[k][per]['verde'] for k in kk]):.3f}->{np.mean([X[k][per]['verde'] for k in kk]):.3f} ret {np.median([B[k][per]['ret'] for k in kk]):+.2f}->{np.median([X[k][per]['ret'] for k in kk]):+.2f}")
        print("   ", c, " | ".join(s))
