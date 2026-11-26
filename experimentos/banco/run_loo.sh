# Banco (26/11/2026): formación robusta a perder un miembro. Tras m1_18.py (mat.pkl, 2018-2023).
export YRS=2018,2019,2020,2021,2022,2023 COSTE=0.0008 ENS=post
LOO=base OUT=teams_base.pkl python3 m2loo.py > m2_base.log 2>&1 &
LOO=min OUT=teams_min.pkl python3 m2loo.py > m2_min.log 2>&1 &
wait
LOO=mean OUT=teams_mean.pkl python3 m2loo.py > m2_mean.log 2>&1
python3 m3x.py base min mean; CS=2018,2022,2023 python3 m3c22.py base min mean; python3 pares_ab.py base min mean
YRS=2019,2020,2021,2022,2023 python3 m3x.py base min mean
