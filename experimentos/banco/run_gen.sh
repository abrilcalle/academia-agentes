# Banco (27/11/2026 15:00): intensidad del inventor. Mismas semillas por brazo; POP × GENS distintos.
arm() { for tf in 1d:120:11 4h:60:12 1h:20:13; do IFS=: read t n s <<< "$tf"; TF=$t N=$n SEED=$s POP=$2 GENS=$3 OUT=r_$1_$t.pkl python3 gen_inv.py > r_$1_$t.log 2>&1; done; }
(arm g30 30 30; arm g5 30 5) &
(arm g15 30 15; arm p60 60 15) &
wait
echo FIN > fin.txt
