# Banco (26/11/2026): "podio estable". Cada lunes el sistema vuelve a elegir el podio con la prueba del año en curso
# (como en vivo con 2026) y el equipo en vivo es una cadena de equipos distintos. ¿Cumple más veces si el podio
# cambia menos (retener al equipo actual mientras siga cumpliendo y esté entre los M primeros, o solo si otro le
# supera por un margen, o elegir una vez al mes)?
# Uso: python podio_estable.py teams_base.pkl   (tras m2loo.py con ENS=post; mat.pkl para los días)
import os, sys, pickle, itertools
S = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(S, "lab", "src"))
import numpy as np, equipos as eq
goal = dict(semanas_en_verde_pct=50, ganancia_minima_anual_pct=10, caida_maxima_pct=25)
ok = lambda s: not eq.fails(s, goal)
M = pickle.load(open(os.path.join(S, "mat.pkl"), "rb")); days = M["days"]
T = pickle.load(open(os.path.join(S, sys.argv[1] if len(sys.argv) > 1 else "teams_base.pkl"), "rb"))
YRS = sorted(T)
W0 = int(os.environ.get("W0", "14"))       # semana ISO del primer lunes en que se juzga (antes: solo prueba)
SW = float(os.environ.get("SW", "0.0016"))  # coste de cambiar de equipo (vender y volver a comprar, pares USDC)
dY = {y: [d for d in days if d.year == y] for y in YRS}


def score(s):
    return (ok(s), s["verde"] + 2 * s["ret"])


def ranking(C_days, cands, m):
    st = [eq.stats(C_days[:m], c["v"][:m]) for c in cands]
    order = sorted(range(len(cands)), key=lambda i: score(st[i]), reverse=True)
    return order, st


def podio(order, cands, keep=()):
    pod = list(keep)
    used = [sorted(cands[i]["team"]) for i in pod]
    for i in order:
        if len(pod) == 3: break
        k = sorted(cands[i]["team"])
        if k in used: continue
        used.append(k); pod.append(i)
    return pod


POL = ["semanal", "mensual", "fijo", "ret3", "ret5", "ret10", "mar02", "mar05", "mar10"]


def run(A, C, pol):
    seen, cands = set(), []
    for t in T[A]:
        k = (tuple(sorted(t["team"])), t["pr"])
        if k in seen: continue
        seen.add(k); cands.append(dict(team=t["team"], v=np.asarray(t["v"][C])))
    Cd = dY[C]
    mons = [k for k, d in enumerate(Cd) if d.weekday() == 0 and d.isocalendar()[1] >= W0 and d.isocalendar()[0] == C]
    slots, out, nsw = None, [[] for _ in range(3)], 0
    for w, m in enumerate(mons):
        end = mons[w + 1] if w + 1 < len(mons) else len(Cd)
        order, st = ranking(Cd, cands, m)
        pos = {i: r for r, i in enumerate(order)}
        if slots is None or pol == "semanal" or (pol == "mensual" and w % 4 == 0):
            new = podio(order, cands)
        elif pol == "fijo" or pol == "mensual":
            new = slots
        elif pol.startswith("ret"):
            Mx = int(pol[3:])
            keep = [i for i in slots if ok(st[i]) and pos[i] < Mx]
            new = podio(order, cands, keep)
            # mantener cada equipo en su puesto (Halcón sigue siendo Halcón) y rellenar los huecos por orden
            new = [i if i in keep else None for i in slots]
            fill = [i for i in podio(order, cands, keep) if i not in keep]
            new = [i if i is not None else fill.pop(0) for i in new]
        else:  # margen
            dl = int(pol[3:]) / 100
            best = podio(order, cands)
            new = []
            for k, i in enumerate(slots):
                ch = best[k]
                si, sc = score(st[i]), score(st[ch])
                if ch != i and (sc[0] > si[0] or (sc[0] == si[0] and sc[1] > si[1] + dl)) and ch not in new and ch not in slots[k + 1:]:
                    new.append(ch)
                else:
                    new.append(i)
        for k in range(3):
            v = cands[new[k]]["v"]
            r = v[m:end] / np.r_[v[m - 1] if m else 100.0, v[m:end - 1]] - 1
            if slots is not None and new[k] != slots[k]:
                r = r.copy(); r[0] -= SW; nsw += 1
            out[k].append(r)
        slots = new
    d0 = mons[0]
    res = []
    for k in range(3):
        r = np.concatenate(out[k]); val = 100 * np.cumprod(1 + r)
        dd_ = Cd[d0:d0 + len(val)]
        s = eq.stats(dd_, val)
        # ventanas de 13 semanas (3 meses, como la meta en vivo) que empiezan cada lunes
        win = []
        for w in range(0, len(mons) - 13 + 1):
            a, b = mons[w] - d0, (mons[w + 13] - d0 if w + 13 < len(mons) else len(val))
            vv = val[a:b] / (val[a - 1] if a else 100.0) * 100
            win.append(ok(eq.stats(Cd[mons[w]:mons[w] + len(vv)], vv)))
        res.append((s, win))
    return res, nsw


print(f"W0 = semana {W0}, coste por cambio {SW*100:.2f} %, {len(YRS)} años")
for pol in POL:
    tot = cum = n = 0; wins = []; flat = []; sw = 0; byC = {c: 0 for c in YRS}; wbyC = {c: [] for c in YRS}
    for A, C in itertools.permutations(YRS, 2):
        res, nsw = run(A, C, pol); sw += nsw
        for s, win in res:
            n += 1; c_ = ok(s); cum += c_; byC[C] += c_; wins += win; wbyC[C] += win; flat.append(s)
    print(f"{pol:8s} cumplen {cum}/{n} {byC} | ventanas 3 meses {np.mean(wins)*100:.1f} % "
          f"[{' '.join(f'{np.mean(wbyC[c])*100:.0f}' for c in YRS)}] | cambios/año {sw/(n/3):.1f} | "
          f"mediana ret {np.median([s['ret'] for s in flat])*100:+.1f} % verde {np.median([s['verde'] for s in flat])*100:.0f} % "
          f"caída {np.median([s['dd'] for s in flat])*100:.0f} %", flush=True)
