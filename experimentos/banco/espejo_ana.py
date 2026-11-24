# Banco (24/11/2026): análisis de espejo.py. Uso: python3 espejo_ana.py 0 0.25 0.5
import pickle, sys, os, numpy as np
arms = sys.argv[1:]
TF = ["1d", "4h", "1h"]
D = {a: {t: pickle.load(open(f"esp_{a}_{t}.pkl", "rb")) for t in TF if os.path.exists(f"esp_{a}_{t}.pkl")} for a in arms}
med = lambda x: np.median(x) * 100 if len(x) else float("nan")
for kind in ("inv", "ch"):
    print(f"== {kind} ({'regla inventada' if kind == 'inv' else 'la elegida con 2022–23'}) ==")
    for a in arms:
        rows = [r for t in D[a] for r in D[a][t]]
        o = [f"{a:5s} n={len(rows)}"]
        for y in (2018, 2019, 2020, 2021, 2022, 2023):
            v = [r[f"{kind}{y}"] for r in rows if f"{kind}{y}" in r]
            o.append(f"{y}: {med([x['ret'] for x in v]):+.0f}% v{med([x['verde'] for x in v]):.0f} dd{med([x['dd'] for x in v]):.0f} g{sum(x['ret'] > 0 for x in v)}/{len(v)}")
        both = sum(r.get(f"{kind}2022", {}).get("ret", -1) > 0 and r.get(f"{kind}2023", {}).get("ret", -1) > 0 for r in rows)
        o.append(f"ganan 22 y 23: {both}")
        print(" | ".join(o))
    base = arms[0]
    for a in arms[1:]:
        for t in D[a]:
            b, c = D[base][t], D[a][t]
            for y in (2022, 2023):
                k = f"{kind}{y}"
                pr = [(x[k]["ret"], z[k]["ret"]) for x, z in zip(b, c) if k in x and k in z]
                print(f"  {a} vs {base} {t} {y}: mejora en {sum(z > x for x, z in pr)}/{len(pr)}, mediana dif {med([z - x for x, z in pr]):+.1f} pp")
    for a in arms:
        for t in D[a]:
            rows = D[a][t]
            s = " ".join(f"{y}:{med([r[f'{kind}{y}']['ret'] for r in rows if f'{kind}{y}' in r]):+.0f}%" for y in (2022, 2023))
            print(f"  {a} {t}: {s}  cortos {sum(r['lado']=='corto' for r in rows)}/{len(rows)}")
