# Banco (12/11/2026 21:00): umbral de 'asegurar la mitad' según la operación. Parche para lab/src/equipos.py
# (aplicar con: cd lab && patch -p0 src/equipos.py < m1aseg.diff, quitando estas líneas). Uso: ASEG=vol_3|gan_0.5|tf_10 OUTM=mat_X.pkl python m1.py ;
# luego MAT=mat_X.pkl ENS=post OUT=teams_X.pkl python m2ens.py ; python m3x.py base X
# --- /home/claude/academia-agentes/src/equipos.py	2026-11-11 08:08:57.217359328 +0000
# +++ src/equipos.py	2026-11-12 20:05:59.371911924 +0000
# @@ -156,6 +156,29 @@
#      return tp, sl, max(1, int(days * mk.bpd))
#  
#  
# +import os as _os
# +_AM = _os.environ.get("ASEG", "base")
# +def _aseg_thr(ag, mk, e, trades, reg):
# +    """Banco 12/11: umbral de 'asegurar la mitad' según la operación (fijo 10 % en la base)."""
# +    if _AM == "base": return ASEGURAR_GANANCIA
# +    kind, k = _AM.split("_"); k = float(k)
# +    if kind == "vol":  # k x volatilidad diaria del mercado (últimos 20 días) en la entrada
# +        c = mk.I.c; n = int(20 * mk.bpd)
# +        x = np.diff(np.log(c[max(0, e - n):e + 1]))
# +        sd = float(np.std(x)) * np.sqrt(mk.bpd) if len(x) > 5 else 0.03
# +        return float(np.clip(k * sd, 0.03, 0.30))
# +    if kind == "gan":  # k x ganancia media de sus operaciones ganadoras (mismo tipo de mercado si hay 2+)
# +        past = [tr for tr in trades if tr[1] <= e]
# +        gw = [tr[2] for tr in past if tr[2] > 0 and reg[tr[0]] == reg[e]]
# +        if len(gw) < 2: gw = [tr[2] for tr in past if tr[2] > 0]
# +        g = float(np.mean(gw)) if gw else ASEGURAR_GANANCIA
# +        return float(np.clip(k * g, 0.03, 0.30))
# +    if kind == "tf":  # por temporalidad: 1h k/2, 4h 3k/4, 1d k (k en %)
# +        f = {"1h": 0.5, "4h": 0.75}.get(ag.get("tf") or ag.get("temporalidad"), 1.0)
# +        return k / 100 * f
# +    raise SystemExit(_AM)
# +
# +
#  def series(ac, ag, start, variante=None):
#      """Desde `start`, por día: rentabilidad, exposición al cierre, y para la operación abierta al cierre
#      la probabilidad estimada de acabar ganando (P) y la ganancia media cuando gana (G).
# @@ -201,6 +224,7 @@
#      L = np.zeros(len(days))  # lo que pierde si sale por el stop
#      rng = np.random.default_rng(zlib.crc32(ag["id"].encode()))
#      tend = trend_by_day(ac, ag)
# +    _thr = {}
#      seguro, hit = {}, set()  # día -> operación en la que el equipo ya aseguró la mitad (al cierre de ese día)
#      for n_, j in enumerate(last_bar):
#          if days[n_] < s0 - dt.timedelta(days=1) or expo[n_] <= 0.05:
# @@ -209,7 +233,9 @@
#          entry = cur[0] if cur else (still_open if still_open is not None and still_open <= j else None)
#          if entry is None:
#              continue
# -        if ASEGURAR_GANANCIA and (entry in hit or r.eq[j - h] / r.eq[max(entry - h, 0)] - 1 >= ASEGURAR_GANANCIA):
# +        if entry not in _thr:
# +            _thr[entry] = _aseg_thr(ag, mk, entry, trades, reg)
# +        if ASEGURAR_GANANCIA and (entry in hit or r.eq[j - h] / r.eq[max(entry - h, 0)] - 1 >= _thr[entry]):
#              hit.add(entry)
#              seguro[n_] = entry
#          past = [tr for tr in trades if tr[1] <= j]
