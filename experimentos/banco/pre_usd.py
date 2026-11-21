import sys, numpy as np, datetime as dt
sys.path.insert(0,'lab/src'); import data as dm
fx={d.date():v[3] for d,v in dm.load_csv('loc/usdc_eur_1d.csv').items()}
def tr(c,dias=50,pend=10):
    ma=np.convolve(c,np.ones(dias)/dias,'full')[:len(c)]; t=np.zeros(len(c))
    for i in range(dias-1+pend,len(c)):
        s=1 if c[i]>ma[i] else -1
        if (ma[i]-ma[i-pend])*s<=0: s=0
        t[i]=s
    return t
for a in ['btc','eth','xrp']:
    D=dm.load_csv(f'loc/{a}_1d.csv'); ks=sorted(D); ks=[k for k in ks if k.date()<dt.date(2024,1,1)]
    c=np.array([D[k][3] for k in ks]); last=None; f=[]
    for k in ks:
        last=fx.get(k.date(),last); f.append(last if last else np.nan)
    f=np.array(f); f=np.where(np.isnan(f),np.nanmean(f[:30]),f); cu=c/f
    te,tu=tr(c),tr(cu); fwd=np.r_[cu[7:]/cu[:-7]-1,np.full(7,np.nan)]
    yrs=np.array([k.year for k in ks])
    for y in range(2018,2024):
        m=yrs==y; d=(te!=tu)&m
        # en días que difieren, rentabilidad 7d (USD) * señal: ganan los usd?
        gu=np.nanmean((tu*fwd)[d]); ge=np.nanmean((te*fwd)[d])
        print(a,y,'difieren %.0f%%'%(100*d.sum()/m.sum()),'larg eur %d usd %d corto eur %d usd %d'%((te[m]==1).sum(),(tu[m]==1).sum(),(te[m]==-1).sum(),(tu[m]==-1).sum()),'señal×7d en difieren: eur %+.2f%% usd %+.2f%%'%(100*ge,100*gu))
