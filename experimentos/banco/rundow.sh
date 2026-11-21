MAT=mat.pkl COSTE=0.0008 ENS=post DOW= OUT=teams_base.pkl python3 m2dow_c.py > m2_base.log 2>&1 &
MAT=mat.pkl COSTE=0.0008 ENS=post DOW=5,6 OUT=teams_finde.pkl python3 m2dow_c.py > m2_finde.log 2>&1 &
MAT=mat.pkl COSTE=0.0008 ENS=post DOW=4,5,6 OUT=teams_vsd.pkl python3 m2dow_c.py > m2_vsd.log 2>&1 &
MAT=mat.pkl COSTE=0.0008 ENS=post DOW=3,4,5,6 OUT=teams_lmx.pkl python3 m2dow_c.py > m2_lmx.log 2>&1 &
MAT=mat.pkl COSTE=0.0008 ENS=post DOW=0,1 OUT=teams_nolm.pkl python3 m2dow_c.py > m2_nolm.log 2>&1 &
MAT=mat.pkl COSTE=0.0008 ENS=post DOW=0 OUT=teams_nol.pkl python3 m2dow_c.py > m2_nol.log 2>&1 &
MAT=mat.pkl COSTE=0.0008 ENS=post DOW=1 OUT=teams_nom.pkl python3 m2dow_c.py > m2_nom.log 2>&1 &
MAT=mat.pkl COSTE=0.0008 ENS=post DOW=0,1,2 OUT=teams_nolmx.pkl python3 m2dow_c.py > m2_nolmx.log 2>&1 &
MAT=mat.pkl COSTE=0.0008 ENS=post DOW=2,3 OUT=teams_noxj.pkl python3 m2dow_c.py > m2_noxj.log 2>&1 &
wait
