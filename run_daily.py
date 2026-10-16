"""Ejecución diaria de la Academia de Agentes.

  python run_daily.py                       # día normal: datos de Bitvavo, Kronos (si está instalado), fábrica, simulado, informe, panel
  python run_daily.py --sin-kronos          # sin calcular previsiones nuevas de Kronos
  python run_daily.py --sin-fabrica         # no crea agentes nuevos
  python run_daily.py --kronos-tiempo 18000 --kronos-max 4000   # tanda larga para rellenar el histórico de Kronos
  python run_daily.py --datos-locales carpeta --hoy 2026-07-01   # pruebas sin internet (carpeta con btc_1d.csv y btc_1h.csv)
"""
import argparse
import datetime as dt
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

import data as datamod  # noqa: E402
import informe  # noqa: E402
import kronos_signal  # noqa: E402
from academia import Academia  # noqa: E402
from dashboard import build  # noqa: E402
from market import Market  # noqa: E402


def load_markets(cfg, local, today, use_intraday):
    if local:
        d1 = datamod.load_csv(os.path.join(local, "btc_1d.csv"))
        h1p = os.path.join(local, "btc_1h.csv")
        h1 = datamod.load_csv(h1p if os.path.exists(h1p) else os.path.join(local, "btc_1h")) if use_intraday else {}
        cut = dt.datetime(today.year, today.month, today.day)
        d1 = {k: v for k, v in d1.items() if k < cut}
        h1 = {k: v for k, v in h1.items() if k < cut}
    else:
        d1 = datamod.update(os.path.join(ROOT, "data", "btc_eur_1d.csv"), "1d", cfg["mercado"], since=dt.datetime(2017, 1, 1))
        h1 = datamod.update(os.path.join(ROOT, "data", "btc_eur_1h") + "/", "1h", cfg["mercado"], since=dt.datetime(2017, 12, 1)) if use_intraday else {}
    mk = {"1d": Market("1d", *datamod.to_arrays(d1, "1d"))}
    if h1:
        mk["1h"] = Market("1h", *datamod.to_arrays(h1, "1h"))
        mk["4h"] = Market("4h", *datamod.to_arrays(datamod.resample(h1, 4), "4h"))
    return mk


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sin-kronos", action="store_true")
    ap.add_argument("--sin-fabrica", action="store_true", help="no crear agentes nuevos en esta ejecución")
    ap.add_argument("--kronos-tiempo", type=int, default=1500, help="segundos máximos calculando previsiones")
    ap.add_argument("--kronos-max", type=int, default=None, help="máximo de velas nuevas de Kronos por temporalidad en esta ejecución")
    ap.add_argument("--solo-kronos", action="store_true", help="solo calcular previsiones de Kronos (sin agentes ni panel)")
    ap.add_argument("--datos-locales", default=None)
    ap.add_argument("--hoy", default=None, help="fecha simulada AAAA-MM-DD (pruebas)")
    args = ap.parse_args()

    cfg = json.load(open(os.path.join(ROOT, "config.json")))
    today = dt.date.fromisoformat(args.hoy) if args.hoy else dt.datetime.now(dt.timezone.utc).date()
    intraday = any(t in cfg["fabrica"]["temporalidades"] for t in ("1h", "4h"))
    mk = load_markets(cfg, args.datos_locales, today, intraday)
    d = mk["1d"]
    print(f"Velas diarias: {d.ts[0].date()} -> {d.ts[-1].date()}. BTC cierra en {d.I.c[-1]:,.0f} €. Temporalidades: {', '.join(mk)}")

    kronos = {}
    t_k = time.time()
    ktfs = [t for t in cfg["kronos"]["temporalidades"] if t in mk]
    for k, tf in enumerate(ktfs):
        kronos[tf] = kronos_signal.load(ROOT, mk[tf], cfg)
        if args.sin_kronos or not cfg["fabrica"]["usar_kronos"]:
            continue
        try:
            left = args.kronos_tiempo - (time.time() - t_k)  # el tiempo que no use una temporalidad pasa a la siguiente
            share = left / (len(ktfs) - k)
            kronos[tf] = kronos_signal.compute(ROOT, mk[tf], cfg, budget_s=max(60, share), max_new=args.kronos_max)
        except ImportError as e:
            print(f"Kronos no está instalado en este equipo ({e}); se usan las previsiones ya guardadas.")
            break
        except Exception as e:  # noqa: BLE001
            print(f"Aviso: fallo calculando previsiones de Kronos {tf} ({e}); se usan las ya guardadas.")

    if args.solo_kronos:
        print("Previsiones de Kronos guardadas.")
        return

    ac = Academia(ROOT, mk, kronos=kronos, today=today)
    counts = ac.day(fabrica=not args.sin_fabrica)
    rep = informe.maybe_report(ac)
    ac.save()
    print("Estados:", counts)
    if rep:
        print(f"Informe mensual de {rep['mes']} generado.")
    for n in ac.news:
        print(" -", n)
    build(ROOT, ac)
    print("Panel actualizado en docs/")


if __name__ == "__main__":
    main()
