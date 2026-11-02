"""Banco (02/11/2026): filtro "BTC manda". Parte de mat_raw.pkl (sin filtro, con lado de cada operación abierta), aplica el
filtro de tendencia actual (media 50 + pendiente 10 del propio activo) y, en las operaciones de ETH, SOL y XRP, además:
  btc     -> la tendencia de BTC (misma definición) tiene que ir a favor (+1 compra / -1 corto)
  btcno   -> solo se bloquea si BTC va en contra (BTC sin tendencia clara no bloquea)
  btc200  -> BTC tiene que estar del lado bueno de su media de 200 días
  btc100  -> igual con la media de 100 días
Uso: python m2btc.py VARIANTE ; después MAT=mat_X.pkl OUT=teams_X.pkl python m2x.py y python m3x.py base X ..."""
import os, sys, pickle, datetime as dt
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
BT = {"btc": TR["BTC-EUR"], "btcno": TR["BTC-EUR"], "btc200": trend("BTC-EUR", 200, 0), "btc100": trend("BTC-EUR", 100, 0)}.get(V)
nb = nx = 0
for j, inf in enumerate(M["info"]):
    sd = M["sides"].get(inf["id"])
    if not sd: continue
    for d, s, e in zip(*sd):
        k = pos.get(d)
        if k is None or P[j, k] <= 0: continue
        tv = TR[inf["activo"]].get(d)
        bad = tv is not None and tv * s <= 0
        if not bad and BT is not None and inf["activo"] != "BTC-EUR":
            b = BT.get(d)
            if b is not None and (b * s < 0 if V == "btcno" else b * s <= 0):
                bad = True; nx += 1
        if bad:
            P[j, k] = -1.0; nb += 1
M2 = dict(M); M2["P"] = P; M2.pop("sides")
pickle.dump(M2, open(os.path.join(S, f"mat_{V}.pkl"), "wb"))
print(V, "días bloqueados", nb, "de ellos por BTC", nx, "abiertas", int((M["P"] > 0).sum()))
