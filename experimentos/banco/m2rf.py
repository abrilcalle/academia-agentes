# Banco (15/11/2026): "presupuesto para agentes sin operación". Como m2cost.py (COSTE 0,08 %, ENS=post), pero cada día
# parte del dinero que el equipo no reparte se deja a los agentes que al cierre de ayer no tenían operación abierta,
# para que si abren durante el día el equipo entre con ellos desde la primera vela (y no al cierre del día).
# Uso: W=0.5 CAPF=0.2 SOLO=intra OUT=teams_X.pkl python m2rf.py   (W=0 = base; SOLO=intra -> solo agentes de 1 h / 4 h)
import os, sys, pickle, json
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "lab", "src"))
import numpy as np
import equipos as eq, data as datamod
eq.COSTE_REPARTO = float(os.environ.get("COSTE", "0.0008"))
W = float(os.environ.get("W", "0")); CAPF = float(os.environ.get("CAPF", "0.2")); SOLO = os.environ.get("SOLO", "all")
BLK = os.environ.get("BLK", "0") == "1"   # también a los que tienen una operación bloqueada por el filtro
M = pickle.load(open(os.path.join(S, "mat.pkl"), "rb"))
RF = pickle.load(open(os.path.join(S, "rf.pkl"), "rb"))["RF"]
tfs = {a["id"]: a["tf"] for a in json.load(open(os.path.join(S, "lab", "state", "agents.json")))["agents"]}
ELIG = np.array([(SOLO == "all") or (tfs.get(x["id"]) in ("1h", "4h")) for x in M["info"]])
days = M["days"]
fxd = {d.date(): v[3] for d, v in datamod.load_csv(os.path.join(S, "loc", "usdc_eur_1d.csv")).items()}
ks = sorted(fxd); last = fxd[ks[0]]; lv = []
for d in days:
    last = fxd.get(d, last); lv.append(last)
lv = np.array(lv); FXR = np.r_[0.0, lv[1:] / lv[:-1] - 1]
print("COSTE", eq.COSTE_REPARTO, "W", W, "CAPF", CAPF, "SOLO", SOLO, "BLK", BLK, "elegibles", ELIG.sum(), flush=True)

def _al(Pc, Gc, pr, prm, Lc):
    if isinstance(prm, list):
        return np.mean([eq.alloc(Pc, Gc, pr, p, Lc) for p in prm], axis=0)
    return eq.alloc(Pc, Gc, pr, prm, Lc)

def simrf(team, s, pr, prm):
    Rt, Et, Pt, Gt, Lt, RFt = M["R"][team, s], M["E"][team, s], M["P"][team, s], M["G"][team, s], M["L"][team, s], RF[team, s]
    el = ELIG[team]; fx = FXR[s]
    n, T = Rt.shape
    val = np.empty(T); v = 100.0; f_prev = np.zeros(n)
    for t in range(T):
        f = _al(Pt[:, t - 1], Gt[:, t - 1], pr, prm, Lt[:, t - 1]) if t else _al(np.zeros(n), np.zeros(n), pr, prm, None)
        b = np.zeros(n)
        if W > 0 and t:
            fl = el & ((Pt[:, t - 1] == 0) | (BLK & (Pt[:, t - 1] < 0)))
            idle = max(0.0, 1.0 - float(f.sum()))
            if fl.any() and idle > 0:
                b[fl] = min(idle * W / fl.sum(), CAPF)
        turnover = float(np.sum(np.abs(f - f_prev) * Et[:, t - 1])) if t else 0.0
        idle = max(0.0, 1.0 - float(f.sum()) - float(b.sum()))
        v *= 1 + float(np.dot(f, Rt[:, t])) + float(np.dot(b, RFt[:, t])) + idle * fx[t] - turnover * eq.COSTE_REPARTO
        val[t] = v; f_prev = f + b
    return val

src = open(os.path.join(S, "m2x.py")).read()
src = src.replace("v, _ = eq.simulate(R[team, s], E[team, s], P[team, s], G[team, s], pr, prm, L=L[team, s])", "v = simrf(team, s, pr, prm)")
assert "simrf(team" in src
ALL = list(eq.PARAMS)
src = src.replace('t["s"][y], t["v"][y] = sim(t["team"], y, t["pr"], t["prm"], full=True)',
                  't["s"][y], t["v"][y] = sim(t["team"], y, t["pr"], ALL, full=True)')
assert "ALL, full" in src
src = src.replace('S = os.path.dirname(os.path.abspath(__file__))', 'pass')
exec(compile(src, "m2x", "exec"))
