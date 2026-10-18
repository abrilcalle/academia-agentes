"""Informe mensual: cómo le fue a cada agente, qué combinación habría ganado más y qué conviene
activar el mes que viene.

Cuentas del informe (todas con 100 € ficticios por agente y comisiones descontadas):
- "Tu cartera" = agentes listos que no has pausado (config.json -> cartera.pausados).
  Mientras no haya ninguno listo, se usan todos los que están en simulado.
- Una combinación reparte el dinero a partes iguales entre sus agentes al empezar el mes.
- La recomendación mira los últimos meses (no solo el último) y premia ganar con caídas
  pequeñas, porque elegir lo que mejor fue el mes pasado suele salir mal el siguiente.
"""
import calendar
import datetime as dt
import itertools
import json
import os

import numpy as np


def eur(v, sign=False):
    s = f"{abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"
    if sign:
        return ("+" if v >= 0 else "−") + s
    return ("−" if v < 0 else "") + s


def pc(x):
    return f"{x * 100:+.1f} %".replace(".", ",")


def names(lst):
    lst = list(lst)
    return lst[0] if len(lst) == 1 else ", ".join(lst[:-1]) + " y " + lst[-1]


def month_bounds(y, m):
    return dt.date(y, m, 1), dt.date(y, m, calendar.monthrange(y, m)[1])


def pending_month(state, last_day):
    """El mes completo más reciente que aún no tiene informe (o None)."""
    first_this = last_day.replace(day=1)
    if last_day == month_bounds(last_day.year, last_day.month)[1]:
        target = first_this
    else:
        prev = first_this - dt.timedelta(days=1)
        target = prev.replace(day=1)
    key = target.strftime("%Y-%m")
    done = {r["mes"] for r in state.get("informes", [])}
    return None if key in done else target


def series(ac, ag):
    """{fecha: saldo al cierre} del simulado de un agente, y sus operaciones cerradas con fechas."""
    r, mk, a = ac.paper_run(ag)
    if r is None:
        return {}, []
    daily = mk.daily(r.eq, a)
    trades, entry = [], None
    for t in r.trades:
        if t["side"] in ("compra", "corto") and entry is None:
            entry = t
        if "pnl" in t:
            trades.append(dict(entra=mk.ts[entry["i"]].date() if entry else mk.ts[t["i"]].date(),
                               sale=mk.ts[t["i"]].date(), pnl=t["pnl"]))
            entry = None
    return daily, trades


def value_at(daily, day, cap):
    """Saldo al cierre de `day` (o el último anterior; si aún no había empezado, el capital inicial)."""
    best = None
    for d in daily:
        if d <= day and (best is None or d > best):
            best = d
    return daily[best] if best else cap


def combo_curve(mat):
    return mat.mean(axis=0)


def maxdd(curve):
    peak = np.maximum.accumulate(curve)
    return float(np.max((peak - curve) / peak)) if len(curve) else 0.0


def weeks_of(curve, days):
    """Rentabilidad de cada semana (lunes a domingo) de una curva diaria."""
    ends = {}
    for v, d in zip(curve, days):
        ends[d.isocalendar()[:2]] = v
    vals = [curve[0]] + list(ends.values())
    return np.array(vals[1:]) / np.array(vals[:-1]) - 1


def team_score(curve, days, goal):
    """Lo que buscas: muchas semanas en verde, ninguna muy mala, y ganar en el total."""
    wk = weeks_of(curve, days)
    if not len(wk):
        return -9, 0.0, 0.0
    green = float(np.mean(wk > 0))
    worst = float(wk.min())
    r = curve[-1] - 1
    s = green + 2 * r - (0.5 if r <= 0 else 0)
    return s, green, worst


def build_report(ac, month_start):
    cfg = ac.cfg
    cap = cfg["saldo_inicial_eur"]
    ms, me = month_bounds(month_start.year, month_start.month)
    pausados = set(cfg.get("cartera", {}).get("pausados", []))
    pool = [a for a in ac.state["agents"] if a.get("paper_start") and a["status"] in ("simulado", "listo", "retirado", "real")]
    data = {}
    for ag in pool:
        if dt.date.fromisoformat(ag["paper_start"]) > me:
            continue
        daily, trades = series(ac, ag)
        if not daily or max(daily) < ms:
            continue
        data[ag["name"]] = dict(ag=ag, daily=daily, trades=trades)
    if not data:
        return None

    # resultado del mes de cada agente
    rows = []
    for n, d in data.items():
        start_val = value_at(d["daily"], ms - dt.timedelta(days=1), cap)
        end_val = value_at(d["daily"], me, cap)
        full = dt.date.fromisoformat(d["ag"]["paper_start"]) <= ms
        tr = [t for t in d["trades"] if ms <= t["sale"] <= me]
        rows.append(dict(name=n, status=d["ag"]["status"], tf=d["ag"].get("activo", "BTC-EUR").split("-")[0].replace("PAXG", "Oro") + " " + d["ag"]["tf"], eleccion=d["ag"]["eleccion"],
                         label=d["ag"]["label"], ret=end_val / start_val - 1, pnl=end_val - start_val,
                         trades=len(tr), lost=sum(1 for t in tr if t["pnl"] < 0), full=full,
                         pausado=n in pausados))
    rows.sort(key=lambda r: -r["ret"])
    by = {r["name"]: r for r in rows}

    # tu cartera
    listos = [n for n, d in data.items() if d["ag"]["status"] in ("listo", "real") and n not in pausados]
    if listos:
        cartera, cartera_txt = listos, "tus agentes listos (sin los pausados)"
    else:
        cartera = [n for n, d in data.items() if d["ag"]["status"] == "simulado" and n not in pausados]
        cartera_txt = "todos los agentes que están en simulado"
    cartera = [n for n in cartera if by[n]["full"]] or cartera
    cand = [r["name"] for r in rows if r["full"] and r["status"] != "retirado"]
    ret_cart = float(np.mean([by[n]["ret"] for n in cartera])) if cartera else 0.0
    capital = cap * max(1, len(cartera))

    insights = []
    # mejor y peor
    if rows:
        b, w = rows[0], rows[-1]
        insights.append(f"Mejor agente del mes: {b['name']} ({pc(b['ret'])}, {eur(b['pnl'], True)}). Peor: {w['name']} ({pc(w['ret'])}, {eur(w['pnl'], True)}).")
    # mejor combinación del mes (a toro pasado)
    icfg = cfg["informe_mensual"]
    best_combo = None
    top = sorted(cand, key=lambda n: -by[n]["ret"])[:12]
    for k in range(1, min(icfg["maximo_agentes_en_combinacion"], len(top)) + 1):
        for combo in itertools.combinations(top, k):
            r = float(np.mean([by[n]["ret"] for n in combo]))
            if best_combo is None or r > best_combo[1]:
                best_combo = (combo, r)
    if cartera and best_combo and set(best_combo[0]) != set(cartera):
        diff = capital * (best_combo[1] - ret_cart)
        insights.append(f"Con {len(cartera)} agente{'s' if len(cartera) > 1 else ''} en tu cartera ({names(cartera)}) el mes acabó en {pc(ret_cart)}. "
                        f"Si solo hubieras tenido a {names(best_combo[0])} con el mismo dinero ({eur(capital)}), tendrías {eur(diff, True)} más. "
                        f"Ojo: esto se sabe a toro pasado.")
    # agentes que hicieron lo mismo
    groups = {}
    for r in rows:
        if r["full"] and r["status"] != "retirado":
            groups.setdefault(round(r["ret"], 3), []).append(r["name"])
    clones = max(groups.values(), key=len, default=[])
    if len(clones) >= 3:
        insights.append(f"{names(clones)} hicieron prácticamente lo mismo este mes ({pc(by[clones[0]]['ret'])}). "
                        "Tener varios agentes que se mueven igual no reparte el riesgo: si uno cae, caen todos.")
    # quién amortiguó las pérdidas de quién
    for n in cartera:
        lost = [t for t in data[n]["trades"] if ms <= t["sale"] <= me and t["pnl"] < 0]
        if not lost:
            continue
        loss = sum(t["pnl"] for t in lost)
        best_h = None
        for m in cand:
            if m == n:
                continue
            g = 0.0
            for t in lost:
                d0, d1 = t["entra"] - dt.timedelta(days=1), t["sale"]
                g += value_at(data[m]["daily"], d1, cap) - value_at(data[m]["daily"], d0, cap)
            if best_h is None or g > best_h[1]:
                best_h = (m, g)
        if best_h and best_h[1] > 0.5:
            m, g = best_h
            activo = m in cartera
            insights.append(f"{n} perdió {len(lost)} {'operaciones' if len(lost) > 1 else 'operación'} ({eur(loss)}). En esos mismos días {m} ganó {eur(g, True)}: "
                            + ("como los tenías a los dos, la pérdida se compensó en parte." if activo else
                               f"con {m} activado habrías perdido {eur(min(g, -loss))} menos."))
    # recomendación con varios meses
    nmon = icfg["meses_para_recomendar"]
    w0 = (ms - dt.timedelta(days=31 * (nmon - 1))).replace(day=1)
    days = []
    starts = sorted(dt.date.fromisoformat(data[n]["ag"]["paper_start"]) for n in cand)
    d = max(w0, starts[len(starts) // 2]) if starts else ms  # desde que al menos la mitad ya operaba
    while d <= me:
        days.append(d)
        d += dt.timedelta(days=1)
    rec = None
    if len(cand) >= 1 and days:
        ok = [n for n in cand if dt.date.fromisoformat(data[n]["ag"]["paper_start"]) <= days[0] + dt.timedelta(days=7)]
        mat = {n: np.array([value_at(data[n]["daily"], x, cap) for x in days]) for n in ok}
        mat = {n: v / v[0] for n, v in mat.items()}
        lo = min(icfg["minimo_agentes_en_combinacion"], len(ok))
        hi = min(icfg["maximo_agentes_en_combinacion"], len(ok))
        goal = cfg.get("objetivo_equipo", {"semanas_en_verde_pct": 50})
        ranked = sorted(ok, key=lambda n: -team_score(mat[n], days, goal)[0])[:12]
        rets = {n: np.diff(np.log(v)) for n, v in mat.items()}

        def too_alike(combo):  # dos agentes que se mueven casi igual no reparten el riesgo
            for x, y in itertools.combinations(combo, 2):
                a_, b_ = rets[x], rets[y]
                if a_.std() == 0 or b_.std() == 0 or np.corrcoef(a_, b_)[0, 1] > 0.9:
                    return True
            return False

        best = None
        for k in range(max(1, lo), hi + 1):
            for combo in itertools.combinations(ranked, k):
                if k > 1 and too_alike(combo):
                    continue
                curve = combo_curve(np.vstack([mat[n] for n in combo]))
                r, dd = curve[-1] - 1, maxdd(curve)
                s, green, worst = team_score(curve, days, goal)
                if best is None or s > best[0]:
                    best = (s, combo, r, dd, green, worst)
        if best:
            cur = [n for n in cartera if n in mat]
            cr, cdd = ((combo_curve(np.vstack([mat[n] for n in cur]))[-1] - 1), maxdd(combo_curve(np.vstack([mat[n] for n in cur])))) if cur else (0.0, 0.0)
            _, combo, r, dd, green, worst = best
            cg = team_score(combo_curve(np.vstack([mat[n] for n in cur])), days, goal)[1] if cur else 0.0
            activar = [n for n in combo if n not in cartera]
            pausar = [n for n in cartera if n not in combo]
            perfil = "es más conservadora" if dd < cdd - 0.01 else ("es más arriesgada" if dd > cdd + 0.01 else "tiene un riesgo parecido")
            txt = (f"Para el mes que viene te recomiendo {names(combo)}. Desde el {days[0].strftime('%d/%m')} esta combinación habría acabado en verde "
                   f"el {green * 100:.0f} % de las semanas (tu objetivo: {goal['semanas_en_verde_pct']} %), con su peor semana en {pc(worst)} y {pc(r)} en total "
                   f"(caída máxima del {dd * 100:.0f} %). Tu cartera actual: {cg * 100:.0f} % de semanas en verde y {pc(cr)}; la nueva {perfil}.")
            if activar:
                txt += f" Activa a {names(activar)}."
            if pausar:
                txt += f" Pausa a {names(pausar)}."
            if not activar and not pausar:
                txt += " Tu cartera actual ya es la mejor combinación: no cambies nada."
            if len(days) < 45:
                txt += f" Ojo: solo hay {len(days)} días de datos, todavía es pronto para fiarse."
            rec = dict(combo=list(combo), ret=r, dd=dd, semanas_verde=green, peor_semana=worst, activar=activar, pausar=pausar, texto=txt, desde=days[0].isoformat())

    return dict(mes=ms.strftime("%Y-%m"), titulo=ms.strftime("%m/%Y"), cartera=cartera, cartera_txt=cartera_txt,
                ret_cartera=ret_cart, capital=capital, filas=rows, conclusiones=insights, recomendacion=rec,
                generado=ac.today.isoformat())


MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def month_name(key):
    y, m = map(int, key.split("-"))
    return f"{MESES[m - 1]} de {y}"


def maybe_report(ac):
    """Si ha terminado un mes sin informe, lo genera, lo guarda y avisa al móvil."""
    target = pending_month(ac.state, ac.daily.ts[-1].date())
    if target is None:
        return None
    rep = build_report(ac, target)
    if rep is None:
        ac.state.setdefault("informes", []).append(dict(mes=target.strftime("%Y-%m"), vacio=True))
        return None
    ac.state.setdefault("informes", []).append(rep)
    head = rep["conclusiones"][0] if rep["conclusiones"] else ""
    rec = rep["recomendacion"]["texto"] if rep["recomendacion"] else ""
    ac.notify(f"Informe de {month_name(rep['mes'])}", f"Tu cartera: {pc(rep['ret_cartera'])}. {head} {rec}".strip())
    return rep
