# Banco (13/11/2026): "rejilla" (grid trading al contado) como nuevo tipo de agente. Nunca probado.
# Órdenes limitadas de compra escalonadas por debajo del precio (cada escalón 1/N del dinero, mismo tamaño: sin martingala)
# y, al llenarse, una venta limitada un escalón más arriba. Solo activa con tendencia (media 50 subiendo, como el filtro
# del equipo); al perder la tendencia se vende todo a mercado. Variante corta: lo mismo dado la vuelta en tendencia bajista.
# Uso: python rejilla.py  (lee data/ del repo; solo 2018-2023)
import os, sys, csv, datetime as dt, itertools
import numpy as np
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MAKER, TAKER, SLIP, INT_H = 0.0005, 0.0005, 0.0003, 0.000023
TOL = 0.0005   # una orden limitada solo se llena si el precio la cruza un 0,05 % (prudente)

def load_1h(m):
    d = os.path.join(REPO, "data", f"{m}_eur_1h"); rows = []
    for f in sorted(os.listdir(d)):
        for r in csv.DictReader(open(os.path.join(d, f))):
            rows.append((dt.datetime.fromisoformat(r["ts"]), float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"])))
    return rows

def load_1d(m):
    return [(dt.date.fromisoformat(r["ts"][:10]), float(r["close"])) for r in csv.DictReader(open(os.path.join(REPO, "data", f"{m}_eur_1d.csv")))]

def trend(d1, n=50, pend=10):
    c = np.array([x[1] for x in d1]); out = {}
    for i in range(n + pend, len(c)):
        sma = c[i - n + 1:i + 1].mean(); sma_p = c[i - pend - n + 1:i - pend + 1].mean()
        out[d1[i][0]] = 1 if (c[i] > sma and sma > sma_p) else (-1 if (c[i] < sma and sma < sma_p) else 0)
    return out

def run(h, tr, s, N, lados=(1,), stop=False, y0=2018, y1=2023):
    """Equity diario (cierre UTC) de la rejilla. s = escalón, N = número de escalones."""
    cash, inv = 1.0, []          # inv: lista de (lado, precio_entrada, qty_en_moneda_base)
    side, ref = 0, None
    eq_d, last_day = {}, None
    nf = 0
    for (t, o, hi, lo, c) in h:
        if t.year < y0 or t.year > y1: continue
        day = t.date()
        if day != last_day:
            # decisión con la tendencia de la víspera
            want = tr.get(day - dt.timedelta(days=1), 0)
            want = want if want in lados else 0
            if want != side:
                for (sd, p, q) in inv:   # cerrar a mercado en la apertura
                    px = o * (1 - SLIP * sd)
                    cash += q * (p + sd * (px - p)) - q * px * TAKER
                inv = []; side = want; ref = o
            last_day = day
        if side == 0:
            eq_d[day] = cash; continue
        unit = None
        # niveles libres
        held = {round((ref - x[1]) / (ref * s) * side) for x in inv} if inv else set()
        tot = cash + sum(q * p for (_, p, q) in inv)
        unit = tot / N
        # ventas (cierres) primero: objetivo un escalón a favor
        keep = []
        for (sd, p, q) in inv:
            tgt = p * (1 + s * sd)
            if stop and ((sd == 1 and lo <= ref * (1 - s * (N + 1))) or (sd == -1 and hi >= ref * (1 + s * (N + 1)))):
                # si en la misma vela tocaría el objetivo y el stop, se supone lo peor: el stop
                px = ref * (1 - s * (N + 1) * sd)
                px = (min(px, o) if sd == 1 else max(px, o)) * (1 - SLIP * sd)
                cash += q * (p + sd * (px - p)) - q * px * TAKER
            elif (sd == 1 and hi >= tgt * (1 + TOL)) or (sd == -1 and lo <= tgt * (1 - TOL)):
                cash += q * (p + sd * (tgt - p)) - q * tgt * MAKER; nf += 1
            else:
                keep.append((sd, p, q))
        inv = keep
        if stop and not inv and ((side == 1 and lo <= ref * (1 - s * (N + 1))) or (side == -1 and hi >= ref * (1 + s * (N + 1)))):
            ref = c  # rehacer la rejilla tras el stop (las órdenes nuevas valen desde la vela siguiente)
            eq_d[day] = cash; continue
        held = {round((ref - x[1]) / (ref * s) * side) for x in inv}
        # compras (aperturas) en los niveles 1..N
        for k in range(1, N + 1):
            if k in held: continue
            lvl = ref * (1 - s * k * side)
            if (side == 1 and lo <= lvl * (1 - TOL)) or (side == -1 and hi >= lvl * (1 + TOL)):
                amt = min(unit, cash)
                if amt <= unit * 0.5: break
                px = min(lvl, o) if side == 1 else max(lvl, o)
                q = amt / px / (1 + MAKER)
                cash -= amt; inv.append((side, px, q)); held.add(k)
        if side == -1 and inv:
            cash -= sum(q * p for (_, p, q) in inv) * INT_H
        # si no hay nada dentro y el precio se aleja a favor, la rejilla sigue al precio
        if not inv and ((side == 1 and c > ref * (1 + s)) or (side == -1 and c < ref * (1 - s))):
            ref = c
        eq_d[day] = cash + sum(q * (p + sd * (c - p)) for (sd, p, q) in inv)
    return eq_d, nf

def stats(eq_d, year):
    ds = sorted(d for d in eq_d if d.year == year)
    if not ds: return None
    prev = [d for d in eq_d if d < ds[0]]
    v0 = eq_d[max(prev)] if prev else 1.0
    vals = np.array([eq_d[d] for d in ds])
    ends = {}
    for d, v in zip(ds, vals): ends[d.isocalendar()[:2]] = v
    w = np.array([v0] + list(ends.values())); wk = w[1:] / w[:-1] - 1
    peak = np.maximum.accumulate(np.r_[v0, vals]); dd = np.max((peak - np.r_[v0, vals]) / peak)
    return vals[-1] / v0 - 1, np.mean(wk > 0), dd

if __name__ == "__main__":
    YRS = range(2018, 2024)
    for m in ["btc", "eth", "xrp"]:
        h = load_1h(m); tr = trend(load_1d(m))
        for s, N, lados, stop in itertools.product([0.01, 0.02, 0.03, 0.05], [4, 8], [(1,), (1, -1)], [False, True]):
            e, nf = run(h, tr, s, N, lados, stop)
            st = [stats(e, y) for y in YRS]
            ok = ["C" if (r > 0.10 and v > 0.5 and dd <= 0.25) else "." for r, v, dd in st]
            txt = " ".join(f"{y}:{r*100:+5.0f}/{v*100:3.0f}/{dd*100:3.0f}" for y, (r, v, dd) in zip(YRS, st))
            print(f"{m} s={s:.2f} N={N} lados={''.join('L' if x==1 else 'C' for x in lados):2s} stop={int(stop)} {''.join(ok)} | {txt}", flush=True)
