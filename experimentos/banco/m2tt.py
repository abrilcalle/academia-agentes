# Banco (09/11/2026): "equipo de equipos" y "equipo consenso". Lee teams_post.pkl (m2ens.py ENS=post) y, por año de formación
# y prudencia, junta las formaciones de las 18 búsquedas:
#  union = un solo equipo por prudencia que reparte cada día la MEDIA de los repartos de todos sus equipos distintos (puede tener >6 agentes)
#  cons  = equipo de 3-6 agentes con los que más veces salen elegidos en las 18 búsquedas (como mucho 2 por mercado), reparto medio
#  consN = como cons pero con tamaño fijo N
import os, sys, pickle, collections
S = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(S, "lab", "src"))
import numpy as np, equipos as eq, data as datamod
M = pickle.load(open(os.path.join(S, "mat.pkl"), "rb"))
days, R, E, P, G, L, info = M["days"], M["R"], M["E"], M["P"], M["G"], M["L"], M["info"]
fxd = {d.date(): v[3] for d, v in datamod.load_csv(os.path.join(S, "loc", "usdc_eur_1d.csv")).items()}
ks = sorted(fxd); last = fxd[ks[0]]; lv = []
for d in days:
    last = fxd.get(d, last); lv.append(last)
lv = np.array(lv); FXR = np.r_[0.0, lv[1:] / lv[:-1] - 1]
YRS = [2019, 2020, 2021, 2022, 2023]
rng_ = {y: [k for k, d in enumerate(days) if d.year == y] for y in YRS}
sl = {y: slice(rng_[y][0], rng_[y][-1] + 1) for y in YRS}
MED = dict(medio=True)
T = pickle.load(open(os.path.join(S, "teams_post.pkl"), "rb"))
cacheF = {}
def Fteam(team, pr, y):
    k = (tuple(team), pr, y)
    if k not in cacheF:
        s = sl[y]
        _, F = eq.simulate(R[team, s], E[team, s], P[team, s], G[team, s], pr, MED, L=L[team, s], fx=FXR[s])
        cacheF[k] = F
    return cacheF[k]
def sim_union(teams, pr, y):
    U = sorted({j for t in teams for j in t})
    pos = {j: i for i, j in enumerate(U)}
    s = sl[y]; Tn = s.stop - s.start
    f = np.zeros((len(U), Tn))
    for t in teams:
        Ft = Fteam(t, pr, y)
        for a, j in enumerate(t):
            f[pos[j]] += Ft[a] / len(teams)
    Rr, Ee, fx = R[U, s], E[U, s], FXR[s]
    v, val, fp = 100.0, np.empty(Tn), np.zeros(len(U))
    for k in range(Tn):
        to = float(np.sum(np.abs(f[:, k] - fp) * Ee[:, k - 1])) if k else 0.0
        idle = max(0.0, 1 - f[:, k].sum()) * fx[k]
        v *= 1 + float(f[:, k] @ Rr[:, k]) + idle - to * eq.COSTE_REPARTO
        val[k] = v; fp = f[:, k]
    return eq.stats(days[s], val), U
def sim_team(team, pr, y):
    s = sl[y]
    v, _ = eq.simulate(R[team, s], E[team, s], P[team, s], G[team, s], pr, MED, L=L[team, s], fx=FXR[s])
    return eq.stats(days[s], v)
def consenso(lst, n=None):
    cnt = collections.Counter(j for t in lst for j in t)
    first = {}
    for t in lst:
        for r, j in enumerate(t):
            first.setdefault(j, r + 100 * lst.index(t))
    size = n or int(round(np.median([len(t) for t in lst])))
    team = []
    for j in sorted(cnt, key=lambda j: (-cnt[j], first[j])):
        if sum(info[i]["activo"] == info[j]["activo"] for i in team) >= eq.MAX_POR_ACTIVO: continue
        team.append(j)
        if len(team) >= size: break
    return team
VAR = sys.argv[1]
out = {}
for A in YRS:
    out[A] = []
    for pr in eq.PRUDENCIAS:
        lst = [t["team"] for t in T[A] if t["pr"] == pr]
        if not lst: continue
        if VAR == "union":
            dist = []
            for t in lst:
                if sorted(t) not in [sorted(d) for d in dist]: dist.append(t)
            d = dict(team=None, pr=pr, s={}, ndist=len(dist))
            for y in YRS:
                d["s"][y], d["team"] = sim_union(dist, pr, y)
        else:
            n = int(VAR[4:]) if len(VAR) > 4 else None
            tm = consenso(lst, n)
            d = dict(team=tm, pr=pr, s={y: sim_team(tm, pr, y) for y in YRS})
        out[A].append(d)
    print(VAR, A, [(len(d["team"]), d.get("ndist")) for d in out[A]], flush=True)
pickle.dump(out, open(os.path.join(S, f"teams_{VAR}.pkl"), "wb"))
