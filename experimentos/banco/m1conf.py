"""Banco (06/11/2026 15:15): "entrar con confirmación" en el equipo. Mientras la operación de un agente no gane
al menos un Y % desde su entrada (al cierre del día), el equipo no le da dinero (como si la bloqueara el filtro de
tendencia) y lo reparte entre los demás; desde el día siguiente a que la gane, la trata como cualquier otra.
La compra del equipo la paga el coste de reparto habitual. Parchea lab/src/equipos.py. Y=0 = base.
Uso: python m1conf.py ; Y=0.05 OUTM=mat_X.pkl python m1.py && MAT=mat_X.pkl OUT=teams_X.pkl python m2x.py"""
import os
S = os.path.dirname(os.path.abspath(__file__))
p = os.path.join(S, "lab", "src", "equipos.py"); s = open(p).read()
old = """            P[n_] = BLOQUEADO  # va contra la tendencia diaria de su activo (o no hay tendencia clara): el equipo no le da dinero
"""
new = old + """        if _Y > 0 and entry not in conf_:
            if r.eq[j - h] / r.eq[max(entry - h, 0)] - 1 >= _Y:
                conf_.add(entry)
            else:
                P[n_] = BLOQUEADO
"""
assert old in s
s = s.replace(old, new).replace("    seguro, hit = {}, set()  #", "    seguro, hit, conf_ = {}, set(), set()  #")
s = s.replace("def series(ac, ag, start, variante=None):", "import os as _os\n_Y = float(_os.environ.get('Y', '0'))\n\n\ndef series(ac, ag, start, variante=None):", 1)
open(p, "w").write(s); print("parcheado")
