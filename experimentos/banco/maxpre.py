# Comprobación previa (21/11/2026): "cerca del máximo". Rentabilidad media de los 7 días siguientes según
# el filtro de tendencia actual (+1) y la distancia del cierre al máximo de N días. Solo 2018-2023.
import sys, os, datetime as dt, numpy as np
sys.path.insert(0, "lab/src"); import data as datamod
for a in ("btc", "eth", "xrp"):
    c = datamod.load_csv(f"loc/{a}_1d.csv"); ks = sorted(k for k in c if k < dt.datetime(2024, 1, 1))
    ds = [k.date() for k in ks]; x = np.array([c[k][3] for k in ks])
    m50 = np.convolve(x, np.ones(50) / 50, "full")[:len(x)]
    for N in (90, 180):
        out = []
        for y in range(2018, 2024):
            r_in, r_out = [], []
            for i in range(max(N, 60), len(x) - 7):
                if ds[i].year != y: continue
                t = 1 if x[i] > m50[i] else -1
                if (m50[i] - m50[i - 10]) * t <= 0 or t < 0: continue
                hi = x[i - N + 1:i + 1].max(); f = x[i + 7] / x[i] - 1
                (r_in if x[i] >= 0.85 * hi else r_out).append(f)
            out.append(f"{y}: cerca {np.mean(r_in)*100 if r_in else float('nan'):+.1f}% ({len(r_in)}) lejos {np.mean(r_out)*100 if r_out else float('nan'):+.1f}% ({len(r_out)})")
        print(a, N, " | ".join(out))
