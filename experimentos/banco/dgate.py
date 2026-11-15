# Banco (15/11/2026): operadores diarios con "puerta" de tendencia diaria (la misma del equipo: media 50 + pendiente 10).
# Paso 1: reglas ya inventadas de los operadores diarios (state), con y sin puerta, medidas en entreno y 2022 / 2023.
# Paso 2 (EVOL=1): evolución completa con la puerta dentro (mismas semillas y azar que sin ella).
import datetime as dt, json, os, sys, pickle, random
S = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.join(S, "lab")
sys.path.insert(0, LAB); sys.path.insert(0, os.path.join(LAB, "src"))
import numpy as np
import run_daily as rd, kronos_signal, data as datamod, equipos as eq, diario, inventor
from academia import Academia
from backtest import run
cfg = json.load(open(os.path.join(LAB, "config.json")))
today = dt.date(2024, 1, 1)
loc = os.path.join(S, "loc")
mk = rd.load_markets(cfg, loc, today, True)
kr = {tf: kronos_signal.load(LAB, mk[tf], cfg) for tf in cfg["kronos"]["temporalidades"] if tf in mk}
otros = rd.load_other_assets(cfg, loc, today, True)
fx = {d.date(): v[3] for d, v in datamod.load_csv(os.path.join(loc, "usdc_eur_1d.csv")).items()}
for g in [mk] + list(otros.values()):
    for m in g.values():
        m.set_fx(fx)
ac = Academia(LAB, mk, kronos=kr, today=today, otros=otros, log=lambda *a: None)
ac.cfg["cotizar_en_usdc"] = True
RC = ac.run_cfg()
cd = ac.cfg["operadores_diarios"]
diario.OBJETIVO_SEMANAL = cd.get("objetivo_semanal_pct", 1) / 100

_gc = {}
def gate(ag, m):
    """+1 / -1 / 0 por vela, con la tendencia del día anterior ya cerrado."""
    key = (ag.get("activo", "BTC-EUR"), ag["tf"])
    if key in _gc: return _gc[key]
    tb = eq.trend_by_day(ac, ag, 50, 10)
    days = sorted(tb); import bisect
    out = np.zeros(m.I.n)
    for i, ts in enumerate(m.ts):
        k = bisect.bisect_left(days, ts.date()) - 1  # último día cerrado antes de hoy
        if k >= 0: out[i] = tb[days[k]]
    _gc[key] = out
    return out

def apply(w, g, mode):
    if mode == "base": return w
    if mode == "gate":   # compras solo con tendencia alcista, cortos solo con bajista
        return np.where(w > 0, w * (g > 0), w * (g < 0))
    if mode == "soft":   # solo prohíbe ir contra la tendencia (en "sin tendencia" deja hacer)
        return np.where(w > 0, w * (g >= 0), w * (g <= 0))
    raise ValueError(mode)

def hold_mask(w, wg):
    # la puerta solo impide ABRIR: si ya está dentro, sigue hasta que la regla salga (como el agente)
    out = wg.copy(); n = len(w)
    for i in range(1, n):
        if w[i] != 0 and out[i - 1] != 0 and np.sign(w[i]) == np.sign(out[i - 1]) and out[i] == 0:
            out[i] = w[i]
    return out

def measure(m, w, win):
    r = run(m.I, w, win[0], win[1], RC)
    s = diario.stats(m, r)
    return dict(ret=r.ret, dd=r.maxdd, sem_pos=s["sem_pos"], sem_neg=s["sem_neg"], dias=s["dias_sem"], avg=r.avg_trade if r.closed else 0.0, closed=r.closed)

def pasa_val(x, crit):
    return (x["ret"] * 100 >= crit["ganancia_minima_pct"] and x["dias"] >= crit["dias_operando_por_semana"]
            and x["sem_pos"] * 100 >= crit["semanas_en_positivo_pct"] and x["dd"] * 100 <= crit["caida_maxima_pct"]
            and x["avg"] * 100 >= crit["ganancia_media_por_operacion_pct"])

def wins(m, y):
    return m.idx(f"{y}-01-01"), min(m.end_idx(f"{y}-12-31"), m.n - 1)

if os.environ.get("EVOL") != "1":
    D = [a for a in ac.state["agents"] if a.get("estilo") == "diario" and ac.has_market(a) and a.get("regla")]
    print(len(D), "operadores", flush=True)
    rows = []
    for ag in D:
        m = ac.m(ag); k = ac.kr_ag(ag)
        w = diario.exposure(m.I, ag["regla"], k, m.bpd)
        g = gate(ag, m)
        row = dict(id=ag["id"], activo=ag.get("activo", "BTC-EUR"), tf=ag["tf"])
        for mode in ("base", "gate", "soft", "gateh"):
            wm = hold_mask(w, apply(w, g, "gate")) if mode == "gateh" else apply(w, g, mode)
            row[mode] = {}
            tr = ac.window(m, "entreno")
            row[mode]["tr"] = measure(m, wm, tr)
            for y in (2022, 2023):
                row[mode][y] = measure(m, wm, wins(m, y))
            row[mode]["va"] = measure(m, wm, ac.window(m, "validacion"))
        rows.append(row)
    pickle.dump(rows, open(os.path.join(S, "dgate_post.pkl"), "wb"))
    print("ok")
else:
    # evolución con la puerta dentro: misma escuela que school_diario (sin padres), mismo azar por brazo
    MODE = os.environ.get("MODE", "base")
    N = int(os.environ.get("N", "8"))
    orig = diario.exposure
    def ex_gate(I, rule, kronos=None, bpd=24):
        w = orig(I, rule, kronos, bpd)
        g = I._gate if getattr(I, "_gate", None) is not None else None
        return w if (MODE == "base" or g is None) else apply(w, g, MODE)
    diario.exposure = ex_gate
    rows = []
    combos = [("BTC-EUR", "4h"), ("ETH-EUR", "4h"), ("XRP-EUR", "4h"), ("BTC-EUR", "1h"), ("ETH-EUR", "1h"), ("XRP-EUR", "1h")]
    for activo, tf in combos:
        for sd in range(N):
            ag = dict(id=f"x{sd}", name="x", activo=activo, tf=tf, personalidad=["prudente", "equilibrado", "atrevido"][sd % 3])
            m = ac.m(ag)
            m.I._gate = gate(ag, m)
            ac.rng = random.Random(1000 + sd * 7 + sum(map(ord, activo + tf)) % 97)
            rng = ac.rng
            P = inventor.pools(m.bpd)
            from academia import TEMPER
            temper = TEMPER[ag["personalidad"]]
            ideas = [i for i in ac.ideas_for(activo)]
            rng.shuffle(ideas)
            seeds = [diario.from_sub(rng, P, False, i["regla"]) for i in ideas[:5]]
            for _ in range(2):
                seeds.append(diario.from_sub(rng, P, False, inventor.pattern_seed(rng, P, False)))
            trw = ac.window(m, "entreno")
            rule, r_tr, hist, _ = diario.evolve(m, seeds, trw, RC, rng, temper, None, pop=cd["poblacion_inventor"], gens=cd["generaciones_inventor"])
            w = diario.exposure(m.I, rule, None, m.bpd)
            row = dict(activo=activo, tf=tf, sd=sd, tr=measure(m, w, trw), va=measure(m, w, ac.window(m, "validacion")))
            for y in (2022, 2023):
                row[y] = measure(m, w, wins(m, y))
            rows.append(row)
            print(MODE, activo, tf, sd, round(row["tr"]["ret"], 3), round(row["va"]["ret"], 3), round(row["va"]["sem_pos"], 2), flush=True)
    pickle.dump(rows, open(os.path.join(S, f"dgate_evol_{MODE}.pkl"), "wb"))
    print("ok")
