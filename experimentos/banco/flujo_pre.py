# Comprobación previa: ratio de compras agresivas de BTC (Binance BTC/EUR) en N días y rentabilidad de BTC la semana siguiente.
import os, glob, csv, datetime as dt, numpy as np, collections
S=os.path.dirname(os.path.abspath(__file__))
vol=collections.defaultdict(float); buy=collections.defaultdict(float)
for f in sorted(glob.glob(os.path.join(S,"loc","btc_flujo_1h","*.csv"))):
    for r in csv.DictReader(open(f)):
        d=dt.date.fromisoformat(r["ts"][:10])
        if d>=dt.date(2024,1,1): continue
        vol[d]+=float(r["volume"]); buy[d]+=float(r["taker_buy"])
ds=sorted(vol); V=np.array([vol[d] for d in ds]); Bq=np.array([buy[d] for d in ds])
px={}
for r in csv.reader(open(os.path.join(S,"loc","btc_1d.csv"))):
    try: px[dt.date.fromisoformat(r[0][:10])]=float(r[4])
    except: pass
for N in (3,7,14,30):
    cv=np.convolve(V,np.ones(N),"full")[:len(V)]; cb=np.convolve(Bq,np.ones(N),"full")[:len(V)]
    ratio=cb/cv
    rel=np.array([ratio[i]-np.median(ratio[max(0,i-180):i+1]) for i in range(len(ratio))])
    for nm,x in (("raw",ratio-0.5),("rel",rel)):
        out=[]
        for y in (2020,2021,2022,2023):
            up=[];dn=[]
            for i,d in enumerate(ds):
                if d.year!=y or i<N: continue
                d7=d+dt.timedelta(days=7)
                if d not in px or d7 not in px: continue
                r7=px[d7]/px[d]-1
                (up if x[i]>0 else dn).append(r7)
            out.append(f"{y}: +{np.mean(up)*100:+.2f}%({len(up)}) -{np.mean(dn)*100:+.2f}%({len(dn)})")
        print(N,nm," | ".join(out))
