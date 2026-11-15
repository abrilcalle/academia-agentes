# Análisis de dgate.py EVOL=1 (MODE=base y MODE=gate, N=6): comparación por pares, misma semilla.
import pickle, numpy as np, json
crit = json.load(open("lab/config.json"))["operadores_diarios"]["aprobar_validacion"]
def pasa(x, d=True): return (x["ret"]*100>=crit["ganancia_minima_pct"] and (not d or x["dias"]>=crit["dias_operando_por_semana"]) and x["sem_pos"]*100>=crit["semanas_en_positivo_pct"] and x["dd"]*100<=crit["caida_maxima_pct"] and x["avg"]*100>=crit["ganancia_media_por_operacion_pct"])
A = {m: pickle.load(open(f"dgate_evol_{m}.pkl","rb")) for m in ("base","gate")}
for m, rows in A.items():
    print(m, len(rows))
    for per in ("tr", 2022, 2023, "va"):
        X = [r[per] for r in rows]
        print(f"  {per}: ret {np.median([x['ret'] for x in X])*100:+.1f}% sem+ {np.mean([x['sem_pos'] for x in X])*100:.1f}% sem- {np.mean([x['sem_neg'] for x in X])*100:.1f}% dias {np.median([x['dias'] for x in X]):.2f} dd {np.median([x['dd'] for x in X])*100:.0f}% gana {np.mean([x['ret']>0 for x in X])*100:.0f}% avg {np.median([x['avg'] for x in X])*100:.2f}%")
    print("  pasa_val", sum(pasa(r["va"]) for r in rows), "sin_dias", sum(pasa(r["va"], False) for r in rows))
    for g in sorted({(r["activo"], r["tf"]) for r in rows}):
        R = [r for r in rows if (r["activo"], r["tf"]) == g]
        print("   ", g, " ".join(f"{y}:{np.median([r[y]['ret'] for r in R])*100:+.0f}%/{np.mean([r[y]['sem_pos'] for r in R])*100:.0f}%" for y in (2022, 2023)))
b, g = A["base"], A["gate"]
for y in (2022, 2023):
    d = [gg[y]["sem_pos"] - bb[y]["sem_pos"] for bb, gg in zip(b, g)]
    dr = [gg[y]["ret"] - bb[y]["ret"] for bb, gg in zip(b, g)]
    print(y, "pares: sem+ mejora", sum(x > 0 for x in d), "empeora", sum(x < 0 for x in d), "media", round(np.mean(d)*100, 1), "| ret mejora", sum(x > 0 for x in dr), "de", len(d))
