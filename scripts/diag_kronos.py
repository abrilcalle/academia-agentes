"""Diagnóstico de Kronos: compara previsiones con distintos ajustes y mide el tiempo. Guarda diag/kronos.json."""
import json, os, sys, time, datetime as dt
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src")); sys.path.insert(0, os.path.join(ROOT, "vendor", "Kronos"))
import numpy as np, pandas as pd, torch
import data as datamod
from market import Market
from model import Kronos, KronosPredictor, KronosTokenizer

torch.set_num_threads(os.cpu_count() or 1)
out = {"cpus": os.cpu_count(), "pruebas": []}
d1 = datamod.load_csv(os.path.join(ROOT, "data", "btc_eur_1d.csv"))
h1 = datamod.load_csv(os.path.join(ROOT, "data", "btc_eur_1h"))
mks = {"1d": Market("1d", *datamod.to_arrays(d1, "1d")), "4h": Market("4h", *datamod.to_arrays(datamod.resample(h1, 4), "4h"))}
models = {}
def pred(name, tok):
    if name not in models:
        models[name] = KronosPredictor(Kronos.from_pretrained(name), KronosTokenizer.from_pretrained(tok), device="cpu", max_context=512)
    return models[name]

def run(tf, when, model, tok, ctx, hz, paths, cols):
    mk = mks[tf]; i = mk.idx(when)
    step = mk.ts[1] - mk.ts[0]
    ts = pd.Series(pd.to_datetime([d.isoformat() for d in mk.ts]))
    fr = pd.DataFrame(dict(open=mk.I.o, high=mk.I.h, low=mk.I.l, close=mk.I.c, volume=mk.v))[cols]
    x = fr.iloc[i - ctx + 1:i + 1].reset_index(drop=True); xt = ts.iloc[i - ctx + 1:i + 1].reset_index(drop=True)
    yt = pd.Series(pd.date_range(ts.iloc[i] + step, periods=hz, freq=step))
    t = time.time()
    outs = pred(model, tok).predict_batch([x] * paths, [xt] * paths, [yt] * paths, pred_len=hz, T=1.0, top_p=0.9, sample_count=1, verbose=False)
    secs = time.time() - t
    c0 = float(mk.I.c[i]); fut = float(mk.I.c[min(i + hz, mk.n - 1)])
    rets = [float(p["close"].iloc[-1]) / c0 - 1 for p in outs]
    first = [round(float(v), 1) for v in outs[0]["close"].tolist()]
    return dict(tf=tf, fecha=str(mk.ts[i]), modelo=model.split("/")[-1], ctx=ctx, hz=hz, caminos=paths, columnas=cols,
                segundos=round(secs, 1), cierre=c0, real_al_final=fut, real_ret=round(fut / c0 - 1, 4),
                med=round(float(np.median(rets)), 4), up=round(float(np.mean(np.array(rets) > 0)), 3), camino_1=first)

S, T = "NeoQuasar/Kronos-small", "NeoQuasar/Kronos-Tokenizer-base"
M, T2 = "NeoQuasar/Kronos-mini", "NeoQuasar/Kronos-Tokenizer-2k"
OHLCV = ["open", "high", "low", "close", "volume"]; OHLC = ["open", "high", "low", "close"]
cases = []
for when in ["2021-03-01", "2023-06-01", "2024-11-01", "2026-10-10"]:
    cases.append(("1d", when, S, T, 360, 7, 8, OHLCV))
cases += [("1d", "2026-10-10", S, T, 360, 7, 8, OHLC), ("1d", "2026-10-10", S, T, 120, 7, 8, OHLCV),
          ("1d", "2024-11-01", S, T, 120, 7, 8, OHLCV), ("1d", "2026-10-10", M, T2, 360, 7, 8, OHLCV),
          ("4h", "2026-10-10", S, T, 360, 12, 8, OHLCV), ("4h", "2026-10-10", M, T2, 360, 12, 8, OHLCV)]
for c in cases:
    try:
        out["pruebas"].append(run(*c))
    except Exception as e:  # noqa: BLE001
        out["pruebas"].append(dict(caso=str(c[:4]), error=repr(e)))
    os.makedirs(os.path.join(ROOT, "diag"), exist_ok=True)
    json.dump(out, open(os.path.join(ROOT, "diag", "kronos.json"), "w"), indent=1, ensure_ascii=False)
print(json.dumps(out, indent=1))
