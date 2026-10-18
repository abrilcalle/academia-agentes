"""Operadores diarios: agentes que operan casi cada día y buscan acabar CADA SEMANA en positivo tras comisiones.

Cada operador tiene tres estrategias, una por tipo de mercado, y un detector que decide cuál usar:
  - alcista: el precio está sobre su media y el mercado avanza con tendencia
  - lateral: el precio va y viene sin tendencia clara
  - bajista: el precio está bajo su media y cae con tendencia (solo puede comprar al contado: o rebotes
    cortos o quedarse fuera)
Las operaciones son cortas (de horas a pocos días) y se puntúan semana a semana: cuenta qué parte de las
semanas acaba en positivo, cuánto gana de media por semana, la peor semana y que opere a menudo.
"""
import numpy as np

import inventor as V
from backtest import run

REGIMES = ("alcista", "lateral", "bajista")
REG_LABEL = {"alcista": "mercado alcista", "lateral": "mercado lateral", "bajista": "mercado bajista"}
HOLD_D = [1, 1, 2, 3, 5]                       # días máximos que dura una operación
TP_D = [0, 0.01, 0.015, 0.02, 0.03, 0.05]       # objetivo de beneficio
TRAIL_D = [0, 0.01, 0.015, 0.02, 0.03]          # stop que sube con el precio
MIN_NET_D = [0.007, 0.01, 0.015]                # ganancia mínima para cerrar por señal (las comisiones ida y vuelta son 0,6 %)
REG_MA = [20, 50, 100]                          # media (en días) que separa alcista de bajista
REG_ER = [3, 7, 14]                             # días con los que se mide si hay tendencia
REG_X = [0.15, 0.2, 0.3]                        # eficiencia mínima para considerar que hay tendencia


# ------------------------------------------------------------------ detector de régimen

def regime_masks(I, reg, bpd):
    key = ("regmask", reg["ma"], reg["er"], reg["x"])
    if key in I._m:
        return I._m[key]
    ma = I.sma(reg["ma"] * bpd)
    er = I.er(reg["er"] * bpd)
    with np.errstate(invalid="ignore"):
        trend = np.nan_to_num(er) > reg["x"]
        up = I.c > ma
        down = I.c < ma
    out = {"alcista": trend & up, "bajista": trend & down, "lateral": ~trend}
    I._m[key] = out
    for k, m in out.items():
        I._m[key + (k,)] = m
    return out


def _fix(sub):
    """Mantiene las operaciones cortas (es un operador diario)."""
    if not sub.get("hold") or sub["hold"] > 5:
        sub["hold"] = 3
    sub["min_net"] = sub.get("min_net", 0.01) if sub.get("min_net", 0.01) <= 0.015 else 0.01
    return sub


def exposure(I, rule, kronos=None, bpd=24):
    masks = regime_masks(I, rule["regimen"], bpd)
    w = np.zeros(I.n)
    for k in REGIMES:
        sub = rule.get(k)
        if not sub:
            continue
        # la estrategia de cada régimen solo ABRE operaciones cuando el detector dice que estamos en ese régimen
        rg = rule["regimen"]
        s = dict(sub, entry=sub["entry"] + [["_mask", ("regmask", rg["ma"], rg["er"], rg["x"], k)]])
        w = np.maximum(w, V.exposure(I, s, kronos, bpd))
    return np.clip(w, 0, 1)


# ------------------------------------------------------------------ medir semanas

def week_ids(mk):
    if not hasattr(mk, "_wid"):
        mk._wid = np.array([d.isocalendar()[0] * 100 + d.isocalendar()[1] for d in mk.ts])
    return mk._wid


def weekly(mk, r):
    """Rentabilidad de cada semana (lunes a domingo) de un resultado del backtest."""
    wid = week_ids(mk)[r.a:r.b + 1]
    eq = np.asarray(r.eq)
    last = np.r_[np.nonzero(wid[1:] != wid[:-1])[0], len(wid) - 1]
    ends = eq[last]
    prev = np.r_[100.0, ends[:-1]]  # la primera semana se mide desde el saldo inicial
    return ends / prev - 1


def stats(mk, r):
    wk = weekly(mk, r)
    n = max(1, len(wk))
    buys = sum(t["side"] == "compra" for t in r.trades)
    days = len({mk.ts[t["i"]].date() for t in r.trades if t["side"] == "compra"})
    return dict(semanas=int(len(wk)), sem_pos=float(np.mean(wk > 0.0005)) if len(wk) else 0.0,
                sem_neg=float(np.mean(wk < -0.0005)) if len(wk) else 0.0,
                media_sem=float(np.mean(wk)) if len(wk) else 0.0, peor_sem=float(np.min(wk)) if len(wk) else 0.0,
                ops_sem=buys / n, dias_sem=days / n)


def score(mk, r, temper):
    """Puntuación de un operador diario: semanas en positivo, ganancia semanal, peor semana y actividad."""
    if r.final <= 0 or r.dead:
        return -9.0, None
    s = stats(mk, r)
    pts = 1.5 * s["sem_pos"] - 1.0 * s["sem_neg"] + 25 * s["media_sem"]
    pts -= temper * 3 * max(0.0, -s["peor_sem"] - 0.04)       # semanas muy malas restan
    pts -= temper * max(0.0, r.maxdd - 0.15)
    pts -= 0.5 * max(0.0, 3 - s["dias_sem"])                    # quiere operar al menos 3 días por semana
    if r.closed and r.avg_trade < 0.002:                         # cada operación debe dejar algo tras comisiones
        pts -= 0.3 + 30 * (0.002 - r.avg_trade)
    return pts, s


def robust(mk, w, window, cfg, temper):
    """Puntúa año a año: la media y, sobre todo, el peor año (alcista, bajista o lateral)."""
    a, b = window
    full = run(mk.I, w, a, b, cfg)
    y0, y1 = mk.ts[a].year, mk.ts[b].year
    per = []
    for y in range(y0, y1 + 1):
        ya, yb = max(a, mk.idx(f"{y}-01-01")), min(b, mk.end_idx(f"{y}-12-31"))
        if yb - ya < 60 * mk.bpd:
            continue
        per.append(score(mk, run(mk.I, w, ya, yb, cfg), temper)[0])
    total = score(mk, full, temper)[0]
    if not per:
        return total, full
    return 0.4 * total + 0.6 * (0.5 * sum(per) / len(per) + 0.5 * min(per)), full


# ------------------------------------------------------------------ inventar

def random_sub(rng, P, kr):
    r = V.random_rule(rng, P, kr)
    r.update(hold=rng.choice(HOLD_D), tp=rng.choice(TP_D), trail=rng.choice(TRAIL_D), min_net=rng.choice(MIN_NET_D),
             pyr=0, frac=rng.choice([1.0, 1.0, 0.5]))
    return _fix(r)


def random_rule(rng, P, kr):
    rule = dict(regimen=dict(ma=rng.choice(REG_MA), er=rng.choice(REG_ER), x=rng.choice(REG_X)))
    for k in REGIMES:
        rule[k] = None if (k == "bajista" and rng.random() < 0.3) else random_sub(rng, P, kr)
    return rule


def from_sub(rng, P, kr, sub):
    """Una idea de partida: usa una estrategia (de internet, chartismo...) en uno de los regímenes."""
    rule = random_rule(rng, P, kr)
    k = rng.choice(REGIMES)
    s = dict(sub)
    s["entry"] = [list(c) for c in sub["entry"]][:3]
    s["exit"] = [list(c) for c in sub["exit"]]
    s.update(hold=rng.choice(HOLD_D), tp=s.get("tp") if s.get("tp") in TP_D else rng.choice(TP_D[1:]),
             trail=rng.choice(TRAIL_D), min_net=rng.choice(MIN_NET_D), pyr=0)
    rule[k] = _fix(s)
    return rule


def mutate(rng, rule, P, kr):
    r = {k: (dict(v) if isinstance(v, dict) else v) for k, v in rule.items()}
    op = rng.random()
    if op < 0.12:
        key = rng.choice(["ma", "er", "x"])
        r["regimen"][key] = rng.choice({"ma": REG_MA, "er": REG_ER, "x": REG_X}[key])
        return r
    k = rng.choice(REGIMES)
    if r[k] is None:
        r[k] = random_sub(rng, P, kr)
    elif k == "bajista" and op < 0.17:
        r[k] = None  # en mercado bajista, quedarse fuera también es una opción
    elif op < 0.3:
        r[k]["hold"] = rng.choice(HOLD_D)
    elif op < 0.4:
        r[k]["tp"] = rng.choice(TP_D)
    elif op < 0.48:
        r[k]["trail"] = rng.choice(TRAIL_D)
    elif op < 0.53:
        r[k]["min_net"] = rng.choice(MIN_NET_D)
    else:
        r[k] = _fix(V.mutate(rng, r[k], P, kr))
    return r


def cross(rng, a, b):
    out = dict(regimen=dict(rng.choice([a, b])["regimen"]))
    for k in REGIMES:
        src = rng.choice([a, b])[k]
        out[k] = None if src is None else {kk: ([c[:] for c in vv] if kk in ("entry", "exit") else vv) for kk, vv in src.items()}
    return out


def evolve(mk, seeds, window, cfg, rng, temper, kronos=None, pop=30, gens=15):
    P = V.pools(mk.bpd)
    kr = kronos is not None
    cache = {}

    def fit(rule):
        key = repr(rule)
        if key not in cache:
            cache[key] = robust(mk, exposure(mk.I, rule, kronos, mk.bpd), window, cfg, temper)
        return cache[key]

    popn = list(seeds)[: pop // 3]
    popn += [mutate(rng, rng.choice(seeds), P, kr) for _ in range(pop // 3)] if seeds else []
    while len(popn) < pop:
        popn.append(random_rule(rng, P, kr))
    hist = []
    for _ in range(gens):
        scored = sorted(((fit(r)[0], k, r) for k, r in enumerate(popn)), key=lambda t: -t[0])
        hist.append(round(float(fit(scored[0][2])[1].ret), 4))
        elite = [t[2] for t in scored[: max(2, pop // 5)]]

        def pick():
            x, y = rng.sample(scored[: pop // 2], 2)
            return x[2] if x[0] >= y[0] else y[2]

        nxt = elite[:]
        while len(nxt) < pop:
            child = cross(rng, pick(), pick()) if rng.random() < 0.4 else pick()
            nxt.append(mutate(rng, child, P, kr))
        popn = nxt
    final = max(popn, key=lambda r: fit(r)[0])
    return final, fit(final)[1], hist, fit


def neighbours(rng, rule, mk, kr, n=6):
    """Versiones ligeramente cambiadas de una regla (para comprobar que no ganó por pura suerte)."""
    P = V.pools(mk.bpd)
    out = []
    for _ in range(n):
        r = mutate(rng, rule, P, kr)
        # solo retoques de parámetros: si la mutación cambió una condición entera, se cuenta igual (más exigente)
        out.append(r)
    return out


def describe(rule, bpd):
    rg = rule["regimen"]
    parts = [f"Detecta el mercado con la media de {rg['ma']} días y la tendencia de los últimos {rg['er']} días."]
    for k in REGIMES:
        sub = rule.get(k)
        if not sub:
            parts.append(f"En {REG_LABEL[k]}: no opera, se queda en euros.")
            continue
        d = V.describe(sub, bpd)
        parts.append(f"En {REG_LABEL[k]}: {d[0].lower() + d[1:]}")
    return " ".join(parts)
