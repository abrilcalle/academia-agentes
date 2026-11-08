# Banco (08/11/2026): parchea la copia lab/ para que los stops de las reglas inventadas sean órdenes stop en el exchange
# (saltan dentro de la vela al nivel fijado con el cierre anterior, comisión taker; INTRABAR=2 también el objetivo, maker).
# Uso: python intrabar_parche.py lab ; luego INTRABAR=0|1|2 OUTM=mat_X.pkl python m1.py ; m2fx.py ; m3x.py ; ag_ana.py mat_0.pkl mat_1.pkl
# Resultado: peor (ver registro 08/11 10:23). No integrado.
import os, sys
L = sys.argv[1]
p = os.path.join(L, 'src/inventor.py'); s = open(p).read()
s = s.replace('''def exposure(I, rule, kronos=None, bpd=1):
    if rule.get("lado") == "corto":''', '''import os as _os
INTRABAR = int(_os.environ.get("INTRABAR", "0"))
LAST_FILLS = {}


def exposure(I, rule, kronos=None, bpd=1):
    global LAST_FILLS
    if rule.get("lado") == "corto":''', 1)
s = s.replace('''        return -_exposure(inverted(I), r, ks, bpd)
    return _exposure(I, rule, kronos, bpd)''', '''        w = -_exposure(inverted(I), r, ks, bpd)
        LAST_FILLS = {i: (1 / p, k) for i, (p, k) in LAST_FILLS.items()}
        return w
    return _exposure(I, rule, kronos, bpd)''', 1)
s = s.replace('''def _exposure(I, rule, kronos=None, bpd=1):
    ent = np.ones(I.n, bool)''', '''def _exposure(I, rule, kronos=None, bpd=1):
    global LAST_FILLS
    fills = {}
    LAST_FILLS = fills
    Lo, Hi, Op = I.l.tolist(), I.h.tolist(), I.o.tolist()
    ent = np.ones(I.n, bool)''', 1)
old = '''        else:
            since += 1
            best = max(best, px)'''
new = '''        else:
            since += 1
            if INTRABAR and since >= 2:
                g0 = best / entry_px - 1
                lev = floor
                if stop and atr_l[i - 1] == atr_l[i - 1]:
                    lev = max(lev, best - stop * atr_l[i - 1])
                if trail:
                    t0 = trail * max(0.4, 1 - g0 / 0.10) if shrink else trail
                    lev = max(lev, best * (1 - t0))
                if esc:
                    lev = max(lev, esc_stop)
                hit = None
                if lev > 0 and Lo[i] < lev:
                    hit = (min(Op[i], lev), "stop")
                elif INTRABAR >= 2 and tp and target > 0 and Hi[i] > target:
                    hit = (max(Op[i], target), "tp")
                if hit:
                    fills[i] = hit
                    pos, blocked = False, True
                    w[i] = 0.0
                    continue
            best = max(best, px)'''
assert old in s; s = s.replace(old, new, 1); open(p, 'w').write(s)
p = os.path.join(L, 'src/academia.py'); s = open(p).read()
old = '''            elif ag["eleccion"] == "propia":
                w = inventor.exposure(I, ag["regla"], kr, mk.bpd)'''
assert old in s
s = s.replace(old, old + '''
                fl = inventor.LAST_FILLS
                if ag.get("lado") == "corto":
                    fl = {i: (1 / p, k) for i, (p, k) in fl.items()}
                self.__dict__.setdefault("_fills", {})[ag["id"]] = fl''', 1); open(p, 'w').write(s)
p = os.path.join(L, 'src/equipos.py'); s = open(p).read()
old = '''    r = run(mk.I, w, h, mk.n - 1, cfg)
    reg = regime_at(mk)'''
assert old in s
s = s.replace(old, '''    fl = getattr(ac, "_fills", {}).get(ag["id"])
    if fl and variante != "vela_tarde":
        cfg = dict(cfg, fills=fl)
''' + old, 1); open(p, 'w').write(s)
p = os.path.join(L, 'src/backtest.py'); s = open(p).read()
old = '''        if btc < 0 and not dead:  # interés por el BTC prestado'''
assert old in s
s = s.replace(old, '''        fl = cfg.get("fills")
        if fl and not dead and btc != 0 and i > a and i in fl:
            pe, kind = fl[i]
            px = pe / k[i] if k is not None else pe
            px = min(max(px, L[i]), H[i])
            rate = maker if kind == "tp" else taker
            val = cash + btc * px
            fee = abs(btc * px) * rate
            fees += fee
            before = btc
            cash = val - fee
            btc = 0.0
            kx = k[i] if k is not None else 1.0
            trades.append(dict(i=i, side="venta" if before > 0 else "cierra corto", px=px * kx, amt=abs(before * px) * kx))
            if open_val is not None:
                trades[-1]["pnl"] = (cash - open_val) * kx
                trades[-1]["pnl_pct"] = (cash - open_val) / open_val
                open_val = None
            cur, force_mkt = 0.0, False
''' + old, 1); open(p, 'w').write(s)
print("parche aplicado")
