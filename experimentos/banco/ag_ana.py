# Banco (08/11/2026): compara dos matrices de m1 agente a agente, año a año. Uso: python ag_ana.py mat_0.pkl mat_1.pkl
# Compara por agente (solo los que cambian) año a año: ganancia, semanas en verde, caída
import pickle, sys, numpy as np, datetime as dt
A = pickle.load(open(sys.argv[1], "rb")); B = pickle.load(open(sys.argv[2], "rb"))
days = A["days"]
def stats(r, idx):
    v = np.cumprod(1 + r[idx]); dd = 1 - v / np.maximum.accumulate(v)
    wk = {}
    for k in idx:
        d = days[k]; key = d - dt.timedelta(days=d.weekday()); wk[key] = wk.get(key, 1) * (1 + r[k])
    w = np.array(list(wk.values())) - 1
    return v[-1] - 1, (w > 0.0001).mean(), dd.max()
chg = [j for j in range(A["R"].shape[0]) if not np.allclose(A["R"][j], B["R"][j])]
print(len(chg), "de", A["R"].shape[0], "agentes cambian")
for y in [2019, 2020, 2021, 2022, 2023]:
    idx = [k for k, d in enumerate(days) if d.year == y]
    sa = np.array([stats(A["R"][j], idx) for j in chg]); sb = np.array([stats(B["R"][j], idx) for j in chg])
    print(y, "ret med %+.1f%% -> %+.1f%%" % (100*np.median(sa[:,0]), 100*np.median(sb[:,0])),
          "| verde %.1f%% -> %.1f%%" % (100*sa[:,1].mean(), 100*sb[:,1].mean()),
          "| caida med %.1f%% -> %.1f%%" % (100*np.median(sa[:,2]), 100*np.median(sb[:,2])),
          "| mejora ret %d%% verde %d%%/%d%%" % (100*(sb[:,0]>sa[:,0]).mean(), 100*(sb[:,1]>sa[:,1]).mean(), 100*(sb[:,1]<sa[:,1]).mean()))
