"""Genera el panel docs/index.html (una página estática pensada para el móvil)."""
import html
import json
import os

STATUS = {
    "listo": ("Listo para dinero real", "ok"),
    "simulado": ("En simulado", "live"),
    "cola": ("Aprobado, en cola", "live"),
    "suspendido": ("Suspendido", "ko"),
    "retirado": ("Retirado", "ko"),
    "esperando": ("Esperando datos", "wait"),
}

CSS = """
:root{--bg:#EEF1F4;--surface:#FFFFFF;--ink:#13202E;--muted:#5B6878;--line:#D6DCE3;--accent:#2446C7;--accent-soft:#E2E8FB;
--up:#0F7A4D;--up-soft:#DDF1E7;--down:#B4322B;--down-soft:#F8E1DF;--wait:#8A5A00;--wait-soft:#F7EBD0;
--f-display:"Bricolage Grotesque","Avenir Next",system-ui,sans-serif;--f-body:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif;--f-mono:"IBM Plex Mono",ui-monospace,Menlo,monospace;color-scheme:light}
@media (prefers-color-scheme:dark){:root{--bg:#0E141B;--surface:#161E28;--ink:#E6ECF2;--muted:#93A0AE;--line:#263241;--accent:#7D98FF;--accent-soft:#1E2950;
--up:#4CC98E;--up-soft:#123326;--down:#F07C73;--down-soft:#3A1A18;--wait:#E8B65A;--wait-soft:#33280F;color-scheme:dark}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--f-body);font-size:15px;line-height:1.5}
.wrap{max-width:760px;margin:0 auto;padding-inline:16px;padding-block:20px 48px;display:flex;flex-direction:column;gap:22px}
h1,h2{font-family:var(--f-display);margin:0;letter-spacing:-.01em;text-wrap:balance}h1{font-size:1.9rem;line-height:1.1}h2{font-size:1.15rem}
p{margin:0}.muted{color:var(--muted)}.mono{font-family:var(--f-mono);font-variant-numeric:tabular-nums}
.eyebrow{font-family:var(--f-mono);font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.funnel{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:6px}
.step{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:10px;display:flex;flex-direction:column;gap:4px;min-width:0}
.step .n{font-family:var(--f-display);font-size:1.6rem;font-weight:700;line-height:1}.step .lbl{font-size:.78rem;color:var(--muted);line-height:1.3}
.step.gold{border-color:var(--up);background:var(--up-soft)}
@media (max-width:520px){.funnel{grid-template-columns:repeat(2,minmax(0,1fr))}}
section{display:flex;flex-direction:column;gap:10px}
.card{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:12px 14px;display:flex;flex-direction:column;gap:8px}
.card.gold{border-color:var(--up)}
.top{display:flex;gap:10px;align-items:baseline;justify-content:space-between;flex-wrap:wrap}
.name{font-family:var(--f-display);font-weight:700;font-size:1.05rem;display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.eq{font-family:var(--f-mono);font-variant-numeric:tabular-nums;font-size:1.05rem;font-weight:500}
.desc{font-size:.82rem;color:var(--muted);line-height:1.35}
.meta{display:flex;gap:6px 14px;flex-wrap:wrap;font-size:.78rem;color:var(--muted);font-family:var(--f-mono)}
.bar{height:5px;border-radius:3px;background:var(--line);overflow:hidden}.bar i{display:block;height:100%;background:var(--accent)}
.pill{font-family:var(--f-body);font-size:.7rem;font-weight:600;padding:2px 8px;border-radius:999px}
.pill.ok{background:var(--up-soft);color:var(--up)}.pill.ko{background:var(--down-soft);color:var(--down)}.pill.live{background:var(--accent-soft);color:var(--accent)}.pill.wait{background:var(--wait-soft);color:var(--wait)}
.up{color:var(--up)}.down{color:var(--down)}
svg.spark{width:100%;height:34px;display:block}
ul.news{margin:0;padding-left:18px;font-size:.88rem;display:flex;flex-direction:column;gap:4px}
.tbl{overflow-x:auto;border:1px solid var(--line);border-radius:8px;background:var(--surface)}
table{border-collapse:collapse;width:100%;font-size:.8rem}th,td{padding:7px 10px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--muted);font-weight:500;font-size:.72rem;text-transform:uppercase;letter-spacing:.06em}td.num{font-family:var(--f-mono);text-align:right;white-space:nowrap}
.foot{font-size:.8rem;color:var(--muted);display:flex;flex-direction:column;gap:6px;max-width:66ch}
.report{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:16px;display:flex;flex-direction:column;gap:12px}
.report ul{margin:0;padding-left:18px;display:flex;flex-direction:column;gap:8px;font-size:.9rem;max-width:64ch}
.rec{border-left:3px solid var(--accent);padding:8px 12px;background:var(--accent-soft);border-radius:0 8px 8px 0;font-size:.92rem;max-width:64ch}
details summary{cursor:pointer;font-weight:600;font-size:.9rem}
.learn{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}
@media (max-width:520px){.learn{grid-template-columns:1fr}}
.weeks{display:flex;flex-direction:column;gap:4px}
.wk{display:grid;grid-template-columns:7.5rem 1fr 6.5rem;gap:8px;align-items:center;font-size:.8rem}
.wk .track{height:10px;position:relative;background:transparent}
.wk .track i{position:absolute;top:0;height:100%;border-radius:3px}
.wk .track::before{content:"";position:absolute;left:50%;top:-2px;bottom:-2px;border-left:1px solid var(--line)}
.alert{background:var(--wait-soft);border:1px solid var(--wait);border-radius:12px;padding:12px 14px;display:flex;flex-direction:column;gap:4px}
.alert .t{font-weight:600}.alert p{font-size:.88rem;max-width:64ch}
.team{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:14px;display:flex;flex-direction:column;gap:12px}
.team.lead{border-color:var(--up);box-shadow:0 0 0 1px var(--up) inset}
.big{font-family:var(--f-display);font-size:2rem;font-weight:700;line-height:1}
.kpis{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}
.kpi{background:var(--bg);border-radius:8px;padding:8px;display:flex;flex-direction:column;gap:2px;min-width:0}
.kpi b{font-family:var(--f-mono);font-size:.95rem;font-weight:500}.kpi span{font-size:.72rem;color:var(--muted);line-height:1.25}
.stack{display:flex;height:14px;border-radius:7px;overflow:hidden;background:var(--line)}
.stack i{display:block;height:100%}
.legend{display:flex;flex-wrap:wrap;gap:4px 12px;font-size:.78rem}
.legend span{display:inline-flex;align-items:center;gap:5px}.legend i{width:9px;height:9px;border-radius:2px;display:inline-block}
.members{display:flex;flex-direction:column;gap:4px;font-size:.82rem}
.member{display:grid;grid-template-columns:1fr auto;gap:8px;padding:6px 0;border-top:1px solid var(--line)}
.markets{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:6px}
@media (max-width:520px){.markets{grid-template-columns:repeat(2,minmax(0,1fr))}}
.empty{font-size:.88rem;color:var(--muted);padding:12px 14px;border:1px dashed var(--line);border-radius:12px}
"""


def e(x):
    return html.escape(str(x))


def eur(v):
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s + " €"


def pct(v):
    return f"{v * 100:+.1f} %".replace(".", ",")


def spark(vals, cap, up):
    if not vals or len(vals) < 7:  # con menos de una semana el gráfico solo enseña ruido
        return ""
    lo, hi = min(min(vals), cap * 0.95), max(max(vals), cap * 1.05)  # escala mínima de ±5 % para no exagerar céntimos
    rng = (hi - lo) or 1
    W, H = 300, 34
    pts = " ".join(f"{i * W / (len(vals) - 1):.1f},{H - 2 - (v - lo) / rng * (H - 4):.1f}" for i, v in enumerate(vals))
    base = H - 2 - (cap - lo) / rng * (H - 4)
    col = "var(--up)" if up else "var(--down)"
    return (f'<svg class="spark" viewBox="0 0 {W} {H}" preserveAspectRatio="none" aria-hidden="true">'
            f'<line x1="0" x2="{W}" y1="{base:.1f}" y2="{base:.1f}" stroke="var(--line)" stroke-dasharray="3 3" fill="none"/>'
            f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="1.6" vector-effect="non-scaling-stroke"/></svg>')


def asset(ag):
    a = ag.get("activo", "BTC-EUR").split("-")[0]
    return "Oro" if a == "PAXG" else a


def price_txt(p):
    return eur(p) if p >= 10 else f"{p:.4f} €".replace(".", ",")


def pill(status):
    lbl, cls = STATUS.get(status, (status, "wait"))
    return f'<span class="pill {cls}">{e(lbl)}</span>'


def card(ag, cfg, gold=False, compact=False):
    p = ag.get("paper") or {}
    cap = cfg["saldo_inicial_eur"]
    days, total = p.get("days", 0), cfg["simulado"]["dias"]
    final, ret = p.get("final", cap), p.get("ret", 0.0)
    pos = p.get("posicion")
    pos_txt = "" if pos is None else ("comprado" if pos > 0.05 else "en corto" if pos < -0.05 else "fuera, en euros")
    exam = ag.get("exam", {})
    return f"""<article class="card{' gold' if gold else ''}">
  <div class="top"><span class="name">{e(ag['name'])} {pill(ag['status'])}</span><span class="eq {'up' if ret >= 0 else 'down'}">{eur(final)}</span></div>
  <p class="desc"><strong>{e(ag['label'])}</strong> · {e(asset(ag))} · {e(ag.get('tf_label', ''))} · {e(ag.get('personalidad', ''))}{'' if compact else '<br>' + e(ag.get('desc', ''))}{'' if compact or not ag.get('ideas_internet') else '<br><span class=muted>Estudió de internet: ' + e(', '.join(ag['ideas_internet'])) + '</span>'}{'' if compact or not ag.get('padres') else '<br><span class=muted>Hijo de: ' + e(', '.join(ag['padres'])) + '</span>'}{'' if compact or not ag.get('entreno_con') else '<br><span class=muted>Entrenó con la historia de ' + e(ag['entreno_con'].split('-')[0]) + ' (su mercado no tiene esos años)</span>'}</p>
  {'' if compact else spark(p.get('eq', []), cap, ret >= 0)}
  <div class="bar" aria-label="Día {days} de {total}"><i style="width:{min(100, days / total * 100):.0f}%"></i></div>
  <div class="meta"><span>día {days} de {total}</span><span>{pct(ret)}</span><span>caída máx {p.get('maxdd', 0) * 100:.0f} %</span><span>{p.get('trades', 0)} operaciones</span>{f'<span>{pos_txt}</span>' if pos_txt else ''}<span>examen {pct(exam.get('ret', 0))}</span></div>
</article>"""


MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def month_name(key):
    y, m = map(int, key.split("-"))
    return f"{MESES[m - 1]} de {y}"


def lost_txt(n):
    if not n:
        return ""
    return f" ({n} perdida)" if n == 1 else f" ({n} perdidas)"


def report_html(rep, open_=True):
    rows = "".join(
        f"<tr><td><strong>{e(r['name'])}</strong>{' <span class=muted>(pausado)</span>' if r.get('pausado') else ''}<br><span class='muted'>{e(r['label'])} · {e(r['tf'])}</span></td>"
        f"<td class='num {'up' if r['ret'] >= 0 else 'down'}'>{pct(r['ret'])}<br>{eur(r['pnl'])}</td>"
        f"<td class='num'>{r['trades']}{lost_txt(r['lost'])}</td></tr>" for r in rep["filas"])
    rec = rep.get("recomendacion")
    body = f"""<p class="muted" style="font-size:.85rem">Tu cartera ({e(rep['cartera_txt'])}: {e(', '.join(rep['cartera']))}) terminó el mes en <strong class="{'up' if rep['ret_cartera'] >= 0 else 'down'}">{pct(rep['ret_cartera'])}</strong> sobre {eur(rep['capital'])} ficticios.</p>
<ul>{''.join(f'<li>{e(c)}</li>' for c in rep['conclusiones'])}</ul>
{f'<p class="rec"><strong>Recomendación:</strong> {e(rec["texto"])}</p>' if rec else ''}
<div class="tbl"><table><thead><tr><th>Agente</th><th style="text-align:right">Mes</th><th style="text-align:right">Operaciones</th></tr></thead><tbody>{rows}</tbody></table></div>
<p class="muted" style="font-size:.78rem">Para pausar o activar agentes, cambia la lista "pausados" en config.json. La recomendación mira los últimos meses, no solo este, porque lo que mejor fue un mes no suele repetirse el siguiente.</p>"""
    title = f"Informe de {month_name(rep['mes'])}"
    if open_:
        return f'<section class="report"><h2>{title}</h2>{body}</section>'
    return f'<details class="report"><summary>{title}</summary>{body}</details>'


def learning_html(agents):
    done = [a for a in agents if a.get("eleccion")]
    if not done:
        return ""
    own = [a for a in done if a["eleccion"] == "propia"]
    own_pass = [a for a in own if a["status"] not in ("suspendido",)]
    kn_pass = [a for a in done if a["eleccion"] == "conocida" and a["status"] not in ("suspendido",)]
    by_tf = {}
    for a in done:
        t = by_tf.setdefault(a["tf"], [0, 0])
        t[0] += 1
        t[1] += a["status"] != "suspendido"
    tf_txt = " · ".join(f"{k}: {v[1]} de {v[0]} aprueban" for k, v in sorted(by_tf.items()))
    dia = [a for a in done if a.get("estilo") == "diario"]
    dia_txt = f" Operadores diarios: {len(dia)} creados, {sum(a['status'] != 'suspendido' for a in dia)} aprobados." if dia else ""
    tf_txt += "." + dia_txt
    return f"""<section><h2>Cómo están aprendiendo</h2><div class="learn">
<div class="step"><span class="n mono">{len(own)}</span><span class="lbl">de {len(done)} eligieron su estrategia propia</span></div>
<div class="step"><span class="n mono">{len(own_pass)}</span><span class="lbl">con estrategia propia aprobaron</span></div>
<div class="step"><span class="n mono">{len(kn_pass)}</span><span class="lbl">con estrategia conocida aprobaron</span></div>
</div><p class="muted" style="font-size:.82rem">Por temporalidad: {e(tf_txt)}</p></section>"""


def btc_change_since(ac, day):
    mk = ac.daily
    try:
        i = mk.idx(day) - 1  # cierre del día anterior al inicio
        return float(mk.I.c[-1] / mk.I.c[max(i, 0)] - 1)
    except Exception:  # noqa: BLE001
        return None


def estado_txt(a):
    p = a.get("paper") or {}
    pos = p.get("posicion") or 0
    if abs(pos) > 0.05:
        tipo = "compra" if pos > 0 else "corto"
        compras = [t for t in p.get("last_trades", []) if t["tipo"] == tipo]
        if compras:
            t = compras[-1]
            f = t["fecha"]
            verbo = "compró" if pos > 0 else "vendió en corto (gana si baja)"
            return f"operación abierta: {verbo} el {f[8:10]}/{f[5:7]} a {t['precio']:,.0f} €".replace(",", ".")
        return "operación abierta"
    cerradas = [t for t in p.get("last_trades", []) if t.get("resultado") is not None]
    if cerradas:
        r = cerradas[-1]["resultado"]
        return f"esperando señal (última operación: {'+' if r >= 0 else '−'}{abs(r):.2f} €)".replace(".", ",")
    return "esperando señal, aún no ha operado"


def sim_html(ac, sim, cola, cfg):
    if not sim:
        return '<section><h2>Ganadores</h2><p class="empty">Ningún agente en simulado todavía.</p></section>'
    rets = [(a, a.get("paper", {}).get("ret", 0.0), a.get("paper", {}).get("trades", 0)) for a in sim]
    win = [a for a, r, _ in rets if r > 0.001]
    lose = [a for a, r, _ in rets if r < -0.001]
    wait = [a for a, r, t in rets if abs(r) <= 0.001]
    first = min(a["paper_start"] for a in sim)
    btc = btc_change_since(ac, first)
    btc_txt = f" BTC {'ha subido' if btc >= 0 else 'ha bajado'} un {abs(btc) * 100:.1f} % desde el {first[8:10]}/{first[5:7]}, cuando empezó el simulado.".replace(".", ",", 1) if btc is not None else ""
    out = ['<section><h2>Ganadores</h2>',
           f'<div class="learn"><div class="step"><span class="n mono up">{len(win)}</span><span class="lbl">ganando</span></div>'
           f'<div class="step"><span class="n mono">{len(wait)}</span><span class="lbl">sin operar aún, con sus 100 € intactos</span></div>'
           f'<div class="step"><span class="n mono down">{len(lose)}</span><span class="lbl">por debajo de 100 € (casi todos con la operación aún abierta)</span></div></div>']
    if win:
        out.append("".join(card(a, cfg, gold=k == 0, compact=k >= 3) for k, a in enumerate(sorted(win, key=lambda a: -a["paper"]["ret"])[:10])))
    else:
        out.append(f'<p class="empty">Todavía ningún agente va en positivo.{e(btc_txt)} Los que están por debajo de 100 € tienen casi todos la operación todavía abierta: el saldo se recalcula cada día al precio actual y aún puede acabar en ganancia o pérdida.</p>')
    rows = "".join(
        f"<tr><td><strong>{e(a['name'])}</strong><br><span class='muted'>{e(a['label'])} · {e(asset(a))} · {e(a.get('tf', ''))}</span></td>"
        f"<td class='num'>día {a.get('paper', {}).get('days', 0)}</td>"
        f"<td class='num {'up' if a.get('paper', {}).get('ret', 0) > 0.001 else 'down' if a.get('paper', {}).get('ret', 0) < -0.001 else ''}'>{eur(a.get('paper', {}).get('final', 100))}<br>{pct(a.get('paper', {}).get('ret', 0))}</td>"
        f"<td>{e(estado_txt(a))}</td></tr>"
        for a in sorted(sim, key=lambda a: -a.get("paper", {}).get("ret", 0)))
    out.append(f'<details class="report"><summary>Ver los {len(sim)} agentes en simulado</summary><div class="tbl"><table><thead><tr><th>Agente</th><th style="text-align:right">Progreso</th><th style="text-align:right">Saldo</th><th>Ahora</th></tr></thead><tbody>{rows}</tbody></table></div></details>')
    if cola:
        out.append(f'<p class="muted" style="font-size:.85rem">{len(cola)} aprobados más esperan hueco.</p>')
    out.append("</section>")
    return "".join(out)


ASSET_COL = {"BTC": "#F2A900", "ETH": "#6F7CF2", "SOL": "#14B88A", "XRP": "#3B8FD9", "EUR": "var(--line)"}


def team_card(tm, cfg, agents_by_id, lead=False):
    from equipos import PRUDENCIAS, TIPOS
    info = TIPOS.get(tm["id"], dict(nombre=tm["id"], puesto=0))
    if not tm.get("periodos"):
        return (f'<article class="team"><div class="top"><span class="name">{e(info["nombre"])}</span><span class="pill wait">Sin equipo todavía</span></div>'
                f'<p class="desc">{e(tm.get("vacio", ""))} Se vuelve a buscar cada día con los agentes nuevos.</p></article>')
    cap0 = tm["capital_inicial"]
    v = tm.get("valor", cap0)
    st = tm.get("stats", {})
    wk = tm.get("semanas", [])
    done = [w for w in wk if w["completa"]]
    cur = wk[-1] if wk else None
    per = tm["periodos"][-1]
    ini = tm["inicio"]
    # reparto del dinero ahora
    ahora = tm.get("ahora") or []
    by_asset = {}
    for m in ahora:
        a = m["activo"].split("-")[0]
        by_asset[a] = by_asset.get(a, 0) + m["invertido"]
    invested = sum(by_asset.values())
    by_asset["EUR"] = max(0.0, v - invested)
    bar = "".join(f'<i style="width:{x / v * 100:.1f}%;background:{ASSET_COL.get(a, "var(--accent)")}" title="{e(a)}"></i>' for a, x in by_asset.items() if v and x > 0.01)
    legend = "".join(f'<span><i style="background:{ASSET_COL.get(a, "var(--accent)")}"></i>{e("En euros" if a == "EUR" else a)} {eur(x)}</span>' for a, x in by_asset.items() if x > 0.01)
    contrib = tm.get("aportacion", {})
    rows = []
    for m in ahora:
        a = agents_by_id.get(m["id"], {})
        estado = (f"operación abierta · {m.get('prob', 0) * 100:.0f} % de probabilidad de ganar, suele ganar un {m.get('ganancia', 0) * 100:.1f} %".replace(".", ",")
                  if m["posicion"] > 0.05 else "esperando señal")
        c = contrib.get(m["id"])
        rows.append(f'<div class="member"><span><strong>{e(m["name"])}</strong> <span class="muted">· {e(m["activo"].split("-")[0])} · {e(m["tf"])} · {e(a.get("label", ""))}</span><br>'
                    f'<span class="muted">{e(estado)}{"" if c is None else " · ha aportado " + ("+" if c >= 0 else "−") + eur(abs(c))}</span></span>'
                    f'<span class="mono" style="text-align:right">{eur(m["euros"])}</span></div>')
    p1, p2 = per["pruebas"]["p1"], per["pruebas"]["p2"]
    prm = per["params"]
    how = [f"prudencia {prm.get('prudencia', 1)}: prioriza las operaciones abiertas por probabilidad{'' if prm.get('prudencia', 1) == 1 else '^' + str(prm.get('prudencia'))} × ganancia",
           f"los que esperan señal se guardan un {prm.get('reserva', 0) * 100:.0f} % para poder entrar",
           f"nadie maneja más del {prm['cap'] * 100:.0f} % de la cartera"]
    weeks_rows = []
    mx = max([abs(w["pct"]) for w in wk[-8:]] + [0.002])
    for w in reversed(wk[-8:]):
        width = min(50, abs(w["pct"]) / mx * 50)
        left = 50 if w["pct"] >= 0 else 50 - width
        col = "var(--up)" if w["eur"] >= 0 else "var(--down)"
        lbl = f"{w['inicio'][8:10]}/{w['inicio'][5:7]}" if w["completa"] else "esta semana"
        weeks_rows.append(f'<div class="wk"><span class="mono muted">{e(lbl)}</span><span class="track"><i style="left:{left:.1f}%;width:{width:.1f}%;background:{col}"></i></span>'
                          f'<span class="mono {"up" if w["eur"] >= 0 else "down"}" style="text-align:right">{"+" if w["eur"] >= 0 else "−"}{eur(abs(w["eur"]))}</span></div>')
    green = sum(w["pct"] > 0.0001 for w in done)
    red = len(done) - green  # igual o pérdidas = semana mala
    # lo que ha aportado cada mercado sobre los 100 € del equipo
    per_asset = {}
    for i, c in contrib.items():
        a = asset(agents_by_id.get(i, {}))
        per_asset[a] = per_asset.get(a, 0.0) + c
    asset_rows = "".join(f'<div class="kpi"><b class="{"up" if c >= 0 else "down"}">{"+" if c >= 0 else "−"}{eur(abs(c))}</b><span>{e(a)} · {pct(c / cap0)} sobre {eur(cap0)}</span></div>'
                         for a, c in sorted(per_asset.items(), key=lambda x: -x[1]))
    miembros_txt = ", ".join(f"{m['name']} ({m['activo'].split('-')[0]})" for m in ahora)
    return f"""<article class="team{' lead' if lead else ''}">
<div class="top"><span class="name">{e(info['nombre'])} <span class="pill live">{info['puesto']}º en la prueba de 2026</span>{' <span class="pill ok">va primero</span>' if lead else ''}</span></div>
<p class="muted" style="font-size:.8rem">Prudencia {per['params'].get('prudencia', 1)} · {e(PRUDENCIAS.get(per['params'].get('prudencia', 1), ''))}.
{(' <span class="down">En 2026 no cumplió todas las condiciones: ' + e(per['cumple']) + '.</span>') if per.get('cumple') else ' <span class="up">En 2026 cumplió todas las condiciones.</span>'}</p>
<div class="top"><span class="big mono {'up' if v >= cap0 else 'down'}">{eur(v)}</span><span class="mono {'up' if v >= cap0 else 'down'}">{pct(v / cap0 - 1)} desde el {ini[8:10]}/{ini[5:7]}</span></div>
<p class="muted" style="font-size:.78rem">Empezó con {eur(cap0)} ficticios. Las semanas cuentan de lunes a domingo y solo cuando están completas.</p>
{spark(tm.get('curva', []), cap0, v >= cap0)}
<p style="font-size:.88rem"><strong>Formado por:</strong> {e(miembros_txt)}</p>
<div class="kpis"><div class="kpi"><b class="{'' if not cur or abs(cur['eur']) < 0.005 else 'up' if cur['eur'] > 0 else 'down'}">{(('+' if cur['eur'] >= 0 else '−') + eur(abs(cur['eur'])) + ' (' + pct(cur['pct']) + ')') if cur else '0,00 €'}</b><span>esta semana, acumulado</span></div>
<div class="kpi"><b class="up">{green}</b><span>semanas ganando</span></div>
<div class="kpi"><b class="down">{red}</b><span>semanas igual o perdiendo</span></div></div>
{('<div><p class="eyebrow" style="margin-bottom:6px">Qué ha aportado cada mercado</p><div class="kpis">' + asset_rows + '</div></div>') if asset_rows else ''}
<div><p class="eyebrow" style="margin-bottom:6px">Dónde está el dinero ahora</p><div class="stack">{bar}</div><div class="legend" style="margin-top:6px">{legend}</div></div>
<div class="members"><p class="eyebrow">Miembros y dinero que maneja cada uno</p>{''.join(rows)}</div>
{'<div class="weeks">' + ''.join(weeks_rows) + '</div>' if weeks_rows else ''}
<details><summary>Cómo se eligió este equipo</summary><div style="display:flex;flex-direction:column;gap:6px;margin-top:8px;font-size:.85rem">
<p>1) Pasaron todos los agentes que ganaron dinero en su examen de 2024–25. 2) Con ellos se formaron equipos usando solo 2024–25, con cada grado de prudencia y forma de repartir. 3) Cada equipo hizo la prueba de 2026 (enero–hoy). 4) Se quedaron los 3 mejores: primero los que más semanas ganaron y, entre parecidos, el que más ganó.</p>
<p class="mono" style="font-size:.8rem">2024–25: {pct(p1['ret'])} · ganó el {p1['verde'] * 100:.0f} % de las semanas · peor semana {pct(p1['peor'])}<br>2026: {pct(p2['ret'])} · ganó el {p2['verde'] * 100:.0f} % de las semanas · peor semana {pct(p2['peor'])}</p>
<p>Reparto: {e('; '.join(how))}. Cada día al cierre se reparte de nuevo (moverlo cuesta comisiones, ya descontadas).</p>
<p class="muted">Se vuelve a elegir el día 1 de cada mes; el dinero del equipo sigue.</p></div></details>
</article>"""


def build(root, ac):
    st, cfg = ac.state, ac.cfg
    agents = st["agents"]
    by_id = {a["id"]: a for a in agents}
    by = lambda s: [a for a in agents if a["status"] == s]  # noqa: E731
    listos = sorted(by("listo"), key=lambda a: -a.get("paper", {}).get("ret", 0))
    sim = sorted(by("simulado"), key=lambda a: -a.get("paper", {}).get("ret", 0))
    cola = by("cola")
    recent = sorted([a for a in agents if a.get("examinado")], key=lambda a: (a["examinado"], a["name"]), reverse=True)[:20]
    news = ac.news
    goal = cfg.get("objetivo_equipo", {"semanas_en_verde_pct": 50, "ganancia_minima_anual_pct": 10, "caida_maxima_pct": 25, "meses": 3})
    sections = []

    # 1. avisos para Abril
    avp = os.path.join(root, "avisos", "avisos.json")
    hoy = ac.today.isoformat()
    todos = [x for x in (json.load(open(avp))["avisos"] if os.path.exists(avp) else [])
             if x.get("estado") == "pendiente" and x.get("desde", "") <= hoy]  # "desde": recordatorios que aparecen más adelante
    avisos = [x for x in todos if x["tipo"] in ("decidir", "hacer")]
    guardado = [x for x in todos if x["tipo"] in ("idea", "recordatorio")]
    futuros = [x for x in (json.load(open(avp))["avisos"] if os.path.exists(avp) else [])
               if x.get("estado") == "pendiente" and x.get("desde", "") > hoy]
    if avisos:
        sections.append('<section><h2>Avisos para Abril</h2>' + "".join(
            f'<div class="alert"><span class="t">{"🟡 Decide" if x["tipo"] == "decidir" else "🔵 Tarea"} · {e(x["titulo"])}</span><p>{e(x["texto"])}</p>'
            f'<span class="muted mono" style="font-size:.72rem">{e(x["fecha"])}</span></div>' for x in avisos) + "</section>")

    recs = [x for x in guardado if x["tipo"] == "recordatorio"]
    ideas = [x for x in guardado if x["tipo"] == "idea"]
    if recs or futuros:
        sections.append('<section><h2>Recordatorios</h2>'
                        + "".join(f'<div class="card"><strong>📌 {e(x["titulo"])}</strong><p class="desc">{e(x["texto"])}</p></div>' for x in recs)
                        + "".join(f'<div class="card"><strong>⏰ A partir del {x["desde"][8:10]}/{x["desde"][5:7]} · {e(x["titulo"])}</strong><p class="desc">{e(x["texto"])}</p></div>' for x in futuros)
                        + '</section>')
    if ideas:
        sections.append('<section><h2>Ideas pendientes</h2>'
                        + "".join(f'<div class="card"><strong>💡 {e(x["titulo"])}</strong><p class="desc">{e(x["texto"])}</p>'
                                  f'<span class="muted mono" style="font-size:.72rem">apuntada el {x["fecha"][8:10]}/{x["fecha"][5:7]}</span></div>' for x in ideas)
                        + '</section>')

    # 2. equipos
    teams = st.get("equipos") or {}
    if teams:
        from equipos import TIPOS
        order = sorted(teams.values(), key=lambda t: TIPOS.get(t["id"], {}).get("puesto", 9))  # podio: 1º, 2º, 3º
        running = [t for t in order if t.get("periodos") and t.get("dias", 0) > 0]
        lead = max(running, key=lambda t: t.get("valor", 0))["id"] if running and len({t.get("valor") for t in running}) > 1 else None
        sections.append('<section><h2>Tus equipos</h2><p class="muted" style="font-size:.85rem">Cada equipo tiene una cartera de '
                        f'{eur(cfg["saldo_inicial_eur"])} ficticios y reparte el dinero entre sus agentes (de BTC, ETH, SOL o XRP) priorizando las operaciones con más probabilidad × ganancia. '
                        f'Son el podio de la prueba de 2026. Todos buscan ganar lo máximo; solo cambia lo prudentes que son al priorizar. Condiciones que buscamos: ganar más del {goal["semanas_en_verde_pct"]} % de las semanas, '
                        f'al menos un {goal.get("ganancia_minima_anual_pct", 0)} % al año y no caer más de un {goal.get("caida_maxima_pct", 100)} %. '
                        f'Para dinero real tendrán que repetirlo aquí durante {goal["meses"]} meses.</p>'
                        + "".join(team_card(t, cfg, by_id, lead=t["id"] == lead) for t in order) + "</section>")

    # 3. mercados
    mks = st.get("mercados") or {}
    if mks:
        sections.append('<section><h2>Mercados</h2><div class="markets">' + "".join(
            f'<div class="step"><span class="lbl">{e(k.split("-")[0])}</span><span class="mono" style="font-weight:500">{price_txt(m["precio"])}</span>'
            f'<span class="mono {"up" if m["semana"] >= 0 else "down"}" style="font-size:.78rem">{pct(m["semana"])} semana</span></div>' for k, m in mks.items()) + "</div></section>")

    # 4. cantera
    assets = {}
    for a in agents:
        k = asset(a)
        t = assets.setdefault(k, [0, 0])
        t[0] += 1
        t[1] += a["status"] in ("simulado", "listo")
    cant = " · ".join(f"{k}: {v[1]} en simulado de {v[0]} creados" for k, v in sorted(assets.items(), key=lambda x: -x[1][0]))
    rows = "".join(
        f"<tr><td><strong>{e(a['name'])}</strong><br><span class='muted'>{e(asset(a))} · {e(a.get('tf', ''))} · {e(a['label'])}</span></td>"
        f"<td class='num {'up' if a.get('paper', {}).get('ret', 0) > 0.001 else 'down' if a.get('paper', {}).get('ret', 0) < -0.001 else ''}'>{pct(a.get('paper', {}).get('ret', 0))}<br><span class='muted'>día {a.get('paper', {}).get('days', 0)}</span></td>"
        f"<td>{e(estado_txt(a))}</td></tr>" for a in listos + sim)
    sections.append(f"""<section><h2>Cantera</h2><p class="muted" style="font-size:.85rem">Cada noche nacen agentes nuevos. Los que aprueban el examen de 2024–25 pueden entrar en un equipo (la prueba de 2026 la hace el equipo); los hijos, además, tienen que superar a su padre. {e(cant)}.</p>
<div class="funnel"><div class="step"><span class="n mono">{len(agents)}</span><span class="lbl">creados</span></div><div class="step"><span class="n mono">{len(sim) + len(listos)}</span><span class="lbl">aprobados (simulado)</span></div>
<div class="step"><span class="n mono">{len(cola)}</span><span class="lbl">en cola</span></div><div class="step"><span class="n mono">{len(by('suspendido'))}</span><span class="lbl">suspendidos</span></div></div>
<details class="report"><summary>Ver los {len(sim) + len(listos)} agentes aprobados</summary><div class="tbl"><table><thead><tr><th>Agente</th><th style="text-align:right">Simulado</th><th>Ahora</th></tr></thead><tbody>{rows}</tbody></table></div></details></section>""")

    # 5. novedades y el resto, plegado
    sections.append('<section><h2>Novedades de hoy</h2>' + (
        '<ul class="news">' + "".join(f"<li>{e(n)}</li>" for n in news[:15]) + "</ul>" if news else '<p class="empty">Sin novedades.</p>') + "</section>")
    rows = "".join(
        f"<tr><td><strong>{e(a['name'])}</strong><br><span class='muted'>{e(asset(a))} · {e(a.get('tf', ''))} · {e(a['label'])}</span></td>"
        f"<td class='num {'up' if a.get('exam', {}).get('ret', 0) >= 0 else 'down'}'>{pct(a.get('exam', {}).get('ret', 0)) if a.get('exam') else '—'}</td>"
        f"<td>{pill(a['status'])}<br><span class='muted'>{e(a.get('motivo', ''))}</span></td></tr>" for a in recent)
    more = ['<details class="report"><summary>Últimos examinados</summary><div class="tbl"><table><thead><tr><th>Agente</th><th style="text-align:right">Examen 24–25</th><th>Resultado</th></tr></thead><tbody>'
            + rows + "</tbody></table></div></details>"]
    reps = [r for r in st.get("informes", []) if not r.get("vacio")]
    more += [report_html(r, open_=False) for r in reversed(reps)]
    sections.append("<section><h2>Más detalle</h2>" + "".join(more) + "</section>")

    page = f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex"><title>Academia de Agentes</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>{CSS}</style></head><body><div class="wrap">
<header style="display:flex;flex-direction:column;gap:6px"><span class="eyebrow">Dinero ficticio · actualizado {e(st.get('actualizado', ''))}</span>
<h1>Academia de Agentes</h1>
<p class="muted">Equipos de agentes que operan BTC, ETH, SOL y XRP en Bitvavo con dinero ficticio, precios reales y comisiones reales.</p></header>
{''.join(sections)}
<section class="foot">
<p>{('Se opera en pares contra USDC (comisión del ' + str(cfg['usdc']['comision_pct']).replace('.', ',') + ' % más ' + str(cfg['usdc']['deslizamiento_pct']).replace('.', ',') + ' % de diferencia de precio; pasar de euros a USDC cuesta ' + str(cfg['usdc']['conversion_pct']).replace('.', ',') + ' % una vez) y todo se cuenta en euros con el cambio USDC/EUR de cada día.') if cfg.get('cotizar_en_usdc') else ('Comisiones de Bitvavo descontadas: órdenes limitadas al ' + str(cfg.get('comision_maker_pct', cfg['comision_pct'])).replace('.', ',') + ' % (si no se llenan, a mercado al ' + str(cfg['comision_pct']).replace('.', ',') + ' % más ' + str(cfg['deslizamiento_pct']).replace('.', ',') + ' % de deslizamiento).')} Datos hasta el {e(st.get('ultimo_dia_con_datos', ''))}.</p>
<p>Todo es dinero ficticio. Resultados pasados no garantizan resultados futuros.</p>
</section></div></body></html>"""
    os.makedirs(os.path.join(root, "docs"), exist_ok=True)
    with open(os.path.join(root, "docs", "index.html"), "w") as f:
        f.write(page)
