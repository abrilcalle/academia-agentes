# Laboratorio 09/11/2026 21:00: agentes "vender rebotes en bajista / comprar retrocesos en alcista" (rebote1.py),
# los 2 mejores por mercado y lado según el ENTRENO (2018-21), añadidos a la cantera de agentes -> mat_reb.pkl
import os, sys, pickle, hashlib, datetime as dt
S = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(S, "rebote1.py")).read().split("out = {}")[0]
exec(compile(src, "reb", "exec"))
import equipos as eq
eq.HIST = "2018-01-01"
o = pickle.load(open(os.path.join(S, "rebote.pkl"), "rb"))
SIDES = [int(x) for x in os.environ.get("SIDES", "-1,1").split(",")]
agents, info = [], []
for act in ["BTC-EUR", "ETH-EUR", "XRP-EUR"]:
    fl = o[(act, "flat")]
    for side in SIDES:
        ks = [k for k in o if k[0] == act and k[1] == side]
        sc = lambda k: sum(o[k][y][0] - fl[y][0] for y in range(2018, 2022)) - max(o[k][y][1] for y in range(2018, 2022))
        for k in sorted(ks, key=sc, reverse=True)[:2]:
            ag = dict(id=hashlib.sha1(str(k).encode()).hexdigest()[:10], name=str(k[1:])[:30], activo=act, tf="1d",
                      eleccion="propia", regla={}, genome={}, params={})
            M = ac.m(ag); ac._w[ag["id"]] = rule(M.I, *k[1:])
            agents.append(ag); info.append(dict(id=ag["id"], name=ag["name"], activo=act, short=(side < 0)))
days, R, E, P, G, L = eq.matrix(ac, agents, "2019-01-01", dt.date(2023, 12, 31))
A = pickle.load(open(os.path.join(S, "mat.pkl"), "rb"))
assert list(A["days"]) == list(days)
out = dict(days=days, info=A["info"] + info, **{k: np.vstack([A[k], v]) for k, v in dict(R=R, E=E, P=P, G=G, L=L).items()})
pickle.dump(out, open(os.path.join(S, os.environ.get("OUTM", "mat_reb.pkl")), "wb"))
print("ok", out["R"].shape, [x["name"] + x["activo"][:3] for x in info])
