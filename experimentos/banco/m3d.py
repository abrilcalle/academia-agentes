"""Etapa 3 (podio variado): formar con A, elegir podio con B exigiendo que los 3 equipos compartan pocos agentes, juzgar en C.
Mide sobre todo la meta: que AL MENOS UN equipo del podio cumpla en C."""
import os, sys, pickle, itertools
S = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(S, "lab", "src"))
import numpy as np, equipos as eq
T = pickle.load(open(os.path.join(S, "teamsp.pkl"), "rb"))
goal = dict(semanas_en_verde_pct=50, ganancia_minima_anual_pct=10, caida_maxima_pct=25)
YRS = [2019, 2020, 2021, 2022, 2023]
ok = lambda s: not eq.fails(s, goal)
def rank(t, B): return t["s"][B]["verde"] + 2 * t["s"][B]["ret"]
def pick(ts, comp=None, usos=None, frac=None):
    pod, used = [], []
    for t in ts:
        k = sorted(t["team"])
        if k in used: continue
        if comp is not None and any(len(set(k) & set(u)) > comp for u in used): continue
        if frac is not None and any(len(set(k) & set(u)) > frac * min(len(k), len(u)) for u in used): continue
        if usos is not None and any(sum(j in u for u in used) >= usos for j in k): continue
        used.append(k); pod.append(t)
        if len(pod) == 3: break
    return pod
def mk(**kw):
    return lambda ts, B: pick(sorted(ts, key=lambda t: (ok(t["s"][B]), rank(t, B)), reverse=True), **kw)
VAR = dict(base=mk(), comp0=mk(comp=0), comp1=mk(comp=1), comp2=mk(comp=2), comp3=mk(comp=3),
           mitad=mk(frac=0.5), usos1=mk(usos=1), usos2=mk(usos=2))
trios = list(itertools.permutations(YRS, 3))
for v, f in VAR.items():
    res = [(t3, f(T[t3[0]], t3[1])) for t3 in trios]
    n_ok = sum(ok(t["s"][C]) for (A, B, C), p in res for t in p)
    alo = sum(any(ok(t["s"][C]) for t in p) for (A, B, C), p in res)
    alo_okB = sum(any(ok(t["s"][C]) for t in p) for (A, B, C), p in res if any(ok(t["s"][B]) for t in p))
    nB = sum(any(ok(t["s"][B]) for t in p) for (A, B, C), p in res)
    byC = {c: sum(any(ok(t["s"][C2]) for t in p) for (A, B, C2), p in res if C2 == c) for c in YRS}
    fw = sum(ok(t["s"][C]) for (A, B, C), p in res if A < B < C for t in p)
    fwa = sum(any(ok(t["s"][C]) for t in p) for (A, B, C), p in res if A < B < C)
    okB = sum(ok(t["s"][B]) for (A, B, C), p in res for t in p)
    ov = np.mean([np.mean([len(set(a["team"]) & set(b["team"])) for a, b in itertools.combinations(p, 2)]) for _, p in res if len(p) == 3])
    flat = [t["s"][C] for (A, B, C), p in res for t in p]
    print(f"{v:6s} cumplen {n_ok}/180 | alguno {alo}/60 (por C {byC}) | en orden {fw}/30, alguno {fwa}/10 | cumplen en B {okB}/180 | comparten {ov:.1f} | med ret {np.median([s['ret'] for s in flat])*100:+.0f} % caída {np.median([s['dd'] for s in flat])*100:.0f} %", flush=True)
# pares A->B (todos los equipos formados, para referencia de la base)
