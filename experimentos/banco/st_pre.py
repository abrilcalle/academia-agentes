"""Comprobación previa (laboratorio 27/11/2026 10:00): piezas "Supertrend" y "ADX / DMI" que faltan en el genoma
(75 ideas de la biblioteca usan ADX y 27 Supertrend, y solo se pueden aproximar).

Familias (velas de 1 d y 4 h; señal al cierre de la vela, posición desde ese cierre hasta el siguiente):
  st   = Supertrend(n, m): comprado mientras el precio va sobre la banda (ATR de Wilder n, m veces); con "LC",
         en corto mientras va por debajo.
  st+adxT = igual, pero solo se abre/mantiene posición si ADX(14) > T (20 / 25 / 30).
  dmi  = comprado si +DI > −DI y ADX(n) > T (n 10 / 14 / 20, T 20 / 25 / 30); con "LC", corto si −DI > +DI.
Precio en USDC (euros ÷ USDC/EUR del día), coste 0,08 % por cada cambio de posición, interés del corto por hora.
Datos cortados el 01/01/2024. Se elige con 2018-21 y se mira 2022 y 2023 por separado.

Uso: python3 experimentos/banco/st_pre.py   (desde la raíz del repo)
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
YEARS = [2018, 2019, 2020, 2021, 2022, 2023]


def cargar(m, tf):
    fx = data.load_csv("data/usdc_eur_1d.csv")
    fxd = {d.date(): v[3] for d, v in fx.items()}
    if tf == "1d":
        c = data.load_csv(f"data/{m}_eur_1d.csv")
        ts = sorted(d for d in c if d.isoformat() < CORTE)
        rows = [(d, c[d]) for d in ts]
    else:
        c = data.load_csv(f"data/{m}_eur_1h")
        g = defaultdict(list)
        for d in sorted(c):
            if d.isoformat() >= CORTE:
                continue
            g[d.replace(hour=d.hour // 4 * 4)].append(c[d])
        rows = [(d, [v[0][0], max(x[1] for x in v), min(x[2] for x in v), v[-1][3]]) for d, v in sorted(g.items()) if len(v) >= 3]
    last = 1.0
    T, O, H, L, C = [], [], [], [], []
    for d, v in rows:
        last = fxd.get(d.date(), last) or last
        T.append(d); O.append(v[0] / last); H.append(v[1] / last); L.append(v[2] / last); C.append(v[3] / last)
    return T, np.array(H), np.array(L), np.array(C)


def wilder(x, n):
    out = np.full(len(x), np.nan)
    if len(x) <= n:
        return out
    out[n] = np.nanmean(x[1:n + 1])
    for i in range(n + 1, len(x)):
        out[i] = out[i - 1] + (x[i] - out[i - 1]) / n
    return out


def tr_(H, L, C):
    pc = np.r_[C[0], C[:-1]]
    return np.maximum(H - L, np.maximum(abs(H - pc), abs(L - pc)))


def supertrend(H, L, C, n, m):
    atr = wilder(tr_(H, L, C), n)
    mid = (H + L) / 2
    ub, lb = mid + m * atr, mid - m * atr
    fu, fl = ub.copy(), lb.copy()
    d = np.zeros(len(C))
    for i in range(1, len(C)):
        if np.isnan(atr[i]):
            continue
        fu[i] = ub[i] if (np.isnan(fu[i - 1]) or ub[i] < fu[i - 1] or C[i - 1] > fu[i - 1]) else fu[i - 1]
        fl[i] = lb[i] if (np.isnan(fl[i - 1]) or lb[i] > fl[i - 1] or C[i - 1] < fl[i - 1]) else fl[i - 1]
        prev = d[i - 1] if d[i - 1] != 0 else 1
        if prev == 1:
            d[i] = -1 if C[i] < fl[i] else 1
        else:
            d[i] = 1 if C[i] > fu[i] else -1
    return d


def adx(H, L, C, n):
    up = np.r_[0, H[1:] - H[:-1]]
    dn = np.r_[0, L[:-1] - L[1:]]
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    atr = wilder(tr_(H, L, C), n)
    with np.errstate(invalid="ignore", divide="ignore"):
        pdi = 100 * wilder(pdm, n) / atr
        mdi = 100 * wilder(mdm, n) / atr
        dx = 100 * abs(pdi - mdi) / (pdi + mdi)
    a = np.full(len(C), np.nan)
    ok = ~np.isnan(dx)
    if ok.sum() > n:
        a[ok] = wilder(dx[ok], n)
    return a, pdi, mdi


def correr(T, C, pos, horas):
    r = np.zeros(len(C))
    prev = 0.0
    for i in range(1, len(C)):
        p = pos[i - 1]
        g = C[i] / C[i - 1] - 1
        r[i] = p * g - abs(p - prev) * COSTE - (INTERES_H * horas if p < 0 else 0)
        prev = p
    return r


def metricas(T, r, pos, year):
    idx = [i for i, d in enumerate(T) if d.year == year]
    if len(idx) < 30:
        return None
    eq = np.cumprod(1 + r[idx])
    dd = float(np.max(1 - eq / np.maximum.accumulate(eq)))
    wk = defaultdict(lambda: 1.0)
    for i in idx:
        wk[T[i].isocalendar()[:2]] *= 1 + r[i]
    w = np.array(list(wk.values())) - 1
    ch = sum(1 for i in idx if pos[i] != pos[i - 1])
    return dict(ret=float(eq[-1] - 1), verde=float((w > 0).mean()), dd=dd, cambios=ch)


def main():
    out = []
    for m in MERCADOS:
        for tf in ("1d", "4h"):
            T, H, L, C = cargar(m, tf)
            horas = 24 if tf == "1d" else 4
            A14 = adx(H, L, C, 14)[0]
            fams = []
            for n in (7, 10, 14, 20):
                for mm in (2, 3, 4):
                    d = supertrend(H, L, C, n, mm)
                    for fil in (0, 20, 25, 30):
                        ok = np.ones(len(C), bool) if fil == 0 else np.nan_to_num(A14, nan=0) > fil
                        fams.append((f"st{n}x{mm}" + (f"+adx{fil}" if fil else ""), d, ok))
            for n in (10, 14, 20):
                a, pdi, mdi = adx(H, L, C, n)
                d = np.where(np.nan_to_num(pdi) > np.nan_to_num(mdi), 1, -1)
                for thr in (20, 25, 30):
                    fams.append((f"dmi{n}>{thr}", d, np.nan_to_num(a, nan=0) > thr))
            for name, d, ok in fams:
                for lado in ("L", "LC"):
                    pos = np.where(ok & (d > 0), 1.0, 0.0)
                    if lado == "LC":
                        pos = pos - np.where(ok & (d < 0), 1.0, 0.0)
                    r = correr(T, C, pos, horas)
                    M = {y: metricas(T, r, pos, y) for y in YEARS}
                    out.append((m, tf, name, lado, M))

    def fmt(x):
        return "   —   " if x is None else f"{x['ret']*100:+5.0f}%/{x['verde']*100:3.0f}%/{x['dd']*100:3.0f}%"

    tot = defaultdict(list)
    for m, tf, name, lado, M in out:
        for y in YEARS:
            if M[y]:
                tot[y].append(M[y]["ret"])
    print("Medianas de todas las combinaciones por año (rent):", {y: f"{np.median(v)*100:+.0f}% (ganan {sum(np.array(v)>0)}/{len(v)})" for y, v in tot.items()})
    for crit in ("gana3de4", "gana3de4_verde50"):
        sel = []
        for m, tf, name, lado, M in out:
            tr = [M[y] for y in (2018, 2019, 2020, 2021) if M[y]]
            if len(tr) < 2:
                continue
            ok = sum(x["ret"] > 0 for x in tr) >= len(tr) - 1 and np.mean([x["ret"] for x in tr]) > 0
            if crit.endswith("verde50"):
                ok = ok and np.mean([x["verde"] for x in tr]) > 0.5
            if ok:
                sel.append((m, tf, name, lado, M))
        print(f"\n== Elegidas con 2018-21 ({crit}): {len(sel)} de {len(out)}")
        for y in (2022, 2023):
            v = [M[y] for *_, M in sel if M[y]]
            if not v:
                continue
            print(f"  {y}: {len(v)} · ganan {sum(x['ret'] > 0 for x in v)} · mediana rent {np.median([x['ret'] for x in v])*100:+.1f} % · "
                  f"semanas en verde {np.median([x['verde'] for x in v])*100:.0f} % · caída {np.median([x['dd'] for x in v])*100:.0f} % · "
                  f"cumplen (>50 % sem, +10 %, caída ≤ 25 %) {sum(x['verde'] > 0.5 and x['ret'] >= 0.10 and x['dd'] <= 0.25 for x in v)}")
        both = [s for s in sel if all(s[4][y] and s[4][y]["ret"] > 0 for y in (2022, 2023))]
        print(f"  ganan en 2022 y 2023 a la vez: {len(both)}")
        by = defaultdict(lambda: [0, 0, 0])
        for m, tf, name, lado, M in sel:
            k = (m, tf, lado, name.split("+")[0][:3] + ("+adx" if "+adx" in name else ""))
            by[k][0] += 1
            by[k][1] += bool(M[2022] and M[2022]["ret"] > 0)
            by[k][2] += bool(M[2023] and M[2023]["ret"] > 0)
        for k, v in sorted(by.items()):
            print(f"   {k}: {v[0]} elegidas · ganan 2022 {v[1]} · ganan 2023 {v[2]}")
        if crit == "gana3de4":
            for m, tf, name, lado, M in sel[:400]:
                if M[2022] and M[2023] and M[2022]["ret"] > 0 and M[2023]["ret"] > 0:
                    print(f"     {m} {tf} {name:14} {lado:2} | " + " ".join(fmt(M[y]) for y in YEARS))


if __name__ == "__main__":
    main()
