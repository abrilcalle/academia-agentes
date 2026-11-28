# Análisis del banco "inventor con más peso a lo reciente" (28/11/2026 15:00). Compara cada brazo con base (como ahora).
import pickle
import numpy as np


def load(arm):
    out = []
    for tf in ("1d", "4h", "1h"):
        try:
            out += pickle.load(open(f"r_{arm}_{tf}.pkl", "rb"))
        except FileNotFoundError:
            pass
    return out


ARMS = ["base", "lin", "exp"]
D = {a: load(a) for a in ARMS}
base = D["base"]
for nm in ARMS:
    X = D[nm]
    if not X:
        continue
    print(f"== {nm}: {len(X)} agentes · propia {sum(r['eleccion']=='propia' for r in X)}")
    for pre in ("inv", "ch"):
        line = []
        for y in (2018, 2019, 2020, 2021, 2022, 2023):
            v = [r[f"{pre}{y}"] for r in X if f"{pre}{y}" in r]
            line.append(f"{y} {np.median([x['ret'] for x in v])*100:+.0f}%/g{sum(x['ret']>0 for x in v)}"
                        f"/c{sum(x['verde']>0.5 and x['ret']>=0.1 and x['dd']<=0.25 for x in v)}/r{sum(x['ret']>=0.1 and x['dd']<=0.25 for x in v)}")
        both = sum(all(r.get(f"{pre}{y}", {}).get("ret", -1) > 0 for y in (2022, 2023)) for r in X)
        v22 = [r[f"{pre}2022"] for r in X if f"{pre}2022" in r]
        print(f"  {pre}: " + " · ".join(line) + f" · ganan22y23 {both} · verde22 {np.median([x['verde'] for x in v22])*100:.0f}% · dd22 {np.median([x['dd'] for x in v22])*100:.0f}%")
    if nm != "base":
        n = min(len(X), len(base))
        for pre in ("inv", "ch"):
            for y in (2022, 2023):
                d = [X[i][f"{pre}{y}"]["ret"] - base[i][f"{pre}{y}"]["ret"] for i in range(n)
                     if f"{pre}{y}" in X[i] and f"{pre}{y}" in base[i] and X[i]["activo"] == base[i]["activo"] and X[i]["tf"] == base[i]["tf"]]
                print(f"  par a par {pre} {y}: {len(d)} · mejor {sum(x>0 for x in d)} · peor {sum(x<0 for x in d)} · mediana {np.median(d)*100:+.1f} pts")
    for tf in ("1d", "4h", "1h"):
        v22 = [r["ch2022"]["ret"] for r in X if r["tf"] == tf and "ch2022" in r]
        v23 = [r["ch2023"]["ret"] for r in X if r["tf"] == tf and "ch2023" in r]
        e = [r["entreno"] for r in X if r["tf"] == tf and isinstance(r.get("entreno"), (int, float))]
        if v22:
            print(f"   {tf}: elegida 2022 {np.median(v22)*100:+.0f}% (g {sum(np.array(v22)>0)}/{len(v22)}) · 2023 {np.median(v23)*100:+.0f}% (g {sum(np.array(v23)>0)}/{len(v23)})")
