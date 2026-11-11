# Banco (11/11/2026 21:00): CUÁNDO se aplica el filtro de tendencia del equipo dentro de la vida de una operación.
# Parte de mat_raw.pkl (m1raw.py con TEND=0 y el parche SIDES: días, lado y vela de entrada de cada operación abierta).
# Filtro igual que el código (media 50 + pendiente 10). Variantes (GATE=):
#  base    -> cada día: bloqueada si la tendencia no va a favor (como ahora; el equipo puede entrar tarde y salir/volver)
#  nace    -> si el primer día de la operación va contra la tendencia, queda bloqueada toda su vida (no entra tarde)
#  pega    -> en cuanto se bloquea un día, queda bloqueada el resto de su vida (ni entra tarde ni vuelve)
#  entrada -> se decide solo el primer día: si va a favor, el equipo la acompaña toda la vida aunque la tendencia gire
#  salida  -> puede entrar tarde, pero si ya estaba dentro y se bloquea, no vuelve (salidaN: solo si lleva N días seguidos bloqueada)
# Uso: GATE=nace OUTM=mat_nace.pkl python m2gate.py ; luego MAT=mat_nace.pkl ENS=post OUT=teams_nace.pkl python m2ens.py
import os, sys, pickle, datetime as dt
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "lab", "src"))
import numpy as np
import data as datamod
M = pickle.load(open(os.path.join(S, "mat_raw.pkl"), "rb"))
days = M["days"]; pos = {d: k for k, d in enumerate(days)}
GATE = os.environ.get("GATE", "base")

def closes(a):
    c = datamod.load_csv(os.path.join(S, "loc", a.split("-")[0].lower() + "_1d.csv"))
    ks = sorted(k for k in c if k < dt.datetime(2024, 1, 1))
    return [k.date() for k in ks], np.array([c[k][3] for k in ks], float)

TR = {}
for a in {i["activo"] for i in M["info"]}:
    ds, c = closes(a)
    ma = np.convolve(c, np.ones(50) / 50, "full")[:len(c)]
    t = {}
    for i in range(59, len(c)):
        v = 1 if c[i] > ma[i] else -1
        if (ma[i] - ma[i - 10]) * v <= 0: v = 0
        t[ds[i]] = v
    TR[a] = t

P = M["P"].copy(); nb = 0
for j, inf in enumerate(M["info"]):
    sd = M["sides"].get(inf["id"])
    if not sd: continue
    st = {}  # vela de entrada -> estado: primero (bool), bloqueo_inicial, estuvo_dentro, pegado
    for d, s, e in zip(*sd):
        tv = TR[inf["activo"]].get(d)
        ok = tv is None or tv * s > 0
        o = st.get(e)
        if o is None:
            o = st[e] = dict(ini=ok, dentro=False, pegado=False)
        if GATE == "base": blk = not ok
        elif GATE == "nace": blk = (not o["ini"]) or not ok
        elif GATE == "pega":
            if not ok: o["pegado"] = True
            blk = o["pegado"]
        elif GATE == "entrada": blk = not o["ini"]
        elif GATE.startswith("salida"):
            nd = int(GATE[6:] or 1)  # salidaN: solo queda fuera para siempre si lleva N días seguidos bloqueada tras haber estado dentro
            o["fuera"] = 0 if ok else o.get("fuera", 0) + 1
            if o["dentro"] and o["fuera"] >= nd: o["pegado"] = True
            blk = o["pegado"] or not ok
            if not blk: o["dentro"] = True
        else: raise SystemExit(GATE)
        k = pos.get(d)
        if blk and k is not None and P[j, k] > 0:
            P[j, k] = -1.0; nb += 1
print(GATE, "bloqueadas", nb, "abiertas", int((M["P"] > 0).sum()), flush=True)
if os.path.exists(os.path.join(S, "mat.pkl")):
    Pb = pickle.load(open(os.path.join(S, "mat.pkl"), "rb"))["P"]
    print("difiere del filtro del código en", int(((Pb < 0) != (P < 0)).sum()), "días-operación", flush=True)
M = dict(M); M["P"] = P; M.pop("sides")
pickle.dump(M, open(os.path.join(S, os.environ.get("OUTM", f"mat_{GATE}.pkl")), "wb"))
