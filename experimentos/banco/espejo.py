# Banco (24/11/2026 10:00): "inventor con espejo". El inventor de los agentes clásicos puntúa cada regla en el
# entreno (2018–21) y TAMBIÉN en el mismo entreno "dado la vuelta" (1/precio: los años de subida pasan a ser de bajada),
# para premiar reglas que no pierden cuando el mercado cae. Mismas semillas y azar en cada brazo.
# Uso: ESP=0|0.25|0.5 N=… SEED=… OUT=… python3 espejo.py   (carpeta con lab/ = copia del repo y loc/ = data/)
import copy, datetime as dt, json, os, sys, pickle, random, time
S = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.join(S, "lab")
sys.path.insert(0, LAB); sys.path.insert(0, os.path.join(LAB, "src"))
import numpy as np
import run_daily as rd, kronos_signal, data as datamod, inventor, diario
from academia import Academia
from backtest import run

ESP = float(os.environ.get("ESP", "0"))
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


def espejo(m):
    """El mismo mercado con el gráfico dado la vuelta (y los precios en USDC también dados la vuelta)."""
    if getattr(m, "_esp", None) is None:
        I = m.I
        J = diario.inverted(I)
        J.fx = I.fx
        J.o_u, J.h_u, J.l_u, J.c_u = 1 / I.o_u, 1 / I.l_u, 1 / I.h_u, 1 / I.c_u
        mm = copy.copy(m)
        mm.I = J
        m._esp = mm
    return m._esp


_evolve = inventor.evolve
CNT = [0]


def evolve(mk_, seeds, window, cfg, rng, temper, kronos=None, pop=30, gens=15, log=None):
    if ESP <= 0:
        return _evolve(mk_, seeds, window, cfg, rng, temper, kronos, pop, gens, log)
    me = espejo(mk_)
    ks = None if kronos is None else dict(kronos, med=-kronos["med"], up=1 - kronos["up"])
    rob = inventor.robust
    cache = {}

    def robust2(m, w, win, c, t):
        # m es mk_ dentro de evolve; w es la exposición de la regla en el mercado real.
        return rob(m, w, win, c, t)

    # se cambia fit a través de exposure+robust: se envuelve inventor.robust durante esta evolución
    def rob_mix(m, w, win, c, t):
        key = id(w)
        s_r, full = rob(m, w, win, c, t)
        rule = _cur.get(key)
        if rule is None:
            return s_r, full
        w_m = inventor.exposure(me.I, rule, ks, me.bpd)
        CNT[0] += 1
        s_m, _ = rob(me, w_m, win, c, t)
        return (1 - ESP) * s_r + ESP * s_m, full

    _cur = {}
    _exp = inventor.exposure

    def exp_track(I, rule, k=None, bpd=1):
        w = _exp(I, rule, k, bpd)
        if I is mk_.I:
            _cur.clear(); _cur[id(w)] = rule
        return w

    inventor.robust, inventor.exposure = rob_mix, exp_track
    try:
        return _evolve(mk_, seeds, window, cfg, rng, temper, kronos, pop, gens, log)
    finally:
        inventor.robust, inventor.exposure = rob, _exp


inventor.evolve = evolve
import academia as acm
acm.inventor.evolve = evolve

N = int(os.environ.get("N", "12"))
SEED = int(os.environ.get("SEED", "1"))
TF = os.environ.get("TF", "")
ac = Academia(LAB, mk, kronos=kr, today=today, otros=otros, log=lambda *a: None)
ac.cfg["cotizar_en_usdc"] = True
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
               lado=ag["regla"].get("lado", "largo"), entreno=ag["invento"]["entreno"])
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
          f"{time.time()-t0:.0f}s", CNT[0], flush=True)
pickle.dump(out, open(os.path.join(S, os.environ.get("OUT", f"esp_{ESP}_{SEED}.pkl")), "wb"))
