# Banco (06/11/2026): 150 equipos al azar de 4 agentes por año con cada matriz (sin formación ni podio). Uso: python azar_mat.py base X ...
import pickle,numpy as np,sys,os
sys.path.insert(0,'lab/src'); import equipos as eq
Ms={v:pickle.load(open(f'mat_{v}.pkl','rb')) for v in sys.argv[1:]}
b=Ms[sys.argv[1]]; days=b['days']; info=b['info']; n=len(info)
rng=np.random.default_rng(1); prm=eq.PARAMS[0]
for y in range(2019,2024):
  s=[k for k,d in enumerate(days) if d.year==y]; s=slice(s[0],s[-1]+1)
  teams=[rng.choice(n,4,replace=False) for _ in range(150)]
  out=[]
  for v,M in Ms.items():
    st=[eq.stats(days[s],eq.simulate(M['R'][t,s],M['E'][t,s],M['P'][t,s],M['G'][t,s],2,prm,L=M['L'][t,s])[0]) for t in teams]
    out.append(f"{v}: verde {np.mean([x['verde'] for x in st])*100:.1f} ret {np.median([x['ret'] for x in st])*100:+.0f} dd {np.median([x['dd'] for x in st])*100:.0f} cumple {sum(not eq.fails(x,dict(semanas_en_verde_pct=50,ganancia_minima_anual_pct=10,caida_maxima_pct=25)) for x in st)}")
  print(y,' | '.join(out))
