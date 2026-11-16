# Banco (16/11/2026): "gemelos obligatorios". Tras formar cada equipo como build, se le añaden TW gemelos en corto
# (de los aprobados), elegidos por su Sharpe en el año de formación, respetando como mucho 2 por mercado.
# Uso: COSTE=0.0008 ENS=post TW=0|1|2|3 MAT=mat18.pkl YRS=2018,2019,... OUT=teams_X.pkl python m2tw.py
import os, sys
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "lab", "src"))
import equipos as eq
eq.COSTE_REPARTO = float(os.environ.get("COSTE", eq.COSTE_REPARTO))
TW = int(os.environ.get("TW", "0"))
YRS_ENV = os.environ.get("YRS", "2019,2020,2021,2022,2023")
_src_ens = open(os.path.join(S, "m2ens.py")).read()
_x = open(os.path.join(S, "m2x.py")).read()
_x = _x.replace("YRS = [2019, 2020, 2021, 2022, 2023]", f"YRS = [{YRS_ENV}]")
old = """            if len(team) >= eq.MIN_MIEMBROS:
                teams.append(dict(team=team, pr=pr, prm=prm))"""
new = """            if len(team) >= eq.MIN_MIEMBROS:
                if TW:
                    pool = [j for j in range(n) if info[j]["short"] and R[j, s].std() > 0 and j not in team]
                    with np.errstate(invalid="ignore", divide="ignore"):
                        shs = np.nan_to_num(R[:, s].mean(1) / R[:, s].std(1))
                    k = 0
                    for j in sorted(pool, key=lambda j: -shs[j]):
                        if k >= TW: break
                        if sum(info[i]["activo"] == info[j]["activo"] for i in team) >= eq.MAX_POR_ACTIVO: continue
                        team = team + [j]; k += 1
                teams.append(dict(team=team, pr=pr, prm=prm))"""
assert old in _x
_x = _x.replace(old, new)
open(os.path.join(S, "_m2x_tw.py"), "w").write(_x)
_src_ens = _src_ens.replace('open(os.path.join(S, "m2x.py"))', 'open(os.path.join(S, "_m2x_tw.py"))')
assert "_m2x_tw" in _src_ens
__file__ = os.path.join(S, "m2ens.py")
exec(compile(_src_ens, "m2ens", "exec"))
