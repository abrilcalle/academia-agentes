"""Banco (01/11/2026 21:00): stop del equipo por operación. Parte de mat_raw.pkl (sin filtro, con lado y vela de entrada
de cada operación abierta), aplica el filtro de tendencia actual (pendiente 10) y además deja sin dinero (P=-1) el resto
de una operación cuando el agente ya pierde en ella más de X % (fijoX), cae X % desde su mejor punto de la operación
(trailX) o pierde más de m veces su stop estimado (stopM). Uso: python m2stop.py VARIANTE
Parche usado en lab/src/equipos.py para TEND=0 python m1raw.py: variable TEND (si 0, series() no aplica trend_by_day) y
SIDES[id] = (días, lado ±1, vela de entrada) de cada día con operación abierta (se rellena junto a G[n_] = tp).
Después: MAT=mat_X.pkl OUT=teams_X.pkl python m2x.py y python m3x.py base X ..."""
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
nt = nb = ns = 0
for j, inf in enumerate(M["info"]):
    sd = M["sides"].get(inf["id"])
    if not sd: continue
    cur, cum, peak, stopped = None, 1.0, 1.0, False
    for d, s, e in zip(*sd):
        k = pos.get(d)
        if k is None or P[j, k] <= 0: continue
        if (e, s) != cur:
            cur, cum, peak, stopped = (e, s), 1.0, 1.0, False; nt += 1
        cum *= 1 + R[j, k]; peak = max(peak, cum)
        if not stopped and V != "base":
            if V.startswith("fijo") and cum - 1 <= -float(V[4:]) / 100: stopped = True
            elif V.startswith("trail") and cum / peak - 1 <= -float(V[5:]) / 100: stopped = True
            elif V.startswith("stop") and cum - 1 <= -float(V[4:]) * max(L[j, k], 1e-3) * max(E[j, k], 0.05): stopped = True
            if stopped: ns += 1
        tv = TR[inf["activo"]].get(d)
        if stopped or (tv is not None and tv * s <= 0):
            P[j, k] = -1.0; nb += 1
M2 = dict(M); M2["P"] = P; M2.pop("sides")
pickle.dump(M2, open(os.path.join(S, f"mat_{V}.pkl"), "wb"))
print(V, "operaciones", nt, "con stop", ns, "días bloqueados", nb, "abiertas", int((M["P"] > 0).sum()))
