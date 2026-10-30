# Banco del laboratorio (30/10/2026): compara formar los equipos con 1, 2 o 3 años (teamsw.pkl de m2w).
# Para cada ventana larga W y cada (B, C) fuera de W: podio elegido con B y juzgado en C, frente a lo mismo
# formando solo con el último año de W (como ahora en el banco) y con cada año de W por separado.
import os, sys, pickle, itertools
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "lab", "src"))
import numpy as np
import equipos as eq
T = pickle.load(open(os.path.join(S, "teamsw.pkl"), "rb"))
goal = dict(semanas_en_verde_pct=50, ganancia_minima_anual_pct=10, caida_maxima_pct=25)
YRS = [2019, 2020, 2021, 2022, 2023]
def podium(ts, B):
    ts = sorted(ts, key=lambda t: (not eq.fails(t["s"][B], goal), t["s"][B]["verde"] + 2 * t["s"][B]["ret"]), reverse=True)
    pod, used = [], []
    for t in ts:
        k = sorted(t["team"])
        if k in used: continue
        used.append(k); pod.append(t)
        if len(pod) == 3: break
    return pod
def ok(pod, C): return sum(not eq.fails(t["s"][C], goal) for t in pod)
print("== Pares W->B (cumplen en B / equipos)")
for w, ts in T.items():
    print(w, {B: f"{sum(not eq.fails(t['s'][B], goal) for t in ts)}/{len(ts)}" for B in YRS if B not in w})
for L in (2, 3):
    print(f"\n== Ventanas de {L} años: tríos W -> B -> C (podio que cumple en C, de 3)")
    tot = dict(largo=0, ultimo=0, media1=0, n=0); rets = dict(largo=[], ultimo=[])
    byC = {}
    for w in [w for w in T if len(w) == L]:
        for B, C in itertools.permutations([y for y in YRS if y not in w], 2):
            pl = podium(T[w], B); pu = podium(T[(w[-1],)], B)
            a, b = ok(pl, C), ok(pu, C)
            m = np.mean([ok(podium(T[(y,)], B), C) for y in w])
            tot["largo"] += a; tot["ultimo"] += b; tot["media1"] += m; tot["n"] += 3
            rets["largo"] += [t["s"][C]["ret"] for t in pl]; rets["ultimo"] += [t["s"][C]["ret"] for t in pu]
            byC.setdefault(C, [0, 0]); byC[C][0] += a; byC[C][1] += b
            print(w, B, C, f"largo {a}  último año {b}  media de 1 año {m:.1f}", " (orden de tiempo)" if w[-1] < B < C else "")
    print("TOTAL", tot, "| por C (largo, último):", byC,
          f"| ret mediana C largo {np.median(rets['largo'])*100:+.0f} % último {np.median(rets['ultimo'])*100:+.0f} %")
