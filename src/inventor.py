"""El agente inventa su propia estrategia.

Una estrategia inventada es un conjunto de reglas legibles:
  ENTRA cuando se cumplen TODAS las condiciones de entrada (1 a 3)
  SALE  cuando se cumple CUALQUIERA de las condiciones de salida (1 o 2),
        o salta el stop dinámico, o llega al objetivo de beneficio, o pasa el tiempo máximo.
  Tamaño: todo el fondo, o ajustado a la volatilidad.

El agente parte de lo que aprendió estudiando estrategias conocidas (sus mejores reglas son la
"semilla") y las va perfeccionando con un algoritmo evolutivo: en cada generación se quedan las
mejores, se cruzan entre sí y se cambian un poco al azar. Solo ve los años de entreno.
"""
import math
import random

import numpy as np

from backtest import run

# ------------------------------------------------------------------ condiciones


def pools(bpd):
    n = [5, 10, 20, 50, 100, 200]
    if bpd > 1:
        n += [20 * bpd, 50 * bpd, 200 * bpd]
    return dict(N=sorted(set(n)), RSI_N=[2, 7, 14], RSI_LO=[10, 20, 30, 40], RSI_HI=[55, 65, 75, 85],
                ROC_N=[5, 10, 20, 60] + ([7 * bpd, 30 * bpd] if bpd > 1 else []), ROC_X=[0.0, 0.02, 0.05, 0.1],
                VOL_N=[20, 60] + ([30 * bpd] if bpd > 1 else []), VOL_X=[0.3, 0.5, 0.7, 0.9], Z_X=[1.0, 1.5, 2.0, 2.5],
                KR=[0.0, 0.01, 0.02])


KINDS_ENTRY = ["sobre_media", "cruce_alcista", "rsi_bajo", "rompe_maximo", "impulso_sube", "vol_baja", "z_bajo",
               "macd_pos", "impulso_baja", "bajo_media"]
KINDS_EXIT = ["bajo_media", "cruce_bajista", "rsi_alto", "pierde_minimo", "impulso_baja", "vol_alta", "z_alto",
              "macd_neg", "sobre_media"]


def random_cond(rng, kinds, P, kronos=False):
    ks = list(kinds) + (["kronos_alcista"] if kronos and "rsi_bajo" in kinds else []) + (["kronos_bajista"] if kronos and "rsi_alto" in kinds else [])
    k = rng.choice(ks)
    if k in ("sobre_media", "bajo_media", "rompe_maximo", "pierde_minimo"):
        return [k, rng.choice(P["N"])]
    if k in ("cruce_alcista", "cruce_bajista"):
        a, b = sorted(rng.sample(P["N"], 2))
        return [k, a, b]
    if k == "rsi_bajo":
        return [k, rng.choice(P["RSI_N"]), rng.choice(P["RSI_LO"])]
    if k == "rsi_alto":
        return [k, rng.choice(P["RSI_N"]), rng.choice(P["RSI_HI"])]
    if k in ("impulso_sube", "impulso_baja"):
        return [k, rng.choice(P["ROC_N"]), rng.choice(P["ROC_X"])]
    if k in ("vol_baja", "vol_alta"):
        return [k, rng.choice(P["VOL_N"]), rng.choice(P["VOL_X"])]
    if k in ("z_bajo", "z_alto"):
        return [k, rng.choice([20, 50]), rng.choice(P["Z_X"])]
    if k == "kronos_alcista":
        return [k, rng.choice(P["KR"])]
    return [k]


def cond_array(I, c, kronos=None):
    k = c[0]
    with np.errstate(invalid="ignore"):
        if k == "sobre_media":
            return I.c > I.sma(c[1])
        if k == "bajo_media":
            return I.c < I.sma(c[1])
        if k == "cruce_alcista":
            return I.sma(c[1]) > I.sma(c[2])
        if k == "cruce_bajista":
            return I.sma(c[1]) < I.sma(c[2])
        if k == "rsi_bajo":
            return I.rsi(c[1]) < c[2]
        if k == "rsi_alto":
            return I.rsi(c[1]) > c[2]
        if k == "rompe_maximo":
            return I.c > I.hh(c[1])
        if k == "pierde_minimo":
            return I.c < I.ll(c[1])
        if k == "impulso_sube":
            return I.roc(c[1]) > c[2]
        if k == "impulso_baja":
            return I.roc(c[1]) < -c[2]
        if k == "vol_baja":
            return I.rvol(c[1]) < c[2]
        if k == "vol_alta":
            return I.rvol(c[1]) > c[2]
        if k == "z_bajo":
            return I.z(c[1]) < -c[2]
        if k == "z_alto":
            return I.z(c[1]) > c[2]
        if k == "macd_pos":
            return I.macd_hist() > 0
        if k == "macd_neg":
            return I.macd_hist() < 0
        if k == "kronos_alcista":
            return (kronos["med"] > c[1]) & (kronos["up"] >= 0.6) if kronos is not None else np.zeros(I.n, bool)
        if k == "kronos_bajista":
            return (kronos["med"] < 0) if kronos is not None else np.zeros(I.n, bool)
    raise ValueError(k)


def span(n, bpd):
    """Expresa n velas de forma legible: '20 días', '480 velas' -> '20 días' en 1h."""
    if bpd == 1:
        return f"{n} días"
    if n % bpd == 0:
        return f"{n // bpd} días"
    return f"{n} velas"


def cond_text(c, bpd):
    k = c[0]
    S = lambda n: span(n, bpd)  # noqa: E731
    t = {
        "sobre_media": lambda: f"el precio está sobre su media de {S(c[1])}",
        "bajo_media": lambda: f"el precio está bajo su media de {S(c[1])}",
        "cruce_alcista": lambda: f"la media de {S(c[1])} está por encima de la de {S(c[2])}",
        "cruce_bajista": lambda: f"la media de {S(c[1])} está por debajo de la de {S(c[2])}",
        "rsi_bajo": lambda: f"el RSI-{c[1]} baja de {c[2]}",
        "rsi_alto": lambda: f"el RSI-{c[1]} supera {c[2]}",
        "rompe_maximo": lambda: f"rompe el máximo de {S(c[1])}",
        "pierde_minimo": lambda: f"pierde el mínimo de {S(c[1])}",
        "impulso_sube": lambda: (f"sube más de un {c[2] * 100:.0f} % en {S(c[1])}" if c[2] else f"está más alto que hace {S(c[1])}"),
        "impulso_baja": lambda: (f"cae más de un {c[2] * 100:.0f} % en {S(c[1])}" if c[2] else f"está más bajo que hace {S(c[1])}"),
        "vol_baja": lambda: f"la volatilidad de {S(c[1])} está por debajo del {c[2] * 100:.0f} %",
        "vol_alta": lambda: f"la volatilidad de {S(c[1])} supera el {c[2] * 100:.0f} %",
        "z_bajo": lambda: f"el precio cae {c[2]} desviaciones bajo su media de {S(c[1])}",
        "z_alto": lambda: f"el precio sube {c[2]} desviaciones sobre su media de {S(c[1])}",
        "macd_pos": lambda: "el MACD gira al alza",
        "macd_neg": lambda: "el MACD gira a la baja",
        "kronos_alcista": lambda: f"Kronos prevé una subida de más del {c[1] * 100:.0f} %",
        "kronos_bajista": lambda: "Kronos prevé una bajada",
    }[k]
    return t()


def describe(rule, bpd):
    s = "Entra si " + " y ".join(cond_text(c, bpd) for c in rule["entry"])
    outs = [cond_text(c, bpd) for c in rule["exit"]]
    if rule["stop"]:
        outs.append(f"salta un stop dinámico a {rule['stop']} ATR")
    if rule.get("trail"):
        outs.append(f"el precio cae un {rule['trail'] * 100:.0f} % desde el máximo alcanzado (stop que sube con el precio)")
    if rule["tp"] == "kronos":
        outs.append("llega al precio que preveía Kronos")
    elif rule["tp"]:
        outs.append(f"gana un {rule['tp'] * 100:.0f} %")
    if rule["hold"]:
        outs.append(f"pasan {rule['hold']} días")
    s += ". Sale si " + " o ".join(outs) + "."
    if rule.get("frac", 1.0) < 1:
        s += f" Usa el {rule['frac'] * 100:.0f} % del fondo en cada operación."
    if rule["sizing"] == "riesgo":
        s += " Ajusta la posición a la volatilidad."
    return s


FRAC = [1.0, 1.0, 0.5, 0.2]          # parte del fondo que arriesga en cada operación
TRAIL = [0, 0, 0.03, 0.05, 0.1]      # stop que sube con el precio, a este % del máximo alcanzado
TP = [0, 0, 0.05, 0.1, 0.2]          # objetivo de beneficio fijo


def random_rule(rng, P, kronos=False):
    return dict(entry=[random_cond(rng, KINDS_ENTRY, P, kronos) for _ in range(rng.randint(1, 3))],
                exit=[random_cond(rng, KINDS_EXIT, P, kronos) for _ in range(rng.randint(1, 2))],
                stop=rng.choice([0, 0, 2, 3, 4]), tp=rng.choice(TP + (["kronos"] if kronos else [])),
                trail=rng.choice(TRAIL), hold=rng.choice([0, 0, 3, 10, 30]),
                sizing=rng.choice(["completo", "riesgo"]), frac=rng.choice(FRAC))


# ------------------------------------------------------------------ de estrategia a exposición


def exposure(I, rule, kronos=None, bpd=1):
    ent = np.ones(I.n, bool)
    for c in rule["entry"]:
        ent &= np.nan_to_num(cond_array(I, c, kronos)).astype(bool)
    ex = np.zeros(I.n, bool)
    for c in rule["exit"]:
        ex |= np.nan_to_num(cond_array(I, c, kronos)).astype(bool)
    stop, tp, hold = rule["stop"], rule["tp"], rule["hold"] * bpd
    trail = rule.get("trail", 0)
    kmed = kronos["med"].tolist() if (tp == "kronos" and kronos is not None) else None
    if tp == "kronos" and kmed is None:
        tp = 0
    atr = I.atr(14) if stop else None
    C = I.c.tolist()
    ent_l, ex_l = ent.tolist(), ex.tolist()
    atr_l = atr.tolist() if stop else None
    w = [0.0] * I.n
    pos, entry_px, best, since, target, blocked = False, 0.0, 0.0, 0, 0.0, False
    for i in range(I.n):
        px = C[i]
        if blocked and not ent_l[i]:
            blocked = False  # tras un stop u objetivo, espera a una señal de entrada nueva
        if not pos:
            if ent_l[i] and not blocked:
                pos, entry_px, best, since = True, px, px, 0
                if tp == "kronos":  # objetivo = precio que prevé Kronos al entrar
                    m = kmed[i]
                    target = px * (1 + m) if (m == m and m > 0.005) else px * 1.05
                elif tp:
                    target = px * (1 + tp)
        else:
            since += 1
            best = max(best, px)
            out = ex_l[i]
            forced = False
            if stop and atr_l[i] == atr_l[i] and px < best - stop * atr_l[i]:
                forced = True
            if tp and px >= target:
                forced = True
            if trail and px < best * (1 - trail):  # el stop sube con el precio y asegura el recorrido
                forced = True
            if forced:
                out, blocked = True, True
            if hold and since >= hold:
                out = True
            if out:
                pos = False
        w[i] = 1.0 if pos else 0.0
    w = np.array(w) * rule.get("frac", 1.0)
    if rule["sizing"] == "riesgo":
        v = I.rvol(min(len(I.c) - 1, 30 * bpd))
        with np.errstate(invalid="ignore", divide="ignore"):
            w = w * np.nan_to_num(np.minimum(1.0, 0.5 / v), nan=0.0)
    return w


# ------------------------------------------------------------------ cómo se puntúa


def score(r, cap, years, temper):
    """Más ganancia es mejor; las caídas grandes restan (más cuanto más prudente es el agente);
    con muy pocas operaciones no se puede saber si es suerte."""
    if r.final <= 0:
        return -9.0
    s = math.log(r.final / cap) / max(years, 0.5)
    s -= temper * max(0.0, r.maxdd - 0.2)
    if r.n_buys < 3 * years:
        s -= 0.5
    return s


# ------------------------------------------------------------------ evolución


def mutate(rng, rule, P, kronos=False):
    r = {k: (v[:] if isinstance(v, list) else v) for k, v in rule.items()}
    r["entry"] = [c[:] for c in rule["entry"]]
    r["exit"] = [c[:] for c in rule["exit"]]
    op = rng.random()
    if op < 0.35:  # cambia un parámetro / condición
        side = rng.choice(["entry", "exit"])
        j = rng.randrange(len(r[side]))
        r[side][j] = random_cond(rng, KINDS_ENTRY if side == "entry" else KINDS_EXIT, P, kronos) if rng.random() < 0.5 else _tweak(rng, r[side][j], P)
    elif op < 0.5 and len(r["entry"]) < 3:
        r["entry"].append(random_cond(rng, KINDS_ENTRY, P, kronos))
    elif op < 0.6 and len(r["entry"]) > 1:
        r["entry"].pop(rng.randrange(len(r["entry"])))
    elif op < 0.7:
        if len(r["exit"]) < 2:
            r["exit"].append(random_cond(rng, KINDS_EXIT, P, kronos))
        else:
            r["exit"].pop(rng.randrange(2))
    elif op < 0.8:
        r["stop"] = rng.choice([0, 2, 3, 4])
    elif op < 0.85:
        r["tp"] = rng.choice(TP + (["kronos"] if kronos else []))
    elif op < 0.9:
        r["trail"] = rng.choice(TRAIL)
    elif op < 0.94:
        r["frac"] = rng.choice(FRAC)
    elif op < 0.97:
        r["hold"] = rng.choice([0, 3, 10, 30])
    else:
        r["sizing"] = "riesgo" if r["sizing"] == "completo" else "completo"
    return r


def _tweak(rng, c, P):
    c = c[:]
    if len(c) > 1 and isinstance(c[1], int):
        for key in ("N", "RSI_N", "ROC_N", "VOL_N"):
            if c[1] in P[key]:
                lst = P[key]
                j = max(0, min(len(lst) - 1, lst.index(c[1]) + rng.choice([-1, 1])))
                c[1] = lst[j]
                break
    if c[0] in ("cruce_alcista", "cruce_bajista") and c[1] >= c[2]:
        lo, hi = sorted([c[1], c[2]])
        c[1], c[2] = lo, (hi if hi != lo else lo * 2)
    return c


def cross(rng, a, b):
    return dict(entry=[c[:] for c in (a["entry"][:1] + b["entry"][1:])][:3] or [a["entry"][0][:]],
                exit=[c[:] for c in rng.choice([a["exit"], b["exit"]])],
                stop=rng.choice([a["stop"], b["stop"]]), tp=rng.choice([a["tp"], b["tp"]]),
                hold=rng.choice([a["hold"], b["hold"]]), sizing=rng.choice([a["sizing"], b["sizing"]]),
                trail=rng.choice([a.get("trail", 0), b.get("trail", 0)]), frac=rng.choice([a.get("frac", 1.0), b.get("frac", 1.0)]))


def evolve(mk, seeds, window, cfg, rng, temper, kronos=None, pop=30, gens=15, log=None):
    """Devuelve (mejor_regla, resultado_en_entreno, historial de la mejor puntuación por generación)."""
    I = mk.I
    P = pools(mk.bpd)
    kr = kronos is not None
    a, b = window
    years = (b - a + 1) / (365 * mk.bpd)
    cache = {}

    def fit(rule):
        key = repr(rule)
        if key not in cache:
            w = exposure(I, rule, kronos if kr else None, mk.bpd)
            r = run(I, w, a, b, cfg)
            cache[key] = (score(r, cfg["cap"], years, temper), r)
        return cache[key]

    popn = [s for s in seeds][:pop // 3]
    popn += [mutate(rng, rng.choice(seeds), P, kr) for _ in range(pop // 3)] if seeds else []
    while len(popn) < pop:
        popn.append(random_rule(rng, P, kr))
    hist = []
    for g in range(gens):
        scored = sorted(((fit(r)[0], k, r) for k, r in enumerate(popn)), key=lambda t: -t[0])
        best = scored[0]
        hist.append(round(float(fit(best[2])[1].ret), 4))  # ganancia en entreno de la mejor regla de esta generación
        elite = [t[2] for t in scored[: max(2, pop // 5)]]

        def pick():
            x, y = rng.sample(scored[: pop // 2], 2)
            return x[2] if x[0] >= y[0] else y[2]

        nxt = elite[:]
        while len(nxt) < pop:
            child = cross(rng, pick(), pick()) if rng.random() < 0.5 else pick()
            nxt.append(mutate(rng, child, P, kr))
        popn = nxt
    final = max(popn, key=lambda r: fit(r)[0])
    return final, fit(final)[1], hist


# ------------------------------------------------------------------ de estrategia conocida a reglas


def seed_from_family(family, p, bpd):
    """Traduce la mejor estrategia conocida que estudió el agente a reglas editables (su experiencia)."""
    base = dict(stop=0, tp=0, hold=0, sizing="completo", trail=0, frac=1.0)
    t = {
        "sma": lambda: dict(entry=[["cruce_alcista", p["fast"], p["slow"]]], exit=[["cruce_bajista", p["fast"], p["slow"]]]),
        "donchian": lambda: dict(entry=[["rompe_maximo", p["entry"]]], exit=[["pierde_minimo", p["exit"]]]),
        "rsi": lambda: dict(entry=[["rsi_bajo", 14, p["buy"]]], exit=[["rsi_alto", 14, p["sell"]]]),
        "boll": lambda: dict(entry=[["z_bajo", 20, p["k"]]], exit=[["sobre_media", 20] if p["exit"] == "media" else ["z_alto", 20, p["k"]]]),
        "macd": lambda: dict(entry=[["macd_pos"]] + ([["sobre_media", 200]] if p.get("filtro") else []), exit=[["macd_neg"]]),
        "tsmom": lambda: dict(entry=[["impulso_sube", p["look"], 0.0]], exit=[["impulso_baja", p["look"], 0.0]]),
        "voltgt": lambda: dict(entry=[["sobre_media", 200]], exit=[["bajo_media", 200]], sizing="riesgo"),
        "supertrend": lambda: dict(entry=[["sobre_media", 50]], exit=[["bajo_media", 50]], stop=p["m"]),
        "connors": lambda: dict(entry=[["sobre_media", 200], ["rsi_bajo", 2, p["buy"]]], exit=[["sobre_media", 5], ["rsi_alto", 2, p["sell"]]]),
        # la idea de "ceñirse a Kronos": entra cuando prevé subida, objetivo en su previsión, stop que sube con el precio
        "kronos": lambda: dict(entry=[["kronos_alcista", p["thr"]]], exit=[["kronos_bajista"]], tp="kronos", trail=0.03),
    }[family]()
    return {**base, **t}
