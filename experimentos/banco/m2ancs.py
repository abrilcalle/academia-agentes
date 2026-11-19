# Banco (19/11/2026 mañana): "ancla bajista". El dinero que el equipo no reparte (en USDC) se pone en CORTO (sin apalancamiento)
# en el propio mercado solo cuando ese mercado está en tendencia bajista con el filtro del equipo (cierre < media de 50 días y la
# media bajando en 10 días; conocido al cierre del día anterior). Paga el interés del préstamo (0,0023 %/h) y el coste de reparto.
# Lo contrario del "ancla de tendencia" del 04/11 (que solo compraba y no ayudaba en 2022).
# Uso: VAR=base|btc_05|btc_1|mix_1|btc200_1|mix200_05 COSTE=0.0008 OUT=teams_X.pkl python m2ancs.py  (sobre mat.pkl de m1.py; reparto medio "post")
#   btc = solo BTC · mix = los mercados del equipo en bajada (a partes iguales) · 200 = además cierre < media de 200 días · _W = parte del dinero libre
import os, sys, pickle, datetime as dt
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "lab", "src"))
import numpy as np
import equipos as eq, data as datamod
eq.COSTE_REPARTO = float(os.environ.get("COSTE", "0.0008"))
VAR = os.environ.get("VAR", "base")
INT_DIA = 0.0023 / 100 * 24
M = pickle.load(open(os.path.join(S, os.environ.get("MAT", "mat.pkl")), "rb"))
days = M["days"]; info = M["info"]
fxd = {d.date(): v[3] for d, v in datamod.load_csv(os.path.join(S, "loc", "usdc_eur_1d.csv")).items()}
ks = sorted(fxd); last = fxd[ks[0]]; lv = []
for d in days:
    last = fxd.get(d, last); lv.append(last)
lv = np.array(lv); FXR = np.r_[0.0, lv[1:] / lv[:-1] - 1]
# rentabilidad diaria en USDC de cada mercado y señal bajista (conocida al cierre del día anterior)
AR, AT = {}, {}
L200 = "200" in VAR
for a, short in [("BTC-EUR", "btc"), ("ETH-EUR", "eth"), ("SOL-EUR", "sol"), ("XRP-EUR", "xrp")]:
    d1 = datamod.load_csv(os.path.join(S, "loc", f"{short}_1d.csv"))
    kk = sorted(k for k in d1 if k < dt.datetime(2024, 1, 1))
    c = np.array([d1[k][3] for k in kk], float)
    ma = np.convolve(c, np.ones(50) / 50, "full")[:len(c)]
    m2 = np.convolve(c, np.ones(200) / 200, "full")[:len(c)]
    cl = {k.date(): c[i] for i, k in enumerate(kk)}
    tr = {}
    for i in range(60, len(c)):
        b = c[i] < ma[i] and ma[i] - ma[i - 10] < 0
        if L200: b = b and i >= 200 and c[i] < m2[i]
        tr[kk[i].date()] = 1 if b else 0
    r = np.zeros(len(days)); t = np.zeros(len(days))
    for k, d in enumerate(days):
        p0 = cl.get(d - dt.timedelta(days=1)); p1 = cl.get(d)
        if p0 and p1: r[k] = (p1 / p0) / (1 + FXR[k]) - 1      # en USDC
        t[k] = tr.get(d - dt.timedelta(days=1), 0)
    AR[a], AT[a] = r, t
if VAR == "base":
    MODO = None
else:
    asset, w = VAR.split("_"); MODO = (asset.replace("200", ""), float(w.replace("05", "0.5").replace("025", "0.25")))
print("VAR", VAR, MODO, "COSTE", eq.COSTE_REPARTO, flush=True)
ALL = list(eq.PARAMS)


def simulate(R, E, P, G, prudencia, prm, cap0=100.0, L=None, fx=None, team=None, s=None):
    n, T = R.shape
    val = np.empty(T); F = np.zeros((n, T)); v = cap0; f_prev = np.zeros(n)
    if MODO:
        assets = ["BTC-EUR"] if MODO[0] == "btc" else sorted({info[i]["activo"] for i in team})
        ar = np.array([AR[a][s] for a in assets]); at = np.array([AT[a][s] for a in assets])
        a_prev = np.zeros(len(assets))
    for t in range(T):
        Pc, Gc, Lc = (P[:, t - 1], G[:, t - 1], None if L is None else L[:, t - 1]) if t else (np.zeros(n), np.zeros(n), None)
        f = np.mean([eq.alloc(Pc, Gc, prudencia, p, Lc) for p in prm], axis=0) if isinstance(prm, list) else eq.alloc(Pc, Gc, prudencia, prm, Lc)
        turnover = float(np.sum(np.abs(f - f_prev) * E[:, t - 1])) if t else 0.0
        idle = max(0.0, 1.0 - float(f.sum()))
        anc = 0.0
        if MODO:
            dn = at[:, t] > 0
            a = np.zeros(len(assets))
            if dn.any(): a[dn] = idle * MODO[1] / dn.sum()
            turnover += float(np.abs(a - a_prev).sum()); a_prev = a
            anc = float(np.dot(a, -ar[:, t] - INT_DIA))     # el colchón sigue en USDC (cuenta en idle*fx)
        v *= 1 + float(np.dot(f, R[:, t])) + idle * fx[t] + anc - turnover * eq.COSTE_REPARTO
        val[t] = v; F[:, t] = f; f_prev = f
    return val, F


src = open(os.path.join(S, "m2x.py")).read()
src = src.replace("v, _ = eq.simulate(R[team, s], E[team, s], P[team, s], G[team, s], pr, prm, L=L[team, s])",
                  "v, _ = simulate(R[team, s], E[team, s], P[team, s], G[team, s], pr, prm, L=L[team, s], fx=FXR[s], team=team, s=s)")
assert "team=team, s=s" in src
src = src.replace('t["s"][y], t["v"][y] = sim(t["team"], y, t["pr"], t["prm"], full=True)',
                  't["s"][y], t["v"][y] = sim(t["team"], y, t["pr"], ALL, full=True)')
assert "ALL, full" in src
src = src.replace('S = os.path.dirname(os.path.abspath(__file__))', 'pass')
src = src.replace('M = pickle.load(open(os.path.join(S, os.environ.get("MAT", "mat.pkl")), "rb"))', 'pass')
exec(compile(src, "m2x", "exec"))
