# Banco (22/11/2026 15:00): "BTC tira de las altcoins" (retraso horario). Uso: python3 leadlag_*.py RUTA/data
# Regla "BTC tira de la altcoin": si en las últimas k horas BTC sube (baja) un g % más que la altcoin, comprar (vender en corto) la altcoin h horas.
# Coste ida y vuelta USDC: 2 × (0,05 + 0,03) % = 0,16 %; cortos pagan 0,0023 %/h. Sin solapes (una operación a la vez).
import csv, glob, os, sys, numpy as np, itertools
D = sys.argv[1]; COST = 0.0016; INT = 0.000023
def load(m):
    out = {}
    for f in sorted(glob.glob(os.path.join(D, f"{m}_eur_1h", "*.csv"))):
        for r in csv.DictReader(open(f)): out[r["ts"]] = float(r["close"])
    return out
B = load("btc")
def run(a, b, yr, k, g, h, lados):
    res = {}
    n = len(a); i = k
    while i < n - h:
        gap = (b[i] / b[i - k] - 1) - (a[i] / a[i - k] - 1)
        s = 1 if gap > g else (-1 if gap < -g else 0)
        if s and (s == 1 or lados == 2):
            r = s * (a[i + h] / a[i] - 1) - COST - (INT * h if s < 0 else 0)
            res.setdefault(yr[i], []).append(r); i += h
        else: i += 1
    return res
for alt in ["eth", "xrp", "sol"]:
    A = load(alt)
    ts = sorted(t for t in A if t in B and t < "2024-01-01")
    a = np.array([A[t] for t in ts]); b = np.array([B[t] for t in ts]); yr = np.array([int(t[:4]) for t in ts])
    rows = []
    for k, g, h, l in itertools.product((1, 2, 3, 6), (0.005, 0.01, 0.015, 0.02, 0.03), (1, 2, 3, 6, 12), (1, 2)):
        R = run(a, b, yr, k, g, h, l)
        tot = {Y: (np.prod(1 + np.array(R.get(Y, []))) - 1, len(R.get(Y, []))) for Y in range(2018, 2024)}
        tr = [Y for Y in range(2018, 2022) if tot[Y][1]]
        fit = np.mean([tot[Y][0] for Y in tr]) if tr else -9
        rows.append((fit, k, g, h, l, tot))
    rows.sort(key=lambda r: -r[0])
    print("==", alt, "combinaciones con entreno > 0:", sum(r[0] > 0 for r in rows), "de", len(rows))
    for fit, k, g, h, l, tot in rows[:6]:
        print(f" k{k} g{g:.3f} h{h} {'L/C' if l==2 else 'L'} entreno {fit*100:+.0f}%  " + "  ".join(f"{Y}:{tot[Y][0]*100:+.0f}%({tot[Y][1]})" for Y in range(2018, 2024)))
    v = [r for r in rows if r[0] > 0]
    if v:
        for Y in (2022, 2023):
            x = [r[5][Y][0] for r in v if r[5][Y][1]]
            print(f"  {Y}: de las {len(v)} que ganan en entreno, ganan {sum(t>0 for t in x)} · mediana {np.median(x)*100:+.1f}%")
