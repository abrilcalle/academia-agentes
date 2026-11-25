# Banco (25/11/2026 15:00): "amplitud del mercado" en el filtro de tendencia del equipo.
# Parte de mat.pkl (m1_18.py, filtro del código puesto). Las operaciones que pasan el filtro van a favor de la
# tendencia de su mercado (media 50 + pendiente 10), así que su lado = esa tendencia. Además, ahora se pide que
# varios de los mercados (BTC, ETH, XRP y SOL cuando hay datos) estén en la misma tendencia ese día:
#  base  -> como el código
#  ampK  -> al menos K mercados (contando el suyo) con tendencia en la misma dirección
#  maj   -> más de la mitad de los mercados con datos
#  todos -> todos los mercados con datos
# Uso: AMP=amp2 python m2amp.py  (escribe mat_amp2.pkl); luego MAT=mat_amp2.pkl COSTE=0.0008 ENS=post OUT=teams_amp2.pkl python m2cost.py
import os, sys, pickle, datetime as dt
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "lab", "src"))
import numpy as np
import data as datamod
M = pickle.load(open(os.path.join(S, os.environ.get("MAT", "mat.pkl")), "rb"))
days = M["days"]
AMP = os.environ.get("AMP", "base")

def closes(a):
    c = datamod.load_csv(os.path.join(S, "loc", a.split("-")[0].lower() + "_1d.csv"))
    ks = sorted(k for k in c if k < dt.datetime(2024, 1, 1))
    return [k.date() for k in ks], np.array([c[k][3] for k in ks], float)

TR = {}
for a in ("BTC-EUR", "ETH-EUR", "XRP-EUR", "SOL-EUR"):
    ds, c = closes(a)
    ma = np.convolve(c, np.ones(50) / 50, "full")[:len(c)]
    t = {}
    for i in range(59, len(c)):
        v = 1 if c[i] > ma[i] else -1
        if (ma[i] - ma[i - 10]) * v <= 0: v = 0
        t[ds[i]] = v
    TR[a] = t

need = {}
for d in days:
    vs = [TR[a][d] for a in TR if d in TR[a]]
    n = len(vs)
    if AMP == "base": k = 0
    elif AMP.startswith("amp"): k = int(AMP[3:])
    elif AMP == "maj": k = n // 2 + 1
    elif AMP == "todos": k = n
    else: raise SystemExit(AMP)
    need[d] = (k, sum(v > 0 for v in vs), sum(v < 0 for v in vs))

P = M["P"].copy(); nb = 0; nbl = nbs = 0
for j, inf in enumerate(M["info"]):
    tr = TR[inf["activo"]]
    for k_, d in enumerate(days):
        if P[j, k_] <= 0: continue
        s = tr.get(d)
        if not s: continue
        k, up, dn = need[d]
        if (up if s > 0 else dn) < k:
            P[j, k_] = -1.0; nb += 1
            if s > 0: nbl += 1
            else: nbs += 1
print(AMP, "bloqueadas de más", nb, "(compras", nbl, "cortos", nbs, ") de", int((M["P"] > 0).sum()), "con dinero", flush=True)
M = dict(M); M["P"] = P
pickle.dump(M, open(os.path.join(S, f"mat_{AMP}.pkl"), "wb"))
