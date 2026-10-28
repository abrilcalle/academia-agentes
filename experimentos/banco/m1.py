# Banco de pruebas del laboratorio (28/10/2026). Uso: carpeta de pruebas con 'lab/' (copia del repo) y 'loc/' (enlaces a data/:
# btc_1d.csv, btc_1h, btc_flujo_1h, eth/sol/xrp_1d.csv y _1h, usdc_eur_1d.csv); copiar m1-m3 a esa carpeta y ejecutar en orden.
# m1: matriz de agentes 2019-2023 (~6 min) · m2: equipos formados por año (~4 min) · m3: pares A->B y tríos formar->podio->juzgar.
"""Etapa 1: matriz R,E,P,G,L de todos los agentes examinados, 2019-2023 (datos cortados el 01/01/2024)."""
import datetime as dt, json, os, sys, pickle
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
print(len(uniq), "agentes", flush=True)
days, R, E, P, G, L = eq.matrix(ac, uniq, "2019-01-01", dt.date(2023, 12, 31))
info = [dict(id=a["id"], name=a["name"], activo=a.get("activo", "BTC-EUR"), short=(a.get("lado") == "corto" and a["status"] != "suspendido")) for a in uniq]
pickle.dump(dict(days=days, R=R, E=E, P=P, G=G, L=L, info=info), open(os.path.join(S, "mat.pkl"), "wb"))
print("ok", R.shape)
