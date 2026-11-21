# Banco (21/11/2026): "cerca del máximo". Como m1.py, pero el filtro de tendencia del equipo además pide, para comprar,
# que el cierre esté a menos de MAXX del máximo de MAXN días (y para un corto, a menos de MAXX del mínimo).
# Si no, tendencia 0 (bloqueada). MAXN=0 -> como el código. Uso: MAXN=90 MAXX=0.15 OUTM=mat_c90.pkl python m1max.py
import os, sys, numpy as np
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "lab")); sys.path.insert(0, os.path.join(S, "lab", "src"))
import equipos as eq
N = int(os.environ.get("MAXN", "0")); X = float(os.environ.get("MAXX", "0.15"))
_orig = eq.trend_by_day
def trend_by_day(ac, ag, dias=eq.TENDENCIA_DIAS, pend=eq.TENDENCIA_PENDIENTE):
    out = _orig(ac, ag, dias, pend)
    if not N: return out
    a = ag.get("activo", ac.cfg["mercado"])
    d1 = ac.daily if a == ac.cfg["mercado"] else ac.otros[a]["1d"]
    c = np.asarray(d1.I.c, float)
    for i in range(len(c)):
        d = d1.ts[i].date(); t = out.get(d)
        if not t: continue
        w = c[max(0, i - N + 1):i + 1]
        if (t > 0 and c[i] < (1 - X) * w.max()) or (t < 0 and c[i] > (1 + X) * w.min()):
            out[d] = 0
    return out
eq.trend_by_day = trend_by_day
__file__ = os.path.join(S, "m1.py")
exec(compile(open(__file__).read(), "m1", "exec"))
