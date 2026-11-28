# Banco (28/11/2026 15:00): "inventor con más peso a lo reciente". En el entreno (2018–21) la nota de cada regla
# usa una media de los años ponderada hacia los últimos (REC=lin: 1,2,3,4 · REC=exp: 1,2,4,8; REC=0 = como ahora).
# Se aplica al estudio y al inventor (inventor.robust) solo cuando la ventana empieza en 2018. Basado en gen_inv.py.
# Banco (27/11/2026 15:00): intensidad del inventor (POP × GENS). Basado en st_inv.py.
# Banco (27/11/2026 10:00): piezas Supertrend / ADX / DMI en el inventor. = espejo.py con LAB=lab|lab_st (lab_st = copia con st_piezas.patch) y la regla guardada.
# Banco (24/11/2026 10:00): "inventor con espejo". El inventor de los agentes clásicos puntúa cada regla en el
# entreno (2018–21) y TAMBIÉN en el mismo entreno "dado la vuelta" (1/precio: los años de subida pasan a ser de bajada),
# para premiar reglas que no pierden cuando el mercado cae. Mismas semillas y azar en cada brazo.
# Uso: ESP=0|0.25|0.5 N=… SEED=… OUT=… python3 espejo.py   (carpeta con lab/ = copia del repo y loc/ = data/)
import copy, datetime as dt, json, os, sys, pickle, random, time
S = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.join(S, os.environ.get("LAB", "lab"))
sys.path.insert(0, LAB); sys.path.insert(0, os.path.join(LAB, "src"))
import numpy as np
import run_daily as rd, kronos_signal, data as datamod, inventor, diario
from academia import Academia
from backtest import run


import math as _m
REC = os.environ.get("REC", "0")
_rob0 = inventor.robust
def _robust(mk, w, window, cfg, temper):
    a, b = window
    if REC == "0" or mk.ts[a].year != 2018:
        return _rob0(mk, w, window, cfg, temper)
    full = run(mk.I, w, a, b, cfg)
    sc, ws = [], []
    for i, y in enumerate(range(mk.ts[a].year, mk.ts[b].year + 1)):
        ya, yb = max(a, mk.idx(f"{y}-01-01")), min(b, mk.end_idx(f"{y}-12-31"))
        if yb - ya < 60 * mk.bpd:
            continue
        r = run(mk.I, w, ya, yb, cfg)
        sc.append(inventor.score(r, cfg["cap"], (yb - ya + 1) / (365 * mk.bpd), temper))
        ws.append(1 + i if REC == "lin" else 2 ** i)
    total = inventor.score(full, cfg["cap"], (b - a + 1) / (365 * mk.bpd), temper)
    if not sc:
        return total, full
    wm = sum(x * q for x, q in zip(sc, ws)) / sum(ws)
    return 0.4 * total + 0.6 * (0.5 * wm + 0.5 * min(sc)), full
inventor.robust = _robust

GENS = int(os.environ.get("GENS", "15")); POP = int(os.environ.get("POP", "30"))
cfg0 = json.load(open(os.path.join(LAB, "config.json")))
today = dt.date(2024, 1, 1)
loc = os.path.join(S, "loc")
mk = rd.load_markets(cfg0, loc, today, True)
kr = {tf: kronos_signal.load(LAB, mk[tf], cfg0) for tf in cfg0["kronos"]["temporalidades"] if tf in mk}
otros = rd.load_other_assets(cfg0, loc, today, True)
fx = {d.date(): v[3] for d, v in datamod.load_csv(os.path.join(loc, "usdc_eur_1d.csv")).items()}
for g in [mk] + list(otros.values()):
    for m in g.values():
        m.set_fx(fx)


N = int(os.environ.get("N", "12"))
SEED = int(os.environ.get("SEED", "1"))
TF = os.environ.get("TF", "")
ac = Academia(LAB, mk, kronos=kr, today=today, otros=otros, log=lambda *a: None)
ac.cfg["cotizar_en_usdc"] = True
ac.cfg["fabrica"] = dict(ac.cfg["fabrica"], poblacion_inventor=POP, generaciones_inventor=GENS)
ac.cfg["operadores_diarios"] = dict(ac.cfg["operadores_diarios"], parte_de_los_nuevos=0.0)
if TF:
    ac.cfg["fabrica"] = dict(ac.cfg["fabrica"], temporalidades={TF: 1})
ac.cfg["examen"] = ["2023-01-01", "2023-12-31"]  # el examen no se usa aquí (no hay datos de 2024–25 en la copia)
ac.exam2 = lambda ag: None
rcfg = ac.run_cfg()
out = []
t0 = time.time()
for k in range(N):
    ac.rng = random.Random(SEED * 1000 + k)
    ag = ac.make_agent()
    m = ac.m(ag)
    krag = ac.kr_ag(ag)
    w_inv = inventor.exposure(m.I, ag["regla"], krag, m.bpd)
    w_ch = ac._w[ag["id"]]
    res = dict(name=ag["name"], activo=ag["activo"], tf=ag["tf"], pers=ag["personalidad"], eleccion=ag["eleccion"],
               lado=ag["regla"].get("lado", "largo"), entreno=ag["invento"]["entreno"], regla=ag["regla"])
    for y in (2018, 2019, 2020, 2021, 2022, 2023):
        a, b = m.idx(f"{y}-01-01"), m.end_idx(f"{y}-12-31")
        if a >= b or b - a < 60 * m.bpd:
            continue
        for nm, w in (("inv", w_inv), ("ch", w_ch)):
            r = run(m.I, w, a, b, rcfg)
            d = m.daily(r.eq, a)
            ks = sorted(d); wk = {}
            for day in ks:
                wk.setdefault(day.isocalendar()[:2], []).append(d[day])
            prev, verde, nw = rcfg["cap"], 0, 0
            for kk in sorted(wk):
                end = wk[kk][-1]
                verde += end > prev; nw += 1; prev = end
            res[f"{nm}{y}"] = dict(ret=r.ret, dd=r.maxdd, n=r.n_buys, verde=verde / max(nw, 1))
    out.append(res)
    print(k, ag["name"], ag["activo"], ag["tf"], ag["eleccion"], res["lado"],
          " ".join(f"{y}:{res.get(f'inv{y}', {}).get('ret', float('nan'))*100:+.0f}" for y in (2018, 2019, 2020, 2021, 2022, 2023)),
          f"{time.time()-t0:.0f}s", flush=True)
pickle.dump(out, open(os.path.join(S, os.environ.get("OUT", "out.pkl")), "wb"))
