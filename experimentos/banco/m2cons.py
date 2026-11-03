"""Banco (03/11/2026): filtro de "consenso de la academia". Parte de mat_raw.pkl (sin filtro, con lado de cada operación
abierta). Para cada mercado y día, consenso = (agentes de ese mercado con compra abierta − con corto abierto) / agentes
de ese mercado (sin contar al propio agente). Variantes:
  base       -> filtro de tendencia actual (media 50 + pendiente 10)
  consT      -> tendencia actual + además consenso a favor (> T, en tanto por uno; p. ej. cons0, cons05, cons10, cons20)
  solocons   -> solo consenso > 0 (sin el filtro de tendencia)
  contra10   -> tendencia actual + bloquea solo si el consenso va claramente en contra (< −0,10 para compras)
Uso: python m2cons.py VARIANTE ; después MAT=mat_X.pkl OUT=teams_X.pkl python m2x.py y python m3x.py base X ..."""
import os, sys, pickle, datetime as dt
from collections import defaultdict
import numpy as np
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "lab", "src"))
import data as datamod
V = sys.argv[1]
M = pickle.load(open(os.path.join(S, "mat_raw.pkl"), "rb"))
days, R, E, P, L = M["days"], M["R"], M["E"], M["P"].copy(), M["L"]
pos = {d: k for k, d in enumerate(days)}
def closes(a):
    c = datamod.load_csv(os.path.join(S, "loc", a.split("-")[0].lower() + "_1d.csv"))
    ks = sorted(k for k in c if k < dt.datetime(2024, 1, 1))
    return [k.date() for k in ks], np.array([c[k][3] for k in ks], float)
def trend(a, n=50, pend=10):
    ds, c = closes(a)
    m = np.convolve(c, np.ones(n) / n, "full")[:len(c)]
    t = {}
    for i in range(n - 1 + pend, len(c)):
        v = 1 if c[i] > m[i] else -1
        if pend and (m[i] - m[i - pend]) * v <= 0: v = 0
        t[ds[i]] = v
    return t
TR = {a: trend(a) for a in {i["activo"] for i in M["info"]}}
# consenso por mercado y día
N = defaultdict(int); NET = defaultdict(float)
for inf in M["info"]:
    N[inf["activo"]] += 1
    sd = M["sides"].get(inf["id"])
    if not sd: continue
    for d, s, e in zip(*sd):
        NET[(inf["activo"], d)] += s
use_tr = V != "solocons"
thr = {"base": None, "solocons": 0.0, "contra10": -0.10}.get(V)
if V.startswith("cons"): thr = int(V[4:] or 0) / 100
nb = nx = 0
for j, inf in enumerate(M["info"]):
    sd = M["sides"].get(inf["id"])
    if not sd: continue
    a = inf["activo"]
    for d, s, e in zip(*sd):
        k = pos.get(d)
        if k is None or P[j, k] <= 0: continue
        tv = TR[a].get(d)
        bad = use_tr and tv is not None and tv * s <= 0
        if not bad and thr is not None:
            c = (NET[(a, d)] - s) / max(1, N[a] - 1)  # sin el propio agente
            if c * s <= thr:
                bad = True; nx += 1
        if bad:
            P[j, k] = -1.0; nb += 1
M2 = dict(M); M2["P"] = P; M2.pop("sides")
pickle.dump(M2, open(os.path.join(S, f"mat_{V}.pkl"), "wb"))
print(V, "días bloqueados", nb, "de ellos por consenso", nx, "abiertas", int((M["P"] > 0).sum()))
