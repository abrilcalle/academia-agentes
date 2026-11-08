import sys, pickle, numpy as np
sys.path.insert(0,'lab/src'); import equipos as eq
goal = dict(semanas_en_verde_pct=50, ganancia_minima_anual_pct=10, caida_maxima_pct=25)
ok = lambda s: not eq.fails(s, goal)
YRS=[2019,2020,2021,2022,2023]
T={v:pickle.load(open(f"teams_{v}.pkl","rb")) for v in sys.argv[1:]}
print("A->B  "+"  ".join(sys.argv[1:]))
for A in YRS:
  for B in YRS:
    if A==B: continue
    print(A,B, *[sum(ok(t["s"][B]) for t in T[v][A]) for v in T])
for v in T:
  fl=[t["s"][B] for A in YRS for t in T[v][A] for B in YRS if B!=A]
  print(v, "verde med %.3f ret med %.3f dd med %.3f  dd>25: %d"%(np.median([s['verde'] for s in fl]),np.median([s['ret'] for s in fl]),np.median([s['dd'] for s in fl]),sum(s['dd']>0.25 for s in fl)))
