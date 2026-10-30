# Especialistas bajistas (30/10/2026): ideas de corto con filtro estricto de mercado bajista. Uso: python3 bear1.py 1d (y 4h), luego bear2.py.
# Especialistas bajistas: cada idea de corto de ideas/, tal cual y con filtro de mercado bajista, por año 2018-2023.
import datetime as dt, json, os, sys, pickle, time
S = os.path.dirname(os.path.abspath(__file__)); LAB = os.path.join(S, "lab")
sys.path.insert(0, LAB); sys.path.insert(0, os.path.join(LAB, "src"))
import numpy as np
import run_daily as rd, data as datamod, inventor, diario
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
TFS = sys.argv[1].split(","); out = {}; t0 = time.time()
for act in ["BTC-EUR", "ETH-EUR", "XRP-EUR"]:
    for tf in TFS:
        ag = dict(id="x", activo=act, tf=tf); M = ac.m(ag); I = M.I
        with np.errstate(invalid="ignore"):
            s200 = I.sma(200 * M.bpd)
            g1 = np.nan_to_num(I.c < s200).astype(bool)
            s200p = np.roll(s200, 20 * M.bpd)
            g2 = g1 & np.nan_to_num(s200 < s200p).astype(bool) & np.nan_to_num(I.sma(50 * M.bpd) < s200).astype(bool)
        yr = {}
        for y in range(2018, 2024):
            ya, yb = max(M.idx(f"{y}-01-01"), 200 * M.bpd + 25 * M.bpd), M.end_idx(f"{y}-12-31")
            yr[y] = (ya, yb)
        def peryear(w):
            o = {}
            for y, (a, b) in yr.items():
                r = run(I, w, a, b, rc); o[y] = (r.ret, r.maxdd, r.n_buys)
            return o
        out[(act, tf, "_flat")] = {"raw": peryear(np.zeros(I.n))}
        for idea in ac.ideas_for(act):
            if idea["regla"].get("lado") != "corto": continue
            w = np.asarray(inventor.exposure(I, idea["regla"], None, M.bpd))
            out[(act, tf, idea["nombre"])] = {"raw": peryear(w), "g1": peryear(w * g1), "g2": peryear(w * g2)}
        print(act, tf, f"{time.time()-t0:.0f}s", flush=True)
        pickle.dump(out, open(os.path.join(S, f"bear_{'_'.join(TFS)}.pkl"), "wb"))
