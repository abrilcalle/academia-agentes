"""Etapa 3 (criterio del podio): formar con A, elegir podio con B según distintos criterios, juzgar en C."""
import os, sys, pickle, itertools
S = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(S, "lab", "src"))
import numpy as np, equipos as eq
T = pickle.load(open(os.path.join(S, "teamsp.pkl"), "rb"))
goal = dict(semanas_en_verde_pct=50, ganancia_minima_anual_pct=10, caida_maxima_pct=25)
YRS = [2019, 2020, 2021, 2022, 2023]
ok = lambda s: not eq.fails(s, goal)
def slack(s):
    return min((s["verde"] - 0.5) / 0.1, (eq.annual(s) - 0.10) / 0.2, (0.25 - s["dd"]) / 0.1)
def dret(v):
    return np.r_[v[0] / 100 - 1, v[1:] / v[:-1] - 1]
def rank(t, B): return t["s"][B]["verde"] + 2 * t["s"][B]["ret"]
_pc = {}
def prob(t, A, B):
    k = (id(t), A, B)
    if k not in _pc:
        a, b = (A, B) if A < B else (B, A)
        _pc[k] = eq.prob_cumplir(np.r_[dret(t["v"][a]), dret(t["v"][b])], goal, n=500)
    return _pc[k]
def prob_b(t, B):
    k = (id(t), B)
    if k not in _pc: _pc[k] = eq.prob_cumplir(dret(t["v"][B]), goal, n=500)
    return _pc[k]
def pick(ts):
    pod, used = [], []
    for t in ts:
        k = sorted(t["team"])
        if k in used: continue
        used.append(k); pod.append(t)
        if len(pod) == 3: break
    return pod
def base(ts, A, B): return pick(sorted(ts, key=lambda t: (ok(t["s"][B]), rank(t, B)), reverse=True))
def real(ts, A, B):
    ts = sorted(ts, key=lambda t: (ok(t["s"][B]), rank(t, B)), reverse=True)
    top, seen = [], []
    for t in ts:
        if len(seen) >= 10: break
        k = (tuple(sorted(t["team"])), t["pr"])
        if k in seen: continue
        seen.append(k); top.append(t)
    return pick(sorted(ts, key=lambda t: (ok(t["s"][B]), (prob(t, A, B) if t in top else 0) + rank(t, B)), reverse=True))
def probB(ts, A, B): return pick(sorted(ts, key=lambda t: (ok(t["s"][B]), prob_b(t, B), rank(t, B)), reverse=True))
def margen(ts, A, B): return pick(sorted(ts, key=lambda t: (ok(t["s"][B]), slack(t["s"][B])), reverse=True))
def margenAB(ts, A, B): return pick(sorted(ts, key=lambda t: (ok(t["s"][B]), min(slack(t["s"][B]), slack(t["s"][A]))), reverse=True))
def semanas(ts, A, B): return pick(sorted(ts, key=lambda t: (ok(t["s"][B]), t["s"][B]["verde"], t["s"][B]["ret"]), reverse=True))
def ganancia(ts, A, B): return pick(sorted(ts, key=lambda t: (ok(t["s"][B]), t["s"][B]["ret"]), reverse=True))
def caida(ts, A, B): return pick(sorted(ts, key=lambda t: (ok(t["s"][B]), -t["s"][B]["dd"]), reverse=True))
VAR = dict(base=base, real=real, probB=probB, margen=margen, margenAB=margenAB, semanas=semanas, ganancia=ganancia, caida=caida)
trios = list(itertools.permutations(YRS, 3))
for v, f in VAR.items():
    res = [(t3, f(T[t3[0]], t3[0], t3[1])) for t3 in trios]
    n_ok = sum(ok(t["s"][C]) for (A, B, C), p in res for t in p)
    byC = {c: sum(ok(t["s"][c]) for (A, B, C2), p in res if C2 == c for t in p) for c in YRS}
    byA = {a: sum(ok(t["s"][C]) for (A2, B, C), p in res if A2 == a for t in p) for a in YRS}
    fw = sum(ok(t["s"][C]) for (A, B, C), p in res if A < B < C for t in p)
    adj = sum(ok(t["s"][C]) for (A, B, C), p in res if B + 1 == C for t in p)
    flat = [t["s"][C] for (A, B, C), p in res for t in p]
    print(f"{v:9s} cumplen {n_ok}/180 | en orden {fw}/30 | C=B+1 {adj} | por C {byC} | por A {byA} | med ret {np.median([s['ret'] for s in flat])*100:+.0f} % sem {np.median([s['verde'] for s in flat])*100:.0f} % caída {np.median([s['dd'] for s in flat])*100:.0f} %", flush=True)
