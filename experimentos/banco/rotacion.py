# Banco (24/11/2026 15:05): agente "rotación" (dual momentum de Antonacci entre mercados): cada semana (o día) se queda
# con el mercado más fuerte por impulso de N días si su impulso es positivo; si no, USDC (o corto del más débil en modo "lc").
# Prueba individual previa al banco de equipos. Uso: python3 rotacion.py  (lee ../../data)
import csv, os, datetime as dt, itertools
import numpy as np
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")
def load(f):
    out = {}
    for r in csv.DictReader(open(os.path.join(D, f))):
        out[dt.date.fromisoformat(r["ts"][:10])] = float(r["close"])
    return out
fx = load("usdc_eur_1d.csv")
px = {k: load(f"{k}_eur_1d.csv") for k in ("btc", "eth", "xrp", "sol")}
days = [d for d in sorted(px["btc"]) if dt.date(2017, 12, 1) <= d < dt.date(2024, 1, 1)]
FX = np.array([fx.get(d, np.nan) for d in days]); FX = np.where(np.isnan(FX), np.nan, FX)
for i in range(1, len(FX)):
    if np.isnan(FX[i]): FX[i] = FX[i - 1]
U = {k: np.array([px[k].get(d, np.nan) for d in days]) / FX for k in px}   # precio en USDC
for k in U:
    a = U[k]
    for i in range(1, len(a)):
        if np.isnan(a[i]) and not np.isnan(a[i - 1]): a[i] = a[i - 1]   # día sin vela: se repite el cierre
C = 0.0008; INT = 0.000023 * 24
def run(N, mkts, mode, weekly, start_sol=dt.date(2020, 8, 1)):
    T = len(days); pos = None; side = 0; v = 1.0; val = np.ones(T)
    for t in range(1, T):
        # rendimiento del día con la posición de ayer (en USDC) y luego en EUR
        r = 0.0
        if pos is not None:
            rr = U[pos][t] / U[pos][t - 1] - 1
            r = rr if side > 0 else -rr - INT
        v *= (1 + r) * FX[t] / FX[t - 1]
        # decidir al cierre de t
        if (not weekly or days[t].weekday() == 6) and t >= N:
            mom = {}
            for k in mkts:
                if k == "sol" and days[t - N] < start_sol: continue
                a, b = U[k][t - N], U[k][t]
                if np.isnan(a) or np.isnan(b): continue
                mom[k] = b / a - 1
            new, ns = None, 0
            if mom:
                best = max(mom, key=mom.get); worst = min(mom, key=mom.get)
                def tend(k, sg):
                    a = U[k][max(0, t - 59): t + 1]; m = np.convolve(a, np.ones(50) / 50, "valid")
                    return len(m) > 10 and sg * (a[-1] - m[-1]) > 0 and sg * (m[-1] - m[-11]) > 0
                if mom[best] > 0 and (mode[-1] != "f" or tend(best, 1)): new, ns = best, 1
                elif mode == "lcf" and mom[worst] < 0 and tend(worst, -1): new, ns = worst, -1
                elif mode == "lc": new, ns = worst, -1
            if (new, ns) != (pos, side):
                legs = (pos is not None) + (new is not None)
                v *= 1 - C * legs
                pos, side = new, ns
        val[t] = v
    return val
def stats(y, val):
    idx = [i for i, d in enumerate(days) if d.year == y]
    s = val[idx[0] - 1: idx[-1] + 1] / val[idx[0] - 1]
    dd = float(np.max(1 - s / np.maximum.accumulate(s)))
    dsub = [days[idx[0] - 1]] + [days[i] for i in idx]
    wk = {}
    for d, x in zip(dsub, s): wk[(d - dt.timedelta(days=d.weekday())).isoformat()] = x
    wv = list(wk.values()); wr = [wv[i] / wv[i - 1] - 1 for i in range(1, len(wv))]
    return s[-1] - 1, np.mean([w > 1e-4 for w in wr]), dd
TR, VA = [2018, 2019, 2020, 2021], [2022, 2023]
rows = []
for N, mode, weekly, U4 in itertools.product([7, 14, 30, 60, 90, 120], ["l", "lc", "lf", "lcf"], [True, False], [False, True]):
    mk = ["btc", "eth", "xrp"] + (["sol"] if U4 else [])
    val = run(N, mk, mode, weekly)
    st = {y: stats(y, val) for y in TR + VA}
    score = np.mean([st[y][0] - 2 * max(0, st[y][2] - 0.25) for y in TR])
    rows.append((score, N, mode, "sem" if weekly else "dia", "4m" if U4 else "3m", st))
rows.sort(key=lambda r: -r[0])
print("score | N modo reb univ | " + " | ".join(f"{y} ret/verde/dd" for y in TR + VA))
for r in rows:
    print(f"{r[0]:+.2f} | {r[1]:3d} {r[2]:2s} {r[3]} {r[4]} | " + " | ".join(f"{r[5][y][0]*100:+5.0f} {r[5][y][1]*100:3.0f} {r[5][y][2]*100:3.0f}" for y in TR + VA))
for lab, sel in [("todas", rows), ("mitad mejor en entreno", rows[:len(rows)//2])]:
    print(lab, *[f"{y}: ret {np.median([r[5][y][0] for r in sel])*100:+.0f} % verde {np.median([r[5][y][1] for r in sel])*100:.0f} % dd {np.median([r[5][y][2] for r in sel])*100:.0f} % gana {sum(r[5][y][0]>0 for r in sel)}/{len(sel)}" for y in VA])
