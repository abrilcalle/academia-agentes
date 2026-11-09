# Banco (09/11/2026): tope de exposición por mercado en el reparto del equipo (sobre ENS=post, el reparto medio actual).
# Uso: MK=0|K OUT=teams_X.pkl [MKMODO=idle|redis] python m2mkt.py
#  MK=0 = como ahora · MK=0.5 = entre todos los miembros de un mismo mercado (BTC, ETH...) el equipo no pone más del 50 %
#  de la cartera; idle = el exceso espera en USDC · redis = el exceso va a las operaciones abiertas de otros mercados (sin pasar su tope).
import os, sys, pickle
S = os.path.dirname(os.path.abspath(__file__))
os.environ["ENS"] = "post"
import numpy as np
K = float(os.environ.get("MK", "0")); MODO = os.environ.get("MKMODO", "idle")
_info = pickle.load(open(os.path.join(S, os.environ.get("MAT", "mat.pkl")), "rb"))["info"]
def capmk(f, P, team):
    if not K or team is None: return f
    f = f.copy(); mk = np.array([_info[j]["activo"] for j in team]); exc = 0.0
    for m in set(mk):
        idx = mk == m; s = f[idx].sum()
        if s > K: exc += s - K; f[idx] *= K / s
    if MODO == "redis" and exc > 0:
        for _ in range(3):
            room = {m: K - f[mk == m].sum() for m in set(mk)}
            el = np.array([(P[i] > 0) and room[mk[i]] > 1e-9 for i in range(len(f))])
            if not el.any() or exc <= 1e-9: break
            w = np.where(el, np.maximum(f, 1e-6), 0.0); add = exc * w / w.sum()
            for m in set(mk):
                idx = (mk == m) & el; a = add[idx].sum()
                if a > room[m]: add[idx] *= room[m] / a
            f += add; exc -= add.sum()
    return f
src = open(os.path.join(S, "m2ens.py")).read()
src = src.replace("def simulate(R, E, P, G, prudencia, prm, cap0=100.0, L=None, fx=None):",
                  "def simulate(R, E, P, G, prudencia, prm, cap0=100.0, L=None, fx=None, team=None):")
src = src.replace("""             else _al(np.zeros(n), np.zeros(n), prudencia, prm, None))""",
                  """             else _al(np.zeros(n), np.zeros(n), prudencia, prm, None))
        if t and isinstance(prm, list): f = capmk(f, P[:, t - 1], team)""")
src = src.replace('fx=FXR[s])")', 'fx=FXR[s], team=team)")')
assert src.count("capmk") == 1 and "team=team)" in src
src = src.replace('S = os.path.dirname(os.path.abspath(__file__))', 'pass', 1)
exec(compile(src, "m2ens", "exec"))
