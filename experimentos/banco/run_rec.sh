# Banco (28/11/2026 15:00): inventor con más peso a lo reciente. Mismas semillas por brazo (como run_gen.sh).
arm() { for tf in 1d:120:11 4h:60:12 1h:20:13; do IFS=: read t n s <<< "$tf"; TF=$t N=$n SEED=$s REC=$2 OUT=r_$1_$t.pkl python3 rec_inv.py > r_$1_$t.log 2>&1; done; }
(arm base 0; arm exp exp) &
(arm lin lin) &
wait
echo FIN > fin.txt
