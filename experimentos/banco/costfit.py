# Laboratorio 19/11/2026: inventor que evoluciona con costes multiplicados ("estrés de comisiones"); copia de robfit.py.
# Uso: MODO=base|cx2|cx3|cx5 SEEDS=n SD0=0 python costfit.py -> rob_<MODO>.json (se compara con robfit_ana.py)
# cxN: en la evolución (2018-21) cada regla se puntúa con comisión y deslizamiento ×N; se mide con los costes reales.
# Entrena (2018-21) agentes clásicos con el mismo azar y solo cambia la puntuación; mide la regla inventada en 2022 y 2023.
import datetime as dt, json, os, sys, random, time, zlib
S = os.path.dirname(os.path.abspath(__file__))
SD0 = int(os.environ.get("SD0", "0"))
LAB = os.path.join(S, "lab")
sys.path.insert(0, LAB); sys.path.insert(0, os.path.join(LAB, "src"))
import numpy as np
import run_daily as rd, data as datamod, inventor, academia
from academia import Academia
from backtest import run

MODO = os.environ.get("MODO", "base"); K = int(os.environ.get("K", "3"))
SEEDS = int(os.environ.get("SEEDS", "6"))
cfgj = json.load(open(os.path.join(LAB, "config.json")))
today = dt.date(2024, 1, 1)
loc = os.path.join(S, "loc")
mk = rd.load_markets(cfgj, loc, today, True)
otros = rd.load_other_assets(cfgj, loc, today, True)
fx = {d.date(): v[3] for d, v in datamod.load_csv(os.path.join(loc, "usdc_eur_1d.csv")).items()}
for g in [mk] + list(otros.values()):
    for m in g.values():
        m.set_fx(fx)
ac = Academia(LAB, mk, kronos={}, today=today, otros=otros, log=lambda *a: None)
ac.cfg["cotizar_en_usdc"] = True
cfg = ac.run_cfg()
XN = float(MODO[2:]) if MODO.startswith("cx") else 1.0
CFGX = dict(cfg, fee=cfg["fee"] * XN, slip=cfg["slip"] * XN, maker=cfg["maker"] * XN)

WK = {}
def weeks(m):
    if id(m) not in WK:
        WK[id(m)] = np.array([t.isocalendar()[0] * 100 + t.isocalendar()[1] for t in m.ts])
    return WK[id(m)]

def week_stats(m, r):
    wk = weeks(m)[r.a:r.b + 1]
    eq = np.asarray(r.eq)
    last = np.r_[np.nonzero(wk[1:] != wk[:-1])[0], len(wk) - 1]
    v = np.r_[eq[0], eq[last]]
    ret = v[1:] / v[:-1] - 1
    ret = ret[1:-1] if len(ret) > 3 else ret  # sin semanas incompletas
    return float(np.mean(ret > 0)), ret

orig = inventor.robust
def fit_rule(m, rule, window, c, temper, cache, kr=False):
    key = repr(rule)
    if key in cache: return cache[key]
    w = inventor.exposure(m.I, rule, None, m.bpd)
    if MODO.startswith("cx"):
        cache[key] = orig(m, w, window, CFGX, temper); return cache[key]
    s, full = orig(m, w, window, c, temper)
    if MODO == "base" or s <= -5:
        cache[key] = (s, full); return cache[key]
    extra = []
    if MODO in ("ret", "ambos"):
        wd = np.r_[0.0, np.asarray(w, float)[:-1]]
        extra.append(orig(m, wd, window, c, temper)[0])
    if MODO in ("vec", "ambos", "vecmin"):
        P = inventor.pools(m.bpd)
        rr = random.Random(zlib.crc32(key.encode()))
        for _ in range(K):
            r2 = {k: (v[:] if isinstance(v, list) else v) for k, v in rule.items()}
            r2["entry"] = [x[:] for x in rule["entry"]]; r2["exit"] = [x[:] for x in rule["exit"]]
            side = rr.choice(["entry", "exit"]) if r2["exit"] else "entry"
            j = rr.randrange(len(r2[side]))
            r2[side][j] = inventor._tweak(rr, r2[side][j], P)
            if repr(r2) == key:  # sin parámetro que mover: cambia el stop
                r2["stop"] = rr.choice([0, 2, 3, 4])
            w2 = inventor.exposure(m.I, r2, None, m.bpd)
            extra.append(orig(m, w2, window, c, temper)[0])
    if MODO == "vecmin":
        sc = 0.5 * s + 0.5 * min(extra)
    else:
        sc = 0.5 * s + 0.5 * float(np.mean(extra))
    cache[key] = (sc, full)
    return cache[key]

def evolve2(mk, seeds, window, c, rng, temper, kronos=None, pop=30, gens=15, log=None):
    P = inventor.pools(mk.bpd); kr = False; cache = {}
    fit = lambda r: fit_rule(mk, r, window, c, temper, cache)
    popn = [s for s in seeds][:pop // 2]
    popn += [inventor.mutate(rng, rng.choice(seeds), P, kr) for _ in range(pop // 3)] if seeds else []
    while len(popn) < pop: popn.append(inventor.random_rule(rng, P, kr))
    for g in range(gens):
        scored = sorted(((fit(r)[0], k, r) for k, r in enumerate(popn)), key=lambda t: -t[0])
        elite = [t[2] for t in scored[: max(2, pop // 5)]]
        def pick():
            x, y = rng.sample(scored[: pop // 2], 2)
            return x[2] if x[0] >= y[0] else y[2]
        nxt = elite[:]
        while len(nxt) < pop:
            child = inventor.cross(rng, pick(), pick()) if rng.random() < 0.5 else pick()
            nxt.append(inventor.mutate(rng, child, P, kr))
        popn = nxt
    final = max(popn, key=lambda r: fit(r)[0])
    return final, fit(final)[1], []
robust_sem = orig

def school_rule(ag, rng):
    m = ac.m(ag); temper = academia.TEMPER[ag["personalidad"]]
    mk_tr, _ = ac.train_market(ag, None)
    inventor.robust = orig
    top, _ = ac.study(mk_tr, temper, None)
    inventor.robust = robust_sem
    seeds = []
    for _, g2, p2, _ in top:
        rule = inventor.seed_from_family(g2["family"], p2, m.bpd)
        rule["stop"] = g2["stop"] or rule["stop"]
        rule["sizing"] = "riesgo" if g2["sizing"] == "riesgo" else rule["sizing"]
        if g2["filter"] == "tendencia": rule["entry"].append(["sobre_media", 200])
        elif g2["filter"] == "calma": rule["entry"].append(["vol_baja", 30 * m.bpd if m.bpd > 1 else 30, 0.9])
        rule["entry"] = rule["entry"][:3]
        seeds.append(rule)
    P = inventor.pools(m.bpd)
    seeds += [dict(r, lado="corto") for r in seeds[:2]]
    for _ in range(3): seeds.append(inventor.pattern_seed(rng, P, False))
    ideas = ac.ideas_for(ag["activo"])
    for idea in rng.sample(ideas, 5):
        r = dict(idea["regla"]); r["entry"] = [list(x) for x in r["entry"]]; r["exit"] = [list(x) for x in r["exit"]]
        seeds.insert(0, r)
    tr = ac.window(m, "entreno")
    rule, r_tr, _ = evolve2(m, seeds, tr, cfg, rng, temper, None, pop=30, gens=15)
    return m, rule

out = []
pers = ["prudente", "equilibrado", "atrevido"]
combos = [("BTC-EUR", "1d"), ("ETH-EUR", "1d"), ("XRP-EUR", "1d"), ("BTC-EUR", "4h")]
t0 = time.time()
for activo, tf in combos:
    for sd in range(SD0, SD0 + SEEDS):
        rng = random.Random(1000 + sd * 7 + sum(map(ord, activo + tf)) % 97)
        ag = dict(id=f"x{sd}", tf=tf, activo=activo, personalidad=pers[sd % 3])
        m, rule = school_rule(ag, rng)
        w = inventor.exposure(m.I, rule, None, m.bpd)
        row = dict(activo=activo, tf=tf, sd=sd)
        for nm, (a0, b0) in dict(tr=("2018-01-01", "2021-12-31"), y22=("2022-01-01", "2022-12-31"), y23=("2023-01-01", "2023-12-31")).items():
            a, b = m.idx(a0), min(m.end_idx(b0), m.n - 1)
            r = run(m.I, w, a, b, cfg)
            v, wr = week_stats(m, r)
            row[nm] = dict(ret=round(r.ret, 4), verde=round(v, 3), dd=round(r.maxdd, 3), n=r.n_buys, wk=[round(float(x), 5) for x in wr])
        out.append(row)
        print(activo, tf, sd, {k: (row[k]["ret"], row[k]["verde"]) for k in ("tr", "y22", "y23")}, round(time.time() - t0), flush=True)
        json.dump(out, open(os.path.join(S, f"rob_{MODO}" + (f"_{SD0}" if SD0 else "") + ".json"), "w"))
