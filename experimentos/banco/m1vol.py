# Banco (08/11/2026): m1 con filtro de volatilidad en el equipo: además del filtro de tendencia, el equipo no da dinero
# a una operación los días en que la volatilidad de 20 días del activo pasa de K veces su mediana del último año.
# Uso: VOLK=1.5 OUTM=mat_v15.pkl python m1vol.py  (VOLK=0 = como ahora)
import os, sys
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "lab")); sys.path.insert(0, os.path.join(S, "lab", "src"))
import numpy as np, equipos as eq
K = float(os.environ.get("VOLK", "0"))
_orig = eq.trend_by_day
def trend_by_day(ac, ag, dias=eq.TENDENCIA_DIAS, pend=eq.TENDENCIA_PENDIENTE):
    out = _orig(ac, ag, dias, pend)
    if not K:
        return out
    a = ag.get("activo", ac.cfg["mercado"])
    d1 = ac.daily if a == ac.cfg["mercado"] else ac.otros[a]["1d"]
    c = np.asarray(d1.I.c, float)
    lr = np.r_[0.0, np.diff(np.log(c))]
    v20 = np.array([lr[max(0, i - 19):i + 1].std() for i in range(len(c))])
    n = 0
    for i in range(385, len(c)):
        d = d1.ts[i].date()
        if d in out and v20[i] > K * np.median(v20[i - 365:i]):
            out[d] = 0; n += 1
    return out
eq.trend_by_day = trend_by_day
exec(compile(open(os.path.join(S, "m1.py")).read().replace("S = os.path.dirname(os.path.abspath(__file__))", "pass"), "m1", "exec"))
