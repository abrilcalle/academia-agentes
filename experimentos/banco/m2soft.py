# Banco (11/11/2026): filtro de tendencia "suave" del equipo (conjunto de filtros). Parte de mat_raw.pkl (sin filtro, con el
# lado de cada operación abierta; m1raw.py con TEND=0 y el parche SIDES). Para cada operación abierta y día se miran K filtros
# de tendencia (media de N días + pendiente de L días, como trend_by_day) y w = parte de los K que van a favor.
#  SOFT=frac  -> el equipo le da w × lo que le daría (el resto espera en USDC); w = 0 -> bloqueada (P = -1)
#  SOFT=may   -> bloqueada si w < 0,5; si no, todo (mayoría)
#  SOFT=any   -> bloqueada solo si w = 0 (basta con uno a favor)
# VARS = "35:5,50:10,..." (N:L). Equipos formados y juzgados con la variante y el reparto medio (como ENS=post).
# Uso: SOFT=frac VARS=50:10 OUT=teams_X.pkl python m2soft.py  (VARS=50:10 con frac reproduce la base)
import os, sys, pickle, datetime as dt
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "lab", "src"))
import numpy as np
import equipos as eq, data as datamod
M = pickle.load(open(os.path.join(S, "mat_raw.pkl"), "rb"))
days = M["days"]
pos = {d: k for k, d in enumerate(days)}
VARS = [tuple(int(x) for x in v.split(":")) for v in os.environ.get("VARS", "50:10").split(",")]
SOFT = os.environ.get("SOFT", "frac")

def closes(a):
    c = datamod.load_csv(os.path.join(S, "loc", a.split("-")[0].lower() + "_1d.csv"))
    ks = sorted(k for k in c if k < dt.datetime(2024, 1, 1))
    return [k.date() for k in ks], np.array([c[k][3] for k in ks], float)

def trend(ds, c, n, l):
    ma = np.convolve(c, np.ones(n) / n, "full")[:len(c)]
    out = {}
    for i in range(n - 1 + l, len(c)):
        t = 1 if c[i] > ma[i] else -1
        if l and (ma[i] - ma[i - l]) * t <= 0: t = 0
        out[ds[i]] = t
    return out

TR = {}
for a in {i["activo"] for i in M["info"]}:
    ds, c = closes(a)
    TR[a] = [trend(ds, c, n, l) for n, l in VARS]
P = M["P"].copy(); Wm = np.ones_like(P)
for j, inf in enumerate(M["info"]):
    sd = M["sides"].get(inf["id"])
    if not sd: continue
    for d, s, e in zip(*sd):
        k = pos.get(d)
        if k is None or P[j, k] <= 0: continue
        vals = [tr.get(d) for tr in TR[inf["activo"]]]
        vals = [v for v in vals if v is not None]
        if not vals: continue
        w = sum(v * s > 0 for v in vals) / len(vals)
        if SOFT == "may": w = 1.0 if w >= 0.5 else 0.0
        elif SOFT == "any": w = 1.0 if w > 0 else 0.0
        if w <= 0: P[j, k] = -1.0
        Wm[j, k] = max(w, 0.0)
print("bloqueadas", int((P < 0).sum()), "parciales", int(((Wm > 0) & (Wm < 1) & (P > 0)).sum()), "abiertas", int((M["P"] > 0).sum()), flush=True)
if os.path.exists(os.path.join(S, "mat.pkl")):
    Pb = pickle.load(open(os.path.join(S, "mat.pkl"), "rb"))["P"]
    print("difiere del filtro del código en", int(((Pb < 0) != (P < 0)).sum()), "días-operación", flush=True)
M = dict(M); M["P"] = P; M.pop("sides")

fxd = {d.date(): v[3] for d, v in datamod.load_csv(os.path.join(S, "loc", "usdc_eur_1d.csv")).items()}
last = fxd[sorted(fxd)[0]]; lv = []
for d in days:
    last = fxd.get(d, last); lv.append(last)
lv = np.array(lv); FXR = np.r_[0.0, lv[1:] / lv[:-1] - 1]

def _al(Pc, Gc, pr, prm, Lc):
    if isinstance(prm, list):
        return np.mean([eq.alloc(Pc, Gc, pr, p, Lc) for p in prm], axis=0)
    return eq.alloc(Pc, Gc, pr, prm, Lc)

def simulate(R, E, P, G, prudencia, prm, cap0=100.0, L=None, fx=None, Wt=None):
    n, T = R.shape
    val = np.empty(T); F = np.zeros((n, T)); v = cap0; f_prev = np.zeros(n)
    for t in range(T):
        f = (_al(P[:, t - 1], G[:, t - 1], prudencia, prm, None if L is None else L[:, t - 1]) * Wt[:, t - 1] if t
             else _al(np.zeros(n), np.zeros(n), prudencia, prm, None))
        turnover = float(np.sum(np.abs(f - f_prev) * E[:, t - 1])) if t else 0.0
        idle = max(0.0, 1.0 - float(f.sum()))
        v *= 1 + float(np.dot(f, R[:, t])) + (idle * fx[t] if fx is not None else 0.0) - turnover * eq.COSTE_REPARTO
        val[t] = v; F[:, t] = f; f_prev = f
    return val, F

src = open(os.path.join(S, "m2x.py")).read()
src = src.replace("v, _ = eq.simulate(R[team, s], E[team, s], P[team, s], G[team, s], pr, prm, L=L[team, s])",
                  "v, _ = simulate(R[team, s], E[team, s], P[team, s], G[team, s], pr, prm, L=L[team, s], fx=FXR[s], Wt=Wm[team, s])")
assert "Wt=Wm" in src
ALL = list(eq.PARAMS)
src = src.replace('t["s"][y], t["v"][y] = sim(t["team"], y, t["pr"], t["prm"], full=True)',
                  't["s"][y], t["v"][y] = sim(t["team"], y, t["pr"], ALL, full=True)')
assert "ALL, full" in src
src = src.replace('S = os.path.dirname(os.path.abspath(__file__))', 'pass')
src = src.replace('M = pickle.load(open(os.path.join(S, os.environ.get("MAT", "mat.pkl")), "rb"))', 'pass')
exec(compile(src, "m2x", "exec"))
