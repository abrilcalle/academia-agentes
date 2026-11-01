# Banco (01/11/2026): 200 equipos al azar por año (4 agentes, como mucho 2 por mercado, prioridad, prudencia 2) con cada variante del filtro de tendencia.
import os, sys, pickle, numpy as np
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "lab", "src"))
import equipos as eq
goal = dict(semanas_en_verde_pct=50, ganancia_minima_anual_pct=10, caida_maxima_pct=25)
YRS = [2019, 2020, 2021, 2022, 2023]
for v in sys.argv[1:]:
    M = pickle.load(open(os.path.join(S, f"mat_{v}.pkl"), "rb"))
    days, R, E, P, G, L, info = M["days"], M["R"], M["E"], M["P"], M["G"], M["L"], M["info"]
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
    tot = sum(x[0] for y in YRS for x in out[y])
    print(f"{v:7s} total {tot}/1000 |", " ".join(f"{y}: {sum(x[0] for x in out[y])} sem {np.median([x[1] for x in out[y]])*100:.0f} ret {np.median([x[2] for x in out[y]])*100:+.0f} dd {np.median([x[3] for x in out[y]])*100:.0f} |" for y in YRS), flush=True)
