# Banco (27/11/2026): la mitad vendida al "asegurar" espera en USDC (cambio USDC/EUR) en vez de quedarse quieta en euros.
# En la copia lab/src/equipos.py, dentro de series(): fxa = fx_returns(ac, days) si ASEG_FX=1 (si no, ceros) y
#   ret[n_] = ASEGURAR_QUEDA * ret[n_] + (1 - ASEGURAR_QUEDA) * fxa[n_] - (coste de la venta)
OUTM=mat.pkl python3 m1_18.py > m1_base.log 2>&1 &
ASEG_FX=1 OUTM=mat_fx.pkl python3 m1_18.py > m1_fx.log 2>&1 &
wait
export YRS=2018,2019,2020,2021,2022,2023 COSTE=0.0008 ENS=post LOO=base
MAT=mat.pkl OUT=teams_base.pkl python3 m2loo.py > m2_base.log 2>&1 &
MAT=mat_fx.pkl OUT=teams_fx.pkl python3 m2loo.py > m2_fx.log 2>&1 &
wait
python3 m3x.py base fx; CS=2018,2022,2023 python3 m3c22.py base fx
YRS=2019,2020,2021,2022,2023 python3 m3x.py base fx
