# Laboratorio 07/11/2026: ¿y si el inventor de los agentes clásicos premia ganar semanas?
# Uso: LAM=0|2|4 MODO=media|peor python semfit.py  -> res_<LAM>_<MODO>.json
# Entrena (2018-21) agentes clásicos con el mismo azar y solo cambia la puntuación; mide la regla inventada en 2022 y 2023.
import datetime as dt, json, os, sys, random, time
S = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.join(S, "lab")
sys.path.insert(0, LAB); sys.path.insert(0, os.path.join(LAB, "src"))
import numpy as np
import run_daily as rd, data as datamod, inventor, academia
from academia import Academia
from backtest import run

LAM = float(os.environ.get("LAM", "0")); MODO = os.environ.get("MODO", "media")
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
def robust_sem(m, w, window, c, temper):
    s, full = orig(m, w, window, c, temper)
    if LAM == 0 or s <= -5:
        return s, full
    a, b = window
    if MODO == "media":
        v, _ = week_stats(m, full)
    else:  # peor año
        vs = []
        for y in range(m.ts[a].year, m.ts[b].year + 1):
            ya, yb = max(a, m.idx(f"{y}-01-01")), min(b, m.end_idx(f"{y}-12-31"))
            if yb - ya < 60 * m.bpd: continue
            vs.append(week_stats(m, run(m.I, w, ya, yb, c))[0])
        v = min(vs) if vs else 0.5
    return s + LAM * (v - 0.5), full
inventor.robust = robust_sem  # solo dentro de la evolución (study y la medida usan la original)

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
    rule, r_tr, _ = inventor.evolve(m, seeds, tr, cfg, rng, temper, None, pop=30, gens=15)
    return m, rule

out = []
pers = ["prudente", "equilibrado", "atrevido"]
combos = [("BTC-EUR", "1d"), ("ETH-EUR", "1d"), ("XRP-EUR", "1d"), ("BTC-EUR", "4h")]
t0 = time.time()
for activo, tf in combos:
    for sd in range(SEEDS):
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
        json.dump(out, open(os.path.join(S, f"res_{int(LAM)}_{MODO}.json"), "w"))
