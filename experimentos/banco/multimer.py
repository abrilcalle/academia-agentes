# Laboratorio 14/11/2026: puntuación multimercado del inventor (ver más abajo; la cabecera viene de conj.py). Uso: SEEDS=n COMBO=0..5 [ARMS=base,pool,min] python multimer.py
# Laboratorio 10/11/2026 14h: 'agente conjunto' = media de la exposición de las k mejores reglas distintas del inventor.
# Uso: SEEDS=n OFF=i COMBO=i python conj.py -> res_conj_<COMBO>_<OFF>.json
# Laboratorio 07/11/2026 21h: pieza 'vender la mitad al objetivo' en el genoma de los agentes clásicos.
# Uso: MEDIO=0|1|g SEEDS=n COMBO=i python semtp.py -> res_tp_<MEDIO>_<COMBO>.json
# 0 = como ahora (al objetivo sale del todo); 1 = al objetivo vende la mitad y deja correr el resto; g = gen 'medio' que la evolución elige
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


# Laboratorio 14/11/2026 10h: puntuación "multimercado" del inventor. La regla se evoluciona puntuándola en el entreno
# (2018-21) de su mercado y TAMBIÉN de los otros dos (BTC/ETH/XRP, misma temporalidad). Se opera solo en el suyo.
# Uso: SEEDS=n OFF=i COMBO=i python multimer.py -> res_mm_<COMBO>_<OFF>.json
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
    ret = ret[1:-1] if len(ret) > 3 else ret
    return float(np.mean(ret > 0)), ret

MKTS = ["BTC-EUR", "ETH-EUR", "XRP-EUR"]
def evolve_arm(mlist, seeds, cfg, rng, temper, arm, pop=30, gens=15):
    own = mlist[0]; P = inventor.pools(own.bpd); kr = False
    wins = [ac.window(m, "entreno") for m in mlist]
    cache = {}
    def fit(rule):
        key = repr(rule)
        if key not in cache:
            ss = []
            for m, wd in zip(mlist if arm != "base" else mlist[:1], wins):
                w = inventor.exposure(m.I, rule, None, m.bpd)
                ss.append(inventor.robust(m, w, wd, cfg, temper)[0])
            if arm == "base": s = ss[0]
            elif arm == "pool": s = 0.5 * ss[0] + 0.5 * float(np.mean(ss[1:]))
            elif arm == "media": s = float(np.mean(ss))
            else: s = float(min(ss))
            cache[key] = s
        return cache[key]
    popn = [s for s in seeds][:pop // 2]
    popn += [inventor.mutate(rng, rng.choice(seeds), P, kr) for _ in range(pop // 3)] if seeds else []
    while len(popn) < pop:
        popn.append(inventor.random_rule(rng, P, kr))
    for g in range(gens):
        scored = sorted(((fit(r), k, r) for k, r in enumerate(popn)), key=lambda t: -t[0])
        elite = [t[2] for t in scored[: max(2, pop // 5)]]
        def pick():
            x, y = rng.sample(scored[: pop // 2], 2)
            return x[2] if x[0] >= y[0] else y[2]
        nxt = elite[:]
        while len(nxt) < pop:
            child = inventor.cross(rng, pick(), pick()) if rng.random() < 0.5 else pick()
            nxt.append(inventor.mutate(rng, child, P, kr))
        popn = nxt
    return max(popn, key=fit)

def school_seeds(ag, rng):
    m = ac.m(ag); temper = academia.TEMPER[ag["personalidad"]]
    top, _ = ac.study(m, temper, None)
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
    return m, temper, seeds

ARMS = os.environ.get("ARMS", "base,pool,min").split(",")
out = []
pers = ["prudente", "equilibrado", "atrevido"]
combos = [(a, tf) for tf in ("1d", "4h") for a in MKTS]
if os.environ.get("COMBO"): combos = [combos[int(os.environ["COMBO"])]]
t0 = time.time()
OFF = int(os.environ.get("OFF", "0"))
PER = dict(tr=("2018-01-01", "2021-12-31"), y22=("2022-01-01", "2022-12-31"), y23=("2023-01-01", "2023-12-31"))
for activo, tf in combos:
    for sd in range(OFF, OFF + SEEDS):
        rng = random.Random(1000 + sd * 7 + sum(map(ord, activo + tf)) % 97)
        ag = dict(id=f"x{sd}", tf=tf, activo=activo, personalidad=pers[sd % 3])
        m, temper, seeds = school_seeds(ag, rng)
        mlist = [m] + [ac.m(dict(ag, activo=o)) for o in MKTS if o != activo]
        st = rng.random()
        row = dict(activo=activo, tf=tf, sd=sd)
        for arm in ARMS:
            rule = evolve_arm(mlist, seeds, cfg, random.Random(st), temper, arm)
            row[arm] = {}
            for j, mm in enumerate(mlist):
                w = inventor.exposure(mm.I, rule, None, mm.bpd)
                for nm, (a0, b0) in PER.items():
                    if j and nm == "tr": continue
                    a, b = mm.idx(a0), min(mm.end_idx(b0), mm.n - 1)
                    r = run(mm.I, w, a, b, cfg)
                    v, _ = week_stats(mm, r)
                    row[arm][("" if j == 0 else f"o{j}_") + nm] = dict(ret=round(r.ret, 4), verde=round(v, 3), dd=round(r.maxdd, 3), n=r.n_buys)
        out.append(row)
        print(activo, tf, sd, {a: (row[a]["y22"]["ret"], row[a]["y23"]["ret"], row[a]["y22"]["verde"], row[a]["y23"]["verde"]) for a in ARMS}, round(time.time() - t0), flush=True)
        json.dump(out, open(os.path.join(S, f"res_mm_{os.environ.get('COMBO','all')}_{OFF}.json"), "w"))
