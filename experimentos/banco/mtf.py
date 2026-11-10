# Banco (10/11/2026): cantera de los equipos según temporalidad. Uso: TFS=1d,4h OUTM=mat_X.pkl python mtf.py
import os, json, pickle, collections
S = os.path.dirname(os.path.abspath(__file__))
M = pickle.load(open(os.path.join(S, "mat.pkl"), "rb"))
st = json.load(open(os.path.join(S, "lab", "state", "agents.json")))
tf = {a["id"]: a.get("tf", "1d") for a in st["agents"]}
for i in M["info"]: i["tf"] = tf.get(i["id"], "?")
print(collections.Counter((i["tf"], i["short"]) for i in M["info"]))
TFS = os.environ["TFS"].split(",")
idx = [k for k, i in enumerate(M["info"]) if i["tf"] in TFS]
out = dict(days=M["days"], info=[M["info"][k] for k in idx], **{x: M[x][idx] for x in "REPGL"})
pickle.dump(out, open(os.path.join(S, os.environ["OUTM"]), "wb")); print(len(idx))
