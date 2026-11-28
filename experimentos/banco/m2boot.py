# Banco (28/11/2026): formación con remuestreo ("bagging" de semanas). Uso: BOOT=base|mean|q25 MAT=mat.pkl OUT=teams_X.pkl YRS=... python m2boot.py
# Al formar (greedy de build), la nota de cada equipo candidato es la media (o el percentil 25) de la nota en K años "posibles"
# hechos con las semanas reales del año de formación sacadas al azar con reemplazo (mismas semanas para todos los candidatos).
import os, sys
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "lab", "src"))
import numpy as np
import equipos as eq
eq.COSTE_REPARTO = float(os.environ.get("COSTE", "0.0008"))
BOOT = os.environ.get("BOOT", "base"); K = int(os.environ.get("K", "30"))
os.environ["ENS"] = "post"; os.environ["LOO"] = "base"
pre = '''
_WK = {}
def _weeks(A):
    if A not in _WK:
        dd = days[sl[A]]; ids = {}
        for i, d in enumerate(dd): ids.setdefault(d.isocalendar()[:2], []).append(i)
        W = list(ids.values()); rg = np.random.default_rng(1000 + A)
        _WK[A] = (W, [rg.integers(0, len(W), len(W)) for _ in range(K)])
    return _WK[A]
def bobj(tj, A, pr, prm):
    st, v = sim(tj, A, pr, prm, full=True)
    if BOOT == "base": return eq.objective(st, goal)
    r = v / np.r_[100.0, v[:-1]] - 1
    W, idx = _weeks(A); wr = [r[w] for w in W]; wk = np.array([np.prod(1 + x) - 1 for x in wr])
    sc = []
    for ix in idx:
        cur = np.cumprod(1 + np.concatenate([wr[i] for i in ix])) * 100
        peak = np.maximum.accumulate(np.r_[100.0, cur]); dd = float(np.max((peak - np.r_[100.0, cur]) / peak))
        s = dict(ret=float(cur[-1] / 100 - 1), verde=float(np.mean(wk[ix] > eq.GOOD)), dd=dd, semanas=len(ix), peor=float(wk[ix].min()))
        sc.append(eq.objective(s, goal))
    return float(np.mean(sc)) if BOOT == "mean" else float(np.percentile(sc, 25))
'''
src = open(os.path.join(S, "m2xloo.py")).read()
src = src.replace("def form(A):", pre + "\ndef form(A):")
src = src.replace("sc = eq.objective(sim(tj, A, pr, prm), goal)", "sc = bobj(tj, A, pr, prm)")
assert "bobj(tj" in src
open(os.path.join(S, "m2xboot_gen.py"), "w").write(src)
# m2ensloo lee m2xloo.py: le damos la versión con remuestreo
ens = open(os.path.join(S, "m2ensloo.py")).read().replace('"m2xloo.py"', '"m2xboot_gen.py"')
assert "m2xboot_gen" in ens
exec(compile(ens, "m2ensboot", "exec"))
