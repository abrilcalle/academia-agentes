"""Variantes del filtro de tendencia del equipo (01/11/2026 15:00). Parte de mat_raw.pkl (sin filtro, con el lado de cada
operación abierta) y bloquea (P=-1) las operaciones según la variante. Uso: python m2tend.py VARIANTE"""
import os, sys, pickle, runpy, datetime as dt
import numpy as np
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "lab", "src"))
import data as datamod
V = sys.argv[1]
M = pickle.load(open(os.path.join(S, "mat_raw.pkl"), "rb"))
days, P = M["days"], M["P"].copy()
pos = {d: k for k, d in enumerate(days)}
def closes(a):
    c = datamod.load_csv(os.path.join(S, "loc", a.split("-")[0].lower() + "_1d.csv"))
    ks = sorted(k for k in c if k < dt.datetime(2024, 1, 1))
    return [k.date() for k in ks], np.array([c[k][3] for k in ks], float)
def ma(c, n):
    m = np.convolve(c, np.ones(n) / n, "full")[:len(c)]; m[:n - 1] = np.nan; return m
def trend(c, V):
    m50 = ma(c, 50)
    t = np.where(c > m50, 1, -1).astype(float)
    if V.startswith("pend"):          # además la media de 50 tiene que ir a favor (subiendo L días)
        L = int(V[4:]); sl = np.r_[np.full(L, np.nan), m50[L:] - m50[:-L]]
        t = np.where((c > m50) & (sl > 0), 1, np.where((c < m50) & (sl < 0), -1, 0))
    elif V.startswith("dos"):         # media de 50 y de N alineadas
        N = int(V[3:]); mN = ma(c, N)
        t = np.where((c > m50) & (c > mN), 1, np.where((c < m50) & (c < mN), -1, 0))
    elif V.startswith("hist"):        # histéresis: cambia solo si cruza la media con margen de X %
        x = float(V[4:]) / 100; t = np.zeros(len(c)); cur = 0
        for i in range(len(c)):
            if np.isnan(m50[i]): continue
            if c[i] > m50[i] * (1 + x): cur = 1
            elif c[i] < m50[i] * (1 - x): cur = -1
            elif cur == 0: cur = 1 if c[i] > m50[i] else -1
            t[i] = cur
    t = np.asarray(t, float); t[np.isnan(m50)] = np.nan
    return t
TR = {}
for a in {i["activo"] for i in M["info"]}:
    ds, c = closes(a)
    TR[a] = dict(zip(ds, trend(c, V)))
nb = 0
for j, inf in enumerate(M["info"]):
    sd = M["sides"].get(inf["id"])
    if not sd: continue
    for d, s in zip(*sd):
        k = pos.get(d)
        if k is None or s == 0 or P[j, k] <= 0: continue
        tv = TR[inf["activo"]].get(d, np.nan)
        if np.isnan(tv): continue
        if tv * s < 0 or (tv == 0):
            P[j, k] = -1.0; nb += 1
M2 = dict(M); M2["P"] = P; M2.pop("sides")
pickle.dump(M2, open(os.path.join(S, f"mat_{V}.pkl"), "wb"))
print(V, "bloqueadas", nb, "abiertas", int((M["P"] > 0).sum()))
if os.path.exists(os.path.join(S, "mat.pkl")) and V == "base":
    Pb = pickle.load(open(os.path.join(S, "mat.pkl"), "rb"))["P"]
    print("coincide con m1 (base):", np.mean((Pb < 0) == (P < 0)), "difieren", int(((Pb < 0) != (P < 0)).sum()))
