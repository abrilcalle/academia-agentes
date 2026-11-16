# Banco (16/11/2026): reparto a partes iguales entre las operaciones abiertas permitidas (ignora P y G), o solo por P.
# Uso: VAR=base|mix|igual|mixprob|prob COSTE=0.0008 OUT=teams_X.pkl python m2igual.py  (mismos equipos que la base; cambia el reparto con que se juzgan)
import os, sys, itertools
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "lab", "src"))
import numpy as np
import equipos as eq
eq.COSTE_REPARTO = float(os.environ.get("COSTE", "0.0008"))
VAR = os.environ.get("VAR", "base")
_orig = eq._alloc
def _alloc(P, G, prudencia, prm, L=None):
    m = prm.get("modo")
    if m in ("igual", "prob"):
        open_ = P > 0
        n = len(P)
        if not open_.any():
            return np.full(n, min(1.0 / n, prm["cap"]))
        score = np.where(open_, 1.0 if m == "igual" else P ** prudencia, 0.0)
        waiting = ~open_
        pool = 1.0 - (prm["reserva"] if waiting.any() else 0.0)
        f = np.zeros(n)
        f[open_] = pool * score[open_] / score.sum()
        if waiting.any():
            f[waiting] = prm["reserva"] / waiting.sum()
        return np.minimum(f, prm["cap"])
    return _orig(P, G, prudencia, prm, L)
eq._alloc = _alloc
BASE = list(eq.PARAMS)
EQ = [dict(reserva=r, cap=c, modo="igual") for r, c in itertools.product([0.1, 0.25, 0.5], [0.35, 0.6, 1.0])]
PR = [dict(reserva=r, cap=c, modo="prob") for r, c in itertools.product([0.1, 0.25, 0.5], [0.35, 0.6, 1.0])]
JUDGE = dict(base=BASE, mix=BASE + EQ, igual=EQ, mixprob=BASE + PR, prob=PR, mix3=BASE + EQ + PR)[VAR]
print(VAR, len(JUDGE), "formas", flush=True)
os.environ["ENS"] = "post"
src = open(os.path.join(S, "m2ens.py")).read()
src = src.replace("ALL = list(eq.PARAMS)", "ALL = JUDGE")
assert "ALL = JUDGE" in src
src = src.replace('S = os.path.dirname(os.path.abspath(__file__))', 'pass', 1)
exec(compile(src, "m2ens", "exec"))
