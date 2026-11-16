# Banco (16/11/2026 21:00): cantera = los 24 agentes de siempre (+ gemelos) y ADEMÁS hasta K ideas puras (las de mejor
# Sharpe en el año de formación, distintas entre sí y de los elegidos, correlación <= 0,9). MAT = matriz mezclada (info["idea"]).
# Uso: COSTE=0.0008 ENS=post K=8 MAT=mat_mix.pkl OUT=teams_X.pkl python m2islot.py
import os, sys
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "lab", "src"))
import equipos as eq
eq.COSTE_REPARTO = float(os.environ.get("COSTE", eq.COSTE_REPARTO))
K = int(os.environ.get("K", "8"))
_src_ens = open(os.path.join(S, "m2ens.py")).read()
_x = open(os.path.join(S, "m2x.py")).read()
old1 = """        if info[j]["short"] or R[j, s].std() == 0 or R[j, s].sum() <= 0: continue"""
new1 = """        if info[j].get("idea") or info[j]["short"] or R[j, s].std() == 0 or R[j, s].sum() <= 0: continue"""
old2 = """    teams = []
    for pr in eq.PRUDENCIAS:"""
new2 = """    nid = 0
    for j in sorted(keep, key=lambda j: -sh[j]):
        if nid >= K: break
        if not info[j].get("idea") or R[j, s].std() == 0 or R[j, s].sum() <= 0: continue
        if any(np.corrcoef(R[j, s], R[i, s])[0, 1] > 0.9 for i in chosen): continue
        chosen.append(j); nid += 1
    teams = []
    for pr in eq.PRUDENCIAS:"""
assert old1 in _x and old2 in _x
_x = _x.replace(old1, new1).replace(old2, new2)
open(os.path.join(S, "_m2x_islot.py"), "w").write(_x)
_src_ens = _src_ens.replace('open(os.path.join(S, "m2x.py"))', 'open(os.path.join(S, "_m2x_islot.py"))')
assert "_m2x_islot" in _src_ens
__file__ = os.path.join(S, "m2ens.py")
exec(compile(_src_ens, "m2ens", "exec"))
