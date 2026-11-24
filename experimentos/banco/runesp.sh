# Banco (24/11/2026 10:00): inventor con espejo. 3 brazos × (1d 60, 4h 30, 1h 10) agentes clásicos, mismas semillas.
arm() { for tf in 1d:60:11 4h:30:12 1h:10:13; do IFS=: read t n s <<< "$tf"; TF=$t N=$n SEED=$s ESP=$1 OUT=esp_$1_$t.pkl python3 espejo.py > esp_$1_$t.log 2>&1; done; }
arm 0 & arm 0.5 & wait
arm 0.25
echo FIN > esp_fin.txt
