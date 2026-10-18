"""Motor de simulación. Mismas reglas que la app:
- la señal del cierre del día i-1 se ejecuta en la apertura del día i
- solo compra BTC al contado, sin apalancamiento
- cada compra y venta paga comisión + deslizamiento
- si el saldo baja de 5 € el agente fracasa
"""
from dataclasses import dataclass, field


@dataclass
class Result:
    a: int
    b: int
    eq: list
    trades: list = field(default_factory=list)
    final: float = 0.0
    ret: float = 0.0
    fees: float = 0.0
    maxdd: float = 0.0
    dead: bool = False
    n_buys: int = 0
    closed: int = 0
    wins: int = 0
    avg_trade: float = 0.0  # ganancia neta media por operación cerrada (tras comisiones)

    def summary(self):
        return dict(final=round(float(self.final), 2), ret=round(float(self.ret), 4), fees=round(float(self.fees), 2),
                    maxdd=round(float(self.maxdd), 4), dead=bool(self.dead), trades=int(self.n_buys),
                    closed=int(self.closed), wins=int(self.wins),
                    avg_trade=round(float(self.avg_trade), 4))


def run(I, w, a, b, cfg):
    """Simula los días a..b (índices incluidos) con la exposición w."""
    cost = (cfg["fee"] + cfg["slip"]) / 100
    cap = cfg["cap"]
    cash, btc, cur = cap, 0.0, 0.0
    dead = False
    fees = 0.0
    peak, maxdd = cap, 0.0
    eq, trades = [], []
    open_val = None
    O, C = I.o, I.c
    for i in range(a, b + 1):
        if not dead and i > a:
            tgt = w[i - 1]
            if abs(tgt - cur) > 0.05 or (tgt == 0 and cur > 0):
                px = O[i]
                val = cash + btc * px
                diff = tgt * val - btc * px
                if abs(diff) > 0.5:
                    fee = abs(diff) * cost
                    fees += fee
                    if diff > 0:
                        btc += (diff - fee) / px
                        cash -= diff
                        if open_val is None:
                            open_val = val
                        trades.append(dict(i=i, side="compra", px=px, amt=diff))
                    else:
                        btc += diff / px
                        cash += -diff - fee
                        trades.append(dict(i=i, side="venta", px=px, amt=-diff))
                    if btc * px < 0.5 and open_val is not None:
                        trades[-1]["pnl"] = cash - open_val
                        trades[-1]["pnl_pct"] = (cash - open_val) / open_val
                        open_val = None
                cur = tgt
        v = cash + btc * C[i]
        eq.append(v)
        peak = max(peak, v)
        maxdd = max(maxdd, (peak - v) / peak)
        if not dead and v < 5:
            dead = True
            cash, btc, cur = v * (1 - cost), 0.0, 0.0
            trades.append(dict(i=i, side="fracasa", px=C[i], amt=v))
    closed = [t for t in trades if "pnl" in t]
    final = eq[-1]
    return Result(a=a, b=b, eq=eq, trades=trades, final=final, ret=final / cap - 1, fees=fees, maxdd=maxdd,
                  dead=dead, n_buys=sum(t["side"] == "compra" for t in trades), closed=len(closed),
                  wins=sum(t["pnl"] > 0 for t in closed),
                  avg_trade=(sum(t["pnl_pct"] for t in closed) / len(closed)) if closed else 0.0)
