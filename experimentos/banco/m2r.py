# Banco de pruebas del laboratorio (31/10/2026): filtro de fuerza relativa entre mercados (BTC, ETH, SOL, XRP).
# Uso: python m2r.py VARIANTE  (base | rsN_mitad | rsN_top1). Necesita mat.pkl de m1.py. Guarda teams_VARIANTE.pkl.
# Para cada día y cada agente con operación abierta (no bloqueada por la tendencia de 50 días, así que su lado = signo de esa
# tendencia): un largo solo recibe dinero si su mercado está entre los más fuertes por impulso de N días; un corto, si está
# entre los más débiles. Si no, P = BLOQUEADO (como el filtro de tendencia). Se forman los equipos con ese P y se miden en todos los años.
import datetime as dt, os, sys, pickle, json
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "lab", "src"))
import numpy as np
import equipos as eq, data as datamod
var = sys.argv[1]
M = pickle.load(open(os.path.join(S, "mat.pkl"), "rb"))
days, R, E, P, G, L, info = M["days"], M["R"], M["E"], M["P"], M["G"], M["L"], M["info"]
ASSETS = ["BTC-EUR", "ETH-EUR", "SOL-EUR", "XRP-EUR"]
close = {}
for a in ASSETS:
    d = datamod.load_csv(os.path.join(S, "loc", a.split("-")[0].lower() + "_1d.csv"))
    close[a] = {k.date(): v[3] for k, v in d.items() if k.date() < dt.date(2024, 1, 1)}


def mom(a, d, n):
    c0, c1 = close[a].get(d - dt.timedelta(days=n)), close[a].get(d)
    return None if c0 is None or c1 is None else c1 / c0 - 1


def trend(a, d, n=50):
    xs = [close[a].get(d - dt.timedelta(days=i)) for i in range(n)]
    if any(x is None for x in xs): return 0
    return 1 if xs[0] > np.mean(xs) else -1


if var != "base":
    n = int(var[2:].split("_")[0]); modo = var.split("_")[1]
    P = P.copy()
    blocked = opened = 0
    for k, d in enumerate(days):
        m = {a: mom(a, d, n) for a in ASSETS}
        m = {a: v for a, v in m.items() if v is not None}
        order = sorted(m, key=lambda a: -m[a])
        na = len(order)
        top = order[:1] if modo == "top1" else order[:(na + 1) // 2]
        bot = order[-1:] if modo == "top1" else order[na // 2:]
        for j in range(len(info)):
            if P[j, k] <= 0: continue
            a = info[j]["activo"]
            if a not in m: continue
            opened += 1
            side = trend(a, d)
            if (side > 0 and a not in top) or (side < 0 and a not in bot):
                P[j, k] = eq.BLOQUEADO; blocked += 1
    print(var, "bloqueadas", blocked, "de", opened, flush=True)

goal = dict(semanas_en_verde_pct=50, ganancia_minima_anual_pct=10, caida_maxima_pct=25)
YRS = [2019, 2020, 2021, 2022, 2023]
rng_ = {y: [k for k, d in enumerate(days) if d.year == y] for y in YRS}
sl = {y: slice(rng_[y][0], rng_[y][-1] + 1) for y in YRS}


def sim(team, y, pr, prm):
    s = sl[y]
    v, _ = eq.simulate(R[team, s], E[team, s], P[team, s], G[team, s], pr, prm, L=L[team, s])
    return eq.stats(days[s], v)


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
    print(var, "formado", A, len(T), flush=True)
pickle.dump(out, open(os.path.join(S, f"teams_{var}.pkl"), "wb"))
