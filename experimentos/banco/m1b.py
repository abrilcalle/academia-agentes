"""Matriz de especialistas bajistas (ideas de corto + filtro estricto de mercado bajista), elegidos solo con 2018-21."""
import datetime as dt, json, os, sys, pickle, hashlib
S = os.path.dirname(os.path.abspath(__file__)); LAB = os.path.join(S, "lab")
sys.path.insert(0, LAB); sys.path.insert(0, os.path.join(LAB, "src"))
import numpy as np
import run_daily as rd, data as datamod, equipos as eq, inventor, diario
from academia import Academia
eq.HIST = "2018-01-01"
cfg = json.load(open(os.path.join(LAB, "config.json")))
today = dt.date(2024, 1, 1); loc = os.path.join(S, "loc")
mk = rd.load_markets(cfg, loc, today, True); otros = rd.load_other_assets(cfg, loc, today, True)
fx = {d.date(): v[3] for d, v in datamod.load_csv(os.path.join(loc, "usdc_eur_1d.csv")).items()}
for g in [mk] + list(otros.values()):
    for m in g.values(): m.set_fx(fx)
ac = Academia(LAB, mk, kronos={}, today=today, otros=otros, log=lambda *a: None)
ac.cfg["cotizar_en_usdc"] = True; diario.ALLOW_SHORT = True
sel = []
for f in ["bear_1d.pkl", "bear_4h.pkl"]:
    o = pickle.load(open(os.path.join(S, f), "rb"))
    for k, v in o.items():
        if k[2] == "_flat": continue
        fl = o[k[:2] + ("_flat",)]["raw"]; r = v["g2"]
        ex = [r[y][0] - fl[y][0] for y in range(2018, 2022)]
        if ex[0] > 0 and sum(ex[1:]) > -0.10:
            sel.append(k)
print(len(sel), "especialistas", flush=True)
ideas = {i["nombre"]: i for i in json.load(open(os.path.join(LAB, "ideas", "estrategias_internet.json")))["ideas"]}
agents, info = [], []
for act, tf, nm in sel:
    rule = json.loads(json.dumps(ideas[nm]["regla"]))
    ag = dict(id=hashlib.sha1(f"{act}{tf}{nm}".encode()).hexdigest()[:10], name=nm[:30], activo=act, tf=tf, eleccion="propia", regla=rule, genome={}, params={})
    M = ac.m(ag); I = M.I
    with np.errstate(invalid="ignore"):
        s200 = I.sma(200 * M.bpd)
        g2 = np.nan_to_num(I.c < s200).astype(bool) & np.nan_to_num(s200 < np.roll(s200, 20 * M.bpd)).astype(bool) & np.nan_to_num(I.sma(50 * M.bpd) < s200).astype(bool)
    ac._w[ag["id"]] = np.asarray(inventor.exposure(I, rule, None, M.bpd)) * g2
    agents.append(ag); info.append(dict(id=ag["id"], name=ag["name"], activo=act, short=True, bear=True))
days, R, E, P, G, L = eq.matrix(ac, agents, "2019-01-01", dt.date(2023, 12, 31))
pickle.dump(dict(days=days, R=R, E=E, P=P, G=G, L=L, info=info), open(os.path.join(S, "matb.pkl"), "wb"))
print("ok", R.shape)
