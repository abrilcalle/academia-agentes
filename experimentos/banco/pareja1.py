# Banco (10/11/2026). Uso: python pareja1.py (lee data/ directamente, guarda rows.pkl).
# Estudio: operaciones de pareja (largo una cripto, corto otra, mismo dinero) en velas diarias. 2018-2023 (datos cortados 01/01/2024).
import csv, datetime as dt, itertools, sys, numpy as np
D = "/home/claude/academia-agentes/data/"
def load(f):
    out = {}
    for r in csv.DictReader(open(D + f)):
        out[r["ts"][:10]] = float(r["close"])
    return out
px = {k: load(f"{k}_eur_1d.csv") for k in ("btc", "eth", "xrp", "sol")}
fx = load("usdc_eur_1d.csv")
days = sorted(d for d in px["btc"] if "2017-12-02" <= d < "2024-01-01" and d in fx)
FX = np.array([fx[d] for d in days])
U = {k: np.array([px[k].get(d, np.nan) / fx[d] for d in days]) for k in px}  # precio en USDC
COM = 0.0005 + 0.0003   # comisión + diferencia por orden
SHORT_DAY = 0.000023 * 24
yrs = np.array([int(d[:4]) for d in days])
wk = np.array([dt.date.fromisoformat(d).isocalendar()[:2] for d in days])

def run(a, b, mode, n, k, kx, H):
    la, lb = np.log(U[a]), np.log(U[b])
    sp = la - lb
    T = len(days); pos = np.zeros(T)  # +1 = largo a / corto b
    cur, age = 0, 0
    for t in range(n, T):
        w = sp[t - n:t + 1]
        if np.isnan(w).any(): cur = 0; pos[t] = 0; continue
        if mode == "mr":
            z = (sp[t] - w.mean()) / (w.std() + 1e-12)
            if cur == 0:
                if z > k: cur, age = -1, 0
                elif z < -k: cur, age = 1, 0
            else:
                age += 1
                if (cur == 1 and z > -kx) or (cur == -1 and z < kx) or age >= H: cur = 0
        else:  # momentum de la pareja
            m = sp[t] - sp[t - n]
            vol = np.std(np.diff(w)) * np.sqrt(n) + 1e-12
            z = m / vol
            if cur == 0:
                if z > k: cur, age = 1, 0
                elif z < -k: cur, age = -1, 0
            else:
                age += 1
                if (cur == 1 and z < kx) or (cur == -1 and z > -kx) or age >= H: cur = 0
        pos[t] = cur
    ra = np.r_[0, U[a][1:] / U[a][:-1] - 1]; rb = np.r_[0, U[b][1:] / U[b][:-1] - 1]
    ra, rb = np.nan_to_num(ra), np.nan_to_num(rb)
    p = np.r_[0, pos[:-1]]  # posición decidida al cierre de ayer
    leg = 0.5 * (p * ra - p * rb)
    cost = np.abs(np.diff(np.r_[0, p])) * COM  # cada cambio = 2 órdenes de media posición
    rusd = leg - cost - (p != 0) * 0.5 * SHORT_DAY
    fxr = np.r_[0, FX[1:] / FX[:-1] - 1]
    reur = (1 + rusd) * (1 + fxr) - 1
    return reur, rusd, p

def stats(r, mask):
    rr = r[mask]
    eq = np.cumprod(1 + rr)
    dd = (1 - eq / np.maximum.accumulate(eq)).max()
    w = wk[mask]; keys = [tuple(x) for x in w]
    wr = {}
    for kk, x in zip(keys, rr): wr[kk] = wr.get(kk, 1) * (1 + x)
    verde = np.mean([v - 1 > 0.0001 for v in wr.values()])
    return eq[-1] - 1, verde, dd

if __name__ == "__main__":
    pairs = [("btc", "eth"), ("btc", "xrp"), ("eth", "xrp")]
    grid = list(itertools.product(["mr"], [20, 40, 60], [1.5, 2.0, 2.5], [0.0, 0.5], [10, 20, 40])) + \
           list(itertools.product(["mo"], [10, 20, 40, 60], [0.5, 1.0, 1.5], [0.0, 0.5], [10, 20, 40]))
    rows = []
    for (a, b) in pairs:
        for g in grid:
            reur, rusd, p = run(a, b, *g)
            # exceso sobre quedarse en USDC = rusd (en USDC); medimos en USDC para quitar el efecto dólar
            st = {y: stats(rusd, yrs == y) for y in range(2018, 2024)}
            act = {y: (p[yrs == y] != 0).mean() for y in range(2018, 2024)}
            rows.append(((a, b) + g, st, act))
    import pickle; pickle.dump(rows, open("rows.pkl", "wb"))
    for mode in ("mr", "mo"):
        for y in range(2018, 2024):
            v = [r[1][y][0] for r in rows if r[0][2] == mode]
            print(mode, y, "mediana %+.1f%%  ganan %.0f%%" % (np.median(v) * 100, np.mean(np.array(v) > 0) * 100))
