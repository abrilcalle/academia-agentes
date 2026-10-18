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

import diario
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
    def __init__(self, root, markets, kronos=None, today=None, log=print, otros=None):
        self.root = root
        self.otros = otros or {}
        diario.ALLOW_SHORT = bool(json.load(open(os.path.join(root, "config.json"))).get("permitir_cortos", False))  # otros mercados (ETH-EUR, SOL-EUR...): dict mercado -> dict tf -> Market
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
        c = self.cfg
        return dict(fee=c["comision_pct"], slip=c["deslizamiento_pct"], cap=c["saldo_inicial_eur"],
                    maker=c.get("comision_maker_pct", c["comision_pct"]), limit=c.get("ordenes_limitadas", False),
                    borrow_h=c.get("corto_interes_hora_pct", 0.0))

    def window(self, mk, key):
        a, b = self.cfg[key]
        return mk.idx(a), min(mk.end_idx(b), mk.n - 1)

    def kronos_coverage(self, tf):
        if self.kronos.get(tf) is None or tf not in self.mk:
            return 0.0
        mk = self.mk[tf]
        a, b = self.window(mk, "entreno")[0], self.window(mk, "examen")[1]
        return round(float(np.mean(~np.isnan(self.kronos[tf]["med"][a:b + 1]))), 3)

    def m(self, ag):
        """Las velas del mercado y la temporalidad de un agente."""
        a = ag.get("activo", self.cfg["mercado"])
        return self.mk[ag["tf"]] if a == self.cfg["mercado"] else self.otros[a][ag["tf"]]

    def kr_ag(self, ag):
        """Kronos solo está calculado para BTC."""
        return self.kr_for(ag["tf"]) if ag.get("activo", self.cfg["mercado"]) == self.cfg["mercado"] else None

    def pref(self, ag):
        a = ag.get("activo", self.cfg["mercado"])
        return "" if a == self.cfg["mercado"] else a

    def parents(self, ag, estilo):
        """Los agentes que van ganando en simulado (mismo mercado, temporalidad y tipo): sus hijos parten de sus reglas."""
        main = self.cfg["mercado"]
        c = [x for x in self.state["agents"] if x["status"] in ("simulado", "listo")
             and x.get("activo", main) == ag.get("activo", main) and x["tf"] == ag["tf"]
             and (x.get("estilo") == "diario") == (estilo == "diario") and x.get("regla")
             and (estilo == "diario" or x.get("eleccion") == "propia")
             and (x.get("paper") or {}).get("ret", 0) > 0.002]
        return sorted(c, key=lambda x: -x["paper"]["ret"])[:2]

    def ideas_for(self, activo):
        return [i for i in self.internet_ideas() if not i.get("activos") or activo in i["activos"]]

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

    def internet_ideas(self):
        if not hasattr(self, "_ideas"):
            p = os.path.join(self.root, "ideas", "estrategias_internet.json")
            self._ideas = json.load(open(p))["ideas"] if os.path.exists(p) else []
        return self._ideas

    def exposure(self, ag):
        """Exposición (0..1) de un agente en todas las velas de su temporalidad."""
        if ag["id"] not in self._w:
            mk = self.m(ag)
            kr = self.kr_ag(ag)
            if ag.get("estilo") == "diario":
                w = diario.exposure(mk.I, ag["regla"], kr, mk.bpd)
            elif ag["eleccion"] == "propia":
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
                s, r = inventor.robust(mk, signal(mk.I, g, p, kr), (a, b), cfg, temper)
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
                        s, r = inventor.robust(mk, signal(mk.I, g, p, kr), (a, b), cfg, temper)
                        extra.append((s, g, p, r))
        allc = sorted(found + extra, key=lambda t: -t[0])
        return allc[:3], len(found) and sum(len(FAMILIES[f]["grid"]) for f in fams) + len(extra)

    def school(self, ag):
        cfg = self.run_cfg()
        mk = self.m(ag)
        kr = self.kr_ag(ag)
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
        P = inventor.pools(mk.bpd)
        for _ in range(3):  # ideas de partida con figuras de chartismo (W, M, HCH, banderas, soportes...)
            seeds.append(inventor.pattern_seed(self.rng, P, kr is not None))
        ideas = [i for i in self.ideas_for(ag.get("activo", self.cfg["mercado"])) if i["regla"].get("lado") != "corto"]  # los clásicos solo compran
        # prioriza las ideas que menos agentes han estudiado (así las nuevas se prueban pronto)
        uso = {}
        for x in self.state["agents"]:
            for nm in x.get("ideas_internet", []):
                uso[nm] = uso.get(nm, 0) + 1
        orden = sorted(ideas, key=lambda i: (uso.get(i["nombre"], 0), self.rng.random()))
        estudiadas = orden[:2]
        for idea in estudiadas:  # estrategias de cursos, vídeos y artículos de internet
            r = dict(idea["regla"])
            r["entry"] = [list(x) for x in r["entry"]]
            r["exit"] = [list(x) for x in r["exit"]]
            seeds.append(r)
        ag["ideas_internet"] = [i["nombre"] for i in estudiadas]
        padres = self.parents(ag, "clasico")
        seeds[:0] = [json.loads(json.dumps(x["regla"])) for x in padres]  # aprende de los que ya ganan con dinero ficticio
        ag["padres"] = [x["name"] for x in padres]
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
        sk, v_known = inventor.robust(mk, w_known, va, cfg, temper)
        si, v_inv = inventor.robust(mk, w_inv, va, cfg, temper)
        propia = si > sk

        # si su elección opera igual que otro agente (en validación), prueba con su otra opción
        def firma_of(r):
            return hashlib.sha1((self.pref(ag) + repr([(str(mk.ts[t["i"]].date()), t["side"]) for t in r.trades])).encode()).hexdigest()[:12]

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
        gmin = crit.get("ganancia_media_por_operacion_pct", 0)
        if re.closed and re.avg_trade * 100 < gmin:
            fails.append(f"de media gana un {re.avg_trade * 100:.1f} % por operación tras comisiones (mínimo {gmin:g} %)".replace(".", ","))
        ag.update(exam=re.summary(), examinado=self.today.isoformat())
        if twin:
            ag["status"], ag["motivo"] = "suspendido", f"Opera exactamente igual que {twin['name']}, no aporta nada nuevo."
        elif fails:
            ag["status"], ag["motivo"] = "suspendido", "No aprobó: " + "; ".join(fails) + "."
        else:
            ag["status"], ag["motivo"] = "cola", f"Aprobó el examen con {pc(re.ret)}."
            self.exam2(ag)
        return ag

    # ------------------------------------------------------------ operadores diarios
    def week_fails(self, mk, r, crit, pre=""):
        """Comprueba las exigencias semanales de un operador diario. Devuelve (estadísticas, motivos de suspenso)."""
        s = diario.stats(mk, r)
        f = []
        if r.ret * 100 < crit["ganancia_minima_pct"]:
            f.append(f"{pre}{'perdió' if r.ret < 0 else 'ganó'} un {abs(r.ret) * 100:.1f} % (mínimo {crit['ganancia_minima_pct']:+g} %)")
        if s["dias_sem"] < crit["dias_operando_por_semana"]:
            f.append(f"{pre}operó {s['dias_sem']:.1f} días por semana (mínimo {crit['dias_operando_por_semana']:g})")
        if s["sem_pos"] * 100 < crit["semanas_en_positivo_pct"]:
            f.append(f"{pre}solo acabó en positivo el {s['sem_pos'] * 100:.0f} % de las semanas (mínimo {crit['semanas_en_positivo_pct']} %)")
        if s["peor_sem"] * 100 < -crit["peor_semana_pct"]:
            f.append(f"{pre}su peor semana perdió un {-s['peor_sem'] * 100:.1f} % (máximo {crit['peor_semana_pct']:g} %)")
        if r.maxdd * 100 > crit["caida_maxima_pct"]:
            f.append(f"{pre}llegó a caer un {r.maxdd * 100:.0f} % (máximo {crit['caida_maxima_pct']} %)")
        if r.closed and r.avg_trade * 100 < crit["ganancia_media_por_operacion_pct"]:
            f.append(f"{pre}de media gana un {r.avg_trade * 100:.2f} % por operación tras comisiones (mínimo {crit['ganancia_media_por_operacion_pct']:g} %)")
        if r.dead:
            f.append(f"{pre}se quedó sin dinero")
        return s, [x.replace(".", ",") for x in f]

    def school_diario(self, ag):
        cfg = self.run_cfg()
        mk = self.m(ag)
        kr = self.kr_ag(ag)
        temper = TEMPER[ag["personalidad"]]
        P = inventor.pools(mk.bpd)
        cd = self.cfg["operadores_diarios"]
        diario.OBJETIVO_SEMANAL = cd.get("objetivo_semanal_pct", 1) / 100

        # ideas de partida: estrategias de internet y de chartismo, cada una probada en un tipo de mercado
        seeds = []
        uso = {}
        for x in self.state["agents"]:
            for nm in x.get("ideas_internet", []):
                uso[nm] = uso.get(nm, 0) + 1
        ideas = sorted([i for i in self.ideas_for(ag.get("activo", self.cfg["mercado"]))
                        if diario.ALLOW_SHORT or i["regla"].get("lado") != "corto"], key=lambda i: (uso.get(i["nombre"], 0), self.rng.random()))[:3]
        for idea in ideas:
            seeds.append(diario.from_sub(self.rng, P, kr is not None, idea["regla"]))
        for _ in range(2):
            seeds.append(diario.from_sub(self.rng, P, kr is not None, inventor.pattern_seed(self.rng, P, kr is not None)))
        ag["ideas_internet"] = [i["nombre"] for i in ideas]
        padres = self.parents(ag, "diario")
        seeds[:0] = [json.loads(json.dumps(x["regla"])) for x in padres]  # aprende de los operadores que ya ganan en simulado
        ag["padres"] = [x["name"] for x in padres]

        tr = self.window(mk, "entreno")
        rule, r_tr, hist, _ = diario.evolve(mk, seeds, tr, cfg, self.rng, temper, kr,
                                            pop=cd["poblacion_inventor"], gens=cd["generaciones_inventor"])
        w = diario.exposure(mk.I, rule, kr, mk.bpd)
        va = self.window(mk, "validacion")
        sv, r_va = diario.robust(mk, w, va, cfg, temper)

        # filtro anti-suerte: si con pequeños cambios deja de funcionar en validación, ganó por casualidad
        vecinos = diario.neighbours(self.rng, rule, mk, kr is not None, n=cd["prueba_suerte"]["variantes"])
        buenos = 0
        for v in vecinos:
            rv = run(mk.I, diario.exposure(mk.I, v, kr, mk.bpd), va[0], va[1], cfg)
            sv2 = diario.stats(mk, rv)
            buenos += rv.ret > 0 and sv2["sem_pos"] >= sv2["sem_neg"]
        firma = hashlib.sha1((self.pref(ag) + repr([(str(mk.ts[t["i"]]), t["side"]) for t in r_va.trades])).encode()).hexdigest()[:12]
        twin = next((x for x in self.state["agents"] if x.get("firma") == firma and x is not ag), None)
        usa_cortos = diario.ALLOW_SHORT and any((rule.get(k) or {}).get("lado") == "corto" for k in diario.REGIMES)
        ag.update(estilo="diario", eleccion="diario", regla=rule, firma=firma, label="Operador diario", usa_cortos=usa_cortos,
                  desc=diario.describe(rule, mk.bpd),
                  invento=dict(desc=diario.describe(rule, mk.bpd), entreno=r_tr.summary(), validacion=r_va.summary(),
                               generaciones=hist, semanas_entreno=diario.stats(mk, r_tr), semanas_validacion=diario.stats(mk, r_va)),
                  suerte=dict(variantes=len(vecinos), siguen_ganando=int(buenos)))
        self._w[ag["id"]] = w

        # examen 2024-25
        ea, eb = self.window(mk, "examen")
        re = run(mk.I, w, ea, eb, cfg)
        s, fails = self.week_fails(mk, re, cd["aprobar_examen"])
        _, vfails = self.week_fails(mk, r_va, cd["aprobar_validacion"], "en 2022–23 ")
        fails = vfails + fails
        if buenos < cd["prueba_suerte"]["minimo_que_siguen_ganando"]:
            fails.insert(0, f"puede ser suerte: con pequeños cambios solo {buenos} de {len(vecinos)} versiones siguen ganando en 2022–23")
        ag.update(exam=re.summary(), exam_semanas=s, examinado=self.today.isoformat())
        if twin:
            ag["status"], ag["motivo"] = "suspendido", f"Opera exactamente igual que {twin['name']}, no aporta nada nuevo."
        elif fails:
            ag["status"], ag["motivo"] = "suspendido", "No aprobó: " + "; ".join(fails) + "."
        else:
            ag["status"], ag["motivo"] = "cola", f"Aprobó el examen con {pc(re.ret)}."
            self.exam2(ag)
        return ag

    def exam2(self, ag):
        """Segundo examen: el mercado de este año (2026), que no se usó para nada antes."""
        c2 = self.cfg.get("examen_2")
        if not c2:
            return True
        mk = self.m(ag)
        a, b = mk.idx(c2["periodo"][0]), min(mk.end_idx(c2["periodo"][1]), mk.n - 1)
        r = run(mk.I, self.exposure(ag), a, b, self.run_cfg())
        ag["exam2"] = r.summary()
        fails = []
        if r.ret * 100 < c2["ganancia_minima_pct"]:
            fails.append(f"en 2026 {'perdió' if r.ret < 0 else 'ganó'} un {abs(r.ret) * 100:.1f} % (mínimo {c2['ganancia_minima_pct']:+g} %)".replace(".", ","))
        if r.n_buys < c2["operaciones_minimas"]:
            fails.append(f"en 2026 solo hizo {r.n_buys} operaciones (mínimo {c2['operaciones_minimas']})")
        if r.maxdd * 100 > c2["caida_maxima_pct"]:
            fails.append(f"en 2026 llegó a caer un {r.maxdd * 100:.0f} % (máximo {c2['caida_maxima_pct']} %)")
        if r.closed and r.avg_trade * 100 < c2.get("ganancia_media_por_operacion_pct", 0):
            fails.append(f"en 2026 ganó de media un {r.avg_trade * 100:.1f} % por operación (mínimo {c2['ganancia_media_por_operacion_pct']:g} %)".replace(".", ","))
        if ag.get("estilo") == "diario":  # los operadores diarios: además, semana a semana
            s, wf = self.week_fails(mk, r, self.cfg["operadores_diarios"]["examen_2"], "en 2026 ")
            ag["exam2_semanas"] = s
            fails = [x for x in fails if "operaciones (mínimo" not in x] + [x for x in wf if "ganó un" not in x and "perdió un" not in x]
        # no tiene sentido tener dos agentes que en 2026 hicieron exactamente lo mismo
        f2 = hashlib.sha1((self.pref(ag) + repr([(str(mk.ts[t["i"]]), t["side"]) for t in r.trades])).encode()).hexdigest()[:12] if r.trades else None
        ag["firma2026"] = f2
        twin = next((x for x in self.state["agents"] if f2 and x is not ag and x.get("firma2026") == f2
                     and x["status"] in ("cola", "simulado", "listo")), None)
        if twin and not fails:
            fails.append(f"en 2026 operó exactamente igual que {twin['name']}, que ya está en simulado")
        if fails:
            ag["status"] = "suspendido"
            ag["motivo"] = "Aprobó 2024–25 pero no el examen de 2026: " + "; ".join(fails) + "."
            return False
        ag["motivo"] = f"Aprobó los dos exámenes: {pc(ag['exam']['ret'])} en 2024–25 y {pc(r.ret)} en 2026."
        return True

    def make_agent(self):
        fz = self.cfg["fabrica"]
        cd = self.cfg.get("operadores_diarios")
        # mercado: BTC o uno de los otros que se hayan podido cargar hoy
        main = self.cfg["mercado"]
        pesos = {k: v.get("peso", 1) for k, v in self.cfg.get("activos", {main: {"peso": 1}}).items()
                 if not k.startswith("_") and (k == main or k in self.otros)}
        pesos = pesos or {main: 1}
        activo = self.rng.choices(list(pesos), weights=list(pesos.values()))[0]
        avail = self.mk if activo == main else self.otros[activo]
        diario_ = bool(cd) and self.rng.random() < cd["parte_de_los_nuevos"]
        opts = cd["temporalidades"] if diario_ else fz["temporalidades"]
        tfs = [t for t in opts if t in avail] or ["1d"]
        tf = self.rng.choices(tfs, weights=[opts.get(t, 1) for t in tfs])[0]
        name = self.new_name()
        ag = dict(id=hashlib.sha1(f"{name}{tf}{self.today}{self.rng.random()}".encode()).hexdigest()[:10],
                  name=name, born=self.today.isoformat(), tf=tf, tf_label=TF_LABEL[tf], activo=activo,
                  personalidad=self.rng.choice(list(TEMPER)), status="nuevo")
        return self.school_diario(ag) if diario_ else self.school(ag)

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
            elig = ("ser operador diario" if ag.get("estilo") == "diario" else "su estrategia propia" if ag["eleccion"] == "propia"
                    else f"una conocida ({ag['estudio']['label']})")
            self.log(f"{ag['name']} ({ag.get('activo', 'BTC-EUR')} {ag['tf']}, {ag['personalidad']}) eligió {elig}: examen {pc(ag['exam']['ret'])} -> {ag['status']}")
        self.log(f"Fábrica: {made} agente{'s' if made != 1 else ''} nuevo{'s' if made != 1 else ''} en {time.time() - t0:.0f} s.")

    # ------------------------------------------------------------ simulado en vivo
    def paper_run(self, ag):
        """Resultado del simulado de un agente desde su inicio hasta la última vela."""
        mk = self.m(ag)
        a = mk.idx(ag["paper_start"])
        if a > mk.n - 1:
            return None, mk, a
        return run(mk.I, self.exposure(ag), a, mk.n - 1, self.run_cfg()), mk, a

    def paper(self):
        sim = self.cfg["simulado"]
        cfg = self.run_cfg()
        # los que se aprobaron antes de existir el examen de 2026 también tienen que pasarlo
        for ag in sorted(self.state["agents"], key=lambda a: (a.get("paper_start") or "9", a.get("born", ""))):
            if ag["status"] in ("cola", "simulado") and ("exam2" not in ag or "firma2026" not in ag):
                if not self.exam2(ag):
                    self.log(f"{ag['name']} sale del simulado: {ag['motivo']}")
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
        team_days, team_ops = [], {}
        paused = set(self.cfg.get("cartera", {}).get("pausados", []))
        for ag in [a for a in self.state["agents"] if a["status"] in ("simulado", "listo")]:
            r, mk, a = self.paper_run(ag)
            if r is not None and ag["name"] not in paused:
                team_days.append((dt.date.fromisoformat(ag["paper_start"]), mk.daily(r.eq, a)))
                for t in r.trades:
                    if t["side"] in ("compra", "corto"):
                        d = mk.ts[t["i"]].date()
                        team_ops[d] = team_ops.get(d, 0) + 1
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
                    extra = " Ojo: usa ventas en corto, que Bitvavo aún no permite por API." if ag.get("usa_cortos") else ""
                    self.notify(f"🏆 {ag['name']} listo para dinero real",
                                f"{pc(r.ret)} en {sim['dias']} días de simulado. Revisa el panel; solo pasará a real si tú lo decides.{extra}")
                else:
                    ag["status"] = "retirado"
                    ag["motivo"] = f"Terminó el simulado con {pc(r.ret)}."
                    self.notify(f"{ag['name']} no supera el simulado", ag["motivo"])
        self.team_week(team_days, team_ops)

    def team_week(self, team_days, team_ops):
        """Resultado del equipo (todos los agentes en simulado o listos, sin los pausados) semana a semana."""
        if not team_days:
            self.state["equipo"] = None
            return
        cap = self.cfg["saldo_inicial_eur"]
        last = self.daily.ts[-1].date()
        first = min(s for s, _ in team_days)
        val = {}
        d = first - dt.timedelta(days=1)
        while d <= last:
            tot = 0.0
            for start, daily in team_days:
                if d < start:
                    tot += cap
                else:
                    v = daily.get(d)
                    if v is None:  # sin vela ese día: usa el último saldo conocido
                        prev = [x for k, x in daily.items() if k <= d]
                        v = prev[-1] if prev else cap
                    tot += v
            val[d] = tot
            d += dt.timedelta(days=1)
        weeks = []
        monday = first - dt.timedelta(days=first.weekday())
        while monday <= last:
            sunday = monday + dt.timedelta(days=6)
            end = min(sunday, last)
            before = max(monday - dt.timedelta(days=1), first - dt.timedelta(days=1))
            v0, v1 = val[before], val[end]
            days_ops = [k for k in team_ops if monday <= k <= end]
            weeks.append(dict(inicio=monday.isoformat(), fin=end.isoformat(), completa=end == sunday,
                              eur=round(v1 - v0, 2), pct=round(v1 / v0 - 1, 5),
                              ops=sum(team_ops[k] for k in days_ops), dias_con_ops=len(days_ops)))
            monday += dt.timedelta(days=7)
        dl = val[last] - val[last - dt.timedelta(days=1)] if last - dt.timedelta(days=1) in val else 0.0
        self.state["equipo"] = dict(con_cortos=sum(1 for a in self.state["agents"] if a["status"] in ("simulado", "listo") and a.get("usa_cortos")),
                                    miembros=len(team_days), capital=cap * len(team_days), semanas=weeks[-26:],
                                    ayer=dict(fecha=last.isoformat(), eur=round(dl, 2), ops=team_ops.get(last, 0)))

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
