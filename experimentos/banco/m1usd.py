# Banco (21/11/2026 21:00): filtro de tendencia del equipo calculado con el precio en USDC (el del par que se opera)
# en vez del precio en euros. Uso: OUTM=mat_usd.pkl python m1usd.py   (VAR=eur reproduce la base)
import os, sys, datetime as dt
import numpy as np
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "lab", "src"))
import equipos as eq
VAR = os.environ.get("VAR", "usd")
def trend_by_day(ac, ag, dias=eq.TENDENCIA_DIAS, pend=eq.TENDENCIA_PENDIENTE):
    if not dias:
        return {}
    a = ag.get("activo", ac.cfg["mercado"])
    d1 = ac.daily if a == ac.cfg["mercado"] else ac.otros[a]["1d"]
    c = np.asarray(d1.I.c_u if VAR == "usd" else d1.I.c, float)
    ma = np.convolve(c, np.ones(dias) / dias, "full")[:len(c)]
    out = {}
    for i in range(dias - 1 + pend, len(c)):
        t = 1 if c[i] > ma[i] else -1
        if pend and (ma[i] - ma[i - pend]) * t <= 0:
            t = 0
        out[d1.ts[i].date()] = t
    return out
eq.trend_by_day = trend_by_day
__file__ = os.path.join(S, "m1.py")
exec(compile(open(__file__).read(), "m1", "exec"))
