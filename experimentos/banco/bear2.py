import pickle, numpy as np, sys
for f in ["bear_1d.pkl", "bear_4h.pkl"]:
    o = pickle.load(open(f, "rb"))
    groups = sorted(set(k[:2] for k in o))
    print("=====", f)
    for g in groups:
        fl = o[g + ("_flat",)]["raw"]
        print(g, "flat USDC:", " ".join(f"{y}:{fl[y][0]*100:+.0f}" for y in fl))
    for var in ["raw", "g1", "g2"]:
        rows = []
        for k, v in o.items():
            if k[2] == "_flat": continue
            fl = o[k[:2] + ("_flat",)]["raw"]; r = v[var]
            ex = {y: r[y][0] - fl[y][0] for y in r}
            rows.append((k, ex, r))
        E = np.array([[x[1][y] for y in range(2018, 2024)] for x in rows])
        print(f"\n-- {var}: {len(rows)} reglas. Exceso medio sobre USDC por año 2018..2023:", " ".join(f"{m*100:+.1f}" for m in np.median(E, 0)),
              "| % que ganan a USDC:", " ".join(f"{(E[:,i]>0).mean()*100:.0f}" for i in range(6)))
        # selección con entreno: exceso 2018 > 0 y suma 2019-21 > -0.10, y por puntuación
        sel = [i for i in range(len(rows)) if E[i,0] > 0.0 and E[i,1:4].sum() > -0.10]
        if sel:
            S_ = E[sel]
            print(f"   elegidas con entreno (2018>0, 2019-21 >-10%): {len(sel)} -> 2022 mediana {np.median(S_[:,4])*100:+.1f} (ganan a USDC {np.mean(S_[:,4]>0)*100:.0f} %), 2023 {np.median(S_[:,5])*100:+.1f}")
            no = [i for i in range(len(rows)) if i not in sel]
            print(f"   resto: {len(no)} -> 2022 {np.median(E[no,4])*100:+.1f} ({np.mean(E[no,4]>0)*100:.0f} %), 2023 {np.median(E[no,5])*100:+.1f}")
        sc = E[:,0] + E[:,1:4].sum(1)
        from scipy.stats import spearmanr
        print("   Spearman(entreno 2018-21, 2022):", round(spearmanr(sc, E[:,4])[0], 2), " (2018, 2022):", round(spearmanr(E[:,0], E[:,4])[0], 2))
        top = np.argsort(-sc)[:10]
        for i in top:
            k, ex, r = rows[i]
            print("    ", k[0][:3], k[1], k[2][:45].ljust(45), " ".join(f"{ex[y]*100:+4.0f}" for y in range(2018, 2024)), f"dd22 {r[2022][1]*100:.0f}%")
