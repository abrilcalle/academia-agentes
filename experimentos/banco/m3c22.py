# Banco (06/11/2026): podios de los tríos juzgados solo en C = 2022 y C = 2023 (fuera del entreno de los agentes). Uso: python m3c22.py base X ...
import os, sys, pickle, itertools
sys.path.insert(0, 'lab/src')
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
    T = pickle.load(open(f"teams_{v}.pkl", "rb"))
    res = [((A, B, C), podio(T[A], B)) for A, B, C in itertools.permutations(YRS, 3)]
    o = []
    for c in (2022, 2023):
        fl = [t["s"][C] for (A, B, C), p in res if C == c for t in p]
        o.append(f"C{c}: cumple {sum(ok(s) for s in fl)}/36 ret {np.median([s['ret'] for s in fl])*100:+.0f} verde {np.median([s['verde'] for s in fl])*100:.0f} dd {np.median([s['dd'] for s in fl])*100:.0f} | ")
    print(f"{v:5s}", *o)
