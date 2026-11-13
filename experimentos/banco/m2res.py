# Banco (13/11/2026): cambiar el conjunto de formas de repartir (reservas y topes) que promedia el reparto medio.
# Uso: RES=0,0.1,0.25 CAP=0.35,0.6,1.0 ENS=post OUT=teams_X.pkl python m2res.py
import os, sys, itertools
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "lab", "src"))
import equipos as eq
res = [float(x) for x in os.environ.get("RES", "0.1,0.25,0.5").split(",")]
cap = [float(x) for x in os.environ.get("CAP", "0.35,0.6,1.0").split(",")]
modos = os.environ.get("MODOS", "prioridad,kelly").split(",")
eq.PARAMS = [dict(reserva=r, cap=c, modo=m) for r, c, m in itertools.product(res, cap, modos)]
print("PARAMS", len(eq.PARAMS), res, cap, modos, flush=True)
__file__ = os.path.join(S, "m2ens.py")
exec(compile(open(__file__).read(), "m2ens", "exec"))
