# Banco (20/11/2026 15:00): filtro de tendencia del equipo SEGÚN EL TIPO de agente.
# Parte de mat_raw.pkl (m1raw.py con TEND=0 y el parche SIDES: días, lado y vela de entrada de cada operación abierta).
# El filtro del código (media 50 + pendiente 10) bloquea igual a todos. Los agentes "contra tendencia" (compran caídas:
# z_bajo, rsi_bajo, rebote_soporte, doble/triple suelo, mercado_lateral, bajo_media, rebota_poc; familias rsi/boll/connors)
# y los operadores diarios (tienen su propio detector de régimen) quizá no deberían seguirlo. Variantes (GATE=):
#  base      -> como el código
#  mr_libre  -> agentes contra tendencia sin filtro         · mr_lat  -> contra tendencia: solo bloqueados si la tendencia va en contra (0 = permitido)
#  dia_libre -> operadores diarios sin filtro                · dia_lat -> operadores diarios: solo bloqueados si va en contra
# Uso: GATE=mr_lat OUTM=mat_mr_lat.pkl python m2tipo.py ; luego MAT=mat_mr_lat.pkl COSTE=0.0008 ENS=post OUT=teams_mr_lat.pkl python m2cost.py
import os, sys, pickle, json, datetime as dt
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "lab", "src"))
import numpy as np
import data as datamod
M = pickle.load(open(os.path.join(S, "mat_raw.pkl"), "rb"))
days = M["days"]; pos = {d: k for k, d in enumerate(days)}
GATE = os.environ.get("GATE", "base")
AG = {a["id"]: a for a in json.load(open(os.path.join(S, "lab", "state", "agents.json")))["agents"]}
MR_C = {"z_bajo", "rsi_bajo", "rebote_soporte", "doble_suelo", "triple_suelo", "mercado_lateral", "bajo_media", "rebota_poc"}
MR_F = {"rsi", "boll", "connors"}
def tipo(a):
    if a.get("eleccion") == "diario": return "dia"
    if a.get("eleccion") == "propia":
        return "mr" if any(c[0] in MR_C for c in (a.get("regla") or {}).get("entry", [])) else "tend"
    return "mr" if (a.get("genome") or {}).get("family") in MR_F else "tend"
TIPO = [tipo(AG[i["id"]]) for i in M["info"]]
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
P = M["P"].copy(); nb = 0; libres = 0
for j, inf in enumerate(M["info"]):
    sd = M["sides"].get(inf["id"])
    if not sd: continue
    ty = TIPO[j]
    for d, s, e in zip(*sd):
        tv = TR[inf["activo"]].get(d)
        blk = tv is not None and tv * s <= 0
        if GATE == f"{ty}_libre": blk2 = False
        elif GATE == f"{ty}_lat": blk2 = tv is not None and tv * s < 0
        else: blk2 = blk
        libres += blk and not blk2
        k = pos.get(d)
        if blk2 and k is not None and P[j, k] > 0:
            P[j, k] = -1.0; nb += 1
import collections
print(GATE, "tipos", collections.Counter(TIPO), "bloqueados", nb, "liberados", libres, flush=True)
M2 = dict(M); M2["P"] = P
pickle.dump(M2, open(os.path.join(S, os.environ.get("OUTM", f"mat_{GATE}.pkl")), "wb"))
