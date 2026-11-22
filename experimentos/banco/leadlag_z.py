# Banco (22/11/2026 15:00): "BTC tira de las altcoins" (retraso horario). Uso: python3 leadlag_*.py RUTA/data
# Variante: umbral en desviaciones típicas del hueco (últimos 30 días), para que dispare igual en años tranquilos.
import csv, glob, os, sys, numpy as np, itertools
D = sys.argv[1]; COST = 0.0016; INT = 0.000023
def load(m):
    out = {}
    for f in sorted(glob.glob(os.path.join(D, f"{m}_eur_1h", "*.csv"))):
        for r in csv.DictReader(open(f)): out[r["ts"]] = float(r["close"])
    return out
B = load("btc")
for alt in ["eth", "xrp"]:
    A = load(alt)
    ts = sorted(t for t in A if t in B and t < "2024-01-01")
    a = np.array([A[t] for t in ts]); b = np.array([B[t] for t in ts]); yr = np.array([int(t[:4]) for t in ts])
    rows = []
    for k, z, h, l in itertools.product((1, 2, 3), (1.5, 2, 2.5, 3), (1, 2, 3, 6), (1, 2)):
        gap = np.full(len(a), np.nan); gap[k:] = (b[k:] / b[:-k] - 1) - (a[k:] / a[:-k] - 1)
        W = 720; sd = np.full(len(a), np.nan)
        cs = np.nancumsum(np.nan_to_num(gap) ** 2)
        sd[W + k:] = np.sqrt((cs[W + k:] - cs[k:-W]) / W)
        R = {}; i = W + k
        while i < len(a) - h:
            s = 1 if gap[i] > z * sd[i] else (-1 if gap[i] < -z * sd[i] else 0)
            if s and (s == 1 or l == 2):
                R.setdefault(yr[i], []).append(s * (a[i + h] / a[i] - 1) - COST - (INT * h if s < 0 else 0)); i += h
            else: i += 1
        tot = {Y: (np.prod(1 + np.array(R.get(Y, []))) - 1, len(R.get(Y, []))) for Y in range(2018, 2024)}
        fit = np.mean([tot[Y][0] for Y in range(2018, 2022)])
        rows.append((fit, k, z, h, l, tot))
    rows.sort(key=lambda r: -r[0])
    v = [r for r in rows if r[0] > 0]
    print("==", alt, "ganan en entreno:", len(v), "de", len(rows))
    for fit, k, z, h, l, tot in rows[:5]:
        print(f" k{k} z{z} h{h} {'L/C' if l==2 else 'L'} entreno {fit*100:+.0f}%  " + "  ".join(f"{Y}:{tot[Y][0]*100:+.0f}%({tot[Y][1]})" for Y in range(2018, 2024)))
    for Y in (2022, 2023):
        x = [r[5][Y][0] for r in v]
        if x: print(f"  {Y}: ganan {sum(t>0 for t in x)} de {len(x)} · mediana {np.median(x)*100:+.1f}% · ops/semana mediana {np.median([r[5][Y][1] for r in v])/52:.1f}")
