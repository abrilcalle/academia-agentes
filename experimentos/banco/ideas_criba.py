# Criba de ideas (28/10/2026 21:15): cada idea de ideas/ tal cual, sin evolucionar, en entreno 2018-21 y validación 2022-23 por mercado y temporalidad.
# Uso: igual que m1 (carpeta con lab/ y loc/); python3 ideas_criba.py 1d   (o 4h, 1h). Guarda s1_<tf>.pkl.
"""Cribado: cada idea de internet tal cual (sin evolucionar) en entreno 2018-21 y validación 2022-23, por mercado y temporalidad.
Datos cortados el 01/01/2024."""
import datetime as dt, json, os, sys, pickle, time
S = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.join(S, "lab")
sys.path.insert(0, LAB); sys.path.insert(0, os.path.join(LAB, "src"))
import numpy as np
import run_daily as rd, data as datamod, inventor, diario
from academia import Academia
from backtest import run
cfg = json.load(open(os.path.join(LAB, "config.json")))
today = dt.date(2024, 1, 1)
loc = os.path.join(S, "loc")
mk = rd.load_markets(cfg, loc, today, True)
otros = rd.load_other_assets(cfg, loc, today, True)
fx = {d.date(): v[3] for d, v in datamod.load_csv(os.path.join(loc, "usdc_eur_1d.csv")).items()}
for g in [mk] + list(otros.values()):
    for m in g.values():
        m.set_fx(fx)
ac = Academia(LAB, mk, kronos={}, today=today, otros=otros, log=lambda *a: None)
ac.cfg["cotizar_en_usdc"] = True
rc = ac.run_cfg()
TFS = sys.argv[1].split(",") if len(sys.argv) > 1 else ["1d", "4h"]
out = {}
t0 = time.time()
for act in ["BTC-EUR", "ETH-EUR", "XRP-EUR", "SOL-EUR"]:
    for tf in TFS:
        ag = dict(id="x", activo=act, tf=tf)
        if not ac.has_market(ag):
            continue
        m = ac.m(ag)
        mtr, _ = ac.train_market(ag, None)
        tr = ac.window(mtr, "entreno"); va = ac.window(m, "validacion")
        ideas = ac.ideas_for(act)
        for idea in ideas:
            r = idea["regla"]
            res = {}
            for nm, M, win in (("tr", mtr, tr), ("va", m, va)):
                w = inventor.exposure(M.I, r, None, M.bpd)
                sc = {}
                for tname, temper in (("eq", 1.0),):
                    s, full = inventor.robust(M, w, win, rc, temper)
                # por año
                y0, y1 = M.ts[win[0]].year, M.ts[win[1]].year
                yrs = {}
                for y in range(y0, y1 + 1):
                    ya, yb = max(win[0], M.idx(f"{y}-01-01")), min(win[1], M.end_idx(f"{y}-12-31"))
                    if yb - ya < 60 * M.bpd:
                        continue
                    ry = run(M.I, w, ya, yb, rc)
                    yrs[y] = (ry.ret, ry.maxdd, ry.n_buys)
                res[nm] = dict(score=s, ret=full.ret, dd=full.maxdd, n=full.n_buys, avg=full.avg_trade if full.closed else 0, yrs=yrs)
            out[(act, tf, idea["nombre"])] = res
        print(act, tf, len(ideas), f"{time.time()-t0:.0f}s", flush=True)
        pickle.dump(out, open(os.path.join(S, f"s1_{'_'.join(TFS)}.pkl"), "wb"))
print("ok", len(out))
