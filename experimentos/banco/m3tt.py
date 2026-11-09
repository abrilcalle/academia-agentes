# Banco (09/11/2026): compara variantes con 1 equipo por prudencia (union/cons) con la base (podio de 3 elegido con B).
import os, sys, pickle, itertools
sys.path.insert(0, 'lab/src')
import numpy as np, equipos as eq
goal = dict(semanas_en_verde_pct=50, ganancia_minima_anual_pct=10, caida_maxima_pct=25)
ok = lambda s: not eq.fails(s, goal)
YRS = [2019, 2020, 2021, 2022, 2023]
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
    tr = list(itertools.permutations(YRS, 3))
    res = [((A, B, C), (podio(T[A], B) if v in ("post", "base") else T[A])) for A, B, C in tr]
    n_ok = sum(ok(t["s"][C]) for (A, B, C), p in res for t in p); npod = sum(len(p) for _, p in res)
    byC = {c: sum(ok(t["s"][C]) for (A, B, C), p in res if C == c for t in p) for c in YRS}
    fw = sum(ok(t["s"][C]) for (A, B, C), p in res if A < B < C for t in p)
    alo = sum(any(ok(t["s"][C]) for t in p) for (A, B, C), p in res)
    pares = [ok(t["s"][B]) for A in YRS for t in T[A] for B in YRS if B != A]
    fl = [t["s"][C] for (A, B, C), p in res for t in p]
    byA = {A: sum(ok(t["s"][B]) for t in T[A] for B in YRS if B != A) for A in YRS}
    print(f"{v:6s} pares {sum(pares)}/{len(pares)} ({100*np.mean(pares):.0f} %) porA {byA} | podio C {n_ok}/{npod} {byC} | alguno {alo}/60 | orden {fw}/{sum(len(p) for (A,B,C),p in res if A<B<C)} | "
          f"med ret {np.median([s['ret'] for s in fl])*100:+.0f} % verde {np.median([s['verde'] for s in fl])*100:.1f} % caída {np.median([s['dd'] for s in fl])*100:.0f} % dd>25 {sum(s['dd']>0.25 for s in fl)}")
