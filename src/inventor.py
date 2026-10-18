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

import patterns as PT
from backtest import run

# ------------------------------------------------------------------ condiciones


def pools(bpd):
    n = [5, 10, 20, 50, 100, 200]
    if bpd > 1:
        n += [20 * bpd, 50 * bpd, 200 * bpd]
    return dict(N=sorted(set(n)), RSI_N=[2, 7, 14], RSI_LO=[10, 20, 30, 40], RSI_HI=[55, 65, 75, 85],
                ROC_N=[5, 10, 20, 60] + ([7 * bpd, 30 * bpd] if bpd > 1 else []), ROC_X=[0.0, 0.02, 0.05, 0.1],
                VOL_N=[20, 60] + ([30 * bpd] if bpd > 1 else []), VOL_X=[0.3, 0.5, 0.7, 0.9], Z_X=[1.0, 1.5, 2.0, 2.5],
                KR=[0.0, 0.01, 0.02],
                PAT_N=[30, 60, 120], PAT_TOL=[0.01, 0.02, 0.03, 0.05], FLAG_IMP=[0.05, 0.08, 0.12], VOL_MULT=[1.5, 2.0, 3.0],
                DELTA_N=[1, 5, 20] + ([bpd, 5 * bpd] if bpd > 1 else []), DELTA_X=[0.02, 0.05, 0.1])


KINDS_ENTRY = ["sobre_media", "cruce_alcista", "rsi_bajo", "rompe_maximo", "impulso_sube", "vol_baja", "z_bajo",
               "macd_pos", "impulso_baja", "bajo_media"]
# figuras de chartismo (ver patterns.py)
PATTERNS_ENTRY = ["doble_suelo", "triple_suelo", "hch_invertido", "triangulo", "bandera", "rebote_soporte",
                  "ruptura_volumen", "volumen_alto"]
PATTERNS_EXIT = ["doble_techo", "hch", "pierde_soporte"]
# flujo de órdenes (delta de Binance; sin datos nunca se cumplen)
FLOW_ENTRY = ["delta_compra", "absorcion", "divergencia_delta"]
FLOW_EXIT = ["delta_venta"]
KINDS_ENTRY = KINDS_ENTRY + PATTERNS_ENTRY + FLOW_ENTRY
KINDS_EXIT = ["bajo_media", "cruce_bajista", "rsi_alto", "pierde_minimo", "impulso_baja", "vol_alta", "z_alto",
              "macd_neg", "sobre_media"] + PATTERNS_EXIT + FLOW_EXIT


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
    if k in ("doble_suelo", "triple_suelo", "hch_invertido", "triangulo", "rebote_soporte",
             "doble_techo", "hch", "pierde_soporte"):
        return [k, rng.choice(P["PAT_N"]), rng.choice(P["PAT_TOL"])]
    if k == "bandera":
        return [k, rng.choice(P["PAT_N"]), rng.choice(P["FLAG_IMP"])]
    if k == "ruptura_volumen":
        return [k, rng.choice(P["N"]), rng.choice(P["VOL_MULT"])]
    if k == "volumen_alto":
        return [k, rng.choice(P["VOL_MULT"])]
    if k in ("delta_compra", "delta_venta"):
        return [k, rng.choice(P["DELTA_N"]), rng.choice(P["DELTA_X"])]
    if k == "absorcion":
        return [k, rng.choice(P["VOL_MULT"])]
    if k == "divergencia_delta":
        return [k, rng.choice(P["N"][:4])]
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
        pat = {"doble_suelo": PT.double_bottom, "triple_suelo": PT.triple_bottom, "hch_invertido": PT.inv_head_shoulders,
               "triangulo": PT.asc_triangle, "rebote_soporte": PT.support_bounce, "doble_techo": PT.double_top,
               "hch": PT.head_shoulders, "pierde_soporte": PT.support_break, "bandera": PT.bull_flag,
               "ruptura_volumen": PT.resistance_break_volume}
        if k in pat:
            return pat[k](I, c[1], c[2])
        if k == "volumen_alto":
            return PT.volume_ratio(I) > c[1]
        if k == "delta_compra":
            return I.delta_avg(c[1]) > c[2]
        if k == "delta_venta":
            return I.delta_avg(c[1]) < -c[2]
        if k == "absorcion":
            return PT.absorption(I, c[1])
        if k == "divergencia_delta":
            return PT.delta_divergence(I, c[1])
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
    W = lambda n: "en la vela" if n == 1 else ("en el último día" if n == bpd else f"durante {S(n)}")  # noqa: E731
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
        "z_bajo": lambda: f"el precio cae {c[2]:g} desviaciones bajo su media de {S(c[1])}".replace(".", ","),
        "z_alto": lambda: f"el precio sube {c[2]:g} desviaciones sobre su media de {S(c[1])}".replace(".", ","),
        "macd_pos": lambda: "el MACD gira al alza",
        "macd_neg": lambda: "el MACD gira a la baja",
        "kronos_alcista": lambda: f"Kronos prevé una subida de más del {c[1] * 100:.0f} %",
        "kronos_bajista": lambda: "Kronos prevé una bajada",
        "doble_suelo": lambda: f"completa un doble suelo (W) en las últimas {S(c[1])}",
        "triple_suelo": lambda: f"completa un triple suelo en las últimas {S(c[1])}",
        "hch_invertido": lambda: f"completa un hombro-cabeza-hombro invertido en las últimas {S(c[1])}",
        "triangulo": lambda: f"rompe un triángulo ascendente de las últimas {S(c[1])}",
        "bandera": lambda: f"completa una bandera alcista (patrón N) tras subir más de un {c[2] * 100:.0f} %",
        "rebote_soporte": lambda: f"rebota en un soporte de las últimas {S(c[1])}",
        "ruptura_volumen": lambda: f"rompe el máximo de {S(c[1])} con {str(c[2]).replace('.', ',').rstrip('0').rstrip(',')} veces el volumen normal",
        "volumen_alto": lambda: f"hay {str(c[1]).replace('.', ',').rstrip('0').rstrip(',')} veces el volumen normal",
        "doble_techo": lambda: f"completa un doble techo (M) en las últimas {S(c[1])}",
        "hch": lambda: f"completa un hombro-cabeza-hombro en las últimas {S(c[1])}",
        "pierde_soporte": lambda: f"pierde un soporte de las últimas {S(c[1])}",
        "delta_compra": lambda: f"dominan las compras agresivas {W(c[1])} (delta de más del {c[2] * 100:.0f} %)",
        "delta_venta": lambda: f"dominan las ventas agresivas {W(c[1])} (delta de menos del -{c[2] * 100:.0f} %)",
        "absorcion": lambda: f"hay absorción compradora ({str(c[1]).replace('.', ',').rstrip('0').rstrip(',')} veces el volumen normal, con ventas agresivas, pero cierra en la mitad alta de la vela)",
        "divergencia_delta": lambda: f"marca un mínimo de {S(c[1])} pero el delta acumulado no (divergencia: se agotan los vendedores)",
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
    mn = rule.get("min_net", 0.01)
    if mn:
        s += f" Solo cierra por su señal de salida si el precio ya ha subido al menos un {mn * 100:.1f} % desde la compra, para cubrir comisiones y ganar (los stops cierran siempre).".replace(".", ",", 1)
    g = []
    if rule.get("pyr"):
        g.append(f"empieza con media posición y la completa si gana un {rule['pyr'] * 100:.0f} %")
    if rule.get("be"):
        g.append(f"al ganar un {rule['be'] * 100:.0f} % sube el stop al precio de entrada")
    if rule.get("stall"):
        g.append(f"si en {rule['stall']} {'día' if rule['stall'] == 1 else 'días'} no avanza, acerca el stop a un 1,5 %")
    if rule.get("shrink") and rule.get("trail"):
        g.append("cuanto más gana, más ajusta el stop")
    if g:
        s += " Gestión: " + "; ".join(g) + "."
    if rule.get("frac", 1.0) < 1:
        s += f" Usa el {rule['frac'] * 100:.0f} % del fondo en cada operación."
    if rule["sizing"] == "riesgo":
        s += " Ajusta la posición a la volatilidad."
    return s


FRAC = [1.0, 1.0, 0.5, 0.2]          # parte del fondo que arriesga en cada operación
TRAIL = [0, 0, 0.03, 0.05, 0.1]      # stop que sube con el precio, a este % del máximo alcanzado
TP = [0, 0, 0.05, 0.08, 0.1, 0.2]    # objetivo de beneficio fijo
MIN_NET = [0.01, 0.01, 0.015, 0.03]  # ganancia mínima tras comisiones para cerrar por señal
BE = [0, 0, 0.02, 0.03, 0.05]        # al ganar esto, el stop sube al precio de entrada
STALL = [0, 0, 1, 3, 7]              # días sin avanzar tras los que se acerca el stop
PYR = [0, 0, 0.02, 0.04]             # entra con media posición y la completa al ganar esto


def random_rule(rng, P, kronos=False):
    return dict(entry=[random_cond(rng, KINDS_ENTRY, P, kronos) for _ in range(rng.randint(1, 3))],
                exit=[random_cond(rng, KINDS_EXIT, P, kronos) for _ in range(rng.randint(1, 2))],
                stop=rng.choice([0, 0, 2, 3, 4]), tp=rng.choice(TP + (["kronos"] if kronos else [])),
                trail=rng.choice(TRAIL), hold=rng.choice([0, 0, 3, 10, 30]),
                sizing=rng.choice(["completo", "riesgo"]), frac=rng.choice(FRAC),
                be=rng.choice(BE), stall=rng.choice(STALL), pyr=rng.choice(PYR), shrink=rng.random() < 0.5,
                min_net=rng.choice(MIN_NET))


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
    be, stall, pyr, shrink = rule.get("be", 0), rule.get("stall", 0) * bpd, rule.get("pyr", 0), rule.get("shrink", False)
    min_net = rule.get("min_net", 0.01)  # la señal de salida solo cierra si la operación ya cubre comisiones y gana algo
    C = I.c.tolist()
    ent_l, ex_l = ent.tolist(), ex.tolist()
    atr_l = atr.tolist() if stop else None
    w = [0.0] * I.n
    pos, entry_px, best, since, target, blocked = False, 0.0, 0.0, 0, 0.0, False
    size, floor = 1.0, 0.0
    for i in range(I.n):
        px = C[i]
        if blocked and not ent_l[i]:
            blocked = False  # tras un stop u objetivo, espera a una señal de entrada nueva
        if not pos:
            if ent_l[i] and not blocked:
                pos, entry_px, best, since = True, px, px, 0
                size = 0.5 if pyr else 1.0
                floor = 0.0
                if tp == "kronos":  # objetivo = precio que prevé Kronos al entrar
                    m = kmed[i]
                    target = px * (1 + m) if (m == m and m > 0.005) else px * 1.05
                elif tp:
                    target = px * (1 + tp)
        else:
            since += 1
            best = max(best, px)
            gain = best / entry_px - 1
            if pyr and size < 1 and px / entry_px - 1 >= pyr:
                size = 1.0  # va a favor: completa la posición
            if be and gain >= be:
                floor = max(floor, entry_px * 1.006)  # stop a precio de entrada (cubre comisiones)
            if stall and since == stall and gain < 0.01:
                floor = max(floor, px * 0.985)  # no avanza: acerca el stop para perder lo mínimo
            out = ex_l[i] and px >= entry_px * (1 + min_net)
            forced = False
            if stop and atr_l[i] == atr_l[i] and px < best - stop * atr_l[i]:
                forced = True
            if tp and px >= target:
                forced = True
            if trail:
                t = trail * max(0.4, 1 - gain / 0.10) if shrink else trail
                if px < best * (1 - t):  # el stop sube con el precio y asegura el recorrido
                    forced = True
            if floor and px < floor:
                forced = True
            if forced:
                out, blocked = True, True
            if hold and since >= hold:
                out = True
            if out:
                pos = False
        w[i] = size if pos else 0.0
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
    if r.closed and r.avg_trade < 0.01:  # operaciones que apenas ganan tras comisiones no interesan
        s -= 0.3 + 20 * max(0.0, 0.01 - r.avg_trade)
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
    elif op < 0.92:
        r["frac"] = rng.choice(FRAC)
    elif op < 0.94:
        r["hold"] = rng.choice([0, 3, 10, 30])
    elif op < 0.955:
        r["be"] = rng.choice(BE)
    elif op < 0.97:
        r["stall"] = rng.choice(STALL)
    elif op < 0.98:
        r["pyr"] = rng.choice(PYR)
    elif op < 0.985:
        r["shrink"] = not r.get("shrink", False)
    elif op < 0.995:
        r["min_net"] = rng.choice(MIN_NET)
    else:
        r["sizing"] = "riesgo" if r["sizing"] == "completo" else "completo"
    return r


def _tweak(rng, c, P):
    c = c[:]
    if len(c) > 1 and isinstance(c[1], int):
        for key in ("N", "RSI_N", "ROC_N", "VOL_N", "PAT_N", "DELTA_N"):
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
                trail=rng.choice([a.get("trail", 0), b.get("trail", 0)]), frac=rng.choice([a.get("frac", 1.0), b.get("frac", 1.0)]),
                be=rng.choice([a.get("be", 0), b.get("be", 0)]), stall=rng.choice([a.get("stall", 0), b.get("stall", 0)]),
                pyr=rng.choice([a.get("pyr", 0), b.get("pyr", 0)]), shrink=rng.choice([a.get("shrink", False), b.get("shrink", False)]),
                min_net=rng.choice([a.get("min_net", 0.01), b.get("min_net", 0.01)]))


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
    base = dict(stop=0, tp=0, hold=0, sizing="completo", trail=0, frac=1.0, be=0, stall=0, pyr=0, shrink=False)
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


def pattern_seed(rng, P, kronos=False):
    """Una idea de partida basada en una figura de chartismo, con gestión activa del stop."""
    entry = [random_cond(rng, PATTERNS_ENTRY, P, kronos)]
    if rng.random() < 0.5:
        entry.append(random_cond(rng, ["sobre_media", "cruce_alcista", "vol_baja"], P, kronos))
    return dict(entry=entry, exit=[random_cond(rng, PATTERNS_EXIT, P, kronos)],
                stop=rng.choice([2, 3]), tp=rng.choice([0, 0.05, 0.08]), trail=rng.choice([0.03, 0.05]),
                hold=0, sizing="completo", frac=1.0, be=rng.choice([0.02, 0.03]), stall=rng.choice([1, 3]),
                pyr=rng.choice([0, 0.02]), shrink=True)
