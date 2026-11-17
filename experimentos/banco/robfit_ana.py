# Compara rob_<MODO>.json con rob_base.json (mismos agentes): 2022 y 2023 son los años de medida (validación).
import json, sys, os, numpy as np
S = os.path.dirname(os.path.abspath(__file__))
B = {(r["activo"], r["tf"], r["sd"]): r for r in json.load(open(os.path.join(S, "rob_base.json")))}
for f in sys.argv[1:]:
    X = {(r["activo"], r["tf"], r["sd"]): r for r in json.load(open(os.path.join(S, f)))}
    ks = [k for k in X if k in B]
    print(f"== {f} ({len(ks)} agentes)")
    for per in ("tr", "y22", "y23"):
        for nm, src in (("base", B), ("var", X)):
            ret = np.array([src[k][per]["ret"] for k in ks]); v = np.array([src[k][per]["verde"] for k in ks]); dd = np.array([src[k][per]["dd"] for k in ks])
            print(f"  {per} {nm:4s} ret med {np.median(ret):+.3f} >0 {np.mean(ret>0):.2f} >10% {np.mean(ret>0.1):.2f} | verde media {v.mean():.3f} >50% {np.mean(v>0.5):.2f} | dd med {np.median(dd):.3f}")
        dr = np.array([X[k][per]["ret"] - B[k][per]["ret"] for k in ks])
        print(f"  {per} Δret mediana {np.median(dr):+.3f}  mejoran {np.mean(dr>0):.2f} empeoran {np.mean(dr<0):.2f}")
    for c in sorted({k[:2] for k in ks}):
        kk = [k for k in ks if k[:2] == c]
        print("   ", c, " | ".join(f"{per} ret {np.median([B[k][per]['ret'] for k in kk]):+.2f}->{np.median([X[k][per]['ret'] for k in kk]):+.2f} verde {np.mean([B[k][per]['verde'] for k in kk]):.3f}->{np.mean([X[k][per]['verde'] for k in kk]):.3f}" for per in ("y22", "y23")))
