# Banco (20/11/2026 21:00): ¿a dónde va el dinero de las operaciones bloqueadas por el filtro de tendencia?
# Necesita mat.pkl hecho con el parche RAWNEG (P bloqueada = -P original, en vez de -1). Variantes (RED=):
#  base  -> como el código: las bloqueadas no reciben y su parte se reparte entre las demás
#  usdc  -> se reparte como si no hubiera filtro y la parte de las bloqueadas se queda en USDC
#  mitad -> la mitad de la parte bloqueada se queda en USDC y la otra mitad se reparte
#  tope  -> como base, pero ninguna operación recibe más de lo que recibiría sin filtro × 1,5
# Uso: RED=usdc MAT=mat.pkl COSTE=0.0008 ENS=post OUT=teams_usdc.pkl python m2redis.py
import os, sys
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "lab", "src"))
import numpy as np, equipos as eq
RED = os.environ.get("RED", "base")
_orig = eq.alloc
def alloc(P, G, prudencia, prm, L=None):
    if prm.get("medio"):
        return np.mean([alloc(P, G, prudencia, p, L) for p in eq.PARAMS], axis=0)
    P = np.asarray(P, float)
    blk = P < 0
    fb = _orig(P, G, prudencia, prm, L)
    if RED == "base" or not blk.any():
        return fb
    fu = eq._alloc(np.abs(P), np.asarray(G), prudencia, prm, None if L is None else np.asarray(L))
    fu = np.where(blk, 0.0, fu)
    if RED == "usdc": return fu
    if RED == "mitad": return 0.5 * fb + 0.5 * fu
    if RED == "tope":
        fr = eq._alloc(np.abs(P), np.asarray(G), prudencia, prm, None if L is None else np.asarray(L))
        return np.minimum(fb, 1.5 * fr)
    raise SystemExit(RED)
eq.alloc = alloc
print("RED", RED, flush=True)
__file__ = os.path.join(S, "m2cost.py")
exec(compile(open(__file__).read(), "m2cost", "exec"))
