"""Indicadores técnicos sobre velas (de cualquier temporalidad). Todo devuelve arrays numpy alineados con las velas."""
import numpy as np


class Ind:
    """Calcula y memoriza indicadores para un conjunto de velas (o, h, l, c)."""

    def __init__(self, o, h, l, c, bpy=365, v=None):
        self.o, self.h, self.l, self.c = (np.asarray(x, dtype=float) for x in (o, h, l, c))
        self.v = np.asarray(v, dtype=float) if v is not None else None
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

    def macd_hist(self, f=12, s=26, sig=9):
        def g():
            line = self.ema_of(self.c, f) - self.ema_of(self.c, s)
            return line - self.ema_of(np.nan_to_num(line), sig)
        return self._memo(("macd", f, s, sig), g)
