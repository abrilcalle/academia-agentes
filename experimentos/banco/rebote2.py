import pickle, numpy as np, os
S=os.path.dirname(os.path.abspath(__file__)); o=pickle.load(open(os.path.join(S,"rebote.pkl"),"rb"))
Y=range(2018,2024)
for act in ["BTC-EUR","ETH-EUR","XRP-EUR"]:
    fl=o[(act,"flat")]; print(act,"flat",[f"{fl[y][0]*100:+.0f}" for y in Y])
    for side in (-1,1):
        ks=[k for k in o if k[0]==act and k[1]==side]
        ex=lambda k,y:o[k][y][0]-fl[y][0]
        # elegir con entreno: suma exceso 2018-21 - caída máx
        sc=lambda k: sum(ex(k,y) for y in range(2018,2022)) - max(o[k][y][1] for y in range(2018,2022))
        best=sorted(ks,key=sc,reverse=True)[:3]
        med={y:np.median([ex(k,y) for k in ks]) for y in Y}
        pos22=np.mean([ex(k,2022)>0 for k in ks]); pos23=np.mean([ex(k,2023)>0 for k in ks])
        print(f"  lado {side:+d} mediana exceso", [f"{med[y]*100:+.0f}" for y in Y], f"| >USDC 2022 {pos22:.0%} 2023 {pos23:.0%}")
        for k in best: print("    elegido",k[2:],[f"{ex(k,y)*100:+.0f}" for y in Y],"dd22 %.0f"%(o[k][2022][1]*100))
