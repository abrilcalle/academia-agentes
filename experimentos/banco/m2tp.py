"""Banco (05/11/2026 10:00): toma de beneficios del equipo por operación. Parte de mat_raw.pkl (sin filtro, con lado y vela
de entrada de cada operación abierta; parche SIDES/TEND descrito en m2stop.py), aplica el filtro de tendencia actual
(50 + pendiente 10) y además, cuando una operación ya gana más de X % para el agente:
  tpX    -> el equipo saca todo su dinero de esa operación (P=-1) desde el día siguiente;
  mitadX -> el equipo se queda solo con la mitad (desde el día siguiente R = mitad de la operación + mitad en USDC).
Uso: python m2tp.py VARIANTE ; después MAT=mat_X.pkl OUT=teams_X.pkl python m2x.py y python m3x.py base X ..."""
import os, sys, pickle, datetime as dt
import numpy as np
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "lab", "src"))
import data as datamod
V = sys.argv[1]
M = pickle.load(open(os.path.join(S, "mat_raw.pkl"), "rb"))
days, R, E, P, L = M["days"], M["R"].copy(), M["E"].copy(), M["P"].copy(), M["L"]
pos = {d: k for k, d in enumerate(days)}
fxc = {k.date(): v[3] for k, v in datamod.load_csv(os.path.join(S, "loc", "usdc_eur_1d.csv")).items()}
fxr = np.zeros(len(days))
for k in range(1, len(days)):
    a, b = fxc.get(days[k - 1]), fxc.get(days[k])
    if a and b: fxr[k] = b / a - 1
def closes(a):
    c = datamod.load_csv(os.path.join(S, "loc", a.split("-")[0].lower() + "_1d.csv"))
    ks = sorted(k for k in c if k < dt.datetime(2024, 1, 1))
    return [k.date() for k in ks], np.array([c[k][3] for k in ks], float)
TR = {}
for a in {i["activo"] for i in M["info"]}:
    ds, c = closes(a)
    m50 = np.convolve(c, np.ones(50) / 50, "full")[:len(c)]
    t = {}
    for i in range(59, len(c)):
        v = 1 if c[i] > m50[i] else -1
        if (m50[i] - m50[i - 10]) * v <= 0: v = 0
        t[ds[i]] = v
    TR[a] = t
KEEP, FX, COST = 0.5, 1.0, 0.0
if V.startswith("k"):  # kKEEP_X: se queda KEEP % (el resto en efectivo que no rinde, como la reserva del equipo) y paga la venta
    a, b = V[1:].split("_"); KEEP, FX, COST = float(a) / 100, 0.0, 0.0008; X = float(b) / 100; V2 = "mitad"
else:
    X = 0.0 if V == "base" else float(V.lstrip("tpmitad")) / 100; V2 = V
nt = ntr = nb = nh = 0
for j, inf in enumerate(M["info"]):
    sd = M["sides"].get(inf["id"])
    if not sd: continue
    cur, cum, hit = None, 1.0, False
    for d, s, e in zip(*sd):
        k = pos.get(d)
        if k is None or P[j, k] <= 0: continue
        if (e, s) != cur:
            cur, cum, hit = (e, s), 1.0, False; nt += 1
        cum *= 1 + M["R"][j, k]
        tv = TR[inf["activo"]].get(d)
        blocked = tv is not None and tv * s <= 0
        if hit and V2.startswith("tp"):
            P[j, k] = -1.0; nb += 1; continue
        if blocked:
            P[j, k] = -1.0; nb += 1
        if hit and V2.startswith("mitad") and k + 1 < len(days):
            R[j, k + 1] = KEEP * M["R"][j, k + 1] + (1 - KEEP) * FX * fxr[k + 1]; E[j, k] *= KEEP; nh += 1
        if not hit and X and cum - 1 >= X:
            hit = True; ntr += 1
            if V2.startswith("tp"): P[j, k] = -1.0; nb += 1
            elif k + 1 < len(days):
                R[j, k + 1] = KEEP * M["R"][j, k + 1] + (1 - KEEP) * FX * fxr[k + 1] - (1 - KEEP) * COST; E[j, k] *= KEEP; nh += 1
M2 = dict(M); M2["P"] = P; M2["R"] = R; M2["E"] = E; M2.pop("sides")
pickle.dump(M2, open(os.path.join(S, f"mat_{V}.pkl"), "wb"))
print(V, "operaciones", nt, "llegan al objetivo", ntr, "días bloqueados", nb, "días a mitad", nh, flush=True)
