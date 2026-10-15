"""La academia: crea agentes, los forma, los examina y lleva el simulado en vivo.

Vida de un agente
  1. Nace con un nombre, una temporalidad (velas de 1 día, 4 horas o 1 hora) y una personalidad
     (prudente, equilibrada o atrevida: cuánto le importan las caídas).
  2. ESTUDIA: prueba las estrategias conocidas con los años de entreno y se queda con las mejores.
  3. INVENTA: parte de lo que mejor le funcionó y lo va perfeccionando generación a generación.
  4. ELIGE: compara su mejor estrategia conocida y la suya en los años de validación (que no usó
     para ajustar nada) y se queda con la que mejor resultado da.
  5. EXAMEN: opera los años de examen sin tocar nada.
  6. SIMULADO: si aprueba, opera con dinero ficticio y precios reales.

Estados: suspendido, cola, simulado, listo, retirado.
"""
import datetime as dt
import hashlib
import json
import os
import random
import time
import urllib.request

import numpy as np

import inventor
from backtest import run
from market import TF_LABEL
from strategies import FAMILIES, FILTERS, SIZING, STOPS, describe, signal

NAMES = ["Lucas", "Pablo", "Marcos", "Luis", "Sara", "Elena", "Irene", "Diego", "Nuria", "Hugo",
         "Alba", "Bruno", "Carla", "Dani", "Eva", "Fran", "Gala", "Héctor", "Inés", "Jaime", "Lola",
         "Mario", "Noa", "Óscar", "Paula", "Quique", "Rocío", "Sergio", "Tere", "Unai", "Vera",
         "Xavi", "Yago", "Zoe", "Adrián", "Berta", "César", "Diana", "Enzo", "Flor", "Gonzalo",
         "Iris", "Javi", "Leire", "Marta", "Nico", "Olga", "Pau", "Raquel", "Saúl", "Tomás",
         "Úrsula", "Víctor", "Alma", "Biel", "Cloe", "Darío", "Emma", "Félix", "Gemma", "Iker"]
FIRST = NAMES[:10]  # los nombres de la primera app salen primero
TEMPER = {"prudente": 2.0, "equilibrado": 1.0, "atrevido": 0.4}


def pc(x):
    return f"{x * 100:+.1f} %".replace(".", ",")


class Academia:
    def __init__(self, root, markets, kronos=None, today=None, log=print):
        self.root = root
        self.cfg = json.load(open(os.path.join(root, "config.json")))
        self.state_path = os.path.join(root, "state", "agents.json")
        self.mk = markets  # dict tf -> Market
        self.daily = markets["1d"]
        self.kronos = kronos or {}  # tf -> previsiones de Kronos alineadas con sus velas
        self.today = today or dt.datetime.now(dt.timezone.utc).date()
        self.log = log
        self.news = []
        self.state = self._load()
        self.rng = random.Random(int(self.today.strftime("%Y%m%d")) + len(self.state["agents"]))
        self._w = {}

    # ------------------------------------------------------------ utilidades
    def _load(self):
        if os.path.exists(self.state_path):
            return json.load(open(self.state_path))
        return {"agents": [], "creado": self.today.isoformat()}

    def save(self):
        os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
        self.state["actualizado"] = self.today.isoformat()
        self.state["ultimo_dia_con_datos"] = self.daily.ts[-1].date().isoformat()
        self.state["precio_btc_eur"] = round(float(self.daily.I.c[-1]), 2)
        self.state["kronos_cobertura"] = {tf: self.kronos_coverage(tf) for tf in self.cfg["kronos"]["temporalidades"] if tf in self.mk}
        with open(self.state_path, "w") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=1)

    def run_cfg(self):
        return dict(fee=self.cfg["comision_pct"], slip=self.cfg["deslizamiento_pct"], cap=self.cfg["saldo_inicial_eur"])

    def window(self, mk, key):
        a, b = self.cfg[key]
        return mk.idx(a), min(mk.end_idx(b), mk.n - 1)

    def kronos_coverage(self, tf):
        if self.kronos.get(tf) is None or tf not in self.mk:
            return 0.0
        mk = self.mk[tf]
        a, b = self.window(mk, "entreno")[0], self.window(mk, "examen")[1]
        return round(float(np.mean(~np.isnan(self.kronos[tf]["med"][a:b + 1]))), 3)

    def kr_for(self, tf):
        ok = self.cfg["fabrica"]["usar_kronos"] and self.kronos_coverage(tf) > 0.9
        return self.kronos[tf] if ok else None

    def new_name(self):
        used = {x["name"] for x in self.state["agents"]}
        for n in FIRST:
            if n not in used:
                return n
        free = [n for n in NAMES if n not in used]
        if free:
            return self.rng.choice(free)
        k = 2
        while True:
            for n in NAMES:
                if f"{n} {k}" not in used:
                    return f"{n} {k}"
            k += 1

    def notify(self, title, msg):
        self.news.append(f"{title}: {msg}")
        topic = os.environ.get("NTFY_TOPIC")
        if not topic:
            return
        try:
            body = json.dumps(dict(topic=topic, title=title, message=msg, tags=["chart_with_upwards_trend"])).encode()
            req = urllib.request.Request("https://ntfy.sh/", data=body, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=15)
        except Exception as e:  # noqa: BLE001
            self.log(f"Aviso: no se pudo enviar la notificación ({e})")

    def exposure(self, ag):
        """Exposición (0..1) de un agente en todas las velas de su temporalidad."""
        if ag["id"] not in self._w:
            mk = self.mk[ag["tf"]]
            kr = self.kr_for(ag["tf"])
            if ag["eleccion"] == "propia":
                w = inventor.exposure(mk.I, ag["regla"], kr, mk.bpd)
            else:
                w = signal(mk.I, ag["genome"], ag["params"], kr)
            self._w[ag["id"]] = w
        return self._w[ag["id"]]

    # ------------------------------------------------------------ formación
    def study(self, mk, temper, kr):
        """Prueba las estrategias conocidas en el entreno. Devuelve las 3 mejores [(puntos, genoma, params, resultado)]."""
        cfg = self.run_cfg()
        a, b = self.window(mk, "entreno")
        years = (b - a + 1) / (365 * mk.bpd)
        fams = [f for f in FAMILIES if f != "kronos" or kr is not None]
        found = []
        for f in fams:  # 1) cada familia con su rejilla de parámetros
            best = None
            g = dict(family=f, filter="ninguno", stop=0, sizing="completo")
            for p in FAMILIES[f]["grid"]:
                r = run(mk.I, signal(mk.I, g, p, kr), a, b, cfg)
                s = inventor.score(r, cfg["cap"], years, temper)
                if best is None or s > best[0]:
                    best = (s, g, p, r)
            found.append(best)
        found.sort(key=lambda t: -t[0])
        extra = []
        for s0, g0, p, _ in found[:3]:  # 2) a las 3 mejores les prueba filtros, stops y tamaño
            for fl in FILTERS:
                for st in STOPS:
                    for sz in SIZING:
                        g = dict(family=g0["family"], filter=fl, stop=st, sizing=sz)
                        if g == g0:
                            continue
                        r = run(mk.I, signal(mk.I, g, p, kr), a, b, cfg)
                        extra.append((inventor.score(r, cfg["cap"], years, temper), g, p, r))
        allc = sorted(found + extra, key=lambda t: -t[0])
        return allc[:3], len(found) and sum(len(FAMILIES[f]["grid"]) for f in fams) + len(extra)

    def school(self, ag):
        cfg = self.run_cfg()
        mk = self.mk[ag["tf"]]
        kr = self.kr_for(ag["tf"])
        temper = TEMPER[ag["personalidad"]]
        u = "días" if mk.bpd == 1 else "velas"

        # 2. estudia
        top, n_tested = self.study(mk, temper, kr)
        s_known, g, p, r_known = top[0]

        # 3. inventa a partir de su experiencia
        seeds = []
        for _, g2, p2, _ in top:
            rule = inventor.seed_from_family(g2["family"], p2, mk.bpd)
            rule["stop"] = g2["stop"] or rule["stop"]
            rule["sizing"] = "riesgo" if g2["sizing"] == "riesgo" else rule["sizing"]
            if g2["filter"] == "tendencia":
                rule["entry"].append(["sobre_media", 200])
            elif g2["filter"] == "calma":
                rule["entry"].append(["vol_baja", 30 * mk.bpd if mk.bpd > 1 else 30, 0.9])
            rule["entry"] = rule["entry"][:3]
            seeds.append(rule)
        if kr is not None:  # con previsiones de Kronos disponibles, "ceñirse a Kronos" siempre es una opción de partida
            seeds.append(inventor.seed_from_family("kronos", dict(thr=0.01), mk.bpd))
        tr = self.window(mk, "entreno")
        fz = self.cfg["fabrica"]
        rule, r_inv, hist = inventor.evolve(mk, seeds, tr, cfg, self.rng, temper, kr,
                                             pop=fz["poblacion_inventor"], gens=fz["generaciones_inventor"])

        # 4. elige con los años de validación
        va = self.window(mk, "validacion")
        vyears = (va[1] - va[0] + 1) / (365 * mk.bpd)
        w_known = signal(mk.I, g, p, kr)
        w_inv = inventor.exposure(mk.I, rule, kr, mk.bpd)
        v_known = run(mk.I, w_known, *va, cfg)
        v_inv = run(mk.I, w_inv, *va, cfg)
        sk = inventor.score(v_known, cfg["cap"], vyears, temper)
        si = inventor.score(v_inv, cfg["cap"], vyears, temper)
        propia = si > sk

        # si su elección opera igual que otro agente (en validación), prueba con su otra opción
        def firma_of(r):
            return hashlib.sha1(repr([(str(mk.ts[t["i"]].date()), t["side"]) for t in r.trades]).encode()).hexdigest()[:12]

        def twin_of(f):
            return next((x for x in self.state["agents"] if x.get("firma") == f and x is not ag), None)

        firma = firma_of(v_inv if propia else v_known)
        twin = twin_of(firma)
        cambio = False
        if twin:
            alt = firma_of(v_known if propia else v_inv)
            if not twin_of(alt) and (v_known if propia else v_inv).n_buys > 0:
                propia, firma, twin, cambio = not propia, alt, None, True
        ag.update(
            estudio=dict(probadas=n_tested, familia=g["family"], label=FAMILIES[g["family"]]["label"],
                         desc=describe(g, p, u), entreno=r_known.summary(), validacion=v_known.summary()),
            invento=dict(desc=inventor.describe(rule, mk.bpd), entreno=r_inv.summary(), validacion=v_inv.summary(),
                         generaciones=hist),
            eleccion="propia" if propia else "conocida", cambio_por_copia=cambio,
            genome=g, params=p, regla=rule, firma=firma,
        )
        ag["label"] = "Estrategia propia" if propia else FAMILIES[g["family"]]["label"]
        ag["desc"] = ag["invento"]["desc"] if propia else ag["estudio"]["desc"]
        w = w_inv if propia else w_known
        self._w[ag["id"]] = w

        # 5. examen
        ea, eb = self.window(mk, "examen")
        re = run(mk.I, w, ea, eb, cfg)
        crit = self.cfg["aprobar_examen"]
        fails = []
        if re.ret * 100 < crit["ganancia_minima_pct"]:
            fails.append(f"ganó {pc(re.ret)} (mínimo +{crit['ganancia_minima_pct']} %)")
        if re.n_buys < crit["operaciones_minimas"]:
            fails.append(f"solo {re.n_buys} operaciones (mínimo {crit['operaciones_minimas']})")
        if re.maxdd * 100 > crit["caida_maxima_pct"]:
            fails.append(f"llegó a caer un {re.maxdd * 100:.0f} % (máximo {crit['caida_maxima_pct']} %)")
        if re.dead:
            fails.append("se quedó sin dinero")
        ag.update(exam=re.summary(), examinado=self.today.isoformat())
        if twin:
            ag["status"], ag["motivo"] = "suspendido", f"Opera exactamente igual que {twin['name']}, no aporta nada nuevo."
        elif fails:
            ag["status"], ag["motivo"] = "suspendido", "No aprobó: " + "; ".join(fails) + "."
        else:
            ag["status"], ag["motivo"] = "cola", f"Aprobó el examen con {pc(re.ret)}."
        return ag

    def make_agent(self):
        fz = self.cfg["fabrica"]
        tfs = list(fz["temporalidades"].keys())
        tf = self.rng.choices(tfs, weights=[fz["temporalidades"][t] for t in tfs])[0]
        if tf not in self.mk:
            tf = "1d"
        name = self.new_name()
        ag = dict(id=hashlib.sha1(f"{name}{tf}{self.today}{self.rng.random()}".encode()).hexdigest()[:10],
                  name=name, born=self.today.isoformat(), tf=tf, tf_label=TF_LABEL[tf],
                  personalidad=self.rng.choice(list(TEMPER)), status="nuevo")
        return self.school(ag)

    # ------------------------------------------------------------ fábrica
    def factory(self):
        fz = self.cfg["fabrica"]
        n = fz["agentes_nuevos_por_dia"] if self.state["agents"] else fz.get("primera_promocion", fz["agentes_nuevos_por_dia"])
        t0 = time.time()
        made = 0
        while made < n and time.time() - t0 < fz["minutos_maximos"] * 60:
            ag = self.make_agent()
            self.state["agents"].append(ag)
            made += 1
            elig = "su estrategia propia" if ag["eleccion"] == "propia" else f"una conocida ({ag['estudio']['label']})"
            self.log(f"{ag['name']} ({ag['tf']}, {ag['personalidad']}) eligió {elig}: examen {pc(ag['exam']['ret'])} -> {ag['status']}")
        self.log(f"Fábrica: {made} agente{'s' if made != 1 else ''} nuevo{'s' if made != 1 else ''} en {time.time() - t0:.0f} s.")

    # ------------------------------------------------------------ simulado en vivo
    def paper_run(self, ag):
        """Resultado del simulado de un agente desde su inicio hasta la última vela."""
        mk = self.mk[ag["tf"]]
        a = mk.idx(ag["paper_start"])
        if a > mk.n - 1:
            return None, mk, a
        return run(mk.I, self.exposure(ag), a, mk.n - 1, self.run_cfg()), mk, a

    def paper(self):
        sim = self.cfg["simulado"]
        cfg = self.run_cfg()
        active = [a for a in self.state["agents"] if a["status"] == "simulado"]
        queue = sorted([a for a in self.state["agents"] if a["status"] == "cola"], key=lambda a: -a["exam"]["ret"])
        start = (self.daily.ts[-1] + dt.timedelta(days=1)).date().isoformat()
        for ag in queue:
            if len(active) >= sim["max_agentes_a_la_vez"]:
                break
            ag["status"], ag["paper_start"] = "simulado", start
            ag["motivo"] = "Empieza el simulado con precios reales."
            active.append(ag)
            how = "con su propia estrategia" if ag["eleccion"] == "propia" else f"con {ag['label']}"
            self.notify(f"{ag['name']} aprueba el examen",
                        f"Ganó {pc(ag['exam']['ret'])} en 2024-25 {how} ({ag['tf_label']}). Empieza {sim['dias']} días en simulado con 100 € ficticios.")
        for ag in [a for a in self.state["agents"] if a["status"] in ("simulado", "listo")]:
            r, mk, a = self.paper_run(ag)
            if r is None:
                ag["paper"] = dict(days=0, final=cfg["cap"], ret=0.0, maxdd=0.0, trades=0, eq=[])
                continue
            days = (mk.ts[-1].date() - dt.date.fromisoformat(ag["paper_start"])).days + 1
            daily = mk.daily(r.eq, a)
            vals = list(daily.values())
            step = max(1, len(vals) // 60)
            w = self.exposure(ag)
            ag["paper"] = dict(days=days, **r.summary(),
                               eq=[round(x, 2) for x in vals[::step]] + ([round(vals[-1], 2)] if (len(vals) - 1) % step else []),
                               last_trades=[dict(fecha=mk.ts[t["i"]].isoformat(timespec="minutes"), tipo=t["side"], precio=round(t["px"], 2),
                                                 importe=round(t["amt"], 2), resultado=round(t["pnl"], 2) if "pnl" in t else None)
                                            for t in r.trades[-15:]],
                               posicion=round(float(w[-1]), 2))
            if ag["status"] != "simulado":
                continue
            if r.maxdd * 100 > sim["caida_maxima_pct"] or r.dead:
                ag["status"] = "retirado"
                ag["motivo"] = f"En simulado llegó a caer un {r.maxdd * 100:.0f} % (máximo {sim['caida_maxima_pct']} %)."
                self.notify(f"{ag['name']} retirado", ag["motivo"])
            elif days >= sim["dias"]:
                if r.ret * 100 >= sim["ganancia_minima_pct"]:
                    ag["status"] = "listo"
                    ag["motivo"] = f"Superó {sim['dias']} días de simulado con {pc(r.ret)}."
                    self.notify(f"🏆 {ag['name']} listo para dinero real",
                                f"{pc(r.ret)} en {sim['dias']} días de simulado. Revisa el panel; solo pasará a real si tú lo decides.")
                else:
                    ag["status"] = "retirado"
                    ag["motivo"] = f"Terminó el simulado con {pc(r.ret)}."
                    self.notify(f"{ag['name']} no supera el simulado", ag["motivo"])

    # ------------------------------------------------------------ día completo
    def day(self, fabrica=True):
        if fabrica:
            self.factory()
        self.paper()
        counts = {}
        for a in self.state["agents"]:
            counts[a["status"]] = counts.get(a["status"], 0) + 1
        hist = self.state.setdefault("diario", [])
        hist.append(dict(fecha=self.today.isoformat(), estados=counts, novedades=self.news[-20:]))
        self.state["diario"] = hist[-120:]
        return counts
