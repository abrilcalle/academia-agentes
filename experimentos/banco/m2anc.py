# Banco (04/11/2026 tarde): "ancla de tendencia". El dinero del equipo que no usa nadie se pone en el propio
# mercado (BTC, o los mercados del equipo) solo cuando ese mercado está en tendencia alcista (filtro del equipo:
# media de 50 días + pendiente de 10). Uso: python m2anc.py VARIANTE  (base | btc_libre_1 | mix_libre_1 | btc_ocioso_05 | mix_ocioso_1 ...)
# Necesita mat.pkl (m1.py). Forma equipos con la variante (como haría build), y guarda teams_VARIANTE.pkl con stats por año.
import os, sys, pickle, json, datetime as dt
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "lab", "src"))
import numpy as np
import equipos as eq, data as datamod
VAR = sys.argv[1]
M = pickle.load(open(os.path.join(S, "mat.pkl"), "rb"))
days, R, E, P, G, L, info = M["days"], M["R"], M["E"], M["P"], M["G"], M["L"], M["info"]
goal = dict(semanas_en_verde_pct=50, ganancia_minima_anual_pct=10, caida_maxima_pct=25)
YRS = [2019, 2020, 2021, 2022, 2023]
rng_ = {y: [k for k, d in enumerate(days) if d.year == y] for y in YRS}
sl = {y: slice(rng_[y][0], rng_[y][-1] + 1) for y in YRS}
# rentabilidad diaria en euros y tendencia (conocida al cierre del día anterior) de cada mercado
AR, AT = {}, {}
for a, short in [("BTC-EUR", "btc"), ("ETH-EUR", "eth"), ("SOL-EUR", "sol"), ("XRP-EUR", "xrp")]:
    d1 = datamod.load_csv(os.path.join(S, "loc", f"{short}_1d.csv"))
    ks = sorted(d1)
    c = np.array([d1[k][3] for k in ks], float)
    ma = np.convolve(c, np.ones(50) / 50, "full")[:len(c)]
    cl = {k.date(): c[i] for i, k in enumerate(ks)}
    tr = {}
    for i in range(59, len(c)):
        tr[ks[i].date()] = 1 if (c[i] > ma[i] and ma[i] - ma[i - 10] > 0) else 0
    r = np.zeros(len(days)); t = np.zeros(len(days))
    for k, d in enumerate(days):
        p0 = cl.get(d - dt.timedelta(days=1)); p1 = cl.get(d)
        if p0 and p1: r[k] = p1 / p0 - 1
        t[k] = tr.get(d - dt.timedelta(days=1), 0)
    AR[a], AT[a] = r, t

if VAR == "base":
    MODO = None
else:
    asset, modo, w = VAR.split("_"); W = float(w.replace("05", "0.5")) if w != "1" else 1.0
    MODO = (asset, modo, W)


def simv(team, s, pr, prm):
    if MODO is None:
        v, _ = eq.simulate(R[team, s], E[team, s], P[team, s], G[team, s], pr, prm, L=L[team, s])
        return v
    asset, modo, W = MODO
    Rt, Et, Pt, Gt, Lt = R[team, s], E[team, s], P[team, s], G[team, s], L[team, s]
    assets = ["BTC-EUR"] if asset == "btc" else sorted({info[i]["activo"] for i in team})
    ar = np.array([AR[a][s] for a in assets]); at = np.array([AT[a][s] for a in assets])
    n, T = Rt.shape
    val = np.empty(T); v = 100.0; f_prev = np.zeros(n); a_prev = np.zeros(len(assets))
    for t in range(T):
        f = eq.alloc(Pt[:, t - 1], Gt[:, t - 1], pr, prm, Lt[:, t - 1]) if t else eq.alloc(np.zeros(n), np.zeros(n), pr, prm)
        used = f.sum() if modo == "libre" else (float(np.dot(f, Et[:, t - 1])) if t else 0.0)
        free = max(0.0, 1.0 - used) * W
        up = at[:, t] > 0
        a = np.zeros(len(assets))
        if up.any():
            a[up] = free / up.sum()
        turnover = (float(np.sum(np.abs(f - f_prev) * Et[:, t - 1])) if t else 0.0) + float(np.abs(a - a_prev).sum())
        v *= 1 + float(np.dot(f, Rt[:, t])) + float(np.dot(a, ar[:, t])) - turnover * eq.COSTE_REPARTO
        val[t] = v; f_prev = f; a_prev = a
    return val


def sim(team, y, pr, prm):
    return eq.stats(days[sl[y]], simv(team, sl[y], pr, prm))


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
        t["s"] = {y: sim(t["team"], y, t["pr"], t["prm"]) for y in YRS if y != A}
    out[A] = T
    print(VAR, "formado", A, len(T), flush=True)
pickle.dump(out, open(os.path.join(S, f"teams_{VAR}.pkl"), "wb"))
