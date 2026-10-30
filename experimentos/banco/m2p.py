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


def sim(team, y, pr, prm, full=False):
    s = sl[y]
    v, _ = eq.simulate(R[team, s], E[team, s], P[team, s], G[team, s], pr, prm, L=L[team, s])
    st = eq.stats(days[s], v)
    return (st, v) if full else st


def form(A):
    s = sl[A]
    n = len(info)
    keep = [j for j in range(n) if np.prod(1 + R[j, s]) - 1 > 0 or info[j]["short"]]
    with np.errstate(invalid="ignore", divide="ignore"):
        sh = np.nan_to_num(R[:, s].mean(1) / R[:, s].std(1))
    chosen = []
    for j in sorted(keep, key=lambda j: -sh[j]):
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
            while len(team) < eq.MAX_MIEMBROS:
                add = None
                for j in chosen:
                    if j in team: continue
                    if sum(info[i]["activo"] == info[j]["activo"] for i in team) >= eq.MAX_POR_ACTIVO: continue
                    sc = eq.objective(sim(team + [j], A, pr, prm), goal)
                    if add is None or sc > add[0]: add = (sc, j)
                if add is None or (len(team) >= eq.MIN_MIEMBROS and add[0] <= cur + 1e-4): break
                cur, team = add[0], team + [add[1]]
            if len(team) >= eq.MIN_MIEMBROS:
                teams.append(dict(team=team, pr=pr, prm=prm))
    return teams


out = {}
for A in YRS:
    T = form(A)
    for t in T:
        t["s"], t["v"] = {}, {}
        for y in YRS:
            t["s"][y], t["v"][y] = sim(t["team"], y, t["pr"], t["prm"], full=True)
    out[A] = T
    print("formado", A, len(T), flush=True)
pickle.dump(out, open(os.path.join(S, "teamsp.pkl"), "wb"))
