# Banco (23/11/2026 21:00): "edad de la operación" (más parte a las operaciones jóvenes o a las viejas). Tras m1_18.py (mat.pkl, 2018-2023).
export YRS=2018,2019,2020,2021,2022,2023 COSTE=0.0008 ENS=post MAT=mat.pkl
run() { EDAD=$1 EDAD_A=$2 OUT=teams_$3.pkl python3 m2costd.py > m2_$3.log 2>&1; }
run 0 5 base & run joven 5 j5 & wait
run vieja 5 v5 & run joven 15 j15 & wait
run vieja 15 v15 & wait
python3 m3x.py base j5 v5 j15 v15; CS=2018,2022,2023 python3 m3c22.py base j5 v5 j15 v15; python3 pares_ab.py base j5 v5 j15 v15
YRS=2019,2020,2021,2022,2023 python3 m3x.py base j5 v5 j15 v15
