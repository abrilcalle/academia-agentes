# Banco (31/10/2026): compara variantes de fuerza relativa. Uso: python m3r.py base rs30_mitad ...
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
    row, tot, n = [], 0, 0
    for A, B in PAIRS:
        c = sum(not eq.fails(t["s"][B], goal) for t in T[A]); row.append(f"{c}/{len(T[A])}"); tot += c; n += len(T[A])
    res = [(t3, [(not eq.fails(t["s"][t3[2]], goal), t["s"][t3[2]]["ret"], t["s"][t3[2]]["verde"], t["s"][t3[2]]["dd"]) for t in podium(T[t3[0]], t3[1])]) for t3 in trios]
    flat = [x for _, r in res for x in r]
    byC = {c: sum(x[0] for t3, r in res if t3[2] == c for x in r) for c in YRS}
    okfw = sum(x[0] for t3, r in res if t3[0] < t3[1] < t3[2] for x in r)
    print(f"{v:11s} pares {' '.join(row)} -> {tot}/{n} | tríos {sum(x[0] for x in flat)}/{len(flat)} por C {byC} | orden tiempo {okfw}/30 | "
          f"mediana C ret {np.median([x[1] for x in flat])*100:+.0f} % sem {np.median([x[2] for x in flat])*100:.0f} % caída {np.median([x[3] for x in flat])*100:.0f} %")
    # todos los equipos formados, en todos los años fuera de A: semanas, ret y caída medianas
    allm = [(t["s"][y]["verde"], t["s"][y]["ret"], t["s"][y]["dd"], y) for A in YRS for t in T[A] for y in YRS if y != A]
    print("            todos los equipos fuera de A: por año sem/ret/caída mediana:",
          " ".join(f"{y}:{np.median([a[0] for a in allm if a[3]==y])*100:.0f}/{np.median([a[1] for a in allm if a[3]==y])*100:+.0f}/{np.median([a[2] for a in allm if a[3]==y])*100:.0f}" for y in YRS))
