# Banco (18/11/2026 21:00): "puerta del dólar". Parte de mat_raw.pkl (m1raw.py con el parche SIDES; filtro de tendencia del código ya puesto)
# y además bloquea (P=-1) las COMPRAS los días en que el dólar (USDC/EUR) va fuerte: cierre > su media de N días (uN),
# o además con la media subiendo en 10 días (uNp). uNs: también bloquea los CORTOS cuando el dólar va débil (cierre < media).
# Uso: GATE=u50 OUTM=mat_u50.pkl python m2usd.py ; luego MAT=mat_u50.pkl COSTE=0.0008 ENS=post OUT=teams_u50.pkl python m2cost.py
import os, sys, pickle, datetime as dt, re
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "lab", "src"))
import numpy as np
import data as datamod
M = pickle.load(open(os.path.join(S, "mat_raw.pkl"), "rb"))
days = M["days"]; pos = {d: k for k, d in enumerate(days)}
GATE = os.environ.get("GATE", "base")
c = datamod.load_csv(os.path.join(S, "loc", "usdc_eur_1d.csv"))
ks = sorted(k for k in c if k < dt.datetime(2024, 1, 1)); ds = [k.date() for k in ks]; x = np.array([c[k][3] for k in ks])
P = M["P"].copy(); nb = 0
if GATE != "base":
    m = re.match(r"u(\d+)(p?)(s?)$", GATE); N, pend, cortos = int(m.group(1)), m.group(2) == "p", m.group(3) == "s"
    ma = np.convolve(x, np.ones(N) / N, "full")[:len(x)]
    FX = {}
    for i in range(N + 10, len(x)):
        v = 1 if x[i] > ma[i] else -1          # +1 dólar fuerte, -1 dólar débil
        if pend and (ma[i] - ma[i - 10]) * v <= 0: v = 0
        FX[ds[i]] = v
    for j, inf in enumerate(M["info"]):
        sd = M["sides"].get(inf["id"])
        if not sd: continue
        for d, s, e in zip(*sd):
            k = pos.get(d); v = FX.get(d)
            if k is None or v is None or P[j, k] <= 0: continue
            if (s > 0 and v > 0) or (cortos and s < 0 and v < 0):
                P[j, k] = -1.0; nb += 1
print(GATE, "bloqueadas de más", nb, "abiertas con dinero", int((M["P"] > 0).sum()), flush=True)
M = dict(M); M["P"] = P; M.pop("sides")
pickle.dump(M, open(os.path.join(S, os.environ.get("OUTM", f"mat_{GATE}.pkl")), "wb"))
