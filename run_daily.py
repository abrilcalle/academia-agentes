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
    # flujo de órdenes (delta de Binance): opcional, los agentes funcionan sin él
    if local:
        flow = datamod.load_flow(os.path.join(local, "btc_flujo_1h"))
        flow = {k: v for k, v in flow.items() if k < cut}
    else:
        flow = datamod.update_flow(os.path.join(ROOT, "data", "btc_eur_flujo_1h"), cfg.get("flujo_simbolo", "BTCEUR"))

    def market(tf, candles, hours):
        arr = datamod.to_arrays(candles, tf)
        return Market(tf, *arr, flow=datamod.flow_arrays(flow, arr[0], hours) if flow else None)

    mk = {"1d": market("1d", d1, 24)}
    if h1:
        mk["1h"] = market("1h", h1, 1)
        mk["4h"] = market("4h", datamod.resample(h1, 4), 4)
    if flow:
        print(f"Flujo de órdenes: {min(flow).date()} -> {max(flow).date()} ({len(flow)} horas)")
    return mk


def load_other_assets(cfg, local, today, use_intraday):
    """Los demás mercados (ETH, SOL, oro...). Si uno falla, se sigue sin él."""
    out = {}
    for market, info in cfg.get("activos", {}).items():
        if market.startswith("_") or market == cfg["mercado"]:
            continue
        slug = market.replace("-", "_").lower()  # eth_eur
        short = market.split("-")[0].lower()
        since = dt.datetime.fromisoformat(info.get("desde", "2017-12-01"))
        try:
            if local:
                d1 = datamod.load_csv(os.path.join(local, f"{short}_1d.csv"))
                h1p = os.path.join(local, f"{short}_1h")
                h1 = datamod.load_csv(h1p if os.path.exists(h1p) else h1p + ".csv") if use_intraday else {}
                cut = dt.datetime(today.year, today.month, today.day)
                d1 = {k: v for k, v in d1.items() if k < cut}
                h1 = {k: v for k, v in h1.items() if k < cut}
                if not d1:
                    continue
            else:
                bs = info.get("bitstamp", "auto")
                d1 = datamod.update(os.path.join(ROOT, "data", f"{slug}_1d.csv"), "1d", market, since=since, bitstamp=bs)
                h1 = datamod.update(os.path.join(ROOT, "data", f"{slug}_1h") + "/", "1h", market, since=since, bitstamp=bs) if use_intraday else {}
            m = {"1d": Market("1d", *datamod.to_arrays(d1, "1d"))}
            if h1:
                m["1h"] = Market("1h", *datamod.to_arrays(h1, "1h"))
                m["4h"] = Market("4h", *datamod.to_arrays(datamod.resample(h1, 4), "4h"))
            out[market] = m
            print(f"{market}: velas diarias {m['1d'].ts[0].date()} -> {m['1d'].ts[-1].date()}, cierra en {m['1d'].I.c[-1]:,.2f} €")
        except Exception as e:  # noqa: BLE001
            print(f"Aviso: no se pudieron cargar los datos de {market} ({e}); hoy se sigue sin él.")
    return out


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

    otros = load_other_assets(cfg, args.datos_locales, today, intraday)
    ac = Academia(ROOT, mk, kronos=kronos, today=today, otros=otros)
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
