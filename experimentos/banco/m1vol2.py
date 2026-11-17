# Banco (17/11/2026): puerta de VOLUMEN en el filtro del equipo. Sobre mat.pkl, bloquea (P = BLOQUEADO) las operaciones
# abiertas que el filtro de tendencia actual deja pasar pero cuyo volumen no acompaña (decisión con el cierre del día):
# VAR=obv50  compras solo si el OBV (volumen acumulado con signo) está sobre su media de 50 días; cortos si está bajo
# VAR=obvp   compras solo si el OBV sube respecto a hace 20 días; cortos si baja
# VAR=vr20   compras solo si en los últimos 20 días el volumen de los días de subida supera al de los de bajada; cortos al revés
# VAR=vrN    igual con N días (30, 50, 70, 100) · obvN: OBV sobre su media de N días
# Uso: VAR=obv50 python m1vol2.py -> mat_obv50.pkl ; luego COSTE=0.0008 ENS=post MAT=mat_obv50.pkl OUT=teams_obv50.pkl python m2cost.py
import os, sys, pickle, numpy as np
S = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(S, "lab", "src"))
import data as datamod, equipos as eq
V = os.environ["VAR"]
M = pickle.load(open(os.path.join(S, "mat.pkl"), "rb")); days = M["days"]; P = M["P"].copy()
def candles(a):
    s = a.split("-")[0].lower(); d = datamod.load_csv(os.path.join(S, "loc", f"{s}_1d.csv"))
    ks = sorted(k for k in d if k.year < 2024)
    return [k.date() for k in ks], np.array([d[k][3] for k in ks], float), np.array([d[k][4] for k in ks], float)
cache = {}
def side_ok(a):
    if a in cache: return cache[a]
    ds, c, vol = candles(a)
    sg = np.r_[0.0, np.sign(np.diff(c))]
    obv = np.cumsum(sg * vol)
    ma = lambda x, n: np.convolve(x, np.ones(n) / n, "full")[:len(x)]
    out = {}
    if V.startswith("obv") and V[3:].isdigit():
        n = int(V[3:]); m = ma(obv, n); st = np.sign(obv - m); i0 = n
    elif V == "obvp":
        st = np.r_[np.zeros(20), np.sign(obv[20:] - obv[:-20])]; i0 = 20
    elif V.startswith("vr"):
        n = int(V[2:]); up = ma(np.where(sg > 0, vol, 0.0), n); dn = ma(np.where(sg < 0, vol, 0.0), n)
        st = np.sign(up - dn); i0 = n
    for i in range(i0, len(c)):
        out[ds[i]] = st[i]
    cache[a] = out; return out
tr = {}
for a in set(i["activo"] for i in M["info"]):
    ds, c, _ = candles(a); m = np.convolve(c, np.ones(50) / 50, "full")[:len(c)]
    tr[a] = {ds[i]: (1 if c[i] > m[i] else -1) for i in range(50, len(c))}
nb = 0; tot = int((M["P"] > 0).sum())
for j, inf in enumerate(M["info"]):
    g = side_ok(inf["activo"])
    for k, d in enumerate(days):
        if P[j, k] > 0:
            side = tr[inf["activo"]].get(d, 0)  # si P > 0 la operación va del lado de la tendencia (precio vs media de 50)
            s = g.get(d, 0)
            if s != side:
                P[j, k] = eq.BLOQUEADO; nb += 1
print(V, "bloqueados", nb, "de", tot, f"({nb/tot:.0%})")
M["P"] = P
pickle.dump(M, open(os.path.join(S, f"mat_{V}.pkl"), "wb"))
