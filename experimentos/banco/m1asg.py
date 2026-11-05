"""Banco (05/11/2026 15:20): variantes de "asegurar" del equipo (segunda toma y salida a la entrada tras asegurar).
Parchea lab/src/equipos.py (copia del repo) para que series() lea STAGES = [[ganancia, parte que se queda], ...]
y BE (si tras asegurar la ganancia de la operación vuelve a <= BE, el equipo sale del resto). Base = [[0.10, 0.5]] (código actual).
Uso: python m1asg.py (parchea), luego por variante:
  STAGES='[[0.10,0.5],[0.20,0.25]]' BE=nan OUTM=mat_X.pkl python m1.py && MAT=mat_X.pkl OUT=teams_X.pkl python m2x.py
  python m3x.py base X ...   (m1.py con el nombre de salida en OUTM)"""
import os
S = os.path.dirname(os.path.abspath(__file__))
p = os.path.join(S, "lab", "src", "equipos.py"); s = open(p).read()
old1 = """        if ASEGURAR_GANANCIA and (entry in hit or r.eq[j - h] / r.eq[max(entry - h, 0)] - 1 >= ASEGURAR_GANANCIA):
            hit.add(entry)
            seguro[n_] = entry
"""
new1 = """        g_ = r.eq[j - h] / r.eq[max(entry - h, 0)] - 1
        q_ = qst.get(entry, 1.0)
        for th_, kq_ in _STAGES:
            if g_ >= th_: q_ = min(q_, kq_)
        if q_ < 1 and _BE == _BE and g_ <= _BE: q_ = 0.0
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
s = s.replace(old1, new1).replace(old2, new2).replace("    seguro, hit = {}, set()  #", "    seguro, qst = {}, {}  #")
s = s.replace("def series(ac, ag, start, variante=None):", "import os as _os, json as _json\n_STAGES = _json.loads(_os.environ.get('STAGES', '[[0.10, 0.5]]'))\n_BE = float(_os.environ.get('BE', 'nan'))\n\n\ndef series(ac, ag, start, variante=None):", 1)
open(p, "w").write(s)
print("parcheado")
