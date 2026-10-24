"""Indicadores técnicos sobre velas (de cualquier temporalidad). Todo devuelve arrays numpy alineados con las velas."""
import numpy as np


class Ind:
    """Calcula y memoriza indicadores para un conjunto de velas (o, h, l, c)."""

    def __init__(self, o, h, l, c, bpy=365, v=None, flow=None):
        self.o, self.h, self.l, self.c = (np.asarray(x, dtype=float) for x in (o, h, l, c))
        self.v = np.asarray(v, dtype=float) if v is not None else None
        # flujo de órdenes: (volumen total, volumen de compradores agresivos) por vela; NaN donde no hay datos
        if flow is not None:
            self.fv, self.fb = (np.asarray(x, dtype=float) for x in flow)
        else:
            self.fv = self.fb = np.full(len(self.c), np.nan)
        self.bpy = bpy  # velas por año (365 en diario, 8760 en 1h)
        self.n = len(self.c)
        self._m = {}

    def _memo(self, key, fn):
        if key not in self._m:
            self._m[key] = fn()
        return self._m[key]

    def sma(self, n):
        def f():
            r = np.full(self.n, np.nan)
            cs = np.cumsum(np.insert(self.c, 0, 0.0))
            r[n - 1:] = (cs[n:] - cs[:-n]) / n
            return r
        return self._memo(("sma", n), f)

    def ema_of(self, src, n):
        r = np.full(self.n, np.nan)
        a = 2 / (n + 1)
        e = src[0]
        for i in range(self.n):
            e = src[0] if i == 0 else a * src[i] + (1 - a) * e
            if i >= n - 1:
                r[i] = e
        return r

    def rsi(self, n):
        def f():
            r = np.full(self.n, np.nan)
            g = l = 0.0
            c = self.c
            for i in range(1, self.n):
                d = c[i] - c[i - 1]
                up, dn = max(d, 0.0), max(-d, 0.0)
                if i <= n:
                    g += up / n
                    l += dn / n
                    if i == n:
                        r[i] = 100.0 if l == 0 else 100 - 100 / (1 + g / l)
                else:
                    g = (g * (n - 1) + up) / n
                    l = (l * (n - 1) + dn) / n
                    r[i] = 100.0 if l == 0 else 100 - 100 / (1 + g / l)
            return r
        return self._memo(("rsi", n), f)

    def stdev(self, n):
        def f():
            r = np.full(self.n, np.nan)
            if self.n >= n:
                win = np.lib.stride_tricks.sliding_window_view(self.c, n)
                r[n - 1:] = win.std(axis=1)
            return r
        return self._memo(("sd", n), f)


    def hh(self, n):
        """Máximo de las n velas ANTERIORES (sin incluir la actual)."""
        def f():
            r = np.full(self.n, np.nan)
            if self.n > n:
                r[n:] = np.lib.stride_tricks.sliding_window_view(self.h, n).max(axis=1)[:-1]
            return r
        return self._memo(("hh", n), f)


    def ll(self, n):
        def f():
            r = np.full(self.n, np.nan)
            if self.n > n:
                r[n:] = np.lib.stride_tricks.sliding_window_view(self.l, n).min(axis=1)[:-1]
            return r
        return self._memo(("ll", n), f)


    def atr(self, n):
        def f():
            r = np.full(self.n, np.nan)
            a = 0.0
            h, l, c = self.h, self.l, self.c
            for i in range(1, self.n):
                tr = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
                if i <= n:
                    a += tr / n
                    if i == n:
                        r[i] = a
                else:
                    a = (a * (n - 1) + tr) / n
                    r[i] = a
            return r
        return self._memo(("atr", n), f)

    def rvol(self, n):
        """Volatilidad realizada anualizada de las últimas n velas."""
        def f():
            r = np.full(self.n, np.nan)
            lr = np.zeros(self.n)
            lr[1:] = np.log(self.c[1:] / self.c[:-1])
            if self.n > n:
                win = np.lib.stride_tricks.sliding_window_view(lr, n)[1:]
                v = (win * win).mean(axis=1) - win.mean(axis=1) ** 2
                r[n:] = np.sqrt(np.maximum(v, 0.0) * self.bpy)
            return r
        return self._memo(("rv", n), f)

    def roc(self, n):
        """Variación del precio respecto a hace n velas."""
        def f():
            r = np.full(self.n, np.nan)
            r[n:] = self.c[n:] / self.c[:-n] - 1
            return r
        return self._memo(("roc", n), f)

    def z(self, n):
        """Distancia a la media de n velas, en desviaciones típicas (Bollinger)."""
        def f():
            with np.errstate(invalid="ignore", divide="ignore"):
                return (self.c - self.sma(n)) / self.stdev(n)
        return self._memo(("z", n), f)

    def ema(self, n):
        return self._memo(("ema", n), lambda: self.ema_of(self.c, n))

    def vwap_d(self):
        """VWAP anclado al día: precio medio ponderado por volumen desde las 00:00 UTC (se reinicia cada día).
        En velas diarias es el precio típico de la vela."""
        def f():
            tp = (self.h + self.l + self.c) / 3
            v = self.v if self.v is not None else np.ones(self.n)
            v = np.where(np.isnan(v) | (v <= 0), 1e-9, v)
            hour = getattr(self, "hour", None)
            out = np.empty(self.n)
            pv = vv = 0.0
            for i in range(self.n):
                if hour is None or hour[i] == 0 or self.bpy <= 365:
                    pv = vv = 0.0
                pv += tp[i] * v[i]
                vv += v[i]
                out[i] = pv / vv
            return out
        return self._memo(("vwap_d",), f)

    def vp_prev(self, bins=40, area=0.7):
        """Perfil de volumen de la sesión anterior (el día anterior en velas de 1 h / 4 h; los 20 días anteriores en
        velas diarias). Devuelve (POC, VAH, VAL) por vela: POC = precio con más volumen; VAH/VAL = techo y suelo de la
        zona donde se negoció el 70 % del volumen. El volumen de cada vela se reparte entre su mínimo y su máximo."""
        def f():
            n = self.n
            poc, vah, val = (np.full(n, np.nan) for _ in range(3))
            v = self.v if self.v is not None else np.ones(n)
            v = np.where(np.isnan(v) | (v <= 0), 0.0, v)
            hour = getattr(self, "hour", None)
            if self.bpy > 365 and hour is not None:
                starts = [i for i in range(n) if hour[i] == 0 or i == 0]
                sessions = list(zip(starts, starts[1:] + [n]))
            else:  # velas diarias: bloques de 20 días
                sessions = [(i, min(i + 20, n)) for i in range(0, n, 20)]
            prev = None
            for a, b in sessions:
                if prev is not None:
                    pa, pb = prev
                    lo, hi = np.nanmin(self.l[pa:pb]), np.nanmax(self.h[pa:pb])
                    if hi > lo:
                        edges = np.linspace(lo, hi, bins + 1)
                        vol = np.zeros(bins)
                        for i in range(pa, pb):
                            ia = max(0, min(bins - 1, int((self.l[i] - lo) / (hi - lo) * bins)))
                            ib = max(0, min(bins - 1, int((self.h[i] - lo) / (hi - lo) * bins)))
                            vol[ia:ib + 1] += v[i] / (ib - ia + 1)
                        k = int(np.argmax(vol))
                        lo_k, hi_k, tot = k, k, vol[k]
                        while tot < area * vol.sum() and (lo_k > 0 or hi_k < bins - 1):
                            dn = vol[lo_k - 1] if lo_k > 0 else -1
                            up = vol[hi_k + 1] if hi_k < bins - 1 else -1
                            if up >= dn:
                                hi_k += 1
                                tot += up
                            else:
                                lo_k -= 1
                                tot += dn
                        mid = (edges[:-1] + edges[1:]) / 2
                        poc[a:b], vah[a:b], val[a:b] = mid[k], edges[hi_k + 1], edges[lo_k]
                prev = (a, b)
            return poc, vah, val
        return self._memo(("vp_prev", bins, area), f)

    def er(self, n):
        """Eficiencia de Kaufman (0 = lateral, 1 = tendencia limpia) de las últimas n velas."""
        def f():
            r = np.full(self.n, np.nan)
            if self.n > n:
                d = np.abs(np.diff(self.c, prepend=self.c[0]))
                cs = np.cumsum(d)
                path = cs[n:] - cs[:-n]
                net = np.abs(self.c[n:] - self.c[:-n])
                with np.errstate(invalid="ignore", divide="ignore"):
                    r[n:] = np.where(path > 0, net / path, 0.0)
            return r
        return self._memo(("er", n), f)

    def macd_hist(self, f=12, s=26, sig=9):
        def g():
            line = self.ema_of(self.c, f) - self.ema_of(self.c, s)
            return line - self.ema_of(np.nan_to_num(line), sig)
        return self._memo(("macd", f, s, sig), g)

    # ------------------------------------------------------------------ flujo de órdenes

    def delta(self):
        """Delta de cada vela en tanto por uno: +1 = todo compras agresivas, -1 = todo ventas agresivas."""
        def f():
            with np.errstate(invalid="ignore", divide="ignore"):
                d = (2 * self.fb - self.fv) / self.fv
            d[~np.isfinite(d)] = np.nan
            return d
        return self._memo(("delta",), f)

    def delta_avg(self, n):
        """Delta medio de las últimas n velas (ponderado por volumen)."""
        def f():
            r = np.full(self.n, np.nan)
            if self.n >= n:
                net = np.lib.stride_tricks.sliding_window_view(2 * self.fb - self.fv, n).sum(axis=1)
                tot = np.lib.stride_tricks.sliding_window_view(self.fv, n).sum(axis=1)
                with np.errstate(invalid="ignore", divide="ignore"):
                    r[n - 1:] = net / tot
            r[~np.isfinite(r)] = np.nan
            return r
        return self._memo(("delta_avg", n), f)

    def cvd(self):
        """Delta acumulado (CVD): suma de compras menos ventas agresivas desde el principio."""
        def f():
            return np.cumsum(np.nan_to_num(2 * self.fb - self.fv))
        return self._memo(("cvd",), f)
