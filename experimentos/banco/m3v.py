import os, sys, pickle, itertools, glob
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "lab", "src"))
import numpy as np
import equipos as eq
T = {}
for f in glob.glob(os.path.join(S, "teams_v_*.pkl")): T.update(pickle.load(open(f, "rb")))
goal = dict(semanas_en_verde_pct=50, ganancia_minima_anual_pct=10, caida_maxima_pct=25)
VARS = ["base", "mitades", "tercios", "cuartos", "minsh", "minsh_pos"]
VARS = [v for v in VARS if (v, 2019) in T]
YRS = [2019, 2020, 2021, 2022, 2023]
PAIRS = [(2019, 2020), (2020, 2021), (2021, 2022), (2022, 2023), (2023, 2022), (2021, 2023), (2020, 2019)]
print("== Pares A->B: equipos que cumplen en B (de 54)")
for v in VARS:
    row = [sum(not eq.fails(t["s"][B], goal) for t in T[(v, A)]) for A, B in PAIRS]
    print(f"{v:10s}", row, "->", sum(row))
print("== Todos los pares A!=B (de 54 cada uno): total y por año B")
for v in VARS:
    byB = {B: sum(not eq.fails(t["s"][B], goal) for A in YRS if A != B for t in T[(v, A)]) for B in YRS}
    print(f"{v:10s}", byB, "->", sum(byB.values()), "| mediana ret", f"{np.median([t['s'][B]['ret'] for A in YRS for B in YRS if A!=B for t in T[(v,A)]])*100:+.0f}%",
          "dd", f"{np.median([t['s'][B]['dd'] for A in YRS for B in YRS if A!=B for t in T[(v,A)]])*100:.0f}%")
def podium(ts, B):
    ts = sorted(ts, key=lambda t: (not eq.fails(t["s"][B], goal), t["s"][B]["verde"] + 2 * t["s"][B]["ret"]), reverse=True)
    pod, used = [], []
    for t in ts:
        k = sorted(t["team"])
        if k in used: continue
        used.append(k); pod.append(t)
        if len(pod) == 3: break
    return pod
trios = list(itertools.permutations(YRS, 3))
print("== Tríos formar A -> podio B -> juzgar C")
for v in VARS:
    res = [(tr, [not eq.fails(t["s"][tr[2]], goal) for t in podium(T[(v, tr[0])], tr[1])], [t["s"][tr[2]]["ret"] for t in podium(T[(v, tr[0])], tr[1])]) for tr in trios]
    ok = sum(sum(r) for _, r, _ in res)
    byC = {c: sum(sum(r) for tr, r, _ in res if tr[2] == c) for c in YRS}
    fw = sum(sum(r) for tr, r, _ in res if tr[0] < tr[1] < tr[2])
    print(f"{v:10s} {ok}/180 | por C {byC} | orden tiempo {fw}/30 | ret mediana C {np.median([x for _,_,rr in res for x in rr])*100:+.0f}%")

print("== Por par (todos A!=B): mitades/tercios/cuartos - base")
for A in YRS:
    for B in YRS:
        if A==B: continue
        c={v: sum(not eq.fails(t["s"][B], goal) for t in T[(v, A)]) for v in VARS}
        print(A,B, c["base"], [c[v]-c["base"] for v in ("mitades","tercios","cuartos") if v in c])
