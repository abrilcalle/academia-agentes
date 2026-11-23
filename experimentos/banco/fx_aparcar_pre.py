# Banco (23/11/2026): comprobación previa de "aparcar en euros" el dinero que el equipo no reparte cuando el dólar va débil.
# Supone el 100 % del dinero sin repartir: en USDC si ayer USDC/EUR >= su media de N días (o la media no baja en P días); si no, en EUR.
# Cada cambio USDC<->EUR cuesta COSTE (0,10 % = conversion_pct de config). Uso: python fx_aparcar_pre.py [COSTE]
import csv, sys, os, numpy as np
S = os.path.dirname(os.path.abspath(__file__))
COSTE = float(sys.argv[1]) if len(sys.argv) > 1 else 0.001
rows = list(csv.reader(open(os.path.join(S, "..", "..", "data", "usdc_eur_1d.csv"))))[1:]
d = np.array([r[0][:10] for r in rows]); c = np.array([float(r[4]) for r in rows])
r = np.r_[0, c[1:] / c[:-1] - 1]
for N in (20, 50, 100):
    for P in (0, 10):
        ma = np.convolve(c, np.ones(N) / N, "full")[:len(c)]
        eur = np.zeros(len(c), bool)
        for t in range(N + P, len(c)):
            eur[t] = c[t] < ma[t] and (P == 0 or ma[t] < ma[t - P])
        out = []
        for y in range(2018, 2024):
            i = np.where(np.char.startswith(d, str(y)))[0]
            e = eur[i - 1]; sw = int(np.sum(e[1:] != e[:-1]))
            out.append(f"{y} usdc {np.prod(1 + r[i]) * 100 - 100:+.1f} aparcar {(np.prod(1 + r[i] * ~e) * (1 - COSTE) ** sw) * 100 - 100:+.1f} ({sw})")
        print(f"N{N} P{P}: " + " | ".join(out))
