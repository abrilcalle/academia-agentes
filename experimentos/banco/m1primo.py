# Banco (18/11/2026): "PRIMOS". Además de cada agente examinado, la MISMA regla aplicada tal cual en los otros mercados
# (misma temporalidad; BTC, ETH, XRP, SOL). Guarda mat_base.pkl (solo originales) y mat_primo.pkl (originales + primos).
import datetime as dt, json, os, sys, pickle, copy
S = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.join(S, "lab")
sys.path.insert(0, LAB); sys.path.insert(0, os.path.join(LAB, "src"))
import numpy as np
import run_daily as rd, kronos_signal, data as datamod, equipos as eq
from academia import Academia
eq.HIST = "2018-01-01"
cfg = json.load(open(os.path.join(LAB, "config.json")))
today = dt.date(2024, 1, 1)
loc = os.path.join(S, "loc")
mk = rd.load_markets(cfg, loc, today, True)
kr = {tf: kronos_signal.load(LAB, mk[tf], cfg) for tf in cfg["kronos"]["temporalidades"] if tf in mk}
otros = rd.load_other_assets(cfg, loc, today, True)
fx = {d.date(): v[3] for d, v in datamod.load_csv(os.path.join(loc, "usdc_eur_1d.csv")).items()}
for g in [mk] + list(otros.values()):
    for m in g.values():
        m.set_fx(fx)
ac = Academia(LAB, mk, kronos=kr, today=today, otros=otros, log=lambda *a: None)
ac.cfg["cotizar_en_usdc"] = True
cands = [a for a in ac.state["agents"] if a.get("exam") and a["status"] != "retirado" and ac.has_market(a)]
seen, uniq = set(), []
for a in cands:
    f = a.get("firma2026") or a["id"]
    if f in seen: continue
    seen.add(f); uniq.append(a)
MK = ["BTC-EUR", "ETH-EUR", "XRP-EUR", "SOL-EUR"]
prim = []
for a in uniq:
    if a.get("estilo") == "diario" and a.get("activo", "BTC-EUR") == "SOL-EUR":
        pass
    for m in MK:
        if m == a.get("activo", "BTC-EUR"): continue
        b = copy.deepcopy(a); b["id"] = a["id"] + "_" + m[:3]; b["activo"] = m; b["primo_de"] = a["id"]
        if ac.has_market(b): prim.append(b)
print(len(uniq), "agentes", len(prim), "primos", flush=True)
allag = uniq + prim
days, R, E, P, G, L = eq.matrix(ac, allag, "2019-01-01", dt.date(2023, 12, 31))
info = [dict(id=a["id"], name=a["name"], activo=a.get("activo", "BTC-EUR"), tf=a["tf"], primo=bool(a.get("primo_de")),
             orig=a.get("primo_de", a["id"]), short=(a.get("lado") == "corto" and a["status"] != "suspendido")) for a in allag]
n0 = len(uniq)
pickle.dump(dict(days=days, R=R[:n0], E=E[:n0], P=P[:n0], G=G[:n0], L=L[:n0], info=info[:n0]), open(os.path.join(S, "mat_base.pkl"), "wb"))
pickle.dump(dict(days=days, R=R, E=E, P=P, G=G, L=L, info=info), open(os.path.join(S, "mat_primo.pkl"), "wb"))
print("ok", R.shape)
