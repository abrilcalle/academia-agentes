"""Banco (05/11/2026 21:00): "stop por tiempo" del equipo. Si una operación lleva TN días abierta y en el primer
cierre con esa edad gana <= TG (p. ej. 0 = no va en positivo), el equipo se queda solo TQ de su parte el resto
de la operación (0 = sale del todo; paga la venta una vez). Se combina con "asegurar la mitad al +10 %" (la parte
más pequeña manda). Parchea lab/src/equipos.py (copia del repo). TN=0 = base (código actual).
Uso: python m1tiempo.py (parchea), luego por variante:
  TN=5 TG=0 TQ=0 OUTM=mat_X.pkl python m1.py && MAT=mat_X.pkl OUT=teams_X.pkl python m2x.py ; python m3x.py base X ..."""
import os
S = os.path.dirname(os.path.abspath(__file__))
p = os.path.join(S, "lab", "src", "equipos.py"); s = open(p).read()
old1 = """        if ASEGURAR_GANANCIA and (entry in hit or r.eq[j - h] / r.eq[max(entry - h, 0)] - 1 >= ASEGURAR_GANANCIA):
            hit.add(entry)
            seguro[n_] = entry
"""
new1 = """        g_ = r.eq[j - h] / r.eq[max(entry - h, 0)] - 1
        q_ = qst.get(entry, 1.0)
        if ASEGURAR_GANANCIA and g_ >= ASEGURAR_GANANCIA:
            q_ = min(q_, ASEGURAR_QUEDA)
        if _TN and entry not in tchk and (days[n_] - mk.ts[entry].date()).days >= _TN:
            tchk.add(entry)
            if g_ <= _TG:
                q_ = min(q_, _TQ)
        if q_ < 1:
            qst[entry] = q_
            seguro[n_] = (entry, q_)
"""
old2 = """        e_ = seguro.get(n_ - 1)
        if e_ is None or _AV0 <= days[n_] < _AV1:
            continue
        ret[n_] = ASEGURAR_QUEDA * ret[n_] - (0 if seguro.get(n_ - 2) == e_ else (1 - ASEGURAR_QUEDA) * coste)
        expo[n_ - 1] *= ASEGURAR_QUEDA
"""
new2 = """        sg_ = seguro.get(n_ - 1)
        if sg_ is None or _AV0 <= days[n_] < _AV1:
            continue
        e_, q_ = sg_
        pv_ = seguro.get(n_ - 2)
        qp_ = pv_[1] if pv_ and pv_[0] == e_ else 1.0
        ret[n_] = q_ * ret[n_] - max(qp_ - q_, 0) * coste
        expo[n_ - 1] *= q_
"""
assert old1 in s and old2 in s
s = s.replace(old1, new1).replace(old2, new2).replace("    seguro, hit = {}, set()  #", "    seguro, qst, tchk = {}, {}, set()  #")
s = s.replace("def series(ac, ag, start, variante=None):", "import os as _os\n_TN = int(_os.environ.get('TN', '0'))\n_TG = float(_os.environ.get('TG', '0'))\n_TQ = float(_os.environ.get('TQ', '0'))\n\n\ndef series(ac, ag, start, variante=None):", 1)
s = s.replace("asegurada=n_ in seguro)", "asegurada=n_ in seguro and seguro[n_][1] == ASEGURAR_QUEDA)")
open(p, "w").write(s)
print("parcheado")
