# m2cost + m2dow: coste de reparto COSTE y día de entrada DOW.
import os, sys
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "lab", "src"))
import equipos as eq
eq.COSTE_REPARTO = float(os.environ.get("COSTE", eq.COSTE_REPARTO))
__file__ = os.path.join(S, "m2dow.py")
exec(compile(open(__file__).read(), "m2dow", "exec"))
