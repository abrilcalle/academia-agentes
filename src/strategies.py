"""Familias de estrategias y "genoma" de cada agente.

Cada familia convierte las velas en una exposición deseada w[i] (0..1) decidida al CIERRE del día i.
El motor la ejecuta en la apertura del día i+1, así nadie ve el futuro.

Un agente = familia + parámetros + filtro + stop + tamaño de posición. La fábrica combina estas
piezas al azar para crear agentes nuevos; el entreno elige los mejores parámetros de la familia.
"""
import itertools
import numpy as np


def grid(**opts):
    keys = list(opts)
    return [dict(zip(keys, vals)) for vals in itertools.product(*opts.values())]


# ---------------------------------------------------------------- familias

def f_sma(I, p):
    f, s = I.sma(p["fast"]), I.sma(p["slow"])
    return np.where(f > s, 1.0, 0.0)


def f_donchian(I, p):
    up, dn = I.hh(p["entry"]), I.ll(p["exit"])
    w = np.zeros(I.n)
    pos = 0
    for i in range(I.n):
        if not pos and I.c[i] > up[i]:
            pos = 1
        elif pos and I.c[i] < dn[i]:
            pos = 0
        w[i] = pos
    return w


def f_rsi(I, p):
    r = I.rsi(14)
    w = np.zeros(I.n)
    pos = 0
    for i in range(I.n):
        if not pos and r[i] < p["buy"]:
            pos = 1
        elif pos and r[i] > p["sell"]:
            pos = 0
        w[i] = pos
    return w


def f_boll(I, p):
    m, sd = I.sma(20), I.stdev(20)
    w = np.zeros(I.n)
    pos = 0
    for i in range(I.n):
        lo = m[i] - p["k"] * sd[i]
        ex = m[i] if p["exit"] == "media" else m[i] + p["k"] * sd[i]
        if not pos and I.c[i] < lo:
            pos = 1
        elif pos and I.c[i] > ex:
            pos = 0
        w[i] = pos
    return w


def f_macd(I, p):
    f, s = I.ema_of(I.c, p["f"]), I.ema_of(I.c, p["s"])
    line = f - s
    sig = I.ema_of(np.nan_to_num(line), p["sig"])
    t = I.sma(200)
    ok = line > sig
    if p.get("filtro"):
        ok = ok & (I.c > t)
    return np.where(ok, 1.0, 0.0)


def f_tsmom(I, p):
    w = np.zeros(I.n)
    pos = 0
    L = p["look"]
    reb = max(1, int(round(7 * I.bpy / 365)))  # revisa una vez por semana
    for i in range(I.n):
        if i % reb == 0 and i >= L:
            pos = 1 if I.c[i] > I.c[i - L] else 0
        w[i] = pos
    return w


def f_voltgt(I, p):
    t, v = I.sma(200), I.rvol(30)
    with np.errstate(invalid="ignore", divide="ignore"):
        w = np.where((I.c > t) & (v > 0), np.minimum(1.0, p["target"] / v), 0.0)
    return np.nan_to_num(w)


def f_supertrend(I, p):
    a, m50 = I.atr(p["n"]), I.sma(50)
    w = np.zeros(I.n)
    pos, stop = 0, 0.0
    for i in range(1, I.n):
        if np.isnan(a[i]) or np.isnan(m50[i - 1]):
            continue
        if not pos:
            if I.c[i] > m50[i] and I.c[i - 1] <= m50[i - 1]:
                pos, stop = 1, I.c[i] - p["m"] * a[i]
        else:
            stop = max(stop, I.c[i] - p["m"] * a[i])
            if I.c[i] < stop:
                pos = 0
        w[i] = pos
    return w


def f_connors(I, p):
    r2, t, s5 = I.rsi(2), I.sma(200), I.sma(5)
    w = np.zeros(I.n)
    pos = 0
    for i in range(I.n):
        if not pos and I.c[i] > t[i] and r2[i] < p["buy"]:
            pos = 1
        elif pos and (I.c[i] > s5[i] or r2[i] > p["sell"]):
            pos = 0
        w[i] = pos
    return w


def f_kronos(I, p, kronos=None):
    """Usa las previsiones de Kronos ya calculadas (ver kronos_signal.py).
    kronos: dict con arrays 'med' (rentabilidad mediana prevista a H días) y 'up' (fracción de caminos al alza)."""
    w = np.zeros(I.n)
    if kronos is None:
        return w
    med, up = kronos["med"], kronos["up"]
    pos = 0
    for i in range(I.n):
        if np.isnan(med[i]):
            w[i] = pos
            continue
        if not pos and med[i] > p["thr"] and up[i] >= p["conf"]:
            pos = 1
        elif pos and (med[i] < 0 or up[i] < 0.5):
            pos = 0
        w[i] = pos
    return w


FAMILIES = {
    "sma": dict(fn=f_sma, label="Cruce de medias móviles",
                src="Tendencia clásica: compra cuando la media rápida cruza por encima de la lenta.",
                grid=[p for p in grid(fast=[10, 20, 50], slow=[50, 100, 200]) if p["fast"] < p["slow"]]),
    "donchian": dict(fn=f_donchian, label="Rupturas de Donchian",
                     src="Reglas de las Tortugas de Richard Dennis (1983): compra al romper el máximo de N días.",
                     grid=grid(entry=[20, 55], exit=[10, 20])),
    "rsi": dict(fn=f_rsi, label="RSI de reversión",
                src="Wilder (1978): compra en sobreventa y vende al recuperarse.",
                grid=grid(buy=[25, 30, 35], sell=[55, 65, 75])),
    "boll": dict(fn=f_boll, label="Bandas de Bollinger",
                 src="Compra por debajo de la banda inferior, apostando a que vuelve a la media.",
                 grid=grid(k=[1.5, 2, 2.5], exit=["media", "banda superior"])),
    "macd": dict(fn=f_macd, label="MACD",
                 src="Gerald Appel: sigue el cruce de la línea MACD con su señal.",
                 grid=[p for p in grid(f=[12, 8], s=[26, 21], sig=[9, 5], filtro=[False, True]) if p["f"] < p["s"]]),
    "tsmom": dict(fn=f_tsmom, label="Momentum temporal",
                  src="Moskowitz, Ooi y Pedersen (2012): mantener si subió en los últimos N días. Revisa cada semana.",
                  grid=grid(look=[30, 60, 90, 180])),
    "voltgt": dict(fn=f_voltgt, label="Tendencia con control de riesgo",
                   src="Invierte sobre la media de 200 días y reduce posición cuando sube la volatilidad.",
                   grid=grid(target=[0.4, 0.6, 0.8])),
    "supertrend": dict(fn=f_supertrend, label="Stop dinámico por ATR",
                       src="Entra al cruzar la media de 50 días y protege con un stop que sube con el precio.",
                       grid=grid(n=[10, 14], m=[2, 3, 4])),
    "connors": dict(fn=f_connors, label="RSI-2 de Connors",
                    src="Larry Connors: compras de pocos días en caídas fuertes dentro de una tendencia alcista.",
                    grid=grid(buy=[5, 10], sell=[70, 90])),
    "kronos": dict(fn=f_kronos, label="Previsión con Kronos",
                   src="Modelo open source Kronos (velas de 45 mercados): compra cuando la mayoría de caminos previstos suben.",
                   grid=grid(thr=[0.0, 0.01, 0.02], conf=[0.6, 0.75])),
}

# ---------------------------------------------------------------- piezas extra del genoma

FILTERS = {
    "ninguno": "sin filtro",
    "tendencia": "solo opera por encima de la media de 200 velas",
    "calma": "solo opera si la volatilidad reciente está por debajo del 80 % anual",
}
STOPS = {0: "sin stop extra", 2.5: "stop dinámico a 2,5 ATR", 4: "stop dinámico a 4 ATR"}
SIZING = {"completo": "invierte todo el fondo", "riesgo": "ajusta la posición a la volatilidad (objetivo 50 % anual)"}


def signal(I, genome, params, kronos=None):
    """Exposición final 0..1 de un agente: familia + filtro + stop + tamaño."""
    fam = FAMILIES[genome["family"]]
    w = fam["fn"](I, params, kronos) if genome["family"] == "kronos" else fam["fn"](I, params)
    w = np.array(w, dtype=float)

    flt = genome.get("filter", "ninguno")
    if flt == "tendencia":
        w = np.where(I.c > I.sma(200), w, 0.0)
    elif flt == "calma":
        w = np.where(I.rvol(30) < 0.8, w, 0.0)

    stop = genome.get("stop", 0)
    if stop:
        a = I.atr(14)
        out = w.copy()
        in_pos, best, blocked = False, 0.0, False
        for i in range(I.n):
            if w[i] <= 0:
                in_pos, blocked = False, False
                out[i] = 0
                continue
            if blocked:  # el stop saltó: espera a que la señal se apague antes de volver a entrar
                out[i] = 0
                continue
            if not in_pos:
                in_pos, best = True, I.c[i]
            best = max(best, I.c[i])
            if not np.isnan(a[i]) and I.c[i] < best - stop * a[i]:
                out[i], in_pos, blocked = 0, False, True
        w = out

    if genome.get("sizing") == "riesgo":
        v = I.rvol(30)
        with np.errstate(invalid="ignore", divide="ignore"):
            k = np.nan_to_num(np.minimum(1.0, 0.5 / v), nan=0.0)
        w = w * k
    return np.clip(np.nan_to_num(w), 0, 1)


def describe(genome, params, u="días"):
    fam = genome["family"]
    p = params
    d = {
        "sma": lambda: f"media {p['fast']} / {p['slow']} {u}",
        "donchian": lambda: f"entra al romper {p['entry']} {u}, sale al perder {p['exit']}",
        "rsi": lambda: f"compra con RSI < {p['buy']}, vende con RSI > {p['sell']}",
        "boll": lambda: f"{p['k']} desviaciones, sale en la {p['exit']}",
        "macd": lambda: f"MACD {p['f']}/{p['s']}/{p['sig']}" + (" con filtro de media 200" if p.get("filtro") else ""),
        "tsmom": lambda: f"mira las últimas {p['look']} {u}",
        "voltgt": lambda: f"volatilidad objetivo {round(p['target'] * 100)} % anual",
        "supertrend": lambda: f"ATR {p['n']} {u} × {p['m']}",
        "connors": lambda: f"compra con RSI-2 < {p['buy']}",
        "kronos": lambda: f"compra si la previsión media supera {p['thr'] * 100:.0f} % y suben el {p['conf'] * 100:.0f} % de los caminos",
    }[fam]()
    extras = [x for x in (
        FILTERS[genome.get("filter", "ninguno")] if genome.get("filter", "ninguno") != "ninguno" else "",
        STOPS[genome.get("stop", 0)] if genome.get("stop", 0) else "",
        SIZING["riesgo"] if genome.get("sizing") == "riesgo" else "",
    ) if x]
    return d + ("; " + "; ".join(extras) if extras else "")
