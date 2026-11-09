# Laboratorio 09/11/2026 21:00: "vender los rebotes en mercado bajista" (y comprar retrocesos en alcista), velas diarias.
# Régimen bajista: cierre < media 200 y media 50 < media 200. Entrada corto: el RSI14 venía de >= X y cruza hacia abajo
# (rebote fallido) o el cierre vuelve a perder la media 20 tras estar encima. Salida: tras H días, o cierre > media 50, o régimen roto.
import datetime as dt, json, os, sys, pickle, itertools
S = os.path.dirname(os.path.abspath(__file__)); LAB = os.path.join(S, "lab")
sys.path.insert(0, LAB); sys.path.insert(0, os.path.join(LAB, "src"))
import numpy as np
import run_daily as rd, data as datamod, diario
from academia import Academia
from backtest import run
cfg = json.load(open(os.path.join(LAB, "config.json")))
today = dt.date(2024, 1, 1); loc = os.path.join(S, "loc")
mk = rd.load_markets(cfg, loc, today, True); otros = rd.load_other_assets(cfg, loc, today, True)
fx = {d.date(): v[3] for d, v in datamod.load_csv(os.path.join(loc, "usdc_eur_1d.csv")).items()}
for g in [mk] + list(otros.values()):
    for m in g.values(): m.set_fx(fx)
ac = Academia(LAB, mk, kronos={}, today=today, otros=otros, log=lambda *a: None)
ac.cfg["cotizar_en_usdc"] = True; rc = ac.run_cfg(); diario.ALLOW_SHORT = True
def rsi(c, n=14):
    d = np.diff(c, prepend=c[0]); up = np.where(d > 0, d, 0.0); dn = np.where(d < 0, -d, 0.0)
    au = np.zeros_like(c); ad = np.zeros_like(c); a = 1.0 / n
    for i in range(1, len(c)):
        au[i] = au[i-1] * (1 - a) + up[i] * a; ad[i] = ad[i-1] * (1 - a) + dn[i] * a
    return 100 - 100 / (1 + au / np.maximum(ad, 1e-12))
def rule(I, side, trig, X, H, ex):
    c = I.c; n = len(c)
    s20, s50, s200 = I.sma(20), I.sma(50), I.sma(200)
    r = rsi(c)
    with np.errstate(invalid="ignore"):
        if side < 0:
            reg = (c < s200) & (s50 < s200)
            if trig == "rsi": ent = (np.roll(r, 1) >= X) & (r < X)
            else: ent = (np.roll(c, 1) > np.roll(s20, 1)) & (c < s20)
            brk = (c > s50) if ex == "m50" else (c > s200)
        else:
            reg = (c > s200) & (s50 > s200)
            Xl = 100 - X
            if trig == "rsi": ent = (np.roll(r, 1) <= Xl) & (r > Xl)
            else: ent = (np.roll(c, 1) < np.roll(s20, 1)) & (c > s20)
            brk = (c < s50) if ex == "m50" else (c < s200)
    reg = np.nan_to_num(reg).astype(bool); ent = np.nan_to_num(ent).astype(bool) & reg; brk = np.nan_to_num(brk).astype(bool)
    w = np.zeros(n); k = -1
    for i in range(200, n):
        if k >= 0:
            if (i - k) >= H or brk[i] or not reg[i]: k = -1
        if k < 0 and ent[i]: k = i
        w[i] = side if k >= 0 else 0.0
    return w
out = {}
for act in ["BTC-EUR", "ETH-EUR", "XRP-EUR"]:
    ag = dict(id="x", activo=act, tf="1d"); M = ac.m(ag); I = M.I
    yr = {y: (max(M.idx(f"{y}-01-01"), 210), M.end_idx(f"{y}-12-31")) for y in range(2018, 2024)}
    def py(w):
        return {y: (run(I, w, a, b, rc).ret, run(I, w, a, b, rc).maxdd) for y, (a, b) in yr.items()}
    out[(act, "flat")] = py(np.zeros(I.n))
    for side, trig, X, H, ex in itertools.product([-1, 1], ["rsi", "m20"], [50, 55, 60, 65], [5, 10, 20, 40], ["m50", "m200"]):
        if trig == "m20" and X != 50: continue
        out[(act, side, trig, X, H, ex)] = py(rule(I, side, trig, X, H, ex))
    print(act, flush=True)
pickle.dump(out, open(os.path.join(S, "rebote.pkl"), "wb"))
