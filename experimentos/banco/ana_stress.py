import sys, pickle, itertools, numpy as np
sys.path.insert(0,'lab/src'); import equipos as eq
goal = dict(semanas_en_verde_pct=50, ganancia_minima_anual_pct=10, caida_maxima_pct=25)
ok = lambda s: not eq.fails(s, goal)
BULL, BEAR = [2019,2020,2021,2023],[2018,2022]
rank = lambda t, B: t["s"][B]["verde"] + 2 * t["s"][B]["ret"]
def podio(ts, B):
    pod, used = [], []
    for t in sorted(ts, key=lambda t: (ok(t["s"][B]), rank(t, B)), reverse=True):
        k = sorted(t["team"])
        if k in used: continue
        used.append(k); pod.append(t)
        if len(pod) == 3: break
    return pod
base = pickle.load(open("stress_base.pkl","rb"))
for v in sys.argv[1:]:
    T = pickle.load(open(f"stress_{v}.pkl","rb"))
    get = (lambda A,S: base[(A,None)]) if v=="base" else (lambda A,S: T[(A,S)])
    # por (A,S): juzgar en el otro año bajista C y en los años de subida != A
    bear_ok=bear_n=bull_ok=bull_n=0; pb=pbn=pu=pun=0; rets=[]; dds=[]; vds=[]; brets=[]
    for A in BULL:
        for S in BEAR:
            C = [y for y in BEAR if y!=S][0]
            ts = get(A,S)
            bear_ok += sum(ok(t["s"][C]) for t in ts); bear_n += len(ts)
            rets += [t["s"][C]["ret"] for t in ts]; dds += [t["s"][C]["dd"] for t in ts]; vds += [t["s"][C]["verde"] for t in ts]
            for B in BULL:
                if B==A: continue
                bull_ok += sum(ok(t["s"][B]) for t in ts); bull_n += len(ts)
                brets += [t["s"][B]["ret"] for t in ts]
            # tríos: podio elegido con un año de subida B != A, juzgado en C (bajista limpio) y en los otros años de subida
            for B in BULL:
                if B==A: continue
                p = podio(ts,B)
                pb += sum(ok(t["s"][C]) for t in p); pbn += len(p)
                for D in BULL:
                    if D in (A,B): continue
                    pu += sum(ok(t["s"][D]) for t in p); pun += len(p)
    print(f"{v:5s} bajista limpio: cumplen {bear_ok}/{bear_n} ret med {np.median(rets)*100:+.0f} % caída {np.median(dds)*100:.0f} % verde {np.median(vds)*100:.0f} % | subida: {bull_ok}/{bull_n} ret med {np.median(brets)*100:+.0f} % | podios: bajista {pb}/{pbn}  subida {pu}/{pun}")
    for C in BEAR:
        S=[y for y in BEAR if y!=C][0]
        r=[t["s"][C] for A in BULL for t in get(A,S)]
        print(f"      C={C}: cumplen {sum(ok(s) for s in r)}/{len(r)} ret {np.median([s['ret'] for s in r])*100:+.0f} caída {np.median([s['dd'] for s in r])*100:.0f} verde {np.median([s['verde'] for s in r])*100:.0f}")
