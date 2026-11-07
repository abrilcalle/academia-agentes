# Banco (07/11/2026): m2x con el dinero sin repartir del equipo en USDC (sigue el cambio USDC/EUR) en vez de quieto en euros.
# Uso: FX=1 OUT=teams_fx.pkl python m2fx.py  (FX=0 = como el código actual)
import os, sys, pickle, datetime as dt
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "lab", "src"))
import numpy as np
import equipos as eq, data as datamod
M = pickle.load(open(os.path.join(S, os.environ.get("MAT", "mat.pkl")), "rb"))
days = M["days"]
fxd = {d.date(): v[3] for d, v in datamod.load_csv(os.path.join(S, "loc", "usdc_eur_1d.csv")).items()}
ks = sorted(fxd); last = fxd[ks[0]]; lv = []
for d in days:
    last = fxd.get(d, last); lv.append(last)
lv = np.array(lv); FXR = np.r_[0.0, lv[1:] / lv[:-1] - 1]
USE = os.environ.get("FX", "1") == "1"
COST = float(os.environ.get("FXCOST", "0"))
_orig = eq.simulate
def simulate(R, E, P, G, prudencia, prm, cap0=100.0, L=None, fx=None):
    n, T = R.shape
    val = np.empty(T); F = np.zeros((n, T)); v = cap0; f_prev = np.zeros(n)
    for t in range(T):
        f = (eq.alloc(P[:, t - 1], G[:, t - 1], prudencia, prm, None if L is None else L[:, t - 1]) if t
             else eq.alloc(np.zeros(n), np.zeros(n), prudencia, prm))
        turnover = float(np.sum(np.abs(f - f_prev) * E[:, t - 1])) if t else 0.0
        idle = max(0.0, 1.0 - float(f.sum()))
        v *= 1 + float(np.dot(f, R[:, t])) + (idle * fx[t] if fx is not None else 0.0) - turnover * eq.COSTE_REPARTO
        val[t] = v; F[:, t] = f; f_prev = f
    return val, F
src = open(os.path.join(S, "m2x.py")).read()
src = src.replace("v, _ = eq.simulate(R[team, s], E[team, s], P[team, s], G[team, s], pr, prm, L=L[team, s])",
                  "v, _ = simulate(R[team, s], E[team, s], P[team, s], G[team, s], pr, prm, L=L[team, s], fx=FXR[s] if USE else None)")
assert "fx=FXR" in src
src = src.replace('S = os.path.dirname(os.path.abspath(__file__))', 'pass')
exec(compile(src, "m2x", "exec"))
