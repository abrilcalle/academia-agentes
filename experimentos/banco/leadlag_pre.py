# Banco (22/11/2026 15:00): "BTC tira de las altcoins" (retraso horario). Uso: python3 leadlag_*.py RUTA/data
# Comprobación previa: ¿el movimiento de BTC en la última(s) hora(s) anticipa el de ETH/XRP/SOL en la(s) siguiente(s)?
import csv, glob, os, sys, numpy as np, datetime as dt
D = sys.argv[1]
def load(m):
    out = {}
    for f in sorted(glob.glob(os.path.join(D, f"{m}_eur_1h", "*.csv"))):
        for r in csv.DictReader(open(f)):
            out[r["ts"]] = float(r["close"])
    return out
B = load("btc")
for alt in ["eth", "xrp", "sol"]:
    A = load(alt)
    ts = sorted(t for t in A if t in B and t < "2024-01-01")
    b = np.log([B[t] for t in ts]); a = np.log([A[t] for t in ts])
    yr = np.array([int(t[:4]) for t in ts])
    rb = np.diff(b); ra = np.diff(a); y = yr[1:]
    for k in (1, 3, 6):
        for h in (1, 3, 6):
            line = []
            for Y in range(2018, 2024):
                idx = np.where(y == Y)[0]
                idx = idx[(idx >= k) & (idx < len(ra) - h)]
                if len(idx) < 500: line.append("   -  "); continue
                sb = np.array([rb[i - k + 1:i + 1].sum() for i in idx])
                sa = np.array([ra[i - k + 1:i + 1].sum() for i in idx])
                gap = sb - sa
                fut = np.array([ra[i + 1:i + 1 + h].sum() for i in idx])
                c = np.corrcoef(gap, fut)[0, 1]
                line.append(f"{c:+.3f}")
            print(alt, f"k{k} h{h}", " ".join(line))
