# Laboratorio (25/11/2026): efecto "cambio de mes" (últimos días + primeros días del mes). Comprobación previa con cierres diarios 2018-2023.
import csv, datetime as dt, numpy as np, calendar
D="/home/claude/academia-agentes/data/"
def load(f):
    r={}
    for row in csv.DictReader(open(D+f)):
        d=dt.date.fromisoformat(row["ts"][:10]); r[d]=float(row["close"])
    return r
fx=load("usdc_eur_1d.csv")
for m in ["btc","eth","xrp","sol"]:
    p=load(f"{m}_eur_1d.csv"); ds=sorted(p)
    out={}
    for i in range(1,len(ds)):
        d=ds[i]; 
        if d.year<2018 or d.year>2023: continue
        ret=p[d]/p[ds[i-1]]-1
        last=calendar.monthrange(d.year,d.month)[1]
        tom = d.day<=3 or d.day>=last-1   # últimos 2 días + primeros 3
        per="entreno" if d.year<=2021 else str(d.year)
        out.setdefault((per,tom),[]).append(ret)
    s=[]
    for per in ["entreno","2022","2023"]:
        a=np.array(out.get((per,True),[]));b=np.array(out.get((per,False),[]))
        if len(a)==0: continue
        t=(a.mean()-b.mean())/np.sqrt(a.var()/len(a)+b.var()/len(b))
        s.append(f"{per}: TOM {a.mean()*1e4:+.0f}pb (n{len(a)}, verde {np.mean(a>0)*100:.0f}%) resto {b.mean()*1e4:+.0f}pb t={t:+.2f}")
    print(m.upper()," | ".join(s))
