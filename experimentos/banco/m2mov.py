# Uso: carpeta con lab/ (copia del repo) y loc/ (enlaces a data/ con nombres cortos: btc_1d.csv, btc_1h, eth_1d.csv...). Matriz: m1h.py con parts={} y salida mat_r.pkl. Luego: python m2mov.py MESES [VENTANA_DIAS].
# Banco (04/11/2026): formación móvil de equipos. Fijo = formado con el año anterior; móvil = re-formado cada F meses con los 365 días anteriores.
import os, sys, pickle, datetime as dt
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "lab", "src"))
import numpy as np
import equipos as eq
M = pickle.load(open(os.path.join(S, "mat_r.pkl"), "rb"))
F = int(sys.argv[1])   # meses entre formaciones
VENT = int(sys.argv[2]) if len(sys.argv) > 2 else 365
days, R, E, P, G, L, info = M["days"], M["R"], M["E"], M["P"], M["G"], M["L"], M["info"]
goal = dict(semanas_en_verde_pct=50, ganancia_minima_anual_pct=10, caida_maxima_pct=25)
def idx(d): return next(k for k, x in enumerate(days) if x >= d)
def simv(team, s, pr, prm, cap0=100.0):
    v, _ = eq.simulate(R[team, s], E[team, s], P[team, s], G[team, s], pr, prm, cap0=cap0, L=L[team, s])
    return np.asarray(v)
def form(s):
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
    shorts = sorted([j for j in keep if info[j]["short"] and R[j, s].std() > 0 and np.prod(1 + R[j, s]) - 1 >= 0.10], key=lambda j: -np.prod(1 + R[j, s]))
    for j in shorts:
        if sum(info[i]["short"] for i in chosen) >= 8: break
        if any(np.corrcoef(R[j, s], R[i, s])[0, 1] > 0.9 for i in chosen): continue
        chosen.append(j)
    dd = days[s]
    teams = {}
    for pr in eq.PRUDENCIAS:
        for pi, prm in enumerate(eq.PARAMS):
            team, cur = [], -1e9
            while len(team) < eq.MAX_MIEMBROS:
                add = None
                for j in chosen:
                    if j in team: continue
                    if sum(info[i]["activo"] == info[j]["activo"] for i in team) >= eq.MAX_POR_ACTIVO: continue
                    sc = eq.objective(eq.stats(dd, simv(team + [j], s, pr, prm)), goal)
                    if add is None or sc > add[0]: add = (sc, j)
                if add is None or (len(team) >= eq.MIN_MIEMBROS and add[0] <= cur + 1e-4): break
                cur, team = add[0], team + [add[1]]
            if len(team) >= eq.MIN_MIEMBROS:
                teams[(pr, pi)] = (team, cur)
    return teams
out = {}
for B in [2020, 2021, 2022, 2023]:
    starts = [dt.date(B, m, 1) for m in range(1, 13, F)] + [dt.date(B + 1, 1, 1)]
    ks = [idx(d) if d.year == B else len(days) if B == 2023 else idx(d) for d in starts]
    fixed = form(slice(idx(dt.date(B - 1, 1, 1)), ks[0]))
    chain = {"fijo": {}, "movil": {}}
    for key in fixed: chain["fijo"][key] = [100.0]; chain["movil"][key] = [100.0]
    prev = fixed; nchange = 0
    for q in range(len(ks) - 1):
        a, b = ks[q], ks[q + 1]
        T = fixed if q == 0 else form(slice(max(0, a - VENT), a))
        for key in fixed:
            pr, pi = key
            for var, src in (("fijo", fixed), ("movil", T if key in T else prev)):
                if key not in src: src = fixed
                team = src[key][0]
                cap = chain[var][key][-1]
                chain[var][key] += list(simv(team, slice(a, b), pr, eq.PARAMS[pi], cap0=cap))
            if q and key in T and key in prev and sorted(T[key][0]) != sorted(prev[key][0]): nchange += 1
        prev = {**prev, **T}
        print(B, "tramo", q, flush=True)
    s = slice(ks[0], ks[-1])
    res = {}
    for var in chain:
        res[var] = {key: eq.stats(days[s], np.array(v[1:]) * 1.0) for key, v in chain[var].items()}
    out[B] = dict(res=res, fixedscore={k: v[1] for k, v in fixed.items()}, nchange=nchange)
    for var in res:
        st = list(res[var].values())
        print(B, var, "cumplen", sum(not eq.fails(x, goal) for x in st), "/", len(st),
              "ret med %+.0f%%" % (100 * np.median([x["ret"] for x in st])), "verde %.0f%%" % (100 * np.median([x["verde"] for x in st])),
              "dd %.0f%%" % (100 * np.median([x["dd"] for x in st])), "cambios", nchange, flush=True)
pickle.dump(out, open(os.path.join(S, f"mov_F{F}_V{VENT}.pkl"), "wb"))
