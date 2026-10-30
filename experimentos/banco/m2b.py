# Seguro bajista (30/10/2026): tras m1, bear1 y m1b; luego m2b.py y m3b.py.
"""Equipos como build (año A) + 'seguro bajista': k especialistas bajistas por mercado añadidos a cada equipo (elegidos solo con 2018-21)."""
import os, sys, pickle
S = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(S, "lab", "src"))
import numpy as np, equipos as eq
exec(open(os.path.join(S, "m2.py")).read().split("out = {}")[0])  # carga mat.pkl, sim y form
B = pickle.load(open(os.path.join(S, "matb.pkl"), "rb"))
o = {**pickle.load(open(os.path.join(S, "bear_1d.pkl"), "rb")), **pickle.load(open(os.path.join(S, "bear_4h.pkl"), "rb"))}
import hashlib
score = {}
for k, v in o.items():
    if k[2] == "_flat": continue
    fl = o[k[:2] + ("_flat",)]["raw"]; r = v["g2"]; ex = [r[y][0] - fl[y][0] for y in range(2018, 2022)]
    score[hashlib.sha1(f"{k[0]}{k[1]}{k[2]}".encode()).hexdigest()[:10]] = ex[0] + sum(ex[1:])
n0 = R.shape[0]
R = np.vstack([R, B["R"]]); E = np.vstack([E, B["E"]]); P = np.vstack([P, B["P"]]); G = np.vstack([G, B["G"]]); L = np.vstack([L, B["L"]])
binfo = B["info"]
def topk(k):
    out = []
    for act in ["BTC-EUR", "ETH-EUR", "XRP-EUR"]:
        c = sorted([j for j, x in enumerate(binfo) if x["activo"] == act], key=lambda j: -score[binfo[j]["id"]])[:k]
        out += [n0 + j for j in c]
    return out
VARS = {"base": [], "b1": topk(1), "b2": topk(2)}
for v, js in VARS.items(): print(v, [binfo[j - n0]["name"] + " " + binfo[j - n0]["activo"][:3] for j in js])
out = {v: {} for v in VARS}
for A in YRS:
    T = form(A)
    for v, js in VARS.items():
        TT = []
        for t in T:
            t2 = dict(team=t["team"] + js, pr=t["pr"], prm=t["prm"])
            t2["s"] = {y: sim(t2["team"], y, t2["pr"], t2["prm"]) for y in YRS if y != A}
            t2["sA"] = sim(t2["team"], A, t2["pr"], t2["prm"])
            TT.append(t2)
        out[v][A] = TT
    print("formado", A, len(T), flush=True)
pickle.dump(out, open(os.path.join(S, "teamsb.pkl"), "wb"))
