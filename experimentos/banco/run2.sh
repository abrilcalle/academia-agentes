for g in "$@"; do MAT=mat_$g.pkl COSTE=0.0008 ENS=post OUT=teams_$g.pkl python3 m2cost.py > m2_$g.log 2>&1; done
