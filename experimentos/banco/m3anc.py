# Banco (04/11/2026 tarde): compara variantes de "ancla de tendencia" (teams_VAR.pkl de m2anc.py). Uso: python m3anc.py base btc_libre_1 ...
import os, sys, pickle, itertools
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "lab", "src"))
import numpy as np
import equipos as eq
goal = dict(semanas_en_verde_pct=50, ganancia_minima_anual_pct=10, caida_maxima_pct=25)
YRS = [2019, 2020, 2021, 2022, 2023]
PAIRS = [(2019, 2020), (2020, 2021), (2021, 2022), (2022, 2023), (2023, 2022), (2021, 2023), (2020, 2019)]
trios = list(itertools.permutations(YRS, 3))


def podium(ts, B):
    ts = sorted(ts, key=lambda t: (not eq.fails(t["s"][B], goal), t["s"][B]["verde"] + 2 * t["s"][B]["ret"]), reverse=True)
    pod, used = [], []
    for t in ts:
        k = sorted(t["team"])
        if k in used: continue
        used.append(k); pod.append(t)
        if len(pod) == 3: break
    return pod


for v in sys.argv[1:]:
    T = pickle.load(open(os.path.join(S, f"teams_{v}.pkl"), "rb"))
    row, tot = [], 0
    for A, B in PAIRS:
        c = sum(not eq.fails(t["s"][B], goal) for t in T[A]); row.append(f"{c}/{len(T[A])}"); tot += c
    med = {B: (np.median([t["s"][B]["ret"] for A in YRS if A != B for t in T[A]]) * 100,
               np.median([t["s"][B]["verde"] for A in YRS if A != B for t in T[A]]) * 100,
               np.median([t["s"][B]["dd"] for A in YRS if A != B for t in T[A]]) * 100) for B in YRS}
    flat, byC, okfw = [], {c: 0 for c in YRS}, 0
    for A, B, C in trios:
        pod = podium(T[A], B)
        for t in pod:
            ok = not eq.fails(t["s"][C], goal)
            flat.append((ok, t["s"][C]["ret"], t["s"][C]["verde"], t["s"][C]["dd"]))
            byC[C] += ok
            if A < B < C: okfw += ok
    print(f"== {v}\n pares: {' '.join(row)} -> {tot}")
    print(f" tríos: cumplen {sum(x[0] for x in flat)}/{len(flat)} | por C {byC} | orden de tiempo {okfw} | mediana ret {np.median([x[1] for x in flat])*100:+.0f} % semanas {np.median([x[2] for x in flat])*100:.0f} % caída {np.median([x[3] for x in flat])*100:.0f} %")
    print(" mediana por año juzgado (ret / semanas / caída):", {B: tuple(round(x) for x in med[B]) for B in YRS})
