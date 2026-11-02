"""Banco (02/11/2026 15:00): filtro de tendencia del equipo según la temporalidad del agente y longitud de la media.
Parte de mat_raw.pkl (sin filtro, con lado de cada operación). Variantes:
  base       media 50 + pendiente 10 para todos (sistema actual)
  solo1d     el filtro solo se aplica a agentes de velas diarias (1h/4h libres)
  libre1h    libres solo los de 1h
  cortaN_L   1h/4h usan media N + pendiente L; 1d sigue con 50/10
  maN        media N + pendiente 10 para todos
Uso: python m2tf.py VARIANTE  -> mat_VARIANTE.pkl"""
import os, sys, pickle, datetime as dt, json
import numpy as np
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "lab", "src"))
import data as datamod
V = sys.argv[1]
M = pickle.load(open(os.path.join(S, "mat_raw.pkl"), "rb"))
days, P = M["days"], M["P"].copy()
pos = {d: k for k, d in enumerate(days)}
TF = {a["id"]: a.get("tf", "1d") for a in json.load(open(os.path.join(S, "lab", "state", "agents.json")))["agents"]}
def closes(a):
    c = datamod.load_csv(os.path.join(S, "loc", a.split("-")[0].lower() + "_1d.csv"))
    ks = sorted(k for k in c if k < dt.datetime(2024, 1, 1))
    return [k.date() for k in ks], np.array([c[k][3] for k in ks], float)
def trend(c, n, L):
    m = np.convolve(c, np.ones(n) / n, "full")[:len(c)]; m[:n - 1] = np.nan
    sl = np.r_[np.full(L, np.nan), m[L:] - m[:-L]]
    t = np.where((c > m) & (sl > 0), 1.0, np.where((c < m) & (sl < 0), -1.0, 0.0))
    t[np.isnan(m) | np.isnan(sl)] = np.nan
    return t
def params(tf):
    if V == "base": return (50, 10)
    if V == "solo1d": return (50, 10) if tf == "1d" else None
    if V == "libre1h": return None if tf == "1h" else (50, 10)
    if V.startswith("corta"):
        n, L = map(int, V[5:].split("_")); return (50, 10) if tf == "1d" else (n, L)
    if V.startswith("ma"): return (int(V[2:]), 10)
    raise SystemExit(V)
CL = {a: closes(a) for a in {i["activo"] for i in M["info"]}}
TR = {}
nb = 0; cnt = {}
for j, inf in enumerate(M["info"]):
    sd = M["sides"].get(inf["id"])
    tf = TF.get(inf["id"], "1d"); cnt[tf] = cnt.get(tf, 0) + 1
    pr = params(tf)
    if not sd or pr is None: continue
    key = (inf["activo"], pr)
    if key not in TR:
        ds, c = CL[inf["activo"]]; TR[key] = dict(zip(ds, trend(c, *pr)))
    for d, s in zip(sd[0], sd[1]):
        k = pos.get(d)
        if k is None or s == 0 or P[j, k] <= 0: continue
        tv = TR[key].get(d, np.nan)
        if np.isnan(tv): continue
        if tv * s <= 0:
            P[j, k] = -1.0; nb += 1
M2 = dict(M); M2["P"] = P; M2.pop("sides")
pickle.dump(M2, open(os.path.join(S, f"mat_{V}.pkl"), "wb"))
print(V, "bloqueadas", nb, "abiertas", int((M["P"] > 0).sum()), cnt)
