"""Equipos: varios agentes (de cualquier mercado) que comparten UNA cartera de 100 € ficticios.

Todos los equipos buscan lo mismo: GANAR LO MÁXIMO cumpliendo las condiciones de config.json → objetivo_equipo
(ganar más de la mitad de las semanas, una rentabilidad anual mínima y una caída máxima). Cada agente operó por separado en sus exámenes; aquí el
algoritmo busca qué agentes JUNTOS cumplen esas condiciones y forma los equipos con ellos.

Lo único que cambia entre equipos es la PRUDENCIA al priorizar operaciones. Cada día, al cierre:
  - Cada agente con una operación abierta estima la probabilidad de que acabe en ganancia y cuánto suele ganar
    cuando gana. Lo saca de su propio historial (2022 en adelante, solo operaciones ya cerradas antes de ese día),
    sobre todo de las que abrió en el mismo tipo de mercado (alcista, lateral o bajista).
  - Prioridad = probabilidad^prudencia × ganancia media.
      prudencia 1 (Halcón): 30 % de ganar un 10 % (3,0) < 90 % de ganar un 8 % (7,2);
                            60 % de ganar un 2 % (1,2) > 90 % de ganar un 0,65 % (0,6)
      prudencia 2 (Lobo) y 3 (Tortuga): la probabilidad pesa cada vez más.
  - Las operaciones abiertas se reparten el dinero según su prioridad (con un tope por agente); los que esperan
    señal se quedan una pequeña reserva para poder entrar; lo demás espera en euros.
  - Mover dinero de un agente a otro cuesta comisiones (se descuentan).
Una semana solo es buena si el equipo GANA; si se queda igual o pierde, es mala.
Cada lunes se vuelven a buscar los equipos con todos los agentes que haya: si uno nuevo lo hace mejor, entra; el dinero de cada equipo sigue.
"""
import datetime as dt
import itertools
import zlib

import numpy as np

from backtest import run

# el podio: 1º, 2º y 3º en la prueba de 2026
TIPOS = {
    "halcon": dict(nombre="Equipo Halcón", puesto=1),
    "lobo": dict(nombre="Equipo Lobo", puesto=2),
    "tortuga": dict(nombre="Equipo Tortuga", puesto=3),
}
PRUDENCIAS = {1: "nada conservador: prioriza por probabilidad × ganancia",
              2: "algo conservador: da más peso a la probabilidad",
              3: "muy conservador: prioriza las operaciones más seguras"}
PARAMS = [dict(reserva=r, cap=c) for r, c in itertools.product([0.1, 0.25, 0.5], [0.35, 0.6, 1.0])]
HIST = "2022-01-01"                 # desde aquí se recuerdan las operaciones de cada agente para estimar probabilidades
P1 = ("2024-01-01", "2025-12-31")   # se buscan con estos años
P2_FROM = "2026-01-01"              # y deben cumplir también en 2026 hasta hoy
MAX_MIEMBROS = 6
COSTE_REPARTO = 0.002               # coste de mover dinero entre agentes (comisión + algo de deslizamiento)
GOOD = 0.0001                       # una semana es buena solo si gana (más de un 0,01 %)


# ------------------------------------------------------------------ lo que sabe cada agente de sus operaciones

def regime_at(mk):
    """Tipo de mercado en cada vela: 0 lateral, 1 alcista, 2 bajista (media de 50 días y eficiencia de 14 días)."""
    I = mk.I
    ma, er = I.sma(50 * mk.bpd), I.er(14 * mk.bpd)
    with np.errstate(invalid="ignore"):
        trend = np.nan_to_num(er) > 0.25
        return np.where(trend & (I.c > ma), 1, np.where(trend & (I.c < ma), 2, 0))


def time_machine(mk, j, side, tp, sl, horizon, n, rng):
    """"Máquina del tiempo": repite miles de veces lo que podría pasar después de la vela j, juntando al azar
    movimientos reales de los últimos 30 días. Devuelve (prob. de llegar al objetivo, prob. de tocar el stop,
    prob. de que al final del plazo siga abierta y en ganancia)."""
    c = mk.I.c
    look = 30 * mk.bpd
    if j < look + 1 or tp <= 0 or sl <= 0:
        return None
    lr = np.diff(np.log(c[j - look:j + 1])) * side
    paths = np.cumsum(rng.choice(lr, size=(n, horizon)), axis=1)
    up, dn = np.log(1 + tp), np.log(1 - min(sl, 0.95))
    hit_up = np.where((paths >= up).any(1), (paths >= up).argmax(1), horizon + 1)
    hit_dn = np.where((paths <= dn).any(1), (paths <= dn).argmax(1), horizon + 1)
    win = hit_up < hit_dn
    lose = hit_dn < hit_up
    still = ~win & ~lose
    return float(win.mean()), float(lose.mean()), float((still & (paths[:, -1] > 0)).mean())


def trade_plan(ag, mk, j, gw, gl):
    """Objetivo, stop y plazo de la operación abierta (de su regla; si no tiene, de su historial o de la volatilidad)."""
    rule = ag.get("regla") if ag.get("eleccion") == "propia" else None
    atr = mk.I.atr(14)[j] / mk.I.c[j] if not np.isnan(mk.I.atr(14)[j]) else 0.02
    tp = rule["tp"] if rule and isinstance(rule.get("tp"), (int, float)) and rule["tp"] > 0 else (gw or 2 * atr)
    if rule and rule.get("stop"):
        sl = rule["stop"] * atr
    elif rule and rule.get("trail"):
        sl = rule["trail"]
    else:
        sl = gl or 1.5 * atr
    days = rule.get("hold") if rule and rule.get("hold") else 5
    return tp, sl, max(1, int(days * mk.bpd))


def series(ac, ag, start, variante=None):
    """Desde `start`, por día: rentabilidad, exposición al cierre, y para la operación abierta al cierre
    la probabilidad estimada de acabar ganando (P) y la ganancia media cuando gana (G).
    variante: None, "comisiones_x2" (paga el doble de comisiones) o "vela_tarde" (entra y sale una vela más tarde)."""
    mk = ac.m(ag)
    h = mk.idx(HIST)
    if h >= mk.n - 1:
        return None
    w = ac.exposure(ag)
    cfg = ac.run_cfg()
    if variante == "comisiones_x2":
        cfg = dict(cfg, fee=cfg["fee"] * 2, slip=cfg["slip"] * 2, maker=cfg.get("maker", cfg["fee"]) * 2)
    elif variante == "vela_tarde":
        w = np.r_[0.0, np.asarray(w)[:-1]]
    r = run(mk.I, w, h, mk.n - 1, cfg)
    reg = regime_at(mk)
    trades, open_i = [], None  # (vela de entrada, vela de salida, resultado)
    for t in r.trades:
        if t["side"] in ("compra", "corto") and open_i is None:
            open_i = t["i"]
        if "pnl" in t and open_i is not None:
            trades.append((open_i, t["i"], t["pnl_pct"]))
            open_i = None
    still_open = open_i
    s0 = dt.date.fromisoformat(start)
    days, vals, expo, last_bar = [], [], [], []
    prev_d = None
    for k, v in enumerate(r.eq):
        j = h + k
        d = mk.ts[j].date()
        if d != prev_d:
            days.append(d)
            vals.append(v)
            expo.append(abs(float(w[j])))
            last_bar.append(j)
            prev_d = d
        else:
            vals[-1], expo[-1], last_bar[-1] = v, abs(float(w[j])), j
    vals = np.array(vals)
    ret = np.r_[vals[0] / ac.run_cfg()["cap"] - 1, vals[1:] / vals[:-1] - 1]
    P = np.zeros(len(days))
    G = np.zeros(len(days))
    rng = np.random.default_rng(zlib.crc32(ag["id"].encode()))
    for n_, j in enumerate(last_bar):
        if days[n_] < s0 - dt.timedelta(days=1) or expo[n_] <= 0.05:
            continue
        cur = next((tr for tr in trades if tr[0] <= j < tr[1]), None)
        entry = cur[0] if cur else (still_open if still_open is not None and still_open <= j else None)
        if entry is None:
            continue
        past = [tr for tr in trades if tr[1] <= j]
        same = [tr for tr in past if reg[tr[0]] == reg[entry]]
        p_all = (sum(tr[2] > 0 for tr in past) + 1) / (len(past) + 2)
        p = (sum(tr[2] > 0 for tr in same) + 2 * p_all) / (len(same) + 2)
        gw = [tr[2] for tr in same if tr[2] > 0]
        if len(gw) < 2:
            gw = [tr[2] for tr in past if tr[2] > 0]
        gl = [-tr[2] for tr in past if tr[2] < 0]
        tp, sl, hz = trade_plan(ag, mk, j, float(np.mean(gw)) if gw else None, float(np.mean(gl)) if gl else None)
        last = n_ == len(last_bar) - 1
        tm = time_machine(mk, j, 1 if w[j] > 0 else -1, tp, sl, hz, 2000 if last else 300, rng)
        p_mc = (tm[0] + tm[2]) if tm else p
        P[n_] = 0.5 * p + 0.5 * p_mc  # la mitad, su historial; la otra mitad, la máquina del tiempo
        G[n_] = tp
        if last:
            ac.__dict__.setdefault("_tm_info", {})[ag["id"]] = dict(historial=round(p, 3), maquina=round(p_mc, 3),
                                                                     objetivo=round(tp, 4), stop=round(sl, 4))
    keep = [k for k, d in enumerate(days) if d >= s0]
    return [days[k] for k in keep], ret[keep], np.array(expo)[keep], P[keep], G[keep]


def matrix(ac, agents, start, end, variante=None):
    """Por día y miembro: rentabilidad R, exposición E, probabilidad P y ganancia G (alineados por fecha)."""
    days = []
    d = dt.date.fromisoformat(start)
    while d <= end:
        days.append(d)
        d += dt.timedelta(days=1)
    pos = {d: k for k, d in enumerate(days)}
    out = [np.zeros((len(agents), len(days))) for _ in range(4)]
    cache = ac.__dict__.setdefault("_series_cache", {})
    for j, ag in enumerate(agents):
        key = (ag["id"], start, variante)
        if key not in cache:
            cache[key] = series(ac, ag, start, variante)
        s = cache[key]
        if s is None:
            continue
        for k_src, d in enumerate(s[0]):
            k = pos.get(d)
            if k is not None:
                for m in range(4):
                    out[m][j, k] = s[m + 1][k_src]
    return (days, *out)


# ------------------------------------------------------------------ simular una cartera compartida

def alloc(P, G, prudencia, prm):
    """Parte de la cartera para cada miembro según la prioridad de su operación abierta."""
    n = len(P)
    open_ = P > 0
    f = np.zeros(n)
    if not open_.any():
        return np.full(n, min(1.0 / n, prm["cap"]))  # nadie tiene operación: cada uno con su parte, por si entra
    score = np.where(open_, P ** prudencia * np.maximum(G, 0.0), 0.0)
    waiting = ~open_
    pool = 1.0 - (prm["reserva"] if waiting.any() else 0.0)
    if score.sum() > 0:
        f[open_] = pool * score[open_] / score.sum()
    if waiting.any():
        f[waiting] = prm["reserva"] / waiting.sum()
    return np.minimum(f, prm["cap"])


def simulate(R, E, P, G, prudencia, prm, cap0=100.0):
    """Devuelve (curva de valor, reparto F[miembro, día]). El reparto de cada día se decide con el cierre anterior."""
    n, T = R.shape
    val = np.empty(T)
    F = np.zeros((n, T))
    v = cap0
    f_prev = np.zeros(n)
    for t in range(T):
        f = alloc(P[:, t - 1], G[:, t - 1], prudencia, prm) if t else alloc(np.zeros(n), np.zeros(n), prudencia, prm)
        turnover = float(np.sum(np.abs(f - f_prev) * E[:, t - 1])) if t else 0.0
        v *= 1 + float(np.dot(f, R[:, t])) - turnover * COSTE_REPARTO
        val[t] = v
        F[:, t] = f
        f_prev = f
    return val, F


def weekly(days, val, cap0=100.0):
    ends = {}
    for d, v in zip(days, val):
        ends[d.isocalendar()[:2]] = v
    vs = [cap0] + list(ends.values())
    return np.array(vs[1:]) / np.array(vs[:-1]) - 1


def stats(days, val, cap0=100.0):
    if not len(val):
        return dict(ret=0.0, verde=0.0, peor=0.0, dd=0.0, semanas=0)
    wk = weekly(days, val, cap0)
    peak = np.maximum.accumulate(np.r_[cap0, val])
    dd = float(np.max((peak - np.r_[cap0, val]) / peak))
    return dict(ret=float(val[-1] / cap0 - 1), verde=float(np.mean(wk > GOOD)) if len(wk) else 0.0,
                peor=float(wk.min()) if len(wk) else 0.0, dd=dd, semanas=int(len(wk)))


def annual(s):
    """Rentabilidad pasada a un año (con las semanas que dura el periodo)."""
    yrs = max(s["semanas"], 1) / 52.0
    return (1 + s["ret"]) ** (1 / yrs) - 1 if s["ret"] > -1 else -1.0


def fails(s, goal):
    """Qué condiciones del equipo no se cumplen (lista vacía = cumple todas)."""
    f = []
    a = annual(s)
    if a * 100 < goal.get("ganancia_minima_anual_pct", 0) or s["ret"] <= 0:
        f.append(f"gana un {a * 100:.1f} % al año (mínimo {goal.get('ganancia_minima_anual_pct', 0)} %)".replace(".", ","))
    if s["verde"] * 100 <= goal["semanas_en_verde_pct"]:
        f.append(f"gana solo el {s['verde'] * 100:.0f} % de las semanas (tiene que ser más del {goal['semanas_en_verde_pct']} %)")
    if s["dd"] * 100 > goal.get("caida_maxima_pct", 100):
        f.append(f"llega a caer un {s['dd'] * 100:.0f} % (máximo {goal.get('caida_maxima_pct')} %)")
    return f


def objective(s, goal):
    """Ganar lo máximo; si no cumple las condiciones, cuanto más lejos esté, peor."""
    miss = (max(0.0, goal["semanas_en_verde_pct"] / 100 + 0.01 - s["verde"]) * 2
            + max(0.0, goal.get("ganancia_minima_anual_pct", 0) / 100 - annual(s))
            + max(0.0, s["dd"] - goal.get("caida_maxima_pct", 100) / 100) * 2)
    return s["ret"] - 3 * miss


# ------------------------------------------------------------------ ¿suerte o habilidad?

def prob_cumplir(daily_ret, goal, n=2000, dias=91, bloque=7, seed=7):
    """Probabilidad de cumplir las condiciones en los próximos 3 meses: se construyen miles de trimestres posibles
    juntando semanas reales del equipo al azar (bloques de 7 días seguidos, para respetar las rachas)."""
    r = np.asarray(daily_ret, float)
    if len(r) < 60:
        return None
    rng = np.random.default_rng(seed)
    nb = dias // bloque
    starts = rng.integers(0, len(r) - bloque, size=(n, nb))
    ok = 0
    for row in starts:
        path = np.concatenate([r[a:a + bloque] for a in row])
        val = 100 * np.cumprod(1 + path)
        wk = val[bloque - 1::bloque] / np.r_[100, val[bloque - 1::bloque][:-1]] - 1
        peak = np.maximum.accumulate(np.r_[100, val])
        st = dict(ret=float(val[-1] / 100 - 1), verde=float(np.mean(wk > GOOD)), peor=float(wk.min()),
                  dd=float(np.max((peak - np.r_[100, val]) / peak)), semanas=len(wk))
        ok += not fails(st, goal)
    return ok / n


def ataques(ac, mem, prm, k2, days):
    """Pruebas duras en 2026: si con ellas el equipo deja de ganar, probablemente tuvo suerte."""
    out = {}
    for var in ("comisiones_x2", "vela_tarde"):
        d, R, E, P, G = matrix(ac, mem, P1[0], days[-1], var)
        val, _ = simulate(R[:, k2:], E[:, k2:], P[:, k2:], G[:, k2:], prm["prudencia"], prm)
        out[var] = float(val[-1] / 100 - 1) if len(val) else 0.0
    d, R, E, P, G = matrix(ac, mem, P1[0], days[-1])
    val, _ = simulate(R[:, k2:], E[:, k2:], P[:, k2:], G[:, k2:], prm["prudencia"], prm)
    rets = np.r_[val[0] / 100 - 1, val[1:] / val[:-1] - 1] if len(val) else np.array([])
    months = {}
    for dd_, r_ in zip(days[k2:], rets):
        months.setdefault((dd_.year, dd_.month), []).append(r_)
    gains = {m: np.prod(1 + np.array(v)) - 1 for m, v in months.items()}
    if gains:
        best = max(gains, key=gains.get)
        out["sin_mejor_mes"] = float(np.prod([1 + g for m, g in gains.items() if m != best]) - 1)
    return out


# ------------------------------------------------------------------ formar equipos

def build(ac, last_day, log=print):
    """1) Pasan todos los agentes que ganaron dinero (tras comisiones) en su examen de 2024–25.
    2) Con ellos se forman equipos usando solo 2024–25 (los que más ganan cumpliendo las condiciones), con cada
       grado de prudencia y cada forma de repartir.
    3) Cada equipo hace la prueba de 2026 (enero–hoy).
    4) Se quedan los 3 mejores (podio): primero los que ganan más semanas, y entre parecidos, el que más gana.
    Devuelve dict puesto -> propuesta."""
    goal = ac.cfg.get("objetivo_equipo", {"semanas_en_verde_pct": 50, "ganancia_minima_anual_pct": 10, "caida_maxima_pct": 25})
    # todos los agentes examinados; abajo se quedan los que ganan dinero en 2024–25 con las condiciones de hoy (comisiones, USDC...)
    cands = [a for a in ac.state["agents"] if a.get("exam") and a["status"] != "retirado" and ac.has_market(a)]
    seen, uniq = set(), []
    for a in cands:  # fuera clones
        f = a.get("firma2026") or a["id"]
        if f in seen:
            continue
        seen.add(f)
        uniq.append(a)
    cands = uniq
    if len(cands) < 2:
        return {t: dict(motivo="Todavía no hay al menos 2 agentes que ganaran dinero en su examen.") for t in TIPOS}
    days, R, E, P, G = matrix(ac, cands, P1[0], last_day)
    p1_end = dt.date.fromisoformat(P1[1])
    k1 = sum(1 for d in days if d <= p1_end)
    keep = [j for j in range(len(cands)) if np.prod(1 + R[j, :k1]) - 1 > 0]
    cands = [cands[j] for j in keep]
    R, E, P, G = R[keep], E[keep], P[keep], G[keep]
    if len(cands) < 2:
        return {t: dict(motivo="Todavía no hay al menos 2 agentes que ganen dinero en 2024–25.") for t in TIPOS}
    k2 = days.index(dt.date.fromisoformat(P2_FROM)) if dt.date.fromisoformat(P2_FROM) in days else k1
    with np.errstate(invalid="ignore", divide="ignore"):
        sharpe = np.nan_to_num(R[:, :k1].mean(axis=1) / R[:, :k1].std(axis=1))
    chosen = []
    for j in np.argsort(-sharpe):  # los 24 mejores en 2024–25, sin dos que se muevan casi igual
        if len(chosen) >= 24:
            break
        if R[j, :k1].std() == 0 or R[j, :k1].sum() <= 0:
            continue
        if any(np.corrcoef(R[j, :k1], R[i, :k1])[0, 1] > 0.9 for i in chosen):
            continue
        chosen.append(int(j))
    log(f"Equipos: {len(cands)} agentes ganan dinero en 2024–25 con las condiciones de hoy; se combinan los {len(chosen)} mejores y distintos.")
    teams = []
    for pr in PRUDENCIAS:
        for prm in PARAMS:
            team, cur = [], -1e9
            while len(team) < MAX_MIEMBROS:  # elige con 2024–25: va añadiendo al que más mejora al equipo
                add = None
                for j in chosen:
                    if j in team:
                        continue
                    idx = team + [j]
                    val, _ = simulate(R[idx, :k1], E[idx, :k1], P[idx, :k1], G[idx, :k1], pr, prm)
                    sc = objective(stats(days[:k1], val), goal)
                    if add is None or sc > add[0]:
                        add = (sc, j)
                if add is None or (team and add[0] <= cur + 1e-4):
                    break
                cur, team = add[0], team + [add[1]]
            if len(team) < 2:
                continue
            v1, _ = simulate(R[team, :k1], E[team, :k1], P[team, :k1], G[team, :k1], pr, prm)
            v2, _ = simulate(R[team, k2:], E[team, k2:], P[team, k2:], G[team, k2:], pr, prm)
            s1, s2 = stats(days[:k1], v1), stats(days[k2:], v2)
            teams.append(dict(team=team, prm=dict(prm, prudencia=pr), s1=s1, s2=s2, f1=fails(s1, goal), f2=fails(s2, goal),
                              rank=s2["verde"] + 2 * s2["ret"]))
    teams.sort(key=lambda t: (not t["f2"], t["rank"]), reverse=True)  # primero los que cumplen en 2026, luego semanas ganadas + ganancia
    # a los mejores candidatos se les hacen los ataques y se calcula su probabilidad de cumplir en 3 meses
    seen = []
    for t in teams:
        if len(seen) >= 10:
            break
        key = (tuple(sorted(t["team"])), t["prm"]["prudencia"])
        if key in seen:
            continue
        seen.append(key)
        mem = [cands[j] for j in t["team"]]
        t["ataques"] = ataques(ac, mem, t["prm"], k2, days)
        t["ataques_ok"] = all(v > 0 for v in t["ataques"].values())
        vall, _ = simulate(R[t["team"]], E[t["team"]], P[t["team"]], G[t["team"]], t["prm"]["prudencia"], t["prm"])
        t["prob"] = prob_cumplir(np.r_[vall[0] / 100 - 1, vall[1:] / vall[:-1] - 1], goal)
    teams.sort(key=lambda t: (not t["f2"], t.get("ataques_ok", False), (t.get("prob") or 0) + t["rank"]), reverse=True)
    podium, used = [], []
    for t in teams:  # 3 equipos distintos (si hay)
        key = (sorted(t["team"]), t["prm"]["prudencia"])
        if sorted(t["team"]) in [u[0] for u in used]:
            continue
        used.append(key)
        podium.append(t)
        if len(podium) == 3:
            break
    for t in teams:  # si no hay 3 grupos distintos, completa con otra prudencia
        if len(podium) == 3:
            break
        key = (sorted(t["team"]), t["prm"]["prudencia"])
        if key not in used:
            used.append(key)
            podium.append(t)
    out = {}
    for (slot, info), t in zip(TIPOS.items(), podium + [None] * 3):
        if t is None:
            out[slot] = dict(motivo="No hay suficientes combinaciones distintas.")
            continue
        out[slot] = dict(miembros=[cands[j]["id"] for j in t["team"]], params=t["prm"],
                         pruebas=dict(p1=t["s1"], p2=t["s2"], prob=t.get("prob"), ataques=t.get("ataques")),
                         cumple="; ".join(t["f2"]) or None)
        log(f"{info['nombre']} ({info['puesto']}º): {', '.join(cands[j]['name'] + ' (' + cands[j].get('activo', 'BTC-EUR').split('-')[0] + ')' for j in t['team'])} | "
            f"prudencia {t['prm']['prudencia']} | 2024–25 {t['s1']['ret'] * 100:+.1f} % | 2026 {t['s2']['ret'] * 100:+.1f} %, "
            f"ganó {t['s2']['verde'] * 100:.0f} % de las semanas, caída máx {t['s2']['dd'] * 100:.0f} %")
    return out


# ------------------------------------------------------------------ el día a día de los equipos

def update(ac, log=print):
    """Crea los equipos si no existen o están vacíos (se reintenta cada día), los rehace el día 1 de cada mes
    y calcula su cartera."""
    st = ac.state
    last_day = ac.daily.ts[-1].date()
    start = last_day + dt.timedelta(days=1)
    teams = st.setdefault("equipos", {})
    for k in [k for k in teams if k not in TIPOS]:
        teams.pop(k)
    cond = "usdc" if ac.cfg.get("cotizar_en_usdc") else "eur"
    # se rehacen si no existen, el día 1 de cada mes, o si han cambiado las condiciones (por ejemplo, pasar a USDC)
    need = {t for t in TIPOS if t not in teams or not teams[t].get("periodos") or start.weekday() == 0
            or teams[t]["periodos"][-1].get("condiciones", "eur") != cond}
    if need:
        props = build(ac, last_day, log)
        for t in need:
            p = props[t]
            tm = teams.setdefault(t, dict(id=t, inicio=None, capital_inicial=ac.cfg["saldo_inicial_eur"], periodos=[]))
            if "miembros" not in p:
                if not tm["periodos"]:
                    tm["vacio"] = p["motivo"]
                continue  # si ya tenía miembros, sigue con ellos
            tm.pop("vacio", None)
            if tm["periodos"] and tm["periodos"][-1]["miembros"] == p["miembros"] and tm["periodos"][-1]["params"] == p["params"]:
                tm["periodos"][-1]["condiciones"] = cond
                continue
            if tm["inicio"] is None:
                tm["inicio"] = start.isoformat()
            tm["periodos"].append(dict(desde=start.isoformat(), condiciones=cond, **p))
            names = ", ".join(f"{a['name']} ({a.get('activo', 'BTC-EUR').split('-')[0]})" for i in p["miembros"]
                              for a in st["agents"] if a["id"] == i)
            ac.notify(TIPOS[t]["nombre"], f"Equipo desde el {start.strftime('%d/%m')}: {names}.")
    for t, tm in teams.items():
        if tm.get("periodos"):
            tm.update(track(ac, tm, last_day))


def _now(mem, v, P, G, E, prm):
    """Reparto de mañana (y para cada miembro, su probabilidad con el detalle de historial y máquina del tiempo)."""
    fn = alloc(P, G, prm["prudencia"], prm)
    return [dict(id=a["id"], name=a["name"], activo=a.get("activo", "BTC-EUR"), tf=a["tf"],
                 euros=round(v * float(fn[j]), 2), invertido=round(v * float(fn[j]) * float(E[j]), 2),
                 posicion=round(float(E[j]), 2), prob=round(float(P[j]), 3), ganancia=round(float(G[j]), 4),
                 detalle=getattr(_now, "info", {}).get(a["id"]))
            for j, a in enumerate(mem)]


def track(ac, tm, last_day):
    """Recorre la vida del equipo con los miembros de cada periodo y devuelve su situación."""
    by_id = {a["id"]: a for a in ac.state["agents"]}
    cap0 = tm["capital_inicial"]
    days_all, vals = [], []
    v = cap0
    ahora = None
    contrib = {}
    for k, per in enumerate(tm["periodos"]):
        d0 = dt.date.fromisoformat(per["desde"])
        d1 = dt.date.fromisoformat(tm["periodos"][k + 1]["desde"]) - dt.timedelta(days=1) if k + 1 < len(tm["periodos"]) else last_day
        mem = [by_id[i] for i in per["miembros"] if i in by_id and ac.has_market(by_id[i])]
        if not mem:
            continue
        prm = per["params"]
        if d1 < d0:  # el equipo empieza mañana: solo se calcula cómo repartirá el dinero
            if k == len(tm["periodos"]) - 1:
                _, R0, E0, P0, G0 = matrix(ac, mem, last_day.isoformat(), last_day)
                _now.info = getattr(ac, "_tm_info", {})
                ahora = _now(mem, v, P0[:, -1], G0[:, -1], E0[:, -1], prm)
            continue
        days, R, E, P, G = matrix(ac, mem, (d0 - dt.timedelta(days=1)).isoformat(), d1)
        val, F = simulate(R[:, 1:], E[:, 1:], P[:, 1:], G[:, 1:], prm["prudencia"], prm, cap0=v)
        days_all += days[1:]
        vals += [float(x) for x in val]
        if len(val):
            base = np.r_[v, val[:-1]]
            for j, a in enumerate(mem):
                contrib[a["id"]] = contrib.get(a["id"], 0.0) + float(np.sum(base * F[j] * R[j, 1:]))
            v = float(val[-1])
        if k == len(tm["periodos"]) - 1:
            _now.info = getattr(ac, "_tm_info", {})
            ahora = _now(mem, v, P[:, -1], G[:, -1], E[:, -1], prm)
    s = stats(days_all, np.array(vals), cap0)
    wk = []
    if vals:
        ends = {}
        for d, x in zip(days_all, vals):
            ends[d - dt.timedelta(days=d.weekday())] = (d, x)
        prev = cap0
        for monday in sorted(ends):
            d, x = ends[monday]
            wk.append(dict(inicio=monday.isoformat(), completa=d == monday + dt.timedelta(days=6),
                           eur=round(x - prev, 2), pct=round(x / prev - 1, 5)))
            prev = x
    step = max(1, len(vals) // 90)
    return dict(valor=round(v, 2), dias=len(vals), stats=s, semanas=wk[-26:], ahora=ahora,
                aportacion={i: round(x, 2) for i, x in contrib.items()},
                curva=[round(x, 2) for x in vals[::step]] + ([round(vals[-1], 2)] if vals and (len(vals) - 1) % step else []))
