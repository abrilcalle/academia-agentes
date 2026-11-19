# Banco (19/11/2026): "equipo de dos caras". Lee dual_base.pkl (m2dual.py) y mat18.pkl (días).
# Equipo alcista: podio de los formados en un año de subida A, elegido con otro año de subida B (como m3x).
# Equipo bajista: podio de los formados en el año bajista S (el que no se juzga), elegido con S.
# Cada día (con el cierre de ayer), si BTC está en régimen bajista se usa la curva del equipo bajista; si no, la del alcista.
# Cambiar de equipo cuesta 2 × 0,08 % (vender todo y volver a repartir). Se juzga en C (ningún año usado para formar/elegir).
import os, sys, pickle, itertools
sys.path.insert(0, "lab/src")
import numpy as np, equipos as eq, data as datamod
goal = dict(semanas_en_verde_pct=50, ganancia_minima_anual_pct=10, caida_maxima_pct=25)
ok = lambda s: not eq.fails(s, goal)
rank = lambda t, B: t["s"][B]["verde"] + 2 * t["s"][B]["ret"]
T = pickle.load(open("dual_base.pkl", "rb")); T = {A: v for (A, _), v in T.items()}
days = pickle.load(open("mat18.pkl", "rb"))["days"]
YRS = [2018, 2019, 2020, 2021, 2022, 2023]; BULL, BEAR = [2019, 2020, 2021, 2023], [2018, 2022]
idx = {y: [k for k, d in enumerate(days) if d.year == y] for y in YRS}
btc = datamod.load_csv("loc/btc_1d.csv"); cl = {d.date(): v[3] for d, v in btc.items()}
ks = sorted(cl); arr = np.array([cl[k] for k in ks]); pos = {k: i for i, k in enumerate(ks)}
def sma(i, n): return arr[max(0, i - n + 1):i + 1].mean()
def regime(d, kind):
    i = pos[max(k for k in ks if k < d)]  # cierre de ayer
    c = arr[i]
    if kind == "m200": return c < sma(i, 200)
    if kind == "m200p": return c < sma(i, 200) and sma(i, 200) < sma(i - 20, 200)
    if kind == "m100": return c < sma(i, 100)
    if kind == "m50p": return c < sma(i, 50) and sma(i, 50) < sma(i - 10, 50)
    if kind == "x50200": return sma(i, 50) < sma(i, 200)
    raise SystemExit(kind)
def podio(ts, B):
    pod, used = [], []
    for t in sorted(ts, key=lambda t: (ok(t["s"][B]), rank(t, B)), reverse=True):
        k = sorted(t["team"])
        if k in used: continue
        used.append(k); pod.append(t)
        if len(pod) == 3: break
    return pod
def curve(vb, vr, bear, cost=0.0016):
    rb = np.r_[vb[0] / 100 - 1, vb[1:] / vb[:-1] - 1]; rr = np.r_[vr[0] / 100 - 1, vr[1:] / vr[:-1] - 1]
    r = np.where(bear, rr, rb); sw = np.r_[False, bear[1:] != bear[:-1]]
    return 100 * np.cumprod(1 + r - sw * cost)
# diagnóstico: equipos formados en un año bajista y juzgados en el otro
print("Diagnóstico (equipos que cumplen / total · mediana ret / semanas / caída):")
for A in YRS:
    for C in BEAR:
        if C == A: continue
        fl = [t["s"][C] for t in T[A]]
        print(f"  formado {A} -> juzgado {C}: {sum(map(ok, fl))}/{len(fl)} · {np.median([s['ret'] for s in fl])*100:+.0f} % / {np.median([s['verde'] for s in fl])*100:.0f} % / {np.median([s['dd'] for s in fl])*100:.0f} %")
KINDS = sys.argv[1:] or ["m200", "m200p", "m100", "m50p", "x50200"]
for kind in ["base"] + KINDS:
    tot, byC, fl_all = 0, {}, {}
    for C in YRS:
        S = [s for s in BEAR if s != C][0]
        bull = [y for y in BULL if y != C]
        if kind != "base":
            bear = np.array([regime(days[k], kind) for k in idx[C]])
            podS = podio(T[S], S)
        n = 0; fl = []
        for A, Bq in itertools.permutations(bull, 2):
            for k, t in enumerate(podio(T[A], Bq)):
                if kind == "base": s = t["s"][C]
                else: s = eq.stats(days[idx[C][0]:idx[C][-1] + 1], curve(t["v"][C], podS[k % len(podS)]["v"][C], bear))
                n += ok(s); fl.append(s)
        byC[C] = f"{n}/{len(fl)}"; fl_all[C] = fl; tot += n
    sub = lambda Cs: [s for C in Cs for s in fl_all[C]]
    print(f"{kind:7s} cumplen {tot} {byC} | 2022: ret {np.median([s['ret'] for s in fl_all[2022]])*100:+.0f} % verde {np.median([s['verde'] for s in fl_all[2022]])*100:.0f} % dd {np.median([s['dd'] for s in fl_all[2022]])*100:.0f} % | "
          f"subida: ret {np.median([s['ret'] for s in sub(BULL)])*100:+.0f} % verde {np.median([s['verde'] for s in sub(BULL)])*100:.0f} % dd {np.median([s['dd'] for s in sub(BULL)])*100:.0f} %")
