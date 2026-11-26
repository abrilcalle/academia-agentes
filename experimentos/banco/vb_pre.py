"""Comprobación previa (laboratorio 26/11/2026 15:00): "ruptura de volatilidad" de Larry Williams / Kang
(la versión exacta, que las ideas de la biblioteca solo aproximan): cada día (UTC), nivel = apertura del día
+ k × rango (máximo − mínimo) de ayer. En velas de 1 h, la primera vela que cierra por encima del nivel
→ compra a mercado en la apertura de la vela siguiente; se vende en la apertura del día siguiente.
Espejo en corto: apertura − k × rango, cierre por debajo (con interés del préstamo).
k fijo (0,3–1,0) o "ruido" (media de 20 días de 1 − |cierre − apertura| / rango, la variante coreana).
Filtros: nada · ma5 (apertura del día sobre la media de 5 cierres; al revés para el corto) ·
tend (filtro de tendencia del equipo: media 50 sube y precio encima; al revés para el corto).
Precio en USDC (euros ÷ USDC/EUR del día), coste 0,08 % por lado. Datos cortados el 01/01/2024.
Se elige con 2018-21 y se mira 2022 y 2023 por separado.

Uso: python3 experimentos/banco/vb_pre.py   (desde la raíz del repo)
"""
import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
import data  # noqa: E402

COSTE = 0.0008
INTERES_H = 0.000023
CORTE = "2024-01-01"
MERCADOS = ["btc", "eth", "xrp", "sol"]
KS = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0, "ruido"]
FILTROS = ["nada", "ma5", "tend"]
LADOS = ["L", "LC"]
YEARS = [2018, 2019, 2020, 2021, 2022, 2023]


def cargar(m):
    c = data.load_csv(f"data/{m}_eur_1h")
    fx = data.load_csv("data/usdc_eur_1d.csv")
    fxd = {d.date(): v[3] for d, v in fx.items()}
    ts = sorted(d for d in c if d.isoformat() < CORTE)
    last = 1.0
    byday = defaultdict(list)
    for d in ts:
        last = fxd.get(d.date(), last) or last
        o, h, l, cl = (x / last for x in c[d][:4])
        byday[d.date()].append((d.hour, o, h, l, cl))
    days = sorted(byday)
    D = []
    for dd in days:
        b = byday[dd]
        if len(b) < 20:
            D.append(None); continue
        D.append(dict(o=b[0][1], h=max(x[2] for x in b), l=min(x[3] for x in b), c=b[-1][4],
                      hours=[(x[0], x[1], x[4]) for x in b]))
    return days, D


def simular(days, D, k, filtro, lado):
    """Rentabilidad de cada día (por la fecha de la salida = apertura del día siguiente)."""
    n = len(days)
    ret = np.zeros(n)
    ntr = np.zeros(n)
    closes = np.array([x["c"] if x else np.nan for x in D])
    noise = np.full(n, np.nan)
    for i in range(n):
        x = D[i]
        if x and x["h"] > x["l"]:
            noise[i] = 1 - abs(x["c"] - x["o"]) / (x["h"] - x["l"])
    for i in range(61, n - 1):
        x, y, z = D[i], D[i - 1], D[i + 1]
        if not (x and y and z):
            continue
        R = y["h"] - y["l"]
        if R <= 0:
            continue
        kk = np.nanmean(noise[i - 20:i]) if k == "ruido" else k
        up, dn = x["o"] + kk * R, x["o"] - kk * R
        # filtros (con el día anterior cerrado)
        okL = okS = True
        if filtro == "ma5":
            ma = np.nanmean(closes[i - 5:i])
            okL, okS = x["o"] > ma, x["o"] < ma
        elif filtro == "tend":
            ma = np.nanmean(closes[i - 50:i]); ma10 = np.nanmean(closes[i - 60:i - 10])
            pc = closes[i - 1]
            okL, okS = (pc > ma and ma > ma10), (pc < ma and ma < ma10)
        hrs = x["hours"]
        for j in range(len(hrs) - 1):
            _, _, cl = hrs[j]
            if okL and cl > up:
                ent = hrs[j + 1][1]; sal = z["o"]
                ret[i + 1] = (sal / ent) * (1 - COSTE) ** 2 - 1
                ntr[i + 1] = 1
                break
            if lado == "LC" and okS and cl < dn:
                ent = hrs[j + 1][1]; sal = z["o"]
                hh = len(hrs) - 1 - j
                ret[i + 1] = (2 - sal / ent) * (1 - COSTE) ** 2 - 1 - INTERES_H * hh
                ntr[i + 1] = 1
                break
    return ret, ntr


def metricas(days, ret, ntr, year):
    idx = [i for i, d in enumerate(days) if d.year == year]
    if not idx:
        return None
    r = ret[idx]
    eq = np.cumprod(1 + r)
    dd = float(np.max(1 - eq / np.maximum.accumulate(eq)))
    wk = defaultdict(float)
    for i in idx:
        wk[days[i].isocalendar()[:2]] = (1 + wk[days[i].isocalendar()[:2]]) * (1 + ret[i]) - 1
    w = np.array(list(wk.values()))
    return dict(ret=float(eq[-1] - 1), verde=float((w > 0).mean()), dd=dd,
                tps=float(ntr[idx].sum() / max(1, len(w))))


def main():
    out = []
    for m in MERCADOS:
        days, D = cargar(m)
        for k in KS:
            for f in FILTROS:
                for lado in LADOS:
                    ret, ntr = simular(days, D, k, f, lado)
                    M = {y: metricas(days, ret, ntr, y) for y in YEARS}
                    out.append((m, k, f, lado, M))
    def fmt(x):
        return "   —   " if x is None else f"{x['ret']*100:+6.0f}%/{x['verde']*100:3.0f}%/{x['dd']*100:3.0f}%/{x['tps']:.1f}"
    print("mercado k filtro lado | 2018 … 2023 (rent/semanas en verde/caída/operaciones por semana)")
    for m, k, f, lado, M in out:
        print(f"{m} {k!s:5} {f:4} {lado:2} | " + " ".join(fmt(M[y]) for y in YEARS))
    # elección con el entreno: gana en >= 3 de 4 años (los que hay) y media > 0, semanas en verde medias > 50 %
    print("\nElegidas con 2018-21 (gana en >= 3 de los años de entreno con datos, media de semanas en verde > 50 %):")
    sel = []
    for m, k, f, lado, M in out:
        tr = [M[y] for y in (2018, 2019, 2020, 2021) if M[y] and M[y]["tps"] > 0.3]
        if len(tr) < 2:
            continue
        gan = sum(x["ret"] > 0 for x in tr)
        if gan >= len(tr) - 1 and np.mean([x["verde"] for x in tr]) > 0.5 and np.mean([x["ret"] for x in tr]) > 0:
            sel.append((m, k, f, lado, M))
    for m, k, f, lado, M in sel:
        print(f"  {m} {k!s:5} {f:4} {lado:2} | 2022 {fmt(M[2022])} | 2023 {fmt(M[2023])}")
    if sel:
        for y in (2022, 2023):
            v = [M[y] for *_, M in sel if M[y]]
            print(f"  {y}: elegidas {len(v)} · ganan {sum(x['ret'] > 0 for x in v)} · mediana rent {np.median([x['ret'] for x in v])*100:+.1f} % · "
                  f"semanas en verde {np.median([x['verde'] for x in v])*100:.0f} % · caída {np.median([x['dd'] for x in v])*100:.0f} % · "
                  f"cumplen (>50 % semanas, +10 %, caída ≤ 25 %) {sum(x['verde'] > 0.5 and x['ret'] >= 0.10 and x['dd'] <= 0.25 for x in v)}")
    # cumplen en los dos años de validación
    both = [(m, k, f, lado) for m, k, f, lado, M in sel if all(M[y] and M[y]['ret'] > 0 for y in (2022, 2023))]
    print("  ganan en 2022 y 2023:", both)


if __name__ == "__main__":
    main()
