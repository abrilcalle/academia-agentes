# Banco (25/11/2026): amplitud del mercado en el filtro de tendencia. Tras m1_18.py (mat.pkl, 2018-2023).
set -e
for g in base amp2 maj todos; do AMP=$g python3 m2amp.py > amp_$g.log 2>&1; done
export YRS=2018,2019,2020,2021,2022,2023
for g in base amp2; do MAT=mat_$g.pkl COSTE=0.0008 ENS=post OUT=teams_$g.pkl python3 m2cost.py > m2_$g.log 2>&1 & done
wait
for g in maj todos; do MAT=mat_$g.pkl COSTE=0.0008 ENS=post OUT=teams_$g.pkl python3 m2cost.py > m2_$g.log 2>&1 & done
wait
python3 m3x.py base amp2 maj todos; CS=2018,2022,2023 python3 m3c22.py base amp2 maj todos; python3 pares_ab.py base amp2 maj todos
YRS=2019,2020,2021,2022,2023 python3 m3x.py base amp2 maj todos
