import os, sys, itertools, numpy as np
sys.argv = ["x", "teams_base.pkl"]
src = open("podio_estable.py").read().split('print(f"W0 =')[0]
exec(src)
for W in (8, 14, 27):
    W0 = W
    for pol in ("fijo", "ret10", "mensual", "mar05"):
        up = dn = 0; dret = []
        for A, C in itertools.permutations(YRS, 2):
            a, _ = run(A, C, "semanal"); b, _ = run(A, C, pol)
            for (sa, wa), (sb, wb) in zip(a, b):
                d = np.mean(wb) - np.mean(wa); up += d > 0.001; dn += d < -0.001; dret.append(sb["ret"] - sa["ret"])
        print(f"W0={W} {pol:7s} vs semanal: series mejor {up} / peor {dn} (de 90) · dif. mediana ret {np.median(dret)*100:+.1f} pts", flush=True)
