"""Banco (06/11/2026 21:00): fracción fija de la cartera del equipo invertida (el resto queda en USDC sin rendimiento).
FRAC=0.5 -> el reparto de cada día se multiplica por 0,5. ELIGE=1 -> la formación elige la fracción (1/0,5/0,33) como un parámetro más.
DRAG=0.0003 -> agentes "más flojos": cada día expuesto se resta esa rentabilidad (≈ −11 %/año a exposición completa).
Uso: FRAC=0.5 OUT=teams_f50.pkl python m2frac.py ; python m3x.py base f50 ..."""
import os, sys, pickle
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "lab", "src"))
import numpy as np, equipos as eq
FRAC = float(os.environ.get("FRAC", "1"))
_orig = eq.alloc
eq.alloc = lambda P, G, pr, prm, L=None: _orig(P, G, pr, prm, L) * prm.get("frac", FRAC)
if os.environ.get("ELIGE"):
    eq.PARAMS = [dict(p, frac=f) for p in eq.PARAMS for f in (1.0, 0.5, 0.33)]
drag = float(os.environ.get("DRAG", "0"))
if drag:
    M = pickle.load(open(os.path.join(S, "mat.pkl"), "rb"))
    M["R"] = M["R"] - M["E"] * drag
    pickle.dump(M, open(os.path.join(S, "mat_drag.pkl"), "wb"))
    os.environ["MAT"] = "mat_drag.pkl"
exec(open(os.path.join(S, "m2x.py")).read())
