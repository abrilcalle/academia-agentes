# Laboratorio (25/11/2026): efecto "cambio de mes" (últimos días + primeros días del mes). Comprobación previa con cierres diarios 2018-2023.
import csv, datetime as dt, numpy as np, calendar
D="/home/claude/academia-agentes/data/"
def load(f):
    return {dt.date.fromisoformat(r["ts"][:10]):float(r["close"]) for r in csv.DictReader(open(D+f))}
fx=load("usdc_eur_1d.csv")
COST=0.0008*2  # entrar y salir cada mes
for m in ["btc","eth","xrp"]:
    p=load(f"{m}_eur_1d.csv"); ds=sorted(p)
    print(m.upper())
    for L,F in [(1,2),(2,3),(3,5),(0,3),(2,0)]:
        row=[]
        for y in range(2018,2024):
            eq=1.0; inpos=False; wk={}
            for i in range(1,len(ds)):
                d=ds[i]
                if d.year!=y: continue
                last=calendar.monthrange(d.year,d.month)[1]
                tom=(d.day<=F) or (d.day>last-L)
                r=p[d]/p[ds[i-1]]-1
                if tom:
                    if not inpos: eq*=1-COST/2; inpos=True
                    eq*=1+r
                else:
                    if inpos: eq*=1-COST/2; inpos=False
                    # en USDC: sigue el cambio
                    if d in fx and ds[i-1] in fx: eq*=fx[d]/fx[ds[i-1]]
                wk[d.isocalendar()[:2]]=eq
            ks=sorted(wk); prev=1.0; g=0
            for k in ks: g+= wk[k]>prev; prev=wk[k]
            row.append(f"{y}:{(eq-1)*100:+4.0f}% v{g/len(ks)*100:2.0f}")
        print(f"  últimos {L} + primeros {F}: "+"  ".join(row))
