# Banco (22/11/2026): "salida" del filtro de tendencia en el banco de 6 años. Tras m1raw18.py (con OUTM=mat_raw.pkl).
set -e
for g in base salida salida2; do GATE=$g python3 m2gate.py > gate_$g.log 2>&1; done
export YRS=2018,2019,2020,2021,2022,2023
for g in base salida salida2; do MAT=mat_$g.pkl COSTE=0.0008 ENS=post OUT=teams_$g.pkl python3 m2cost.py > m2_$g.log 2>&1 & done
wait
echo done
python3 m3x.py base salida salida2; CS=2018,2022,2023 python3 m3c22.py base salida salida2; python3 pares_ab.py base salida salida2
YRS=2019,2020,2021,2022,2023 python3 m3x.py base salida salida2
