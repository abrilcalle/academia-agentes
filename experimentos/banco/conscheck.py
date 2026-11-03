import pickle, os, sys, datetime as dt, numpy as np
from collections import defaultdict
sys.path.insert(0,"lab/src"); import data as datamod
M=pickle.load(open("mat_raw.pkl","rb"))
N=defaultdict(int); NET=defaultdict(float)
for inf in M["info"]:
    N[inf["activo"]]+=1
    sd=M["sides"].get(inf["id"])
    if not sd: continue
    for d,s,e in zip(*sd): NET[(inf["activo"],d)]+=s
for a in sorted(N):
    c=datamod.load_csv(f"loc/{a.split('-')[0].lower()}_1d.csv"); ks=sorted(k for k in c if k<dt.datetime(2024,1,1))
    cl={k.date():c[k][3] for k in ks}; ds=[k.date() for k in ks]
    out=[]
    for y in range(2019,2024):
        r=[];r0=[]
        for i in range(len(ds)-1):
            d=ds[i]
            if d.year!=y: continue
            nr=cl[ds[i+1]]/cl[d]-1; x=NET[(a,d)]/N[a]
            r0.append(nr)
            if abs(x)>0.2: r.append(np.sign(x)*nr)
        out.append(f"{y}: {np.mean(r)*1e4 if r else 0:+.0f}pb/d n{len(r)}")
    print(a,N[a]," | ".join(out))
print("--- tendencia 50+10 y comprar-mantener")
def trend(cl_list, ds, n=50, pend=10):
    c=np.array(cl_list); m=np.convolve(c,np.ones(n)/n,"full")[:len(c)]; t={}
    for i in range(n-1+pend,len(c)):
        v=1 if c[i]>m[i] else -1
        if (m[i]-m[i-pend])*v<=0: v=0
        t[ds[i]]=v
    return t
for a in sorted(N):
    c=datamod.load_csv(f"loc/{a.split('-')[0].lower()}_1d.csv"); ks=sorted(k for k in c if k<dt.datetime(2024,1,1))
    ds=[k.date() for k in ks]; cl=[c[k][3] for k in ks]; T=trend(cl,ds)
    out=[]
    for y in range(2019,2024):
        r=[];r0=[]
        for i in range(len(ds)-1):
            if ds[i].year!=y: continue
            nr=cl[i+1]/cl[i]-1; r0.append(nr)
            if T.get(ds[i]): r.append(T[ds[i]]*nr)
        out.append(f"{y}: tend {np.mean(r)*1e4 if r else 0:+.0f} n{len(r)} bh {np.mean(r0)*1e4:+.0f}")
    print(a," | ".join(out))
