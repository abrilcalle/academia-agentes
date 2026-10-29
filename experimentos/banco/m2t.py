# Banco (29/10/2026 tarde): variante de m2 que forma equipos con distinto tamaño (min3 = actual, min4, min5, max4, max3). Uso: python3 m2v.py base mitades ... (una por proceso) y luego m3v.py.
# Banco de pruebas del laboratorio (28/10/2026). Uso: carpeta de pruebas con 'lab/' (copia del repo) y 'loc/' (enlaces a data/:
# btc_1d.csv, btc_1h, btc_flujo_1h, eth/sol/xrp_1d.csv y _1h, usdc_eur_1d.csv); copiar m1-m3 a esa carpeta y ejecutar en orden.
# m1: matriz de agentes 2019-2023 (~6 min) · m2: equipos formados por año (~4 min) · m3: pares A->B y tríos formar->podio->juzgar.
"""Etapa 2: formar equipos con el año A (como build), elegir podio con el año B, juzgar en el año C.
Compara: ambos modos (actual), solo prioridad, solo kelly."""
import datetime as dt, os, sys, pickle, itertools, json
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "lab", "src"))
import numpy as np
import equipos as eq
M = pickle.load(open(os.path.join(S, "mat.pkl"), "rb"))
days, R, E, P, G, L, info = M["days"], M["R"], M["E"], M["P"], M["G"], M["L"], M["info"]
goal = dict(semanas_en_verde_pct=50, ganancia_minima_anual_pct=10, caida_maxima_pct=25)
YRS = [2019, 2020, 2021, 2022, 2023]
rng_ = {y: [k for k, d in enumerate(days) if d.year == y] for y in YRS}
sl = {y: slice(rng_[y][0], rng_[y][-1] + 1) for y in YRS}


def sim(team, y, pr, prm):
    s = sl[y]
    v, _ = eq.simulate(R[team, s], E[team, s], P[team, s], G[team, s], pr, prm, L=L[team, s])
    return eq.stats(days[s], v)


def form(A, var):
    s = sl[A]
    n = len(info)
    keep = [j for j in range(n) if np.prod(1 + R[j, s]) - 1 > 0 or info[j]["short"]]
    with np.errstate(invalid="ignore", divide="ignore"):
        sh = np.nan_to_num(R[:, s].mean(1) / R[:, s].std(1))
    ix = rng_[A]; h = len(ix)//2
    s1, s2 = slice(ix[0], ix[0]+h), slice(ix[0]+h, ix[-1]+1)
    with np.errstate(invalid="ignore", divide="ignore"):
        sh1 = np.nan_to_num(R[:, s1].mean(1) / R[:, s1].std(1)); sh2 = np.nan_to_num(R[:, s2].mean(1) / R[:, s2].std(1))
    nseg = {"tercios": 3, "cuartos": 4}.get(var, 2)
    segs = np.array_split(np.array(ix), nseg)
    pos = lambda j: all(np.prod(1 + R[j, sg[0]:sg[-1] + 1]) > 1 for sg in segs)
    key = lambda j: -sh[j]
    MINM = {"min4": 4, "min5": 5}.get(var, eq.MIN_MIEMBROS); MAXM = {"max4": 4, "max3": 3}.get(var, eq.MAX_MIEMBROS)
    chosen = []
    for j in sorted(keep, key=key):
        pass
        if len(chosen) >= 24: break
        if info[j]["short"] or R[j, s].std() == 0 or R[j, s].sum() <= 0: continue
        if any(np.corrcoef(R[j, s], R[i, s])[0, 1] > 0.9 for i in chosen): continue
        chosen.append(j)
    shorts = sorted([j for j in keep if info[j]["short"] and R[j, s].std() > 0 and np.prod(1 + R[j, s]) - 1 >= 0.10],
                    key=lambda j: -np.prod(1 + R[j, s]))
    for j in shorts:
        if sum(info[i]["short"] for i in chosen) >= 8: break
        if any(np.corrcoef(R[j, s], R[i, s])[0, 1] > 0.9 for i in chosen): continue
        chosen.append(j)
    teams = []
    for pr in eq.PRUDENCIAS:
        for prm in eq.PARAMS:
            team, cur = [], -1e9
            while len(team) < MAXM:
                add = None
                for j in chosen:
                    if j in team: continue
                    if sum(info[i]["activo"] == info[j]["activo"] for i in team) >= eq.MAX_POR_ACTIVO: continue
                    sc = eq.objective(sim(team + [j], A, pr, prm), goal)
                    if add is None or sc > add[0]: add = (sc, j)
                if add is None or (len(team) >= MINM and add[0] <= cur + 1e-4): break
                cur, team = add[0], team + [add[1]]
            if len(team) >= MINM:
                teams.append(dict(team=team, pr=pr, prm=prm))
    return teams


VARS = sys.argv[1:] or ["base", "min4", "min5", "max4"]
out = {}
for var in VARS:
  for A in YRS:
    T = form(A, var)
    for t in T:
        t["s"] = {y: sim(t["team"], y, t["pr"], t["prm"]) for y in YRS if y != A}
    out[(var, A)] = T
    print("formado", var, A, len(T), flush=True)
pickle.dump(out, open(os.path.join(S, "teams_t_" + "_".join(VARS) + ".pkl"), "wb"))
