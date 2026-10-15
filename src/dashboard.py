"""Genera el panel docs/index.html (una página estática pensada para el móvil)."""
import html
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
    if not vals or len(vals) < 2:
        return ""
    lo, hi = min(min(vals), cap), max(max(vals), cap)
    rng = (hi - lo) or 1
    W, H = 300, 34
    pts = " ".join(f"{i * W / (len(vals) - 1):.1f},{H - 2 - (v - lo) / rng * (H - 4):.1f}" for i, v in enumerate(vals))
    base = H - 2 - (cap - lo) / rng * (H - 4)
    col = "var(--up)" if up else "var(--down)"
    return (f'<svg class="spark" viewBox="0 0 {W} {H}" preserveAspectRatio="none" aria-hidden="true">'
            f'<line x1="0" x2="{W}" y1="{base:.1f}" y2="{base:.1f}" stroke="var(--line)" stroke-dasharray="3 3" fill="none"/>'
            f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="1.6" vector-effect="non-scaling-stroke"/></svg>')


def pill(status):
    lbl, cls = STATUS.get(status, (status, "wait"))
    return f'<span class="pill {cls}">{e(lbl)}</span>'


def card(ag, cfg, gold=False, compact=False):
    p = ag.get("paper") or {}
    cap = cfg["saldo_inicial_eur"]
    days, total = p.get("days", 0), cfg["simulado"]["dias"]
    final, ret = p.get("final", cap), p.get("ret", 0.0)
    pos = p.get("posicion")
    pos_txt = "" if pos is None else ("dentro de BTC" if pos > 0.05 else "fuera, en euros")
    exam = ag.get("exam", {})
    return f"""<article class="card{' gold' if gold else ''}">
  <div class="top"><span class="name">{e(ag['name'])} {pill(ag['status'])}</span><span class="eq {'up' if ret >= 0 else 'down'}">{eur(final)}</span></div>
  <p class="desc"><strong>{e(ag['label'])}</strong> · {e(ag.get('tf_label', ''))} · {e(ag.get('personalidad', ''))}{'' if compact else '<br>' + e(ag.get('desc', ''))}</p>
  {'' if compact else spark(p.get('eq', []), cap, ret >= 0)}
  <div class="bar" aria-label="Día {days} de {total}"><i style="width:{min(100, days / total * 100):.0f}%"></i></div>
  <div class="meta"><span>día {days} de {total}</span><span>{pct(ret)}</span><span>caída máx {p.get('maxdd', 0) * 100:.0f} %</span><span>{p.get('trades', 0)} operaciones</span>{f'<span>{pos_txt}</span>' if pos_txt else ''}<span>examen {pct(exam.get('ret', 0))}</span></div>
</article>"""


MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def month_name(key):
    y, m = map(int, key.split("-"))
    return f"{MESES[m - 1]} de {y}"


def report_html(rep, open_=True):
    rows = "".join(
        f"<tr><td><strong>{e(r['name'])}</strong>{' <span class=muted>(pausado)</span>' if r.get('pausado') else ''}<br><span class='muted'>{e(r['label'])} · {e(r['tf'])}</span></td>"
        f"<td class='num {'up' if r['ret'] >= 0 else 'down'}'>{pct(r['ret'])}<br>{eur(r['pnl'])}</td>"
        f"<td class='num'>{r['trades']}{(f' ({r["lost"]} perdida)' if r['lost'] == 1 else f' ({r["lost"]} perdidas)') if r['lost'] else ''}</td></tr>" for r in rep["filas"])
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
    return f"""<section><h2>Cómo están aprendiendo</h2><div class="learn">
<div class="step"><span class="n mono">{len(own)}</span><span class="lbl">de {len(done)} eligieron su estrategia propia</span></div>
<div class="step"><span class="n mono">{len(own_pass)}</span><span class="lbl">con estrategia propia aprobaron</span></div>
<div class="step"><span class="n mono">{len(kn_pass)}</span><span class="lbl">con estrategia conocida aprobaron</span></div>
</div><p class="muted" style="font-size:.82rem">Por temporalidad: {e(tf_txt)}.</p></section>"""


def build(root, ac):
    st, cfg = ac.state, ac.cfg
    agents = st["agents"]
    by = lambda s: [a for a in agents if a["status"] == s]  # noqa: E731
    listos = sorted(by("listo"), key=lambda a: -a.get("paper", {}).get("ret", 0))
    sim = sorted(by("simulado"), key=lambda a: -a.get("paper", {}).get("ret", 0))
    cola, esperando = by("cola"), by("esperando")
    suspendidos, retirados = by("suspendido"), by("retirado")
    recent = sorted([a for a in agents if a.get("examinado")], key=lambda a: (a["examinado"], a["name"]), reverse=True)[:20]
    news = ac.news

    sections = []
    reps = [r for r in st.get("informes", []) if not r.get("vacio")]
    if reps:
        sections.append(report_html(reps[-1]))
    if listos:
        sections.append('<section><h2>Listos para dinero real</h2><p class="muted" style="font-size:.85rem">Superaron el examen y el simulado. Solo pasan a dinero real si tú lo decides.</p>'
                        + "".join(card(a, cfg, gold=True, compact=k >= 5) for k, a in enumerate(listos)) + "</section>")
    sections.append('<section><h2>En simulado</h2>'
                    + ("".join(card(a, cfg, compact=k >= 3) for k, a in enumerate(sim)) if sim else '<p class="empty">Ningún agente en simulado todavía.</p>')
                    + (f'<p class="muted" style="font-size:.85rem">{len(cola)} aprobados más esperan hueco.</p>' if cola else "")
                    + "</section>")
    sections.append('<section><h2>Novedades de hoy</h2>' + (
        '<ul class="news">' + "".join(f"<li>{e(n)}</li>" for n in news) + "</ul>" if news else '<p class="empty">Sin novedades: los agentes siguen operando.</p>') + "</section>")
    rows = "".join(
        f"<tr><td><strong>{e(a['name'])}</strong><br><span class='muted'>{e(a['label'])} · {e(a.get('tf', ''))}</span></td>"
        f"<td class='num {'up' if a.get('exam', {}).get('ret', 0) >= 0 else 'down'}'>{pct(a.get('exam', {}).get('ret', 0)) if a.get('exam') else '—'}</td>"
        f"<td>{pill(a['status'])}<br><span class='muted'>{e(a.get('motivo', ''))}</span></td></tr>" for a in recent)
    sections.append('<section><h2>Últimos examinados</h2><div class="tbl"><table><thead><tr><th>Agente</th><th style="text-align:right">Examen 24–25</th><th>Resultado</th></tr></thead><tbody>'
                    + rows + "</tbody></table></div></section>")
    sections.append(learning_html(agents))
    if len(reps) > 1:
        sections.append("<section><h2>Informes anteriores</h2>" + "".join(report_html(r, open_=False) for r in reversed(reps[:-1])) + "</section>")
    if esperando:
        sections.append('<section><h2>Esperando datos</h2>' + "".join(
            f'<article class="card"><div class="top"><span class="name">{e(a["name"])} {pill(a["status"])}</span></div><p class="desc">{e(a["label"])} · {e(a.get("motivo", ""))}</p></article>'
            for a in esperando) + "</section>")

    page = f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex"><title>Academia de Agentes</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>{CSS}</style></head><body><div class="wrap">
<header style="display:flex;flex-direction:column;gap:6px"><span class="eyebrow">{e(cfg['mercado'])} · actualizado {e(st.get('actualizado', ''))}</span>
<h1>Academia de Agentes</h1>
<p class="muted">BTC cerró ayer en <span class="mono">{eur(st.get('precio_btc_eur', 0))}</span>. Cada día nacen agentes nuevos, estudian estrategias conocidas e inventan la suya con 2018–21, eligen la mejor con 2022–23 y se examinan con 2024–25. Los que aprueban operan {cfg['simulado']['dias']} días con 100 € ficticios y precios reales.</p></header>
<div class="funnel">
<div class="step"><span class="n mono">{len(agents)}</span><span class="lbl">Agentes creados</span></div>
<div class="step"><span class="n mono">{len(suspendidos)}</span><span class="lbl">Suspendidos en el examen</span></div>
<div class="step"><span class="n mono">{len(sim) + len(cola)}</span><span class="lbl">En simulado o en cola</span></div>
<div class="step{' gold' if listos else ''}"><span class="n mono">{len(listos)}</span><span class="lbl">Listos para dinero real</span></div>
</div>
{''.join(sections)}
<section class="foot">
<p>{len(retirados)} agentes retirados tras el simulado. Previsiones de Kronos: {e(', '.join(f'{k} {v * 100:.0f} %' for k, v in (st.get('kronos_cobertura') or {}).items()) or 'todavía ninguna')} (los agentes las usan al llegar al 90 %).</p>
<p>Comisiones de Bitvavo descontadas: {str(cfg['comision_pct']).replace('.', ',')} % por orden más {str(cfg['deslizamiento_pct']).replace('.', ',')} % de deslizamiento. Datos hasta el {e(st.get('ultimo_dia_con_datos', ''))}.</p>
<p>Todo es dinero ficticio. Resultados pasados no garantizan resultados futuros.</p>
</section></div></body></html>"""
    os.makedirs(os.path.join(root, "docs"), exist_ok=True)
    with open(os.path.join(root, "docs", "index.html"), "w") as f:
        f.write(page)
