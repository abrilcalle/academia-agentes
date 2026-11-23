# Banco (23/11/2026 15:00): "la parte del equipo es exposición" (capital = parte / exposición propia del agente). Tras m1_18e.py (mat.pkl con ERAW).
export YRS=2018,2019,2020,2021,2022,2023 COSTE=0.0008 ENS=post MAT=mat.pkl
run() { EXPO=$1 POT=$2 MAXR=$3 OUT=teams_$4.pkl python3 m2costx.py > m2_$4.log 2>&1; }
run 0 1 1e9 base & run full 1 1e9 full & wait
run full 0.5 1e9 half & run full 1 2 x2 & wait
python3 m3x.py base full half x2; CS=2018,2022,2023 python3 m3c22.py base full half x2; python3 pares_ab.py base full half x2
YRS=2019,2020,2021,2022,2023 python3 m3x.py base full half x2
