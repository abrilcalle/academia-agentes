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
  (N = número de velas; pct, tol y subida en tanto por uno: 0.05 = 5 %)
Gestión: stop (ATR: 0, 2, 3, 4), tp (0 o tanto por uno), trail (0 o tanto por uno), hold (días, 0 = sin límite),
  sizing ("completo" o "riesgo"), frac (0.2-1), be (tanto por uno), stall (días), pyr (tanto por uno), shrink (true/false).
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
import numpy as np  # noqa: E402
import inventor  # noqa: E402
from indicators import Ind  # noqa: E402

KEYS = {"entry", "exit", "stop", "tp", "trail", "hold", "sizing", "frac", "be", "stall", "pyr", "shrink"}


def main():
    data = json.load(open(os.path.join(ROOT, "ideas", "estrategias_internet.json")))
    rng = np.random.default_rng(1)
    c = 30000 * np.exp(np.cumsum(rng.normal(0, 0.03, 1500)))
    I = Ind(c * 1.0, c * 1.02, c * 0.98, c, v=rng.uniform(100, 1000, 1500))
    names, errs = set(), []
    for k, idea in enumerate(data["ideas"]):
        n = idea.get("nombre", f"#{k}")
        try:
            assert n not in names, "nombre repetido"
            names.add(n)
            for f in ("nombre", "fuente", "idea", "regla"):
                assert idea.get(f), f"falta '{f}'"
            r = idea["regla"]
            assert set(r) == KEYS, f"campos de la regla: faltan {KEYS - set(r)}, sobran {set(r) - KEYS}"
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
