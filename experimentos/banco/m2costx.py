# Banco (14/11/2026): coste de mover dinero del equipo (COSTE_REPARTO). Uso: COSTE=0.0008 ENS=post OUT=teams_X.pkl python m2cost.py
import os, sys
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "lab", "src"))
import equipos as eq
eq.COSTE_REPARTO = float(os.environ.get("COSTE", eq.COSTE_REPARTO))
print("COSTE_REPARTO", eq.COSTE_REPARTO, flush=True)
__file__ = os.path.join(S, "m2expo.py")
exec(compile(open(__file__).read(), "m2expo", "exec"))
