"""Banco (06/11/2026 10:00): "entrada en retroceso" del equipo. Cuando un agente abre una operación, el equipo no
compra al cierre: deja una orden limitada a un PX % por debajo del precio de entrada (por encima, en cortos) y solo
entra si el precio la toca antes de que el agente cierre (y, con NW > 0, como mucho NW días después de la entrada).
Mientras espera, ese dinero queda reservado en efectivo. Si la orden se llena, el equipo gana el retroceso; si no
se llena, no entra. Parchea lab/src/equipos.py (copia del repo). PX=0 = base (código actual).
Uso: python m1entrada.py (parchea), luego por variante:
  PX=0.01 NW=0 python m1.py && mv mat.pkl mat_X.pkl && MAT=mat_X.pkl OUT=teams_X.pkl python m2x.py ; python m3x.py base X"""
import os
S = os.path.dirname(os.path.abspath(__file__))
p = os.path.join(S, "lab", "src", "equipos.py"); s = open(p).read()
old = """    # Asegurar la mitad: desde el día siguiente"""
new = """    if _PX > 0:
        lo_, hi_, c_ = mk.I.l, mk.I.h, mk.I.c
        ex_ = {tr[0]: tr[1] for tr in trades}
        if still_open is not None:
            ex_[still_open] = mk.n
        fill_ = {}
        for e_, x_ in ex_.items():
            sg_ = 1 if w[e_ - 1] > 0 else -1
            lim_ = c_[e_ - 1] * (1 - sg_ * _PX)
            fill_[e_] = None
            for jj in range(e_, min(x_, mk.n)):
                if _NW and (mk.ts[jj].date() - mk.ts[e_].date()).days > _NW:
                    break
                if (lo_[jj] <= lim_) if sg_ > 0 else (hi_[jj] >= lim_):
                    fill_[e_] = jj
                    break
        cst_ = (cfg.get("maker", cfg["fee"])) / 100
        for n_, j in enumerate(last_bar):
            cur = next((tr for tr in trades if tr[0] <= j < tr[1] or (tr[1] <= j and n_ > 0 and tr[1] > last_bar[n_ - 1])), None)
            e_ = cur[0] if cur else (still_open if still_open is not None and still_open <= j else None)
            if e_ is None or e_ not in fill_:
                continue
            jf = fill_[e_]
            if jf is None or jf > j:
                ret[n_], expo[n_] = 0.0, 0.0  # orden sin llenar: dinero reservado en efectivo
            elif n_ == 0 or jf > last_bar[n_ - 1]:
                eq_f = r.eq[max(e_ - 1 - h, 0)] * (1 - abs(float(w[e_ - 1])) * _PX)
                ret[n_] = r.eq[j - h] / eq_f - 1 - abs(float(w[e_ - 1])) * cst_  # se llena hoy: gana desde el precio límite
    # Asegurar la mitad: desde el día siguiente"""
assert old in s
s = s.replace(old, new, 1)
s = s.replace("def series(ac, ag, start, variante=None):", "import os as _os\n_PX = float(_os.environ.get('PX', '0'))\n_NW = int(_os.environ.get('NW', '0'))\n\n\ndef series(ac, ag, start, variante=None):", 1)
open(p, "w").write(s)
print("parcheado")
