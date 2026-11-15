# Análisis de dgate.py (paso 1: reglas ya inventadas, con y sin puerta). Uso: python dgate_ana.py dgate_post.pkl
import pickle, numpy as np, json, sys
rows = pickle.load(open(sys.argv[1], "rb"))
crit = json.load(open("lab/config.json"))["operadores_diarios"]["aprobar_validacion"]
def pasa(x): return (x["ret"]*100>=crit["ganancia_minima_pct"] and x["dias"]>=crit["dias_operando_por_semana"] and x["sem_pos"]*100>=crit["semanas_en_positivo_pct"] and x["dd"]*100<=crit["caida_maxima_pct"] and x["avg"]*100>=crit["ganancia_media_por_operacion_pct"])
modes = [k for k in rows[0] if isinstance(rows[0][k], dict) and "tr" in rows[0][k]] or [None]
print(len(rows), "agentes")
for mo in modes:
    g = (lambda r: r[mo]) if mo else (lambda r: r)
    out = [mo or "-"]
    for per in ("tr", 2022, 2023, "va"):
        X = [g(r)[per] for r in rows]
        out.append(f"{per}: ret {np.median([x['ret'] for x in X])*100:+.1f}% sem+ {np.mean([x['sem_pos'] for x in X])*100:.1f}% sem- {np.mean([x['sem_neg'] for x in X])*100:.1f}% dias {np.median([x['dias'] for x in X]):.2f} gana {np.mean([x['ret']>0 for x in X])*100:.0f}%")
    out.append(f"pasa_val {sum(pasa(g(r)['va']) for r in rows)}  pasa_val_sin_dias {sum(pasa(dict(g(r)['va'], dias=9)) for r in rows)}")
    print("\n  ".join(out))
