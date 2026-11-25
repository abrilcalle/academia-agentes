# Laboratorio (25/11/2026): efecto "cambio de mes" (últimos días + primeros días del mes). Comprobación previa con cierres diarios 2018-2023.
import csv, datetime as dt, numpy as np, calendar
D="/home/claude/academia-agentes/data/"
def load(f):
    return {dt.date.fromisoformat(r["ts"][:10]):float(r["close"]) for r in csv.DictReader(open(D+f))}
fx=load("usdc_eur_1d.csv")
# media diaria de los días TOM (últimos 3 + primeros 5) con filtro de tendencia (sobre media 50 que sube vs hace 10) frente a días con tendencia no TOM
for m in ["btc","eth","xrp"]:
    p=load(f"{m}_eur_1d.csv"); ds=sorted(p); c=np.array([p[d] for d in ds])
    ma=np.convolve(c,np.ones(50)/50,"full")[:len(c)]; ma[:49]=np.nan
    res={}
    for i in range(61,len(ds)):
        d=ds[i]; y=d.year
        if y<2018 or y>2023: continue
        up = c[i-1]>ma[i-1] and ma[i-1]>ma[i-11]
        if not up: continue
        last=calendar.monthrange(d.year,d.month)[1]
        tom=d.day<=5 or d.day>last-3
        per="entreno" if y<=2021 else str(y)
        res.setdefault((per,tom),[]).append(c[i]/c[i-1]-1)
    out=[]
    for per in ["entreno","2022","2023"]:
        a=np.array(res.get((per,True),[]));b=np.array(res.get((per,False),[]))
        if len(a)<5: out.append(f"{per}: n{len(a)}"); continue
        t=(a.mean()-b.mean())/np.sqrt(a.var()/len(a)+b.var()/len(b))
        out.append(f"{per}: TOM {a.mean()*1e4:+.0f}pb n{len(a)} / resto {b.mean()*1e4:+.0f}pb n{len(b)} t={t:+.2f}")
    print(m.upper()," | ".join(out))
