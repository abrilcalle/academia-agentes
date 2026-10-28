# Banco de pruebas del laboratorio (28/10/2026). Uso: carpeta de pruebas con 'lab/' (copia del repo) y 'loc/' (enlaces a data/:
# btc_1d.csv, btc_1h, btc_flujo_1h, eth/sol/xrp_1d.csv y _1h, usdc_eur_1d.csv); copiar m1-m3 a esa carpeta y ejecutar en orden.
# m1: matriz de agentes 2019-2023 (~6 min) · m2: equipos formados por año (~4 min) · m3: pares A->B y tríos formar->podio->juzgar.
import os, sys, pickle, itertools
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "lab", "src"))
import numpy as np
import equipos as eq
T = pickle.load(open(os.path.join(S, "teams.pkl"), "rb"))
goal = dict(semanas_en_verde_pct=50, ganancia_minima_anual_pct=10, caida_maxima_pct=25)
VAR = {"ambos": lambda t: True, "prioridad": lambda t: t["prm"]["modo"] == "prioridad", "kelly": lambda t: t["prm"]["modo"] == "kelly"}
PAIRS = [(2019, 2020), (2020, 2021), (2021, 2022), (2022, 2023), (2023, 2022), (2021, 2023), (2020, 2019)]
print("== Pares A->B: % de equipos que cumplen en B")
for v, f in VAR.items():
    row, tot, n = [], 0, 0
    for A, B in PAIRS:
        ts = [t for t in T[A] if f(t)]
        c = sum(not eq.fails(t["s"][B], goal) for t in ts)
        row.append(f"{c}/{len(ts)}"); tot += c; n += len(ts)
    print(f"{v:10s}", " ".join(row), f"-> {tot}/{n} = {100*tot/n:.0f} %")


def podium(ts, B):
    ts = sorted(ts, key=lambda t: (not eq.fails(t["s"][B], goal), t["s"][B]["verde"] + 2 * t["s"][B]["ret"]), reverse=True)
    pod, used = [], []
    for t in ts:
        k = sorted(t["team"])
        if k in used: continue
        used.append(k); pod.append(t)
        if len(pod) == 3: break
    return pod

print("\n== Tríos A (formar) -> B (elegir podio) -> C (juzgar): podio que cumple en C, mediana ret / semanas / caída en C")
YRS = [2019, 2020, 2021, 2022, 2023]
trios = [(a, b, c) for a, b, c in itertools.permutations(YRS, 3)]
res = {v: [] for v in VAR}
for A, B, C in trios:
    for v, f in VAR.items():
        pod = podium([t for t in T[A] if f(t)], B)
        res[v].append([(not eq.fails(t["s"][C], goal), t["s"][C]["ret"], t["s"][C]["verde"], t["s"][C]["dd"], t["prm"]["modo"]) for t in pod])
for v in VAR:
    flat = [x for r in res[v] for x in r]
    ok = sum(x[0] for x in flat)
    byC = {c: sum(x[0] for (A, B, C2), r in zip(trios, res[v]) if C2 == c for x in r) for c in YRS}
    fw = [(A, B, C) for (A, B, C), r in zip(trios, res[v]) if A < B < C]
    okfw = sum(x[0] for (t3, r) in zip(trios, res[v]) if t3[0] < t3[1] < t3[2] for x in r)
    nfw = sum(len(r) for (t3, r) in zip(trios, res[v]) if t3[0] < t3[1] < t3[2])
    print(f"{v:10s} cumplen {ok}/{len(flat)} | por año C {byC} | solo en orden de tiempo {okfw}/{nfw} | "
          f"mediana ret {np.median([x[1] for x in flat])*100:+.0f} % semanas {np.median([x[2] for x in flat])*100:.0f} % caída {np.median([x[3] for x in flat])*100:.0f} % | "
          f"podios con kelly {sum(x[4]=='kelly' for x in flat)}")
# por trío en orden temporal
print("\nTríos en orden temporal (cumplen de 3: ambos / prioridad / kelly)")
for (A, B, C), *rs in zip(trios, *[res[v] for v in VAR]):
    if A < B < C:
        print(A, B, C, " / ".join(str(sum(x[0] for x in r)) for r in rs), " ret medio C:", " / ".join(f"{np.mean([x[1] for x in r])*100:+.0f}" for r in rs))
