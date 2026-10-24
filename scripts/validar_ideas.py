"""Comprueba que todas las ideas de ideas/estrategias_internet.json se pueden ejecutar.

Uso: python scripts/validar_ideas.py   (sale con error si alguna idea está mal escrita)

Piezas permitidas en "entry" y "exit" (lista de condiciones; entrada = todas, salida = cualquiera):
  ["sobre_media", N] ["bajo_media", N] ["cruce_alcista", N1, N2] ["cruce_bajista", N1, N2]
  ["rsi_bajo", N, nivel] ["rsi_alto", N, nivel] ["rompe_maximo", N] ["pierde_minimo", N]
  ["impulso_sube", N, pct] ["impulso_baja", N, pct] ["vol_baja", N, pct] ["vol_alta", N, pct]
  ["z_bajo", N, desv] ["z_alto", N, desv] ["macd_pos"] ["macd_neg"]
  ["doble_suelo", N, tol] ["triple_suelo", N, tol] ["hch_invertido", N, tol] ["triangulo", N, tol]
  ["rebote_soporte", N, tol] ["doble_techo", N, tol] ["hch", N, tol] ["pierde_soporte", N, tol]
  ["bandera", N, subida_min] ["ruptura_volumen", N, veces_volumen] ["volumen_alto", veces_volumen]
  Flujo de órdenes (delta = compras agresivas menos ventas agresivas, de Binance desde 2020):
  ["delta_compra", N, nivel] ["delta_venta", N, nivel] ["absorcion", veces_volumen] ["divergencia_delta", N]
  VWAP y EMA: ["ema_cruza_vwap", N] (en la vela del cruce) ["ema_sobre_vwap", N] ["ema_bajo_vwap", N] (EMA de N velas frente al VWAP anclado al día), ["bajo_ema", N] ["sobre_ema", N]
  Estacionalidad (solo agentes de 1h y 4h): ["franja_horaria", hora_inicio_UTC, horas] ["dia_semana", [0..6]] (0 = lunes)
  Régimen: ["en_tendencia", N, eficiencia] ["mercado_lateral", N, eficiencia]
  (N = número de velas; pct, tol y subida en tanto por uno: 0.05 = 5 %)
Gestión: stop (ATR: 0, 2, 3, 4), tp (0 o tanto por uno), trail (0 o tanto por uno), hold (días, 0 = sin límite),
  sizing ("completo" o "riesgo"), frac (0.2-1), be (tanto por uno), stall (días), pyr (tanto por uno), shrink (true/false),
  min_net (opcional, por defecto 0.01: la señal de salida solo cierra si el precio ya subió eso desde la compra),
  salida_siempre (opcional, true: la señal de salida cierra siempre, aunque pierda; para estrategias cuya salida es su stop),
  lado (opcional: "largo" o "corto"; en corto las reglas se aplican al gráfico dado la vuelta, para ganar cuando baja).
Campo opcional de la idea: "activos": lista de mercados de config.json (["BTC-EUR", "ETH-EUR", "SOL-EUR", "XRP-EUR"]);
  sin él, la idea se usa para todos.
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
import numpy as np  # noqa: E402
import inventor  # noqa: E402
from indicators import Ind  # noqa: E402

KEYS = {"entry", "exit", "stop", "tp", "trail", "hold", "sizing", "frac", "be", "stall", "pyr", "shrink"}


MARKETS = [k for k in json.load(open(os.path.join(ROOT, "config.json"))).get("activos", {"BTC-EUR": 1}) if not k.startswith("_")]


def main():
    data = json.load(open(os.path.join(ROOT, "ideas", "estrategias_internet.json")))
    rng = np.random.default_rng(1)
    c = 30000 * np.exp(np.cumsum(rng.normal(0, 0.03, 1500)))
    v = rng.uniform(100, 1000, 1500)
    I = Ind(c * 1.0, c * 1.02, c * 0.98, c, v=v, flow=(v, v * rng.uniform(0.3, 0.7, 1500)))
    I.hour = [k % 24 for k in range(1500)]
    I.dow = [(k // 24) % 7 for k in range(1500)]
    names, errs = set(), []
    for k, idea in enumerate(data["ideas"]):
        n = idea.get("nombre", f"#{k}")
        try:
            assert n not in names, "nombre repetido"
            names.add(n)
            for f in ("nombre", "fuente", "idea", "regla"):
                assert idea.get(f), f"falta '{f}'"
            r = idea["regla"]
            extra = {"min_net", "lado", "salida_siempre"}
            assert KEYS <= set(r) <= KEYS | extra, f"campos de la regla: faltan {KEYS - set(r)}, sobran {set(r) - KEYS - extra}"
            assert r.get("lado", "largo") in ("largo", "corto"), "lado debe ser largo o corto"
            for a in idea.get("activos", []):
                assert a in MARKETS, f"mercado desconocido {a}"
            assert r["entry"] and r["exit"], "entry y exit no pueden estar vacíos"
            w = inventor.exposure(I, r, None, 1)
            assert w.shape == (1500,), "salida incorrecta"
            inventor.describe(r, 1)
        except Exception as e:  # noqa: BLE001
            errs.append(f"{n}: {e}")
    print(f"{len(data['ideas'])} ideas, {len(errs)} con errores")
    for e in errs:
        print(" -", e)
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
