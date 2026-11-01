# Banco (01/11/2026): igual que m3band.py, lee teams_VARIANTE.pkl. Uso: python m3x.py base pend10 ...
import os, sys, pickle, itertools
S = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(S, "lab", "src"))
import numpy as np, equipos as eq
goal = dict(semanas_en_verde_pct=50, ganancia_minima_anual_pct=10, caida_maxima_pct=25)
YRS = [2019, 2020, 2021, 2022, 2023]
ok = lambda s: not eq.fails(s, goal)
rank = lambda t, B: t["s"][B]["verde"] + 2 * t["s"][B]["ret"]
def podio(ts, B):
    pod, used = [], []
    for t in sorted(ts, key=lambda t: (ok(t["s"][B]), rank(t, B)), reverse=True):
        k = sorted(t["team"])
        if k in used: continue
        used.append(k); pod.append(t)
        if len(pod) == 3: break
    return pod
for v in sys.argv[1:]:
    p = os.path.join(S, f"teams_{v}.pkl")
    if not os.path.exists(p): continue
    T = pickle.load(open(p, "rb"))
    pares = sum(ok(t["s"][B]) for A in YRS for t in T[A] for B in YRS if B != A)
    npar = sum(len(T[A]) * 4 for A in YRS)
    trios = list(itertools.permutations(YRS, 3))
    res = [((A, B, C), podio(T[A], B)) for A, B, C in trios]
    n_ok = sum(ok(t["s"][C]) for (A, B, C), p in res for t in p)
    alo = sum(any(ok(t["s"][C]) for t in p) for (A, B, C), p in res)
    byC = {c: sum(ok(t["s"][C]) for (A, B, C), p in res if C == c for t in p) for c in YRS}
    fw = sum(ok(t["s"][C]) for (A, B, C), p in res if A < B < C for t in p)
    flat = [t["s"][C] for (A, B, C), p in res for t in p]
    print(f"{v:7s} pares {pares}/{npar} | podio C {n_ok}/180 por C {byC} | alguno {alo}/60 | orden {fw}/30 | "
          f"med ret {np.median([s['ret'] for s in flat])*100:+.0f} % verde {np.median([s['verde'] for s in flat])*100:.0f} % caída {np.median([s['dd'] for s in flat])*100:.0f} %")
