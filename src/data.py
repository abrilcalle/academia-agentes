"""Velas de BTC-EUR en diario (1d) y por horas (1h; las de 4h se construyen a partir de las de 1h).

Fuente principal: Bitvavo (el exchange donde se operará). Para los años anteriores a que Bitvavo
tenga histórico se completa con Bitstamp BTC/EUR. Solo se guardan velas ya cerradas (hora UTC).
Las fechas se guardan como datetime UTC sin zona horaria.
"""
import csv
import datetime as dt
import json
import os
import time
import urllib.request

UA = {"User-Agent": "academia-agentes/1.0"}
BITVAVO = "https://api.bitvavo.com/v2/{market}/candles?interval={interval}&limit=1440{end}"
BITSTAMP = "https://www.bitstamp.net/api/v2/ohlc/{pair}/?step={step}&limit=1000&start={start}"
STEP = {"1d": 86400, "4h": 14400, "1h": 3600}


def _get(url, tries=3):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except Exception:
            if k == tries - 1:
                raise
            time.sleep(2 * (k + 1))


def _utc(ts_seconds):
    return dt.datetime.fromtimestamp(ts_seconds, dt.timezone.utc).replace(tzinfo=None)


def _secs(d):
    return int(d.replace(tzinfo=dt.timezone.utc).timestamp())


def parse_bitvavo(rows):
    """[[ms, o, h, l, c, v], ...] (texto) -> dict datetime -> vela"""
    return {_utc(int(r[0]) / 1000): tuple(float(x) for x in r[1:6]) for r in rows}


def parse_bitstamp(payload):
    return {_utc(int(r["timestamp"])): (float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]), float(r["volume"]))
            for r in payload["data"]["ohlc"]}


def fetch_bitvavo(market, interval, since):
    out, end = {}, ""
    while True:
        rows = _get(BITVAVO.format(market=market, interval=interval, end=end))
        if not rows:
            break
        new = {k: v for k, v in parse_bitvavo(rows).items() if k not in out}
        if not new:
            break
        out.update(new)
        oldest_ms = min(int(r[0]) for r in rows)
        if _utc(oldest_ms / 1000) <= since:
            break
        end = f"&end={oldest_ms - 1}"
        time.sleep(0.25)
    return out


def fetch_bitstamp(pair, step, since, until):
    out = {}
    start = _secs(since)
    while True:
        new = {k: v for k, v in parse_bitstamp(_get(BITSTAMP.format(pair=pair, step=step, start=start))).items() if k not in out}
        if not new:
            break
        out.update(new)
        last = max(new)
        if last >= until:
            break
        start = _secs(last) + step
        time.sleep(0.25)
    return out


def _read(path, out):
    with open(path) as f:
        for r in csv.DictReader(f):
            key = r.get("ts") or r.get("date")
            out[dt.datetime.fromisoformat(key)] = tuple(float(r[k]) for k in ("open", "high", "low", "close", "volume"))


def _rows(candles):
    lines = ["ts,open,high,low,close,volume"]
    for d in sorted(candles):
        o, h, l, c, v = candles[d][:5]
        lines.append(f"{d.isoformat(timespec='minutes')},{o},{h},{l},{c},{round(v, 6)}")
    return "\n".join(lines) + "\n"


def load_csv(path):
    """Lee un CSV, o una carpeta con un CSV por mes (así el histórico de 1h no se reescribe entero cada día)."""
    out = {}
    if os.path.isdir(path):
        for fn in sorted(os.listdir(path)):
            if fn.endswith(".csv"):
                _read(os.path.join(path, fn), out)
    elif os.path.exists(path):
        _read(path, out)
    return out


def save_csv(path, candles):
    if path.endswith("/") or os.path.isdir(path):
        os.makedirs(path, exist_ok=True)
        months = {}
        for d, v in candles.items():
            months.setdefault(d.strftime("%Y-%m"), {})[d] = v
        for m, part in months.items():
            fp = os.path.join(path, f"{m}.csv")
            txt = _rows(part)
            if not os.path.exists(fp) or open(fp).read() != txt:
                with open(fp, "w") as f:
                    f.write(txt)
        return
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        f.write(_rows(candles))


def update(path, interval="1d", market="BTC-EUR", since=dt.datetime(2017, 1, 1), log=print):
    """Descarga lo que falta, guarda el CSV y devuelve dict datetime -> (o,h,l,c,v)."""
    step = STEP[interval]
    now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    merged = load_csv(path)
    try:
        start = (max(merged) - dt.timedelta(seconds=step * 5)) if merged else since
        bv = fetch_bitvavo(market, interval, since=start)
        merged.update(bv)
        log(f"Bitvavo {interval}: {len(bv)} velas descargadas")
    except Exception as e:  # noqa: BLE001
        log(f"Aviso: no se pudo descargar {interval} de Bitvavo ({e})")
    if not merged or min(merged) > since + dt.timedelta(days=7):
        until = (min(merged) - dt.timedelta(seconds=step)) if merged else now
        try:
            bs = fetch_bitstamp("btceur", step, since, until)
            added = 0
            for d, v in bs.items():
                if d not in merged and d <= until:
                    merged[d] = v
                    added += 1
            log(f"Bitstamp BTC/EUR {interval}: {added} velas antiguas añadidas")
        except Exception as e:  # noqa: BLE001
            log(f"Aviso: no se pudo descargar {interval} de Bitstamp ({e})")
    merged = {d: v[:5] for d, v in merged.items() if since <= d and d + dt.timedelta(seconds=step) <= now}
    if not merged:
        raise RuntimeError(f"No hay datos {interval}: revisa la conexión con Bitvavo/Bitstamp.")
    save_csv(path, merged)
    return merged


def resample(candles, hours):
    """Agrupa velas de 1h en velas de `hours` horas (alineadas a medianoche UTC)."""
    out = {}
    for d in sorted(candles):
        o, h, l, c, v = candles[d]
        k = d.replace(hour=d.hour - d.hour % hours, minute=0)
        if k not in out:
            out[k] = [o, h, l, c, v]
        else:
            x = out[k]
            x[1], x[2], x[3], x[4] = max(x[1], h), min(x[2], l), c, x[4] + v
    return {k: tuple(v) for k, v in out.items()}


def to_arrays(candles, interval="1d"):
    """Rellena huecos con la vela anterior y devuelve (fechas, o, h, l, c, v)."""
    step = dt.timedelta(seconds=STEP[interval])
    keys = sorted(candles)
    d, d1 = keys[0], keys[-1]
    ts, o, h, l, c, v = [], [], [], [], [], []
    prev = None
    while d <= d1:
        x = candles.get(d) or (prev[3], prev[3], prev[3], prev[3], 0.0)
        ts.append(d)
        o.append(x[0]); h.append(x[1]); l.append(x[2]); c.append(x[3]); v.append(x[4])
        prev = x
        d += step
    return ts, o, h, l, c, v
