# Banco (31/10/2026): 200 equipos al azar (4 agentes, como mucho 2 por mercado, prioridad, prudencia 2) con y sin filtro de fuerza relativa.
import os, sys, pickle, runpy, numpy as np
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "lab", "src"))
import equipos as eq
goal = dict(semanas_en_verde_pct=50, ganancia_minima_anual_pct=10, caida_maxima_pct=25)
YRS = [2019, 2020, 2021, 2022, 2023]
res = {}
for v in sys.argv[1:]:
    src = open(os.path.join(S, "m2r.py")).read().split("goal = dict")[0].replace("var = sys.argv[1]", f"var = {v!r}")
    g = {"__file__": os.path.join(S, "m2r.py"), "__name__": "x"}
    exec(src, g)
    days, R, E, P, G, L, info = g["days"], g["R"], g["E"], g["P"], g["G"], g["L"], g["info"]
    rng = np.random.default_rng(1)
    sl = {y: slice(min(k for k, d in enumerate(days) if d.year == y), max(k for k, d in enumerate(days) if d.year == y) + 1) for y in YRS}
    out = {y: [] for y in YRS}
    for y in YRS:
        s = sl[y]
        pool = [j for j in range(len(info)) if R[j, s].std() > 0]
        r2 = np.random.default_rng(y)
        for _ in range(200):
            team = []
            while len(team) < 4:
                j = int(r2.choice(pool))
                if j in team or sum(info[i]["activo"] == info[j]["activo"] for i in team) >= 2: continue
                team.append(j)
            prm = dict(reserva=0.1, cap=0.6, modo="prioridad")
            vv, _ = eq.simulate(R[team, s], E[team, s], P[team, s], G[team, s], 2, prm, L=L[team, s])
            st = eq.stats(days[s], vv)
            out[y].append((not eq.fails(st, goal), st["verde"], st["ret"], st["dd"]))
    print(f"{v:11s}", " ".join(f"{y}: cumplen {sum(x[0] for x in out[y])}/200 sem {np.median([x[1] for x in out[y]])*100:.0f} ret {np.median([x[2] for x in out[y]])*100:+.0f} caída {np.median([x[3] for x in out[y]])*100:.0f} |" for y in YRS), flush=True)
