"""Figuras de chartismo (análisis técnico clásico) detectadas sin mirar el futuro.

Todas se basan en "pivotes": un mínimo (o máximo) local de k velas a cada lado. Un pivote en la
vela j solo se conoce en la vela j+k, así que cada figura usa únicamente pivotes ya confirmados.
Cada función devuelve un array de booleanos: True en la vela en la que la figura se completa
(normalmente, cuando el precio rompe la "línea de cuello").

Figuras de entrada (alcistas): doble suelo (W), triple suelo, hombro-cabeza-hombro invertido,
triángulo ascendente, bandera alcista / patrón N, rebote en zona de soporte (demanda),
ruptura de resistencia con volumen.
Figuras de salida (bajistas): doble techo (M), hombro-cabeza-hombro, pérdida de soporte.
"""
import numpy as np

K = 3  # velas a cada lado para confirmar un pivote


def pivots(I):
    """Listas de pivotes confirmados: (vela_confirmación, vela_pivote, precio)."""
    if "piv" in I._m:
        return I._m["piv"]
    h, l = I.h, I.l
    lows, highs = [], []
    n = I.n
    for j in range(K, n - K):
        lo = l[j - K:j + K + 1]
        if l[j] == lo.min() and l[j] < l[j - 1]:
            lows.append((j + K, j, float(l[j])))
        hi = h[j - K:j + K + 1]
        if h[j] == hi.max() and h[j] > h[j - 1]:
            highs.append((j + K, j, float(h[j])))
    I._m["piv"] = (lows, highs)
    return lows, highs


def _recent(piv, i, n, ptr):
    """Pivotes confirmados hasta la vela i y dentro de las últimas n velas (ptr: índice móvil)."""
    while ptr[0] < len(piv) and piv[ptr[0]][0] <= i:
        ptr[0] += 1
    out = []
    j = ptr[0] - 1
    while j >= 0 and piv[j][1] >= i - n:
        out.append(piv[j])
        j -= 1
    return out[::-1]  # del más antiguo al más reciente


def _memo(I, key, fn):
    if key not in I._m:
        I._m[key] = fn()
    return I._m[key]


def double_bottom(I, n, tol):
    """W: dos mínimos parecidos y el precio rompe el máximo entre ambos."""
    def f():
        lows, _ = pivots(I)
        out = np.zeros(I.n, bool)
        ptr = [0]
        c, h = I.c, I.h
        for i in range(1, I.n):
            pl = _recent(lows, i, n, ptr)
            if len(pl) < 2:
                continue
            (_, a, la), (_, b, lb) = pl[-2], pl[-1]
            if b - a < 3 or abs(lb - la) / la > tol:
                continue
            neck = h[a:b + 1].max()
            if c[i] > neck >= c[i - 1]:
                out[i] = True
        return out
    return _memo(I, ("W", n, tol), f)


def double_top(I, n, tol):
    """M: dos máximos parecidos y el precio pierde el mínimo entre ambos."""
    def f():
        _, highs = pivots(I)
        out = np.zeros(I.n, bool)
        ptr = [0]
        c, l = I.c, I.l
        for i in range(1, I.n):
            ph = _recent(highs, i, n, ptr)
            if len(ph) < 2:
                continue
            (_, a, ha), (_, b, hb) = ph[-2], ph[-1]
            if b - a < 3 or abs(hb - ha) / ha > tol:
                continue
            neck = l[a:b + 1].min()
            if c[i] < neck <= c[i - 1]:
                out[i] = True
        return out
    return _memo(I, ("M", n, tol), f)


def triple_bottom(I, n, tol):
    def f():
        lows, _ = pivots(I)
        out = np.zeros(I.n, bool)
        ptr = [0]
        c, h = I.c, I.h
        for i in range(1, I.n):
            pl = _recent(lows, i, n, ptr)
            if len(pl) < 3:
                continue
            (_, a, x1), (_, _, x2), (_, b, x3) = pl[-3:]
            m = (x1 + x2 + x3) / 3
            if max(abs(x1 - m), abs(x2 - m), abs(x3 - m)) / m > tol:
                continue
            neck = h[a:b + 1].max()
            if c[i] > neck >= c[i - 1]:
                out[i] = True
        return out
    return _memo(I, ("3W", n, tol), f)


def inv_head_shoulders(I, n, tol):
    """Hombro-cabeza-hombro invertido: tres mínimos, el del medio más bajo; rompe el cuello."""
    def f():
        lows, _ = pivots(I)
        out = np.zeros(I.n, bool)
        ptr = [0]
        c, h = I.c, I.h
        for i in range(1, I.n):
            pl = _recent(lows, i, n, ptr)
            if len(pl) < 3:
                continue
            (_, a, s1), (_, _, hd), (_, b, s2) = pl[-3:]
            if not (hd < s1 * (1 - tol / 2) and hd < s2 * (1 - tol / 2) and abs(s1 - s2) / s1 <= tol * 1.5):
                continue
            neck = h[a:b + 1].max()
            if c[i] > neck >= c[i - 1]:
                out[i] = True
        return out
    return _memo(I, ("iHCH", n, tol), f)


def head_shoulders(I, n, tol):
    def f():
        _, highs = pivots(I)
        out = np.zeros(I.n, bool)
        ptr = [0]
        c, l = I.c, I.l
        for i in range(1, I.n):
            ph = _recent(highs, i, n, ptr)
            if len(ph) < 3:
                continue
            (_, a, s1), (_, _, hd), (_, b, s2) = ph[-3:]
            if not (hd > s1 * (1 + tol / 2) and hd > s2 * (1 + tol / 2) and abs(s1 - s2) / s1 <= tol * 1.5):
                continue
            neck = l[a:b + 1].min()
            if c[i] < neck <= c[i - 1]:
                out[i] = True
        return out
    return _memo(I, ("HCH", n, tol), f)


def asc_triangle(I, n, tol):
    """Triángulo ascendente: techos a la misma altura y suelos cada vez más altos; rompe el techo."""
    def f():
        lows, highs = pivots(I)
        out = np.zeros(I.n, bool)
        pl_ptr, ph_ptr = [0], [0]
        c = I.c
        for i in range(1, I.n):
            ph = _recent(highs, i, n, ph_ptr)
            pl = _recent(lows, i, n, pl_ptr)
            if len(ph) < 2 or len(pl) < 2:
                continue
            tops = [x[2] for x in ph[-3:]]
            top = max(tops)
            if (top - min(tops)) / top > tol:
                continue
            if not (pl[-1][2] > pl[-2][2] * (1 + tol / 3)):
                continue
            if c[i] > top >= c[i - 1]:
                out[i] = True
        return out
    return _memo(I, ("TRI", n, tol), f)


def bull_flag(I, n, imp):
    """Bandera alcista / patrón N: subida fuerte (>= imp), retroceso de menos de la mitad
    y el precio supera el máximo de la subida."""
    def f():
        out = np.zeros(I.n, bool)
        c, h, l = I.c, I.h, I.l
        m = max(3, n // 3)
        for i in range(n, I.n):
            seg_h = h[i - n:i]
            p = int(np.argmax(seg_h)) + i - n  # máximo de la subida
            if p <= i - n + m or p >= i - 1:
                continue
            base = l[max(0, p - m):p].min()
            if seg_h.max() / base - 1 < imp:
                continue
            pull = l[p:i].min()
            if (seg_h.max() - pull) > 0.5 * (seg_h.max() - base):
                continue
            if c[i] > seg_h.max() >= c[i - 1]:
                out[i] = True
        return out
    return _memo(I, ("FLAG", n, imp), f)


def support_bounce(I, n, tol):
    """Zona de demanda: el precio toca un nivel donde ya se apoyó al menos dos veces y rebota."""
    def f():
        lows, _ = pivots(I)
        out = np.zeros(I.n, bool)
        ptr = [0]
        c, o, l = I.c, I.o, I.l
        for i in range(1, I.n):
            pl = _recent(lows, i, n, ptr)
            if len(pl) < 2:
                continue
            lv = [x[2] for x in pl]
            for j in range(len(lv) - 1, -1, -1):
                level = lv[j]
                touches = sum(1 for x in lv if abs(x - level) / level <= tol)
                if touches >= 2 and abs(l[i] - level) / level <= tol and c[i] > level and c[i] > o[i]:
                    out[i] = True
                    break
        return out
    return _memo(I, ("SUP", n, tol), f)


def support_break(I, n, tol):
    """Pierde un soporte tocado al menos dos veces."""
    def f():
        lows, _ = pivots(I)
        out = np.zeros(I.n, bool)
        ptr = [0]
        c = I.c
        for i in range(1, I.n):
            pl = _recent(lows, i, n, ptr)
            if len(pl) < 2:
                continue
            lv = sorted(x[2] for x in pl)
            for level in lv:
                touches = sum(1 for x in lv if abs(x - level) / level <= tol)
                if touches >= 2 and c[i] < level * (1 - tol) <= c[i - 1]:
                    out[i] = True
                    break
        return out
    return _memo(I, ("SUPX", n, tol), f)


def volume_ratio(I, n=20):
    def f():
        v = I.v if I.v is not None else np.zeros(I.n)
        r = np.full(I.n, np.nan)
        if I.n > n:
            cs = np.cumsum(np.insert(v, 0, 0.0))
            avg = (cs[n:] - cs[:-n]) / n  # media de las n velas anteriores (sin la actual)
            with np.errstate(invalid="ignore", divide="ignore"):
                r[n:] = v[n:] / avg[:-1]
        return r
    return _memo(I, ("VR", n), f)


def resistance_break_volume(I, n, vol):
    """Rompe el máximo de n velas con un volumen al menos `vol` veces el normal."""
    def f():
        with np.errstate(invalid="ignore"):
            return (I.c > I.hh(n)) & (volume_ratio(I) > vol)
    return _memo(I, ("RBV", n, vol), f)
