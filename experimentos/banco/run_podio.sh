# Banco (26/11/2026): podio estable. Tras m1_18.py (mat.pkl, 2018-2023).
export YRS=2018,2019,2020,2021,2022,2023 COSTE=0.0008 ENS=post
LOO=base OUT=teams_base.pkl python3 m2loo.py > m2_base.log 2>&1
for W in 8 14 27; do W0=$W python3 podio_estable.py teams_base.pkl; done
SW=0 python3 podio_estable.py teams_base.pkl
python3 pe_par.py
