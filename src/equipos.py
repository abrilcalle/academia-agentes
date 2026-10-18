"""Equipos: varios agentes (de cualquier mercado) que comparten UNA cartera de 100 € ficticios.

Cada día, al cierre, el equipo decide cuánto dinero da a cada miembro:
  - cada miembro tiene una "nota" (calidad) según cómo le fue en las pruebas
  - el que tiene una operación abierta recibe más dinero ("impulso"); el que está esperando, menos ("base")
  - nadie puede llevarse más de un tope de la cartera; lo que no se reparte se queda en euros
Mover dinero de un agente a otro cuesta comisiones (se descuentan).

Cómo se forman (automático):
  - Candidatos: agentes que aprobaron los dos exámenes (en simulado o listos).
  - Se prueban combinaciones y repartos con 2024–25 y deben salir ganadoras también en 2026.
  - Tres equipos compiten, cada uno con un objetivo distinto:
      Ganancia (ganar lo máximo), Semanas en verde (acabar en positivo el máximo de semanas), Equilibrio.
  - Cada mes se vuelve a elegir a los miembros con los datos más recientes; el dinero del equipo sigue.
"""
import datetime as dt
import itertools

import numpy as np

from backtest import run

TIPOS = {
    "ganancia": dict(nombre="Equipo Ganancia", lema="Busca ganar lo máximo"),
    "verde": dict(nombre="Equipo Semanas en verde", lema="Busca acabar en positivo el máximo de semanas"),
    "equilibrio": dict(nombre="Equipo Equilibrio", lema="Busca ganar sin semanas malas"),
}
PARAMS = [dict(base=b, boost=k, cap=c) for b, k, c in itertools.product([1.0, 0.3, 0.0], [0.0, 2.0, 6.0], [0.35, 0.6, 1.0])
          if not (b == 0 and k == 0)]
P1 = ("2024-01-01", "2025-12-31")   # se eligen con estos años
P2_FROM = "2026-01-01"              # y deben ganar también en 2026 hasta hoy
MAX_MIEMBROS = 6
COSTE_REPARTO = 0.002               # coste de mover dinero entre agentes (comisión + algo de deslizamiento)


# ------------------------------------------------------------------ series diarias de cada agente

def series(ac, ag, start):
    """Devuelve (días, rentabilidad diaria, exposición al cierre de cada día) de la estrategia del agente desde `start`."""
    mk = ac.m(ag)
    a = mk.idx(start)
    if a >= mk.n - 1:
        return None
    w = ac.exposure(ag)
    r = run(mk.I, w, a, mk.n - 1, ac.run_cfg())
    days, vals, expo = [], [], []
    last = None
    for k, v in enumerate(r.eq):
        d = mk.ts[a + k].date()
        if d != last:
            days.append(d)
            vals.append(v)
            expo.append(abs(float(w[a + k])))
            last = d
        else:
            vals[-1] = v
            expo[-1] = abs(float(w[a + k]))
    vals = np.array(vals)
    ret = np.r_[vals[0] / r.eq[0] - 1 if len(vals) else 0.0, vals[1:] / vals[:-1] - 1]
    return days, ret, np.array(expo)


def matrix(ac, agents, start, end):
    """Rentabilidades y exposiciones diarias alineadas por fecha: (días, R[miembro, día], E[miembro, día], ids)."""
    days = []
    d = dt.date.fromisoformat(start)
    while d <= end:
        days.append(d)
        d += dt.timedelta(days=1)
    pos = {d: k for k, d in enumerate(days)}
    R = np.zeros((len(agents), len(days)))
    E = np.zeros((len(agents), len(days)))
    ok = []
    for j, ag in enumerate(agents):
        s = ac._series_cache.get((ag["id"], start)) if hasattr(ac, "_series_cache") else None
        if s is None:
            s = series(ac, ag, start)
            ac.__dict__.setdefault("_series_cache", {})[(ag["id"], start)] = s
        if s is None:
            continue
        for d, r_, e_ in zip(*s):
            k = pos.get(d)
            if k is not None:
                R[j, k], E[j, k] = r_, e_
        ok.append(j)
    return days, R, E


# ------------------------------------------------------------------ simular una cartera compartida

def simulate(R, E, q, prm, cap0=100.0):
    """R, E: [miembros, días]; q: notas. Devuelve (curva de valor, repartos f[miembros, días])."""
    n, T = R.shape
    val = np.empty(T)
    F = np.zeros((n, T))
    v = cap0
    f_prev = np.zeros(n)
    for t in range(T):
        if t == 0:
            f = alloc(q, np.zeros(n), prm)
        else:
            f = alloc(q, E[:, t - 1], prm)
        turnover = np.sum(np.abs(f - f_prev) * (E[:, t - 1] if t else np.zeros(n)))
        v *= 1 + float(np.dot(f, R[:, t])) - turnover * COSTE_REPARTO
        val[t] = v
        F[:, t] = f
        f_prev = f
    return val, F


def alloc(q, expo, prm):
    raw = q * (prm["base"] + prm["boost"] * (expo > 0.05))
    s = raw.sum()
    if s <= 0:
        return np.zeros(len(q))
    return np.minimum(raw / s, prm["cap"])


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
    return dict(ret=float(val[-1] / cap0 - 1), verde=float(np.mean(wk > 0)) if len(wk) else 0.0,
                peor=float(wk.min()) if len(wk) else 0.0, dd=dd, semanas=int(len(wk)))


def objective(tipo, s, goal):
    worst_pen = 3 * max(0.0, -s["peor"] - goal["peor_semana_pct"] / 100)
    if tipo == "ganancia":
        return s["ret"] - 2 * max(0.0, s["dd"] - 0.3)
    if tipo == "verde":
        return s["verde"] + 0.5 * s["ret"] - worst_pen
    return s["verde"] + 2 * s["ret"] - worst_pen - s["dd"]


def quality(R, E):
    """Nota de cada agente: rentabilidad diaria media / volatilidad (mínimo 0,05)."""
    m, sd = R.mean(axis=1), R.std(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        q = np.where(sd > 0, m / sd, 0.0)
    return np.clip(np.nan_to_num(q) * np.sqrt(365), 0.05, None)


# ------------------------------------------------------------------ formar equipos

def build(ac, last_day, log=print):
    """Busca el mejor equipo de cada tipo. Devuelve dict tipo -> propuesta (o motivo si ninguno aprueba)."""
    goal = ac.cfg.get("objetivo_equipo", {"semanas_en_verde_pct": 65, "peor_semana_pct": 3})
    cands = [a for a in ac.state["agents"] if a["status"] in ("simulado", "listo")]
    if len(cands) < 2:
        return {t: dict(motivo="Todavía no hay al menos 2 agentes que hayan aprobado los dos exámenes.") for t in TIPOS}
    days, R, E = matrix(ac, cands, P1[0], last_day)
    p1_end = dt.date.fromisoformat(P1[1])
    k1 = sum(1 for d in days if d <= p1_end)
    k2 = days.index(dt.date.fromisoformat(P2_FROM)) if dt.date.fromisoformat(P2_FROM) in days else k1
    q_all = quality(R[:, :k1], E[:, :k1])
    # preselección: los 18 mejores por su nota en 2024–25, sin repetir a dos que se mueven casi igual
    order = np.argsort(-q_all)
    chosen = []
    for j in order:
        if len(chosen) >= 18:
            break
        if R[j, :k1].std() == 0:
            continue
        if any(np.corrcoef(R[j, :k1], R[i, :k1])[0, 1] > 0.9 for i in chosen):
            continue
        chosen.append(int(j))
    out = {}
    used = []
    for tipo in TIPOS:
        best = None
        for prm in PARAMS:
            team = []
            cur = -1e9
            while len(team) < MAX_MIEMBROS:  # va añadiendo al agente que más mejora al equipo
                add = None
                for j in chosen:
                    if j in team:
                        continue
                    idx = team + [j]
                    val, _ = simulate(R[idx, :k1], E[idx, :k1], q_all[idx], prm)
                    sc = objective(tipo, stats(days[:k1], val), goal)
                    if add is None or sc > add[0]:
                        add = (sc, j)
                if add is None or (team and add[0] <= cur + 1e-4):
                    break
                cur, team = add[0], team + [add[1]]
            if len(team) < 2:
                continue
            idx = team
            v1, _ = simulate(R[idx, :k1], E[idx, :k1], q_all[idx], prm)
            s1 = stats(days[:k1], v1)
            v2, _ = simulate(R[idx, k2:], E[idx, k2:], q_all[idx], prm)
            s2 = stats(days[k2:], v2)
            passed = s1["ret"] > 0 and s2["ret"] > 0 and s2["dd"] <= 0.25  # ganador en las dos pruebas
            cand = (passed, cur, idx, prm, s1, s2)
            if sorted(idx) in used:  # cada equipo tiene que ser distinto de los demás
                continue
            if best is None or (cand[0], cand[1]) > (best[0], best[1]):
                best = cand
        if best is None or not best[0]:
            out[tipo] = dict(motivo="Ninguna combinación salió ganadora (y sin caídas de más del 25 %) en las dos pruebas (2024–25 y 2026)." +
                             (f" La mejor ganó {best[4]['ret'] * 100:+.1f} % en 2024–25 y {best[5]['ret'] * 100:+.1f} % en 2026, "
                              f"con {best[5]['verde'] * 100:.0f} % de semanas en verde.".replace(".", ",", 2) if best else ""))
            continue
        _, sc, idx, prm, s1, s2 = best
        used.append(sorted(idx))
        out[tipo] = dict(miembros=[cands[j]["id"] for j in idx], notas={cands[j]["id"]: round(float(q_all[j]), 3) for j in idx},
                         params=prm, pruebas=dict(p1=s1, p2=s2))
        log(f"{TIPOS[tipo]['nombre']}: {', '.join(cands[j]['name'] for j in idx)} | 2024–25 {s1['ret'] * 100:+.1f} %, "
            f"2026 {s2['ret'] * 100:+.1f} % ({s2['verde'] * 100:.0f} % semanas en verde)")
    return out


# ------------------------------------------------------------------ el día a día de los equipos

def update(ac, log=print):
    """Crea los equipos si no existen, los rehace al empezar cada mes (o si un hueco está vacío) y calcula su cartera."""
    st = ac.state
    last_day = ac.daily.ts[-1].date()
    start = last_day + dt.timedelta(days=1)
    teams = st.setdefault("equipos", {})
    # se forman si no existen o están vacíos (se reintenta cada día) y se rehacen todos el primer día de cada mes
    need = {t for t in TIPOS if t not in teams or not teams[t].get("periodos") or start.day == 1}
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
                continue
            if tm["inicio"] is None:
                tm["inicio"] = start.isoformat()
            tm["periodos"].append(dict(desde=start.isoformat(), **p))
            names = ", ".join(next(a["name"] for a in st["agents"] if a["id"] == i) for i in p["miembros"])
            ac.notify(f"{TIPOS[t]['nombre']}", f"Nuevo equipo desde el {start.strftime('%d/%m')}: {names}.")
    for t, tm in teams.items():
        if tm.get("periodos"):
            tm.update(track(ac, tm, last_day))


def track(ac, tm, last_day):
    """Recorre la vida del equipo con sus miembros de cada periodo y devuelve su situación."""
    by_id = {a["id"]: a for a in ac.state["agents"]}
    cap0 = tm["capital_inicial"]
    inicio = dt.date.fromisoformat(tm["inicio"])
    days_all, vals = [], []
    v = cap0
    ahora = None
    contrib = {}
    for k, per in enumerate(tm["periodos"]):
        d0 = dt.date.fromisoformat(per["desde"])
        d1 = dt.date.fromisoformat(tm["periodos"][k + 1]["desde"]) - dt.timedelta(days=1) if k + 1 < len(tm["periodos"]) else last_day
        mem = [by_id[i] for i in per["miembros"] if i in by_id]
        if not mem:
            continue
        q = np.array([per["notas"].get(a["id"], 0.05) for a in mem])
        if d1 < d0:  # el equipo empieza hoy: solo se calcula cómo repartirá el dinero
            if k == len(tm["periodos"]) - 1:
                _, _, E0 = matrix(ac, mem, last_day.isoformat(), last_day)
                fn = alloc(q, E0[:, -1], per["params"])
                ahora = [dict(id=a["id"], name=a["name"], activo=a.get("activo", "BTC-EUR"), tf=a["tf"],
                              euros=round(v * float(fn[j]), 2), invertido=round(v * float(fn[j]) * float(E0[j, -1]), 2),
                              posicion=round(float(E0[j, -1]), 2)) for j, a in enumerate(mem)]
            continue
        # se simula desde un día antes para conocer las posiciones de partida
        days, R, E = matrix(ac, mem, (d0 - dt.timedelta(days=1)).isoformat(), d1)
        val, F = simulate(R[:, 1:], E[:, 1:], q, per["params"], cap0=v)
        for d, x in zip(days[1:], val):
            days_all.append(d)
            vals.append(float(x))
        # aportación de cada miembro (aprox.: reparto × rentabilidad)
        if len(val):
            base = np.r_[v, val[:-1]]
            for j, a in enumerate(mem):
                contrib[a["id"]] = contrib.get(a["id"], 0.0) + float(np.sum(base * F[j] * R[j, 1:]))
            v = float(val[-1])
        if k == len(tm["periodos"]) - 1:
            fn = alloc(q, E[:, -1], per["params"])  # reparto para mañana
            ahora = [dict(id=a["id"], name=a["name"], activo=a.get("activo", "BTC-EUR"), tf=a["tf"],
                          euros=round(v * float(fn[j]), 2), invertido=round(v * float(fn[j]) * float(E[j, -1]), 2),
                          posicion=round(float(E[j, -1]), 2)) for j, a in enumerate(mem)]
    days_arr = days_all
    s = stats(days_arr, np.array(vals), cap0) if vals else stats([], np.array([]), cap0)
    wk = []
    if vals:
        ends = {}
        for d, x in zip(days_arr, vals):
            k = d - dt.timedelta(days=d.weekday())
            ends[k] = (d, x)
        prev = cap0
        for monday in sorted(ends):
            d, x = ends[monday]
            wk.append(dict(inicio=monday.isoformat(), completa=d == monday + dt.timedelta(days=6), eur=round(x - prev, 2), pct=round(x / prev - 1, 5)))
            prev = x
    step = max(1, len(vals) // 90)
    return dict(valor=round(v if vals else cap0, 2), dias=len(vals), stats=s, semanas=wk[-26:], ahora=ahora,
                aportacion={i: round(x, 2) for i, x in contrib.items()},
                curva=[round(x, 2) for x in vals[::step]] + ([round(vals[-1], 2)] if vals and (len(vals) - 1) % step else []))
