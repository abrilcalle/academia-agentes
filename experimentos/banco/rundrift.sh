# Banco (22/11/2026 21:00): "dejar correr" (deriva) frente a volver cada día a la parte objetivo. Tras m1_18.py (mat.pkl, 2018-2023).
export YRS=2018,2019,2020,2021,2022,2023 COSTE=0.0008 ENS=post MAT=mat.pkl
run() { DRIFT=$1 BAND=$2 OUT=teams_$3.pkl python3 m2drift.py > m2_$3.log 2>&1; }
run base 0 base & run costo 0 costo & wait
run banda 0.05 b05 & run banda 0.10 b10 & wait
run ev 0 ev & wait
python3 m3x.py base costo b05 b10 ev; CS=2018,2022,2023 python3 m3c22.py base costo b05 b10 ev; python3 pares_ab.py base costo b05 b10 ev
YRS=2019,2020,2021,2022,2023 python3 m3x.py base costo b05 b10 ev
