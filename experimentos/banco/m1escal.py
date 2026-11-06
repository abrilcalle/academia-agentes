"""Banco (06/11/2026 15:00): "entrada escalonada" del equipo (confirmación). Cuando un agente abre una operación,
el equipo solo pone Q0 de su parte; el día siguiente a que la operación gane un Y % desde su entrada, completa la
posición (parte = 1, paga la compra de lo que añade). Se combina con "asegurar la mitad al +10 %" (manda la parte
más pequeña desde ese momento). Lo que no se pone espera en efectivo. Se puede hacer por la API (compras al contado).
Parchea lab/src/equipos.py (copia del repo). Q0=1 = base (código actual).
Uso: python m1escal.py (parchea), luego por variante:
  Q0=0.5 Y=0.03 OUTM=mat_X.pkl python m1.py && MAT=mat_X.pkl OUT=teams_X.pkl python m2x.py ; python m3x.py base X ..."""
import os
S = os.path.dirname(os.path.abspath(__file__))
p = os.path.join(S, "lab", "src", "equipos.py"); s = open(p).read()
old1 = """        if ASEGURAR_GANANCIA and (entry in hit or r.eq[j - h] / r.eq[max(entry - h, 0)] - 1 >= ASEGURAR_GANANCIA):
            hit.add(entry)
            seguro[n_] = entry
"""
new1 = """        g_ = r.eq[j - h] / r.eq[max(entry - h, 0)] - 1
        if g_ >= _Y:
            full_.add(entry)
        q_ = 1.0 if entry in full_ else _Q0
        if ASEGURAR_GANANCIA and (entry in hit or g_ >= ASEGURAR_GANANCIA):
            hit.add(entry)
            q_ = min(q_, ASEGURAR_QUEDA)
        if n_ == 0 or entry > last_bar[n_ - 1]:
            first_[n_] = entry
        if q_ < 1 or _Q0 < 1:
            seguro[n_] = (entry, q_)
"""
old2 = """        e_ = seguro.get(n_ - 1)
        if e_ is None or _AV0 <= days[n_] < _AV1:
            continue
        ret[n_] = ASEGURAR_QUEDA * ret[n_] - (0 if seguro.get(n_ - 2) == e_ else (1 - ASEGURAR_QUEDA) * coste)
        expo[n_ - 1] *= ASEGURAR_QUEDA
"""
new2 = """        if _AV0 <= days[n_] < _AV1:
            continue
        sg_ = seguro.get(n_ - 1)
        if sg_ is None:
            if _Q0 < 1 and n_ in first_:
                ret[n_] *= _Q0  # día de entrada: el equipo solo pone Q0
            continue
        e_, q_ = sg_
        pv_ = seguro.get(n_ - 2)
        qp_ = pv_[1] if pv_ and pv_[0] == e_ else (_Q0 if first_.get(n_ - 1) == e_ else 1.0)
        ret[n_] = q_ * ret[n_] - abs(qp_ - q_) * coste
        expo[n_ - 1] *= q_
"""
assert old1 in s and old2 in s
s = s.replace(old1, new1).replace(old2, new2).replace("    seguro, hit = {}, set()  #", "    seguro, hit, full_, first_ = {}, set(), set(), {}  #")
s = s.replace("    for n_ in range(1, len(days)):\n        if _AV0", "    for n_ in range(len(days)):\n        if _AV0")
s = s.replace("def series(ac, ag, start, variante=None):", "import os as _os\n_Q0 = float(_os.environ.get('Q0', '1'))\n_Y = float(_os.environ.get('Y', '0'))\n\n\ndef series(ac, ag, start, variante=None):", 1)
s = s.replace("asegurada=n_ in seguro)", "asegurada=n_ in seguro and seguro[n_][1] == ASEGURAR_QUEDA)")
assert "for n_ in range(len(days)):" in s
open(p, "w").write(s)
print("parcheado")
