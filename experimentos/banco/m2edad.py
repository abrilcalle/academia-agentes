# Banco (23/11/2026 21:00): "edad de la operación". m2ens.py con un simulate que da más (o menos) parte a las
# operaciones abiertas hace pocos días. Uso: EDAD=0|joven|vieja EDAD_A=5 EDAD_W=0.5 vía m2costd.py (COSTE=0.0008 ENS=post).
# Banco (08/11/2026): reparto "promedio" del equipo. En vez de quedarse con UNA forma de repartir (reserva, tope, modo)
# elegida con el año de formación, el equipo reparte cada día la MEDIA de las partes que darían varias formas.
# Uso: ENS=0|post|form|modo OUT=teams_X.pkl python m2ens.py   (dinero sin repartir en USDC, como el código)
#  0    = como ahora · post = mismos equipos que la base, pero se juzgan con el reparto medio de las 18 formas
#  form = se forman y juzgan con la media de las 18 formas (1 equipo por prudencia) · modo = media dentro de cada modo (2 por prudencia)
import os, sys, pickle
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "lab", "src"))
import numpy as np
import equipos as eq, data as datamod
M = pickle.load(open(os.path.join(S, os.environ.get("MAT", "mat.pkl")), "rb"))
days = M["days"]
fxd = {d.date(): v[3] for d, v in datamod.load_csv(os.path.join(S, "loc", "usdc_eur_1d.csv")).items()}
ks = sorted(fxd); last = fxd[ks[0]]; lv = []
for d in days:
    last = fxd.get(d, last); lv.append(last)
lv = np.array(lv); FXR = np.r_[0.0, lv[1:] / lv[:-1] - 1]
ENS = os.environ.get("ENS", "0")
EDAD = os.environ.get("EDAD", "0")       # 0 = como el código; joven / vieja = más peso a las operaciones jóvenes / viejas
EDAD_A = int(os.environ.get("EDAD_A", "5"))  # días que separan "joven" de "vieja"
EDAD_W = float(os.environ.get("EDAD_W", "0.5"))  # peso del grupo no preferido

def edad_scale(f, age):
    """Las operaciones del grupo no preferido reciben EDAD_W de su parte; luego se reescala para invertir lo mismo
    en total (el dinero pasa a las del grupo preferido, sin pasar nunca del 100 %)."""
    if EDAD == "0":
        return f
    m = f > 0
    if not m.any():
        return f
    young = age <= EDAD_A
    w = np.where(young, 1.0, EDAD_W) if EDAD == "joven" else np.where(young, EDAD_W, 1.0)
    g = f * w
    tot, gt = float(f.sum()), float(g.sum())
    return g * (tot / gt) if gt > 0 else f

def _al(Pc, Gc, pr, prm, Lc):
    if isinstance(prm, list):
        return np.mean([eq.alloc(Pc, Gc, pr, p, Lc) for p in prm], axis=0)
    return eq.alloc(Pc, Gc, pr, prm, Lc)

def simulate(R, E, P, G, prudencia, prm, cap0=100.0, L=None, fx=None):
    n, T = R.shape
    val = np.empty(T); F = np.zeros((n, T)); v = cap0; f_prev = np.zeros(n)
    age = np.zeros(n)
    for t in range(T):
        f = (_al(P[:, t - 1], G[:, t - 1], prudencia, prm, None if L is None else L[:, t - 1]) if t
             else _al(np.zeros(n), np.zeros(n), prudencia, prm, None))
        if t:
            age = np.where(np.abs(E[:, t - 1]) > 0, age + 1, 0)
            f = edad_scale(f, age)
        turnover = float(np.sum(np.abs(f - f_prev) * E[:, t - 1])) if t else 0.0
        idle = max(0.0, 1.0 - float(f.sum()))
        v *= 1 + float(np.dot(f, R[:, t])) + (idle * fx[t] if fx is not None else 0.0) - turnover * eq.COSTE_REPARTO
        val[t] = v; F[:, t] = f; f_prev = f
    return val, F

if ENS == "form":
    eq.PARAMS = [list(eq.PARAMS)]
elif ENS == "modo":
    eq.PARAMS = [[p for p in eq.PARAMS if p["modo"] == m] for m in ("prioridad", "kelly")]
src = open(os.path.join(S, "m2x.py")).read()
src = src.replace("v, _ = eq.simulate(R[team, s], E[team, s], P[team, s], G[team, s], pr, prm, L=L[team, s])",
                  "v, _ = simulate(R[team, s], E[team, s], P[team, s], G[team, s], pr, prm, L=L[team, s], fx=FXR[s])")
assert "fx=FXR" in src
if ENS.startswith("post"):
    ALL = list(eq.PARAMS)
    def grupo(prm):
        if ENS == "postmodo": return [p for p in ALL if p["modo"] == prm["modo"]]
        if ENS == "postcap": return [p for p in ALL if p["modo"] == prm["modo"] and p["cap"] == prm["cap"]]
        if ENS == "postres": return [p for p in ALL if p["modo"] == prm["modo"] and p["reserva"] == prm["reserva"]]
        return ALL
    src = src.replace('t["s"][y], t["v"][y] = sim(t["team"], y, t["pr"], t["prm"], full=True)',
                      't["s"][y], t["v"][y] = sim(t["team"], y, t["pr"], grupo(t["prm"]), full=True)')
    assert "grupo(t" in src
src = src.replace('S = os.path.dirname(os.path.abspath(__file__))', 'pass')
exec(compile(src, "m2x", "exec"))
