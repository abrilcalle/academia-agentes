"""Un mercado = las velas de una temporalidad (1d, 4h o 1h) con sus indicadores."""
import bisect
import datetime as dt

from indicators import Ind

BARS_PER_DAY = {"1d": 1, "4h": 6, "1h": 24}
TF_LABEL = {"1d": "velas diarias", "4h": "velas de 4 horas", "1h": "velas de 1 hora"}


class Market:
    def __init__(self, tf, ts, o, h, l, c, v=None, flow=None):
        self.tf = tf
        self.ts = list(ts)
        self.bpd = BARS_PER_DAY[tf]
        self.I = Ind(o, h, l, c, bpy=365 * self.bpd, v=v, flow=flow)
        self.v = v
        self.n = len(self.ts)
        # hora (UTC) y día de la semana de cada vela, para las condiciones de estacionalidad
        self.I.hour = [d.hour for d in self.ts]
        self.I.dow = [d.weekday() for d in self.ts]

    def idx(self, when):
        """Primera vela que empieza en `when` o después (when: fecha, datetime o texto AAAA-MM-DD)."""
        if isinstance(when, str):
            when = dt.datetime.fromisoformat(when)
        elif isinstance(when, dt.date) and not isinstance(when, dt.datetime):
            when = dt.datetime(when.year, when.month, when.day)
        return bisect.bisect_left(self.ts, when)

    def end_idx(self, day):
        """Última vela del día `day` (incluido)."""
        if isinstance(day, str):
            day = dt.date.fromisoformat(day)
        return self.idx(day + dt.timedelta(days=1)) - 1

    def daily(self, eq, a):
        """Convierte una curva de saldo (desde la vela a) en {fecha: saldo al cierre del día}."""
        out = {}
        for k, v in enumerate(eq):
            out[self.ts[a + k].date()] = v
        return out
