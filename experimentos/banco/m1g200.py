# Banco (15/11/2026): segunda puerta de tendencia larga en el filtro del equipo. Sobre mat.pkl, bloquea (P = BLOQUEADO)
# las operaciones abiertas que el filtro de 50 días deja pasar pero que van contra la tendencia larga:
# VAR=g200 compras solo con cierre > media de 200 días y cortos solo con cierre < media 200 · g200L solo las compras ·
# g100 igual con media de 100 · gx compras solo con media 50 > media 200 (y cortos con 50 < 200).
# Uso: VAR=g200 python m1g200.py -> mat_g200.pkl ; luego COSTE=0.0008 ENS=post MAT=mat_g200.pkl OUT=teams_g200.pkl python m2cost.py
import os, sys, pickle, numpy as np
S = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(S, "lab", "src"))
import data as datamod, equipos as eq
V = os.environ["VAR"]
M = pickle.load(open(os.path.join(S, "mat.pkl"), "rb")); days = M["days"]; P = M["P"].copy()
def closes(a):
    s = a.split("-")[0].lower(); d = datamod.load_csv(os.path.join(S, "loc", f"{s}_1d.csv"))
    ks = sorted(k for k in d if k.year < 2024); return [k.date() for k in ks], np.array([d[k][3] for k in ks], float)
cache = {}
def gate(a):
    if a in cache: return cache[a]
    ds, c = closes(a)
    ma = lambda n: np.convolve(c, np.ones(n) / n, "full")[:len(c)]
    m50, m200, m100 = ma(50), ma(200), ma(100)
    out = {}
    for i in range(200, len(c)):
        t50 = 1 if c[i] > m50[i] else -1
        if V in ("g200", "g200L"): t2 = 1 if c[i] > m200[i] else -1
        elif V == "g100": t2 = 1 if c[i] > m100[i] else -1
        elif V == "gx": t2 = 1 if m50[i] > m200[i] else -1
        bad = t2 != t50 and (V != "g200L" or t50 == 1)
        out[ds[i]] = bad
    cache[a] = out; return out
nb = 0
for j, inf in enumerate(M["info"]):
    g = gate(inf["activo"])
    for k, d in enumerate(days):
        if P[j, k] > 0 and g.get(d, False):
            P[j, k] = eq.BLOQUEADO; nb += 1
print(V, "bloqueados", nb, "de", int((M["P"] > 0).sum()))
M["P"] = P
pickle.dump(M, open(os.path.join(S, f"mat_{V}.pkl"), "wb"))
