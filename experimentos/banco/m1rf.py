# Banco (15/11/2026): "presupuesto para agentes sin operación". Para cada agente de mat.pkl calcula por día RF = su
# rentabilidad del día empezando el día SIN operación abierta, contando solo las velas en las que va del lado que permite
# el filtro de tendencia del equipo (conocido al cierre de ayer); en las demás velas, el dinero sigue el cambio USDC/EUR.
# Así el equipo podría dejar dinero libre a agentes que aún no han abierto y pillar sus entradas desde la primera vela.
# Uso: python m1rf.py  (necesita mat.pkl con los mismos agentes; guarda rf.pkl)
import datetime as dt, json, os, sys, pickle
S = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.join(S, "lab"); sys.path.insert(0, LAB); sys.path.insert(0, os.path.join(LAB, "src"))
import numpy as np
exec(open(os.path.join(S, "m1.py")).read().split("days, R, E, P, G, L = eq.matrix")[0].split("print(len(uniq)")[0])
from backtest import run
M = pickle.load(open(os.path.join(S, "mat.pkl"), "rb"))
days = M["days"]; pos = {d: k for k, d in enumerate(days)}
ids = [x["id"] for x in M["info"]]; byid = {a["id"]: a for a in uniq}
RF = np.zeros((len(ids), len(days))); RA = np.zeros_like(RF)
for n, aid in enumerate(ids):
    ag = byid[aid]; mk = ac.m(ag); h = mk.idx(eq.HIST)
    if h >= mk.n - 1: continue
    w = np.asarray(ac.exposure(ag), float); cfg = ac.run_cfg()
    r = run(mk.I, w, h, mk.n - 1, cfg); e = np.asarray(r.eq, float)
    k = getattr(mk.I, "fx", None)
    tend = eq.trend_by_day(ac, ag)
    accF, accA = {}, {}
    for j in range(h + 1, mk.n):
        d = mk.ts[j].date()
        rb = e[j - h] / e[j - 1 - h] - 1
        accA[d] = accA.get(d, 1.0) * (1 + rb)
        side = np.sign(w[j - 1])
        ok = tend.get(d - dt.timedelta(days=1), 0)
        if side != 0 and side != ok:
            rb = (k[j] / k[j - 1] - 1) if k is not None else 0.0
        accF[d] = accF.get(d, 1.0) * (1 + rb)
    for d, v in accF.items():
        if d in pos: RF[n, pos[d]] = v - 1; RA[n, pos[d]] = accA[d] - 1
pickle.dump(dict(RF=RF, RA=RA), open(os.path.join(S, "rf.pkl"), "wb"))
R = M["R"]; print("ok; |RA-R| mediana", np.median(np.abs(RA - R)), "parte de días iguales", np.mean(np.abs(RA - R) < 1e-9))
