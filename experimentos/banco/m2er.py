# Banco (12/11/2026 10:00): filtro de "tendencia limpia" (ratio de eficiencia de Kaufman) además del filtro de tendencia del equipo.
# ER(n) = |cierre hoy - cierre hace n días| / suma de los movimientos diarios absolutos en esos n días (1 = va recto, 0 = zigzag).
# Parte de mat_raw.pkl (m1raw.py con TEND=0 y el parche SIDES). Variantes (ER=):
#  base        -> filtro actual (media 50 + pendiente 10)
#  erN_U       -> además bloqueada si ER(N) < U (mercado en zigzag aunque la media vaya a favor)
# Uso: ER=er20_0.2 OUTM=mat_er20_0.2.pkl python m2er.py ; luego MAT=... ENS=post OUT=teams_X.pkl python m2ens.py
import os, sys, pickle, datetime as dt
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "lab", "src"))
import numpy as np
import data as datamod
M = pickle.load(open(os.path.join(S, "mat_raw.pkl"), "rb"))
days = M["days"]; pos = {d: k for k, d in enumerate(days)}
V = os.environ.get("ER", "base")

def closes(a):
    c = datamod.load_csv(os.path.join(S, "loc", a.split("-")[0].lower() + "_1d.csv"))
    ks = sorted(k for k in c if k < dt.datetime(2024, 1, 1))
    return [k.date() for k in ks], np.array([c[k][3] for k in ks], float)

N, U = (int(V.split("_")[0][2:]), float(V.split("_")[1])) if V != "base" else (0, 0.0)
TR, ER = {}, {}
for a in {i["activo"] for i in M["info"]}:
    ds, c = closes(a)
    ma = np.convolve(c, np.ones(50) / 50, "full")[:len(c)]
    t, e = {}, {}
    ad = np.r_[0, np.abs(np.diff(c))]; cs = np.cumsum(ad)
    for i in range(59, len(c)):
        v = 1 if c[i] > ma[i] else -1
        if (ma[i] - ma[i - 10]) * v <= 0: v = 0
        t[ds[i]] = v
        if N and i >= N:
            e[ds[i]] = abs(c[i] - c[i - N]) / max(cs[i] - cs[i - N], 1e-12)
    TR[a], ER[a] = t, e

P = M["P"].copy(); nb = ne = 0
for j, inf in enumerate(M["info"]):
    sd = M["sides"].get(inf["id"])
    if not sd: continue
    for d, s, e_ in zip(*sd):
        tv = TR[inf["activo"]].get(d)
        blk = tv is not None and tv * s <= 0
        if not blk and N:
            er = ER[inf["activo"]].get(d)
            if er is not None and er < U:
                blk = True; ne += 1
        k = pos.get(d)
        if blk and k is not None and P[j, k] > 0:
            P[j, k] = -1.0; nb += 1
print(V, "bloqueadas", nb, "por ER", ne, "abiertas", int((M["P"] > 0).sum()), flush=True)
M = dict(M); M["P"] = P; M.pop("sides")
pickle.dump(M, open(os.path.join(S, os.environ.get("OUTM", f"mat_{V}.pkl")), "wb"))
