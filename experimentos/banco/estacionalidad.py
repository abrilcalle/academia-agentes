# Estacionalidad hora-de-la-semana + tendencia diaria (solo 2018-2023)
import numpy as np, glob, csv, datetime as dt, sys
R='/home/claude/academia-agentes/data/'
def load(m):
    ts=[];c=[]
    for f in sorted(glob.glob(R+m+'_eur_1h/*.csv')):
        for row in csv.DictReader(open(f)):
            ts.append(row['ts']);c.append(float(row['close']))
    t=np.array([dt.datetime.fromisoformat(x) for x in ts]);c=np.array(c)
    k=t<dt.datetime(2024,1,1); return t[k],c[k]
fx={}
for row in csv.DictReader(open(R+'usdc_eur_1d.csv')): fx[row['ts'][:10]]=float(row['close'])
COST=0.0016  # ida y vuelta: 2x(0,05 % comision + 0,03 % diferencia)
def run(m, K=3, W=None, short=True, ma=50):
    t,c=load(m)
    r=np.r_[0,np.diff(np.log(c))]  # retorno de la hora que acaba en t
    how=np.array([x.weekday()*24+x.hour for x in t])
    yr=np.array([x.year for x in t])
    # tendencia diaria: cierre de ayer vs media de ma dias (cierres 23:00)
    day=np.array([x.date() for x in t])
    dc={}
    for i in range(len(t)): dc[day[i]]=c[i]
    ds=sorted(dc); dv=np.array([dc[d] for d in ds])
    sma=np.convolve(dv,np.ones(ma)/ma,'full')[:len(dv)]; sma[:ma]=np.nan
    up={ds[j+1]:(1 if dv[j]>sma[j] else -1) for j in range(ma,len(ds)-1)}
    tr=np.array([up.get(d,0) for d in day])
    sig=tr if short else np.maximum(tr,0)
    out={}
    for Wh in ([W] if W else [4,8,12,24]):
        # retorno de una ventana de Wh horas que empieza en el bucket s (retornos de s+1..s+Wh)
        cs=np.r_[0,np.cumsum(r)]
        n=len(r)
        idx=np.arange(n-Wh)
        wr=cs[idx+Wh+1]-cs[idx+1]  # entra al cierre de idx, sale al cierre de idx+Wh
        s_=sig[idx]; h_=how[idx]; y_=yr[idx]
        g=s_*wr
        trn=(y_>=2018)&(y_<=2021)&(s_!=0)
        mean_tr=np.array([g[trn&(h_==h)].mean() if (trn&(h_==h)).any() else -1 for h in range(168)])
        val={}
        for Y in (2022,2023):
            k=(y_==Y)&(s_!=0)
            val[Y]=np.array([g[k&(h_==h)].mean() for h in range(168)])
        # correlacion por buckets
        rho={Y:np.corrcoef(mean_tr,val[Y])[0,1] for Y in val}
        # elegir K ventanas no solapadas con mejor media en entreno
        order=np.argsort(-mean_tr); pick=[]
        for h in order:
            if all(min((h-p)%168,(p-h)%168)>=Wh for p in pick): pick.append(h)
            if len(pick)==K: break
        # simular semanas: cada operacion paga COST
        res={}
        for Y in (2018,2019,2020,2021,2022,2023):
            k=(y_==Y)&np.isin(h_,pick)&(s_!=0)
            pnl=g[k]-COST
            wk=np.array([t[i].isocalendar()[1]+100*t[i].isocalendar()[0] for i in idx[k]])
            W_=np.unique(np.array([x.isocalendar()[1]+100*x.isocalendar()[0] for x in t[yr==Y]]))
            weeks=np.array([pnl[wk==w].sum() for w in W_])
            res[Y]=(np.expm1(pnl.sum())*100, (weeks>0.0005).mean()*100, len(pnl)/len(W_))
        out[Wh]=(rho,pick,res)
    return out
if __name__=='__main__':
  for m in ['btc','eth','xrp']:
    for short in (True,False):
        o=run(m,short=short)
        for Wh,(rho,pick,res) in o.items():
            print(m,'LS' if short else 'L',Wh,'rho22 %.2f rho23 %.2f'%(rho[2022],rho[2023]),' | '.join('%d: %+.0f%% %.0f%%v %.1fop'%(Y,*res[Y]) for Y in res))
