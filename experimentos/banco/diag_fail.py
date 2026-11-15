import sys, pickle, itertools, numpy as np
sys.path.insert(0,'lab/src'); import equipos as eq
goal = dict(semanas_en_verde_pct=50, ganancia_minima_anual_pct=10, caida_maxima_pct=25)
YRS=[2019,2020,2021,2022,2023]
ok=lambda s: not eq.fails(s,goal)
rank=lambda t,B: t["s"][B]["verde"]+2*t["s"][B]["ret"]
def podio(ts,B):
    pod,used=[],[]
    for t in sorted(ts,key=lambda t:(ok(t["s"][B]),rank(t,B)),reverse=True):
        k=sorted(t["team"])
        if k in used: continue
        used.append(k); pod.append(t)
        if len(pod)==3: break
    return pod
T=pickle.load(open(f"teams_{sys.argv[1]}.pkl","rb"))
from collections import Counter
for c in YRS:
    cnt=Counter(); n=0; vs=[]
    for A,B,C in itertools.permutations(YRS,3):
        if C!=c: continue
        for t in podio(T[A],B):
            s=t["s"][C]; n+=1; vs.append((s['verde'],s['ret'],s['dd']))
            f=[]
            if eq.annual(s)<0.10 or s['ret']<=0: f.append('ret')
            if s['verde']<=0.5: f.append('sem')
            if s['dd']>0.25: f.append('dd')
            cnt['+'.join(f) or 'ok']+=1
    v=np.array(vs); print(c,n,dict(cnt),"verde med %.3f min %.3f"%(np.median(v[:,0]),v[:,0].min()))
