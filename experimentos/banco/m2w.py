# Banco del laboratorio (30/10/2026): ¿cuántos años usar para FORMAR los equipos? (1, 2 o 3 años seguidos).
# Usa mat.pkl de m1. Guarda teamsw.pkl: {ventana(tupla de años): [equipos con stats en cada año de fuera]}.
import os, sys, pickle
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "lab", "src"))
import numpy as np
import equipos as eq
M = pickle.load(open(os.path.join(S, "mat.pkl"), "rb"))
days, R, E, P, G, L, info = M["days"], M["R"], M["E"], M["P"], M["G"], M["L"], M["info"]
goal = dict(semanas_en_verde_pct=50, ganancia_minima_anual_pct=10, caida_maxima_pct=25)
YRS = [2019, 2020, 2021, 2022, 2023]
idx = {y: [k for k, d in enumerate(days) if d.year == y] for y in YRS}
def slw(w): return slice(idx[w[0]][0], idx[w[-1]][-1] + 1)
def sim(team, s, pr, prm):
    v, _ = eq.simulate(R[team, s], E[team, s], P[team, s], G[team, s], pr, prm, L=L[team, s])
    return eq.stats(days[s], v)
def form(w):
    s = slw(w)
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
    # gemelos: ganar >= 10 % al año en la ventana (como en el banco de 1 año)
    def ann(j):
        st = eq.stats(days[s], 100 * np.cumprod(1 + R[j, s])); return eq.annual(st)
    shorts = sorted([j for j in keep if info[j]["short"] and R[j, s].std() > 0 and ann(j) >= 0.10], key=lambda j: -ann(j))
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
                    sc = eq.objective(sim(team + [j], s, pr, prm), goal)
                    if add is None or sc > add[0]: add = (sc, j)
                if add is None or (len(team) >= eq.MIN_MIEMBROS and add[0] <= cur + 1e-4): break
                cur, team = add[0], team + [add[1]]
            if len(team) >= eq.MIN_MIEMBROS:
                teams.append(dict(team=team, pr=pr, prm=prm))
    return teams
W = [(y,) for y in YRS] + [tuple(YRS[i:i + 2]) for i in range(4)] + [tuple(YRS[i:i + 3]) for i in range(3)]
out = {}
for w in W:
    T = form(w)
    for t in T:
        t["s"] = {y: sim(t["team"], slw((y,)), t["pr"], t["prm"]) for y in YRS if y not in w}
    out[w] = T
    print("formado", w, len(T), flush=True)
pickle.dump(out, open(os.path.join(S, "teamsw.pkl"), "wb"))
