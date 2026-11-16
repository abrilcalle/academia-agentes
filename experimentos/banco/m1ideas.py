# Banco (16/11/2026 21:00): "ideas puras" como candidatas de los equipos. Cada idea de ideas/ tal cual (sin evolucionar),
# en cada mercado y temporalidad (1d, 4h), como si fuera un agente. Pre-filtro solo con el entreno (2018-21): gana dinero
# y hace >= 8 operaciones. Matriz R,E,P,G,L 2019-2023 igual que m1.py. Uso: TFS=1d,4h OUTM=mat_ideas.pkl python m1ideas.py
import datetime as dt, json, os, sys, pickle, time, hashlib
S = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.join(S, "lab")
sys.path.insert(0, LAB); sys.path.insert(0, os.path.join(LAB, "src"))
import numpy as np
import run_daily as rd, data as datamod, equipos as eq, inventor
from academia import Academia
from backtest import run
eq.HIST = "2018-01-01"
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
TFS = os.environ.get("TFS", "1d,4h").split(",")
ags, t0 = [], time.time()
for act in ["BTC-EUR", "ETH-EUR", "XRP-EUR", "SOL-EUR"]:
    for tf in TFS:
        base = dict(id="x", activo=act, tf=tf)
        if not ac.has_market(base):
            continue
        mtr, _ = ac.train_market(base, None)
        a, b = ac.window(mtr, "entreno")
        seen, n0 = set(), 0
        for idea in ac.ideas_for(act):
            r = idea["regla"]
            w = np.asarray(inventor.exposure(mtr.I, r, None, mtr.bpd))
            res = run(mtr.I, w, a, b, rc)
            n0 += 1
            if res.ret <= 0 or res.n_buys < 8:
                continue
            key = hashlib.md5(np.round(w[a:b + 1], 3).tobytes()).hexdigest()
            if key in seen:
                continue
            seen.add(key)
            iid = "i" + hashlib.md5(f"{act}{tf}{idea['nombre']}".encode()).hexdigest()[:9]
            ags.append(dict(id=iid, name=idea["nombre"][:30], activo=act, tf=tf, eleccion="propia", regla=r,
                            status="examinado", exam={"ret": 0}, lado=None, usa_cortos=r.get("lado") == "corto"))
        print(act, tf, n0, "ideas ->", len(ags), f"{time.time()-t0:.0f}s", flush=True)
print(len(ags), "ideas-agente", flush=True)
days, R, E, P, G, L = eq.matrix(ac, ags, "2019-01-01", dt.date(2023, 12, 31))
info = [dict(id=a["id"], name=a["name"], activo=a["activo"], short=False, idea=True, tf=a["tf"]) for a in ags]
pickle.dump(dict(days=days, R=R, E=E, P=P, G=G, L=L, info=info), open(os.path.join(S, os.environ.get("OUTM", "mat_ideas.pkl")), "wb"))
print("ok", R.shape, f"{time.time()-t0:.0f}s")
