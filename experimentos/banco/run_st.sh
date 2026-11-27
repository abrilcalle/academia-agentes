arm() { for tf in 1d:120:11 4h:60:12 1h:20:13; do IFS=: read t n s <<< "$tf"; LAB=$1 TF=$t N=$n SEED=$s ESP=0 OUT=r_$1_$t.pkl python3 st_inv.py > r_$1_$t.log 2>&1; done; }
arm lab & arm lab_st & wait
echo FIN > fin.txt
