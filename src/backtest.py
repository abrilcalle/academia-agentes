"""Motor de simulación. Mismas reglas que la app:
- la señal del cierre de la vela i-1 se ejecuta en la vela i
- sin apalancamiento: como mucho el 100 % del saldo, comprado (largo) o vendido en corto
- órdenes limitadas (si se activan): se pone una orden al precio del último cierre; si el precio
  la toca en la vela siguiente se ejecuta pagando la comisión "maker" (más barata, sin deslizamiento);
  si no, en la vela de después se ejecuta a mercado (comisión "taker" + deslizamiento)
- los cortos pagan además un interés por hora por el BTC prestado
- si el saldo baja de 5 € el agente fracasa
- con usdc=True se opera en pares contra USDC (comisión más baja): precios en USDC, saldo contado en euros
  con el cambio USDC/EUR de cada vela (así se nota si el dólar sube o baja)
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
    shorts: int = 0

    def summary(self):
        return dict(final=round(float(self.final), 2), ret=round(float(self.ret), 4), fees=round(float(self.fees), 2),
                    maxdd=round(float(self.maxdd), 4), dead=bool(self.dead), trades=int(self.n_buys),
                    closed=int(self.closed), wins=int(self.wins),
                    avg_trade=round(float(self.avg_trade), 4), cortos=int(self.shorts))


OPEN_SIDES = ("compra", "corto")
THROUGH = 0.0005  # el precio tiene que pasar un 0,05 % más allá de la orden limitada para darla por ejecutada


def run(I, w, a, b, cfg):
    """Simula las velas a..b (índices incluidos) con la exposición w (-1..1; negativo = corto)."""
    taker = (cfg["fee"] + cfg["slip"]) / 100
    maker = cfg.get("maker", cfg["fee"]) / 100
    limit = bool(cfg.get("limit"))
    borrow = cfg.get("borrow_h", 0.0) / 100 * (8760 / I.bpy)  # interés del préstamo por vela
    cap = cfg["cap"]
    # en USDC: se opera con precios en USDC y el saldo se cuenta en euros con el cambio de cada vela
    fx = getattr(I, "fx", None) if cfg.get("usdc") else None
    k = fx if fx is not None else None
    if k is not None:
        O, H, L, C = I.o_u, I.h_u, I.l_u, I.c_u
        cash = cap / k[a] * (1 - cfg.get("conversion", 0.0) / 100)  # de euros a USDC una vez
    else:
        O, H, L, C = I.o, I.h, I.l, I.c
        cash = cap
    btc, cur = 0.0, 0.0
    dead, force_mkt = False, False
    fees = 0.0
    peak, maxdd = cap, 0.0
    eq, trades = [], []
    open_val = None
    for i in range(a, b + 1):
        if not dead and i > a:
            tgt = w[i - 1]
            if abs(tgt - cur) > 0.05 or (tgt == 0 and cur != 0):
                if limit and not force_mkt:
                    lp = C[i - 1]
                    diff0 = tgt * (cash + btc * lp) - btc * lp
                    # prudente: solo se da por llena si el precio cruza la orden (no basta con tocarla)
                    if diff0 > 0 and L[i] < lp * (1 - THROUGH):
                        px, rate = min(O[i], lp), maker
                    elif diff0 < 0 and H[i] > lp * (1 + THROUGH):
                        px, rate = max(O[i], lp), maker
                    else:
                        px = None
                        force_mkt = True  # no se llenó: en la siguiente vela, a mercado
                else:
                    px, rate = O[i], taker
                if px is not None:
                    force_mkt = False
                    val = cash + btc * px
                    diff = tgt * val - btc * px
                    if abs(diff) > 0.5:
                        before = btc
                        fee = abs(diff) * rate
                        fees += fee
                        cash -= diff + fee
                        btc += diff / px
                        if abs(btc * px) < 0.5:  # posición cerrada: el resto, a euros
                            cash += btc * px
                            btc = 0.0
                        if before >= 0 and diff > 0:
                            side = "compra"
                        elif before > 0:
                            side = "venta" if btc >= 0 else "corto"
                        elif diff < 0:
                            side = "corto"
                        else:
                            side = "cierra corto" if btc <= 0 else "compra"
                        if abs(before * px) < 0.5 and btc != 0:
                            open_val = val
                        kx = k[i] if k is not None else 1.0
                        trades.append(dict(i=i, side=side, px=px * kx, amt=abs(diff) * kx))  # en euros
                        if btc == 0 and open_val is not None:
                            trades[-1]["pnl"] = (cash - open_val) * kx
                            trades[-1]["pnl_pct"] = (cash - open_val) / open_val
                            open_val = None
                    cur = tgt
        if btc < 0 and not dead:  # interés por el BTC prestado
            f = -btc * C[i] * borrow
            cash -= f
            fees += f
        v = (cash + btc * C[i]) * (k[i] if k is not None else 1.0)  # saldo en euros
        eq.append(v)
        peak = max(peak, v)
        maxdd = max(maxdd, (peak - v) / peak)
        if not dead and v < 5:
            dead = True
            cash, btc, cur = (cash + btc * C[i]) * (1 - taker), 0.0, 0.0
            trades.append(dict(i=i, side="fracasa", px=C[i], amt=v))
    closed = [t for t in trades if "pnl" in t]
    final = eq[-1]
    return Result(a=a, b=b, eq=eq, trades=trades, final=final, ret=final / cap - 1, fees=fees, maxdd=maxdd,
                  dead=dead, n_buys=sum(t["side"] in OPEN_SIDES for t in trades), closed=len(closed),
                  wins=sum(t["pnl"] > 0 for t in closed),
                  avg_trade=(sum(t["pnl_pct"] for t in closed) / len(closed)) if closed else 0.0,
                  shorts=sum(t["side"] == "corto" for t in trades))
