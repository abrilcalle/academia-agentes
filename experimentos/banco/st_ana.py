import pickle, sys, json
import numpy as np

NEW = {"supertrend_alcista", "supertrend_bajista", "adx_fuerte", "dmi_alcista"}


def load(arm):
    out = []
    for tf in ("1d", "4h", "1h"):
        try:
            out += pickle.load(open(f"r_{arm}_{tf}.pkl", "rb"))
        except FileNotFoundError:
            pass
    return out


def usa(r):
    reg = r["regla"]
    cs = []
    for k in ("entry", "exit"):
        cs += [c[0] for c in reg.get(k, []) if isinstance(c, list)]
    return bool(NEW & set(cs))


A, B = load("lab"), load("lab_st")
print(len(A), len(B))
for nm, X in (("base", A), ("st", B)):
    print(f"== {nm}: usan piezas nuevas {sum(usa(r) for r in X)} de {len(X)}")
    for pre in ("inv", "ch"):
        for y in (2018, 2019, 2020, 2021, 2022, 2023):
            v = [r[f"{pre}{y}"] for r in X if f"{pre}{y}" in r]
            if not v:
                continue
            print(f"  {pre} {y}: n {len(v)} · mediana {np.median([x['ret'] for x in v])*100:+.0f} % · ganan {sum(x['ret']>0 for x in v)} · "
                  f"verde {np.median([x['verde'] for x in v])*100:.0f} % · caída {np.median([x['dd'] for x in v])*100:.0f} % · "
                  f"cumplen {sum(x['verde']>0.5 and x['ret']>=0.1 and x['dd']<=0.25 for x in v)}")
        both = sum(all(r.get(f"{pre}{y}", {}).get("ret", -1) > 0 for y in (2022, 2023)) for r in X)
        print(f"  {pre} ganan 2022 y 2023: {both}")
# agente a agente (mismas semillas)
n = min(len(A), len(B))
for pre in ("inv", "ch"):
    for y in (2022, 2023):
        d = [(B[i][f"{pre}{y}"]["ret"] - A[i][f"{pre}{y}"]["ret"]) for i in range(n)
             if f"{pre}{y}" in A[i] and f"{pre}{y}" in B[i] and A[i]["activo"] == B[i]["activo"] and A[i]["tf"] == B[i]["tf"]]
        print(f"par a par {pre} {y}: {len(d)} pares · mejor {sum(x>0 for x in d)} · peor {sum(x<0 for x in d)} · mediana {np.median(d)*100:+.1f} pts")
for tf in ("1d", "4h", "1h"):
    for nm, X in (("base", A), ("st", B)):
        v22 = [r["ch2022"]["ret"] for r in X if r["tf"] == tf and "ch2022" in r]
        v23 = [r["ch2023"]["ret"] for r in X if r["tf"] == tf and "ch2023" in r]
        if v22:
            print(f" {tf} {nm}: elegida 2022 {np.median(v22)*100:+.0f} % (ganan {sum(np.array(v22)>0)}/{len(v22)}) · 2023 {np.median(v23)*100:+.0f} % (ganan {sum(np.array(v23)>0)}/{len(v23)})")
U = [r for r in B if usa(r)]
if U:
    print("Con piezas nuevas (st):", len(U), "elegida 2022", f"{np.median([r['ch2022']['ret'] for r in U if 'ch2022' in r])*100:+.0f} %",
          "2023", f"{np.median([r['ch2023']['ret'] for r in U if 'ch2023' in r])*100:+.0f} %", "eleccion propia", sum(r['eleccion'] == 'propia' for r in U))
