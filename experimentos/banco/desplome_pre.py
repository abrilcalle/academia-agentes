"""Comprobación previa (laboratorio 25/11/2026 21:00): "reversión tras desplome" en velas de 1 h.

Si en las últimas k horas el precio (en USDC) cae más de z veces su volatilidad normal (la de los
30 días anteriores), comprar en la apertura de la vela siguiente y vender H horas después
(y el espejo: vender en corto tras una subida brusca). Coste USDC 0,08 % por lado (+ interés del
corto). Solo se miden 2018-2023: se elige con 2018-21 y se mira 2022 y 2023 por separado.

Uso: python3 experimentos/banco/desplome_pre.py   (desde la raíz del repo)
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
import data  # noqa: E402

COSTE = 0.0008            # comisión 0,05 % + deslizamiento 0,03 % por lado
INTERES_H = 0.000023      # 0,0023 %/h del préstamo en corto
CORTE = "2024-01-01"      # nada de 2024 en adelante
MERCADOS = ["btc", "eth", "xrp", "sol"]
KS = [1, 4, 12, 24]
ZS = [2.5, 3.0, 4.0]
HS = [6, 12, 24, 48]
FILTROS = ["nada", "afavor", "contra"]   # afavor = compra con tendencia diaria alcista (media 50 sube) / corto con bajista
YEARS = [2018, 2019, 2020, 2021, 2022, 2023]


def cargar(m):
    c = data.load_csv(f"data/{m}_eur_1h")
    fx = data.load_csv("data/usdc_eur_1d.csv")
    fxd = {d.date(): v[3] for d, v in fx.items()}
    ts = sorted(d for d in c if d.isoformat() < CORTE)
    o = np.array([c[d][0] for d in ts]); cl = np.array([c[d][3] for d in ts])
    last = None
    f = []
    for d in ts:
        last = fxd.get(d.date(), last)
        f.append(last if last else 1.0)
    f = np.array(f)
    o, cl = o / f, cl / f                      # precio en USDC (aprox. con el cambio del día)
    # tendencia diaria (día anterior cerrado): cierre > media 50 y media 50 > la de hace 10 días
    days = sorted({d.date() for d in ts})
    dclose = {}
    for d, x in zip(ts, cl):
        dclose[d.date()] = x
    dc = np.array([dclose[d] for d in days])
    tr = np.zeros(len(days))
    for i in range(60, len(days)):
        ma = dc[i - 49:i + 1].mean(); ma10 = dc[i - 59:i - 9].mean()
        tr[i] = 1 if (dc[i] > ma and ma > ma10) else (-1 if (dc[i] < ma and ma < ma10) else 0)
    di = {d: i for i, d in enumerate(days)}
    trh = np.array([tr[di[d.date()] - 1] if di[d.date()] > 0 else 0 for d in ts])   # la de ayer
    yr = np.array([d.year for d in ts])
    return ts, o, cl, trh, yr


_CACHE = {}


def _sig_rk(cl, k):
    key = (id(cl), k)
    if key not in _CACHE:
        lr = np.diff(np.log(cl), prepend=np.log(cl[0]))
        n = len(cl); W = 720
        cs = np.concatenate([[0], np.cumsum(lr ** 2)])
        sig = np.full(n, np.nan)
        t = np.arange(W + k, n)
        sig[t] = np.sqrt((cs[t - k + 1] - cs[t - k + 1 - W]) / W * k)
        rk = np.full(n, np.nan)
        rk[k:] = np.log(cl[k:] / cl[:-k])
        _CACHE[key] = (sig, rk)
    return _CACHE[key]


def eventos(o, cl, trh, k, z, H, filtro, lado):
    sig, rk = _sig_rk(cl, k)
    n = len(cl); W = 720
    with np.errstate(invalid="ignore"):
        hit = (rk < -z * sig) if lado == 1 else (rk > z * sig)
    if filtro == "afavor":
        hit &= trh == lado
    elif filtro == "contra":
        hit &= trh != lado
    cand = np.flatnonzero(hit)
    out = []
    nxt = W + k
    for t in cand:
        if t < nxt or t >= n - H - 1:
            continue
        e = o[t + 1]; x = cl[t + H]
        r = (x / e - 1) if lado == 1 else (e / x - 1 - INTERES_H * H)
        out.append((t + 1, r - 2 * COSTE))
        nxt = t + H + 1
    return out


def resumen(ev, yr):
    res = {}
    for y in YEARS:
        rr = np.array([r for i, r in ev if yr[i] == y])
        if len(rr) == 0:
            res[y] = (0, 0.0, 0.0, 0.0); continue
        tt = rr.mean() / (rr.std(ddof=1) / math.sqrt(len(rr))) if len(rr) > 2 and rr.std() > 0 else 0.0
        res[y] = (len(rr), rr.mean() * 100, tt, (rr > 0).mean() * 100)
    return res


def main():
    filas = []
    for m in MERCADOS:
        ts, o, cl, trh, yr = cargar(m)
        for lado in (1, -1):
            for k in KS:
                for z in ZS:
                    for H in HS:
                        for f in FILTROS:
                            ev = eventos(o, cl, trh, k, z, H, f, lado)
                            filas.append((m, lado, k, z, H, f, resumen(ev, yr)))
        print("hecho", m, file=sys.stderr)
    import pickle
    pickle.dump(filas, open(os.environ.get("OUT", "/tmp/desplome.pkl"), "wb"))


if __name__ == "__main__":
    main()
