# Banco (17/11/2026): "prueba de estrés bajista" al formar los equipos.
# Los equipos se forman con un año de subida A (como build con 2024–25) pero la nota con la que se añaden agentes
# mezcla la de A con la de un año bajista S (2018 o 2022). Se juzgan en el OTRO año bajista (limpio) y en los años de subida.
# Uso: VAR=base|w25|w50|min MAT=mat18.pkl OUT=stress_VAR.pkl python m2stress.py
import os, sys, pickle
S_ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S_, "lab", "src"))
import numpy as np
import equipos as eq, data as datamod
eq.COSTE_REPARTO = 0.0008
M = pickle.load(open(os.path.join(S_, os.environ.get("MAT", "mat18.pkl")), "rb"))
days, R, E, P, G, L, info = M["days"], M["R"], M["E"], M["P"], M["G"], M["L"], M["info"]
goal = dict(semanas_en_verde_pct=50, ganancia_minima_anual_pct=10, caida_maxima_pct=25)
YRS = [2018, 2019, 2020, 2021, 2022, 2023]
BULL, BEAR = [2019, 2020, 2021, 2023], [2018, 2022]
idx = {y: [k for k, d in enumerate(days) if d.year == y] for y in YRS}
sl = {y: slice(idx[y][0], idx[y][-1] + 1) for y in YRS}
fxd = {d.date(): v[3] for d, v in datamod.load_csv(os.path.join(S_, "loc", "usdc_eur_1d.csv")).items()}
last = fxd[min(fxd)]; lv = []
for d in days:
    last = fxd.get(d, last); lv.append(last)
lv = np.array(lv); FXR = np.r_[0.0, lv[1:] / lv[:-1] - 1]
VAR = os.environ.get("VAR", "base")
ALL = list(eq.PARAMS)


def _al(Pc, Gc, pr, prm, Lc):
    if isinstance(prm, list):
        return np.mean([eq.alloc(Pc, Gc, pr, p, Lc) for p in prm], axis=0)
    return eq.alloc(Pc, Gc, pr, prm, Lc)


def simulate(R, E, P, G, pr, prm, L, fx, cap0=100.0):
    n, T = R.shape
    val = np.empty(T); v = cap0; f_prev = np.zeros(n)
    for t in range(T):
        f = _al(P[:, t - 1], G[:, t - 1], pr, prm, L[:, t - 1]) if t else _al(np.zeros(n), np.zeros(n), pr, prm, None)
        turnover = float(np.sum(np.abs(f - f_prev) * E[:, t - 1])) if t else 0.0
        idle = max(0.0, 1.0 - float(f.sum()))
        v *= 1 + float(np.dot(f, R[:, t])) + idle * fx[t] - turnover * eq.COSTE_REPARTO
        val[t] = v; f_prev = f
    return val


def sim(team, y, pr, prm):
    s = sl[y]
    return eq.stats(days[s], simulate(R[team, s], E[team, s], P[team, s], G[team, s], pr, prm, L[team, s], FXR[s]))


def nota(team, A, S, pr, prm):
    a = eq.objective(sim(team, A, pr, prm), goal)
    if VAR == "base" or S is None:
        return a
    b = eq.objective(sim(team, S, pr, prm), goal)
    if VAR == "w25": return 0.75 * a + 0.25 * b
    if VAR == "w50": return 0.5 * a + 0.5 * b
    if VAR == "min": return min(a, b)
    if VAR == "veto":  # solo castiga si en S cae más del 25 % o pierde más de un 10 %
        sb = sim(team, S, pr, prm)
        return a - 3 * (max(0.0, sb["dd"] - 0.25) * 2 + max(0.0, -0.10 - sb["ret"]))
    raise SystemExit(VAR)


def form(A, S):
    s = sl[A]; n = len(info)
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
                    sc = nota(team + [j], A, S, pr, prm)
                    if add is None or sc > add[0]: add = (sc, j)
                if add is None or (len(team) >= eq.MIN_MIEMBROS and add[0] <= cur + 1e-4): break
                cur, team = add[0], team + [add[1]]
            if len(team) >= eq.MIN_MIEMBROS:
                teams.append(dict(team=team, pr=pr, prm=prm))
    # sin repetidos (mismos miembros y prudencia), y se juzgan con el reparto medio (como el código)
    seen, out = set(), []
    for t in teams:
        k = (tuple(sorted(t["team"])), t["pr"])
        if k in seen: continue
        seen.add(k); out.append(t)
    for t in out:
        t["s"] = {y: sim(t["team"], y, t["pr"], ALL) for y in YRS}
    return out


res = {}
pairs = [(A, None) for A in BULL] if VAR == "base" else [(A, S) for A in BULL for S in BEAR]
for A, S in pairs:
    res[(A, S)] = form(A, S)
    print("formado", A, S, len(res[(A, S)]), flush=True)
pickle.dump(res, open(os.path.join(S_, os.environ.get("OUT", f"stress_{VAR}.pkl")), "wb"))
