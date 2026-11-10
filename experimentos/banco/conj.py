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


def evolve2(mk, seeds, window, cfg, rng, temper, pop=30, gens=15):
    I = mk.I; P = inventor.pools(mk.bpd); kr = False; a, b = window
    cache = {}
    def fit(rule):
        key = repr(rule)
        if key not in cache:
            w = inventor.exposure(I, rule, None, mk.bpd)
            cache[key] = (inventor.robust(mk, w, (a, b), cfg, temper), w, rule)
        return cache[key][0]
    popn = [s for s in seeds][:pop // 2]
    popn += [inventor.mutate(rng, rng.choice(seeds), P, kr) for _ in range(pop // 3)] if seeds else []
    while len(popn) < pop:
        popn.append(inventor.random_rule(rng, P, kr))
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
    fin = sorted({repr(r): r for r in popn}.values(), key=lambda r: -fit(r)[0])
    hof = sorted(cache.values(), key=lambda t: -t[0][0])
    return dict(final=final, fin=[(fit(r)[0], cache[repr(r)][1]) for r in fin], hof=[(t[0][0], t[1]) for t in hof])

def greedy(cands, k, a, b, thr=0.9):
    sel = []
    for s, w in cands:
        if s <= -5: break
        x = np.asarray(w, float)[a:b + 1]
        if x.std() == 0: continue
        if all(abs(np.corrcoef(x, y)[0, 1]) < thr for y in [np.asarray(v, float)[a:b + 1] for v in sel]):
            sel.append(w)
        if len(sel) == k: break
    return sel

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
    return m, evolve2(m, seeds, tr, cfg, rng, temper)

out = []
pers = ["prudente", "equilibrado", "atrevido"]
combos = [("BTC-EUR", "1d"), ("ETH-EUR", "1d"), ("XRP-EUR", "1d"), ("BTC-EUR", "4h"), ("ETH-EUR", "4h"), ("XRP-EUR", "4h"), ("SOL-EUR", "1d")]
if os.environ.get("COMBO"): combos = [combos[int(os.environ["COMBO"])]]
t0 = time.time()
for activo, tf in combos:
    for sd in range(int(os.environ.get("OFF","0")), int(os.environ.get("OFF","0")) + SEEDS):
        rng = random.Random(1000 + sd * 7 + sum(map(ord, activo + tf)) % 97)
        ag = dict(id=f"x{sd}", tf=tf, activo=activo, personalidad=pers[sd % 3])
        m, E = school_rule(ag, rng)
        tra, trb = m.idx("2018-01-01"), m.end_idx("2021-12-31")
        W = {"base": inventor.exposure(m.I, E["final"], None, m.bpd)}
        for nm, src_, k in (("f3", "fin", 3), ("f5", "fin", 5), ("h3", "hof", 3), ("h5", "hof", 5)):
            sel = greedy(E[src_], k, tra, trb)
            W[nm] = np.mean([np.asarray(v, float) for v in sel], axis=0) if sel else W["base"]
        row = dict(activo=activo, tf=tf, sd=sd)
        for vn, w in W.items():
            row[vn] = {}
            for nm, (a0, b0) in dict(tr=("2018-01-01", "2021-12-31"), y22=("2022-01-01", "2022-12-31"), y23=("2023-01-01", "2023-12-31")).items():
                a, b = m.idx(a0), min(m.end_idx(b0), m.n - 1)
                r = run(m.I, w, a, b, cfg)
                v, wr = week_stats(m, r)
                row[vn][nm] = dict(ret=round(r.ret, 4), verde=round(v, 3), dd=round(r.maxdd, 3), n=r.n_buys)
        out.append(row)
        print(activo, tf, sd, {v: (row[v]["y22"]["ret"], row[v]["y23"]["ret"], row[v]["y23"]["verde"]) for v in W}, round(time.time() - t0), flush=True)
        json.dump(out, open(os.path.join(S, f"res_conj_{os.environ.get('COMBO','all')}_{os.environ.get('OFF','0')}.json"), "w"))
