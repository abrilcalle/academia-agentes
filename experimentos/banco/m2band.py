# Uso: en la carpeta de pruebas del banco (ver m1.py); antes: sed "s/^pickle.dump(out.*$//" m2p.py > m2p_nosave.py
"""Banda de reparto (31/10/2026 21:00): el equipo solo mueve el dinero de un agente si su parte cambia más de BANDA
(o si abre/cierra/queda bloqueada su operación). Forma con A (como build), guarda stats por año. Uso: python m2band.py VARIANTE"""
import os, sys, pickle, runpy
import numpy as np
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "lab", "src"))
import equipos as eq
V = sys.argv[1]
orig_alloc = eq.alloc
TURN = []
def sim_band(R, E, P, G, prudencia, prm, cap0=100.0, L=None, band=0.0, evento=False):
    n, T = R.shape
    val = np.empty(T); F = np.zeros((n, T)); v = cap0; f_prev = np.zeros(n); tot = 0.0
    st_prev = None
    for t in range(T):
        tgt = (orig_alloc(P[:, t - 1], G[:, t - 1], prudencia, prm, None if L is None else L[:, t - 1]) if t
               else orig_alloc(np.zeros(n), np.zeros(n), prudencia, prm))
        if t:
            st = np.sign(P[:, t - 1])  # 1 abierta, 0 esperando, -1 bloqueada
            f = f_prev.copy()
            chg = (st != st_prev)
            if evento:
                if chg.any(): f = tgt
            else:
                mv = chg | (np.abs(tgt - f_prev) > band) | (tgt == 0)
                f[mv] = tgt[mv]
                if f.sum() > 1: f = f / f.sum()
            st_prev = st
        else:
            f = tgt; st_prev = np.zeros(n)
        turnover = float(np.sum(np.abs(f - f_prev) * E[:, t - 1])) if t else 0.0
        tot += turnover
        v *= 1 + float(np.dot(f, R[:, t])) - turnover * eq.COSTE_REPARTO
        val[t] = v; F[:, t] = f; f_prev = f
    TURN.append(tot / T)
    return val, F
VARS = {"base": None, "b02": dict(band=0.02), "b05": dict(band=0.05), "b10": dict(band=0.10), "b20": dict(band=0.20),
        "evento": dict(evento=True), "b05x0": dict(band=0.05), "base0": None, "c08": None, "c12": None}
kw = VARS[V]
if V.endswith("x0") or V == "base0":
    eq.COSTE_REPARTO = 0.0
if V == "c08": eq.COSTE_REPARTO = 0.0008
if V == "c12": eq.COSTE_REPARTO = 0.0012
if kw is not None:
    eq.simulate = lambda *a, **k: sim_band(*a, **{**k, **kw})
else:
    o = eq.simulate
    eq.simulate = lambda *a, **k: sim_band(*a, **k, band=-1)  # band -1: mueve siempre = base (comprobación)
sys.argv = ["m2p.py"]
g = runpy.run_path(os.path.join(S, "m2p_nosave.py"), run_name="__main__")
pickle.dump(g["out"], open(os.path.join(S, f"teams_{V}.pkl"), "wb"))
print(V, "rotación media diaria", np.mean(TURN))
