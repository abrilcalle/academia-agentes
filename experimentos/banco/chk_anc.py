# Banco (19/11/2026): comprobación previa del "ancla bajista": corto de cada mercado solo cuando cierre < media 50 y la media baja en 10 días (y opcionalmente < media 200), con interés del préstamo. Solo 2018-2023. Uso: python chk_anc.py (en la carpeta de pruebas)
import os,sys,datetime as dt
sys.path.insert(0,'lab/src'); import numpy as np, data as datamod
INT=0.0023/100*24
for short in ['btc','eth','xrp']:
  for L200 in (0,1):
    d1=datamod.load_csv(f'loc/{short}_1d.csv'); kk=sorted(k for k in d1 if k<dt.datetime(2024,1,1))
    c=np.array([d1[k][3] for k in kk]); ma=np.convolve(c,np.ones(50)/50,'full')[:len(c)]; m2=np.convolve(c,np.ones(200)/200,'full')[:len(c)]
    out=[]
    for y in range(2018,2024):
      v=1; on=0; wk={}
      for i in range(201,len(c)):
        if kk[i].year!=y: continue
        b=c[i-1]<ma[i-1] and ma[i-1]<ma[i-11] and (not L200 or c[i-1]<m2[i-1])
        r=(-(c[i]/c[i-1]-1)-INT) if b else 0; v*=1+r; on+=b
      out.append(f"{y}:{(v-1)*100:+.0f}%({on}d)")
    print(short,'200' if L200 else '50 ',' '.join(out))
