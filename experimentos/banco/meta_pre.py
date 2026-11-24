# Banco (24/11/2026 21:00): "meta-etiquetado" - comprobación previa. ¿Un modelo sencillo (regresión logística) entrenado con
# 2018-21 sobre las operaciones abiertas de todos los agentes predice mejor que P (historial) si la operación gana en los
# próximos días? Se mide en 2022-23 (validación). Si no gana a P, no merece pasar al banco de equipos.
import os, sys, pickle, datetime as dt
S = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(S, "lab", "src"))
import numpy as np, data as datamod
M = pickle.load(open(os.path.join(S, "mat.pkl"), "rb"))
days, R, E, P, G, L, info = M["days"], M["R"], M["E"], M["P"], M["G"], M["L"], M["info"]
n, T = R.shape
H = int(os.environ.get("H", "5"))
px = {}
for a, f in [("BTC-EUR", "btc"), ("ETH-EUR", "eth"), ("SOL-EUR", "sol"), ("XRP-EUR", "xrp")]:
    d = {k.date(): v[3] for k, v in datamod.load_csv(os.path.join(S, "loc", f + "_1d.csv")).items()}
    ks = sorted(d); last = d[ks[0]]; arr = []
    for day in days:
        last = d.get(day, last); arr.append(last)
    px[a] = np.array(arr, float)
def feats_mkt(c):
    lr = np.r_[0, np.diff(np.log(c))]
    cs = np.cumsum(lr)
    def back(k): return np.r_[np.zeros(k), cs[k:] - cs[:-k]]
    ma50 = np.convolve(c, np.ones(50) / 50, "full")[:len(c)]; ma50[:50] = c[:50]
    vol20 = np.array([lr[max(0, t - 19):t + 1].std() for t in range(len(c))])
    return dict(r7=back(7), r30=back(30), dist=c / ma50 - 1, vol=vol20)
FM = {a: feats_mkt(c) for a, c in px.items()}
btc = FM["BTC-EUR"]
cumR = np.cumsum(np.log1p(np.clip(R, -0.99, None)), axis=1)
X, Y, YR, Pv, yr, sgn = [], [], [], [], [], []
for j in range(n):
    a = info[j]["activo"]; fm = FM[a]
    for t in range(31, T - H):
        p = P[j, t - 1]
        if p <= 0 or E[j, t - 1] <= 0: continue
        s = -1.0 if info[j]["short"] else 1.0
        fwd = cumR[j, t + H - 1] - cumR[j, t - 1]
        own20 = cumR[j, t - 1] - cumR[j, t - 21]
        X.append([p, G[j, t - 1], L[j, t - 1], E[j, t - 1], own20, s * fm["r7"][t - 1], s * fm["r30"][t - 1], s * fm["dist"][t - 1],
                  fm["vol"][t - 1], s * btc["r30"][t - 1], s * btc["dist"][t - 1]])
        Y.append(fwd > 0); YR.append(fwd); Pv.append(p); yr.append(days[t].year)
X, Y, YR, Pv, yr = map(np.array, (X, Y, YR, Pv, yr))
names = "P G L E propio20 mkt7 mkt30 dist50 vol20 btc30 btcdist".split()
tr, va = yr <= 2021, yr >= 2022
mu, sd = X[tr].mean(0), X[tr].std(0) + 1e-9
Z = (X - mu) / sd; Z = np.c_[np.ones(len(Z)), Z]
def fit(Z, y, lam=1.0):
    w = np.zeros(Z.shape[1])
    for _ in range(30):
        p = 1 / (1 + np.exp(-Z @ w)); W = p * (1 - p)
        Hm = Z.T @ (Z * W[:, None]) + lam * np.eye(len(w)); g = Z.T @ (p - y) + lam * w
        w -= np.linalg.solve(Hm, g)
    return w
def auc(s, y):
    o = np.argsort(s); r = np.empty(len(s)); r[o] = np.arange(len(s))
    npos = y.sum(); return (r[y].sum() - npos * (npos - 1) / 2) / (npos * (len(y) - npos))
w = fit(Z[tr], Y[tr].astype(float))
q = 1 / (1 + np.exp(-Z @ w))
print(f"H={H} filas entreno {tr.sum()} validación {va.sum()} · base gana en {H} días: entreno {Y[tr].mean():.3f} valid {Y[va].mean():.3f}")
print("pesos:", " ".join(f"{k} {v:+.2f}" for k, v in zip(["c"] + names, w)))
for y_ in [2018, 2019, 2020, 2021, 2022, 2023]:
    m = yr == y_
    print(y_, f"AUC P {auc(Pv[m], Y[m]):.3f} modelo {auc(q[m], Y[m]):.3f}", end=" | ")
    for lab_, sc in (("P", Pv[m]), ("mod", q[m])):
        thr = np.quantile(sc, 0.3); hi, lo = sc > thr, sc <= thr
        print(f"{lab_}: 70% alto {YR[m][hi].mean()*100:+.2f} / 30% bajo {YR[m][lo].mean()*100:+.2f}", end="  ")
    print()
for k, nm in enumerate(names):  # cada variable sola en validación
    print(f"  {nm:8s} AUC valid {auc(X[va, k], Y[va]):.3f} entreno {auc(X[tr, k], Y[tr]):.3f}")
