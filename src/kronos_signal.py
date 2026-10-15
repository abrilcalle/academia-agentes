"""Previsiones de Kronos para los agentes que quieran usarlas.

Para cada vela t, con las últimas `contexto` velas hasta t (incluida), Kronos genera `caminos`
trayectorias posibles de las próximas `horizonte` velas. Guardamos:
  med = rentabilidad mediana prevista al final del horizonte
  up  = fracción de caminos que acaban por encima del cierre de t
Así los agentes usan el rango con su incertidumbre, no una sola previsión.

Se calcula para cada temporalidad de config.json -> kronos.temporalidades (por defecto 1d y 4h;
1h es posible pero rellenar su histórico lleva decenas de horas de cálculo).
Necesita PyTorch y el código de Kronos (https://github.com/shiyu-coder/Kronos) en vendor/Kronos.
Las previsiones se guardan en data/kronos_<tf>.csv y solo se calculan las que faltan.
"""
import csv
import datetime as dt
import os
import sys
import time

import numpy as np

_MODEL = {}


def cache_path(root, tf, cfg):
    """Un archivo por temporalidad y ajustes: si cambian el modelo o el contexto, se empieza de cero."""
    k = cfg["kronos"]
    t = k["por_temporalidad"][tf]
    tag = f"{k['modelo'].split('/')[-1].lower()}_c{t['contexto']}_h{t['horizonte']}"
    return os.path.join(root, "data", f"kronos_{tf}_{tag}.csv")


def load_cache(path):
    out = {}
    if os.path.exists(path):
        with open(path) as f:
            for r in csv.DictReader(f):
                out[dt.datetime.fromisoformat(r["ts"])] = (float(r["med"]), float(r["up"]))
    return out


def save_cache(path, cache):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ts", "med", "up"])
        for d in sorted(cache):
            w.writerow([d.isoformat(timespec="minutes"), f"{cache[d][0]:.6f}", f"{cache[d][1]:.4f}"])


def as_arrays(cache, ts):
    med = np.full(len(ts), np.nan)
    up = np.full(len(ts), np.nan)
    for i, d in enumerate(ts):
        if d in cache:
            med[i], up[i] = cache[d]
    return dict(med=med, up=up)


def load(root, mk, cfg):
    p = cache_path(root, mk.tf, cfg)
    return as_arrays(load_cache(p), mk.ts) if os.path.exists(p) else None


def _predictor(root, k):
    if "p" not in _MODEL:
        sys.path.insert(0, os.path.join(root, "vendor", "Kronos"))
        import torch
        from model import Kronos, KronosPredictor, KronosTokenizer  # type: ignore
        torch.set_num_threads(max(1, os.cpu_count() or 1))
        tok = KronosTokenizer.from_pretrained(k["tokenizer"])
        model = Kronos.from_pretrained(k["modelo"])
        _MODEL["p"] = KronosPredictor(model, tok, device="cpu", max_context=512)
    return _MODEL["p"]


def compute(root, mk, cfg, budget_s=None, max_new=None, log=print):
    """Calcula las previsiones que falten para el mercado `mk` (de la más reciente hacia atrás,
    para que la de hoy siempre esté) hasta `max_new` velas o `budget_s` segundos."""
    k = cfg["kronos"]
    tcfg = k["por_temporalidad"][mk.tf]
    ctx, hz, paths = tcfg["contexto"], tcfg["horizonte"], k["caminos"]
    path = cache_path(root, mk.tf, cfg)
    cache = load_cache(path)
    first = dt.datetime.fromisoformat(cfg["entreno"][0])
    todo = [i for i, d in enumerate(mk.ts) if d >= first and i >= ctx and d not in cache]
    todo = sorted(todo, reverse=True)[: max_new or k["max_velas_nuevas_por_ejecucion"]]
    if not todo:
        log(f"Kronos {mk.tf}: no hay velas nuevas que prever.")
        return as_arrays(cache, mk.ts)

    import pandas as pd
    pred = _predictor(root, k)
    step = mk.ts[1] - mk.ts[0]
    ts = pd.Series(pd.to_datetime([d.isoformat() for d in mk.ts]))
    c = mk.I.c
    frame = pd.DataFrame(dict(open=mk.I.o, high=mk.I.h, low=mk.I.l, close=c, volume=mk.v))
    t0 = time.time()
    done = 0
    for i in todo:
        if budget_s and time.time() - t0 > budget_s:
            break
        x = frame.iloc[i - ctx + 1:i + 1].reset_index(drop=True)
        xt = ts.iloc[i - ctx + 1:i + 1].reset_index(drop=True)
        yt = pd.Series(pd.date_range(ts.iloc[i] + step, periods=hz, freq=step))
        outs = pred.predict_batch([x] * paths, [xt] * paths, [yt] * paths, pred_len=hz,
                                  T=1.0, top_p=0.9, sample_count=1, verbose=False)
        rets = np.array([float(p["close"].iloc[-1]) / c[i] - 1 for p in outs])
        cache[mk.ts[i]] = (float(np.median(rets)), float(np.mean(rets > 0)))
        done += 1
        if done % 50 == 0:
            save_cache(path, cache)
            log(f"Kronos {mk.tf}: {done}/{len(todo)} velas previstas ({time.time() - t0:.0f} s)")
    save_cache(path, cache)
    log(f"Kronos {mk.tf}: {done} velas nuevas en {time.time() - t0:.0f} s; quedan {len(todo) - done} en esta tanda.")
    return as_arrays(cache, mk.ts)
