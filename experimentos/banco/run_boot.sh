# Banco (28/11/2026): formación con remuestreo de semanas del año de formación (BOOT=base|mean|q25; SEED cambia las semanas sacadas).
# m2boot2.py = m2boot.py con la semilla 1000 cambiada por SEED (sed 's/1000 + A/int(os.environ.get("SEED","1000")) + A/').
OUTM=mat.pkl python3 m1_18.py > m1.log 2>&1
export YRS=2018,2019,2020,2021,2022,2023
BOOT=base OUT=teams_base.pkl python3 m2boot.py > m2_base.log 2>&1 &
BOOT=mean OUT=teams_mean.pkl python3 m2boot.py > m2_mean.log 2>&1 &
wait
BOOT=q25 OUT=teams_q25.pkl python3 m2boot.py > m2_q25.log 2>&1 &
SEED=5000 BOOT=mean OUT=teams_mean2.pkl python3 m2boot2.py > m2_mean2.log 2>&1 &
wait
python3 m3x.py base mean q25 mean2; CS=2018,2022,2023 python3 m3c22.py base mean q25 mean2
YRS=2019,2020,2021,2022,2023 python3 m3x.py base mean q25 mean2
