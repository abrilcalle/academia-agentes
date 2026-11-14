# Banco (14/11/2026): candado de fin de semana (m2lock.py) con el coste de reparto real de los pares USDC.
# Uso: COSTE=0.0008 ENS=post LOCKD=5,6 LOCKX=0 LOCKF=0 OUT=teams_X.pkl python m2lockc.py
import os, sys
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "lab", "src"))
import equipos as eq
eq.COSTE_REPARTO = float(os.environ.get("COSTE", "0.0008"))
print("COSTE_REPARTO", eq.COSTE_REPARTO, "LOCK", os.environ.get("LOCKD"), os.environ.get("LOCKX"), os.environ.get("LOCKF"), flush=True)
__file__ = os.path.join(S, "m2lock.py")
exec(compile(open(__file__).read(), "m2lock", "exec"))
