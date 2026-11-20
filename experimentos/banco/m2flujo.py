# Banco (20/11/2026 10:00): "puerta de flujo de órdenes". Parte de mat_raw.pkl (m1raw.py con el parche SIDES; filtro de
# tendencia del código ya puesto) y además bloquea (P=-1) las operaciones que van contra el flujo de órdenes de BTC
# (Binance BTC/EUR, compras agresivas / volumen en los últimos N días; para todos los mercados, como "BTC manda").
# GATE = fN (ratio > 0,5 para comprar, < 0,5 para cortos) · rN (ratio sobre su mediana de 180 días) · cN (rN al revés).
# Sin datos de flujo (2019) no bloquea. Uso: GATE=r14 OUTM=mat_r14.pkl python m2flujo.py ; luego m2cost.py con MAT=
import os, sys, pickle, datetime as dt, re, glob, csv, collections
S = os.path.dirname(os.path.abspath(__file__))
import numpy as np
M = pickle.load(open(os.path.join(S, "mat_raw.pkl"), "rb"))
days = M["days"]; pos = {d: k for k, d in enumerate(days)}
GATE = os.environ.get("GATE", "base")
vol = collections.defaultdict(float); buy = collections.defaultdict(float)
for f in sorted(glob.glob(os.path.join(S, "loc", "btc_flujo_1h", "*.csv"))):
    for r in csv.DictReader(open(f)):
        d = dt.date.fromisoformat(r["ts"][:10])
        if d >= dt.date(2024, 1, 1): continue
        vol[d] += float(r["volume"]); buy[d] += float(r["taker_buy"])
ds = sorted(vol); V = np.array([vol[d] for d in ds]); Bq = np.array([buy[d] for d in ds])
P = M["P"].copy(); nb = 0
if GATE != "base":
    m = re.match(r"([frc])(\d+)$", GATE); kind, N = m.group(1), int(m.group(2))
    ratio = np.convolve(Bq, np.ones(N), "full")[:len(V)] / np.convolve(V, np.ones(N), "full")[:len(V)]
    FL = {}
    for i in range(N + 30, len(ds)):
        x = ratio[i] - (0.5 if kind == "f" else np.median(ratio[max(0, i - 180):i + 1]))
        v = 1 if x > 0 else -1
        FL[ds[i]] = -v if kind == "c" else v     # +1: el flujo dice comprar; -1: vender
    for j, inf in enumerate(M["info"]):
        sd = M["sides"].get(inf["id"])
        if not sd: continue
        for d, s, e in zip(*sd):
            k = pos.get(d); v = FL.get(d)       # flujo del propio día (cierre): se usa al día siguiente, como el filtro
            if k is None or v is None or P[j, k] <= 0: continue
            if s * v < 0:
                P[j, k] = -1.0; nb += 1
print(GATE, "bloqueadas de más", nb, "abiertas con dinero", int((M["P"] > 0).sum()), flush=True)
M = dict(M); M["P"] = P; M.pop("sides")
pickle.dump(M, open(os.path.join(S, os.environ.get("OUTM", f"mat_{GATE}.pkl")), "wb"))
