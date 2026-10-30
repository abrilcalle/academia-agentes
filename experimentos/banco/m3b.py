import os, sys, pickle, itertools
S = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(S, "lab", "src"))
import numpy as np, equipos as eq
TB = pickle.load(open(os.path.join(S, "teamsb.pkl"), "rb"))
goal = dict(semanas_en_verde_pct=50, ganancia_minima_anual_pct=10, caida_maxima_pct=25)
YRS = [2019, 2020, 2021, 2022, 2023]
PAIRS = [(a, b) for a in YRS for b in YRS if a != b]
print("== Pares A->B (20): equipos que cumplen en B")
for v, T in TB.items():
    row = {(A, B): sum(not eq.fails(t["s"][B], goal) for t in T[A]) for A, B in PAIRS}
    byB = {b: sum(c for (A, B), c in row.items() if B == b) for b in YRS}
    print(f"{v:5s} total {sum(row.values())} | por año B {byB}")
    print("      ", " ".join(f"{A%100}>{B%100}:{c}" for (A, B), c in row.items()))
def podium(ts, B):
    ts = sorted(ts, key=lambda t: (not eq.fails(t["s"][B], goal), t["s"][B]["verde"] + 2 * t["s"][B]["ret"]), reverse=True)
    pod, used = [], []
    for t in ts:
        k = sorted(t["team"])
        if k in used: continue
        used.append(k); pod.append(t)
        if len(pod) == 3: break
    return pod
print("\n== Tríos A->B->C: podio que cumple en C")
trios = list(itertools.permutations(YRS, 3))
for v, T in TB.items():
    res = [(t3, podium(T[t3[0]], t3[1])) for t3 in trios]
    ok = sum(not eq.fails(t["s"][C], goal) for (A, B, C), p in res for t in p)
    byC = {c: sum(not eq.fails(t["s"][c], goal) for (A, B, C2), p in res if C2 == c for t in p) for c in YRS}
    fw = sum(not eq.fails(t["s"][C], goal) for (A, B, C), p in res if A < B < C for t in p)
    flat = [t["s"][C] for (A, B, C), p in res for t in p]
    f22 = [t["s"][2022] for (A, B, C), p in res if C == 2022 for t in p]
    print(f"{v:5s} cumplen {ok}/180 | por C {byC} | en orden {fw}/30 | mediana ret {np.median([s['ret'] for s in flat])*100:+.0f} % sem {np.median([s['verde'] for s in flat])*100:.0f} % caída {np.median([s['dd'] for s in flat])*100:.0f} %"
          f" | C=2022: ret {np.median([s['ret'] for s in f22])*100:+.0f} % sem {np.median([s['verde'] for s in f22])*100:.0f} % caída {np.median([s['dd'] for s in f22])*100:.0f} %")
