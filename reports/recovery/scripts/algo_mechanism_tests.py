"""Mechanism probes for relic_v2 (read-only; synthetic JCL). Run: PYTHONPATH=src:. python this.py"""
import sys; sys.path.insert(0,'.')
from relic_eval.detectors import RelicDetector
d=RelicDetector(False,True)
def hdr(body): return "//J JOB (A),'X',CLASS=A\n"+body
BASE=hdr("""//S1 EXEC PGM=GEN
//OUT DD DSN=A.B,DISP=(NEW,CATLG,DELETE)
//OUT2 DD DSN=A.C,DISP=(NEW,CATLG,DELETE)
//S2 EXEC PGM=USE,COND=(4,LT,S1)
//IN DD DSN=A.B,DISP=SHR
//IN2 DD DSN=A.C,DISP=SHR
""")
def t(name,mut,expect_change=True):
    p=d.predict(BASE,mut,'x.jcl'); print(f"{name:55s} flagged={p.flagged} (real change={expect_change})")
t("T1 DISP NEW,CATLG,DELETE -> NEW,KEEP,DELETE",BASE.replace("A.B,DISP=(NEW,CATLG,DELETE)","A.B,DISP=(NEW,KEEP,DELETE)"))
t("T2 SHR -> OLD on consumer",BASE.replace("A.B,DISP=SHR","A.B,DISP=OLD"))
t("T3 add 2nd COND keyword (COND=(0,LE))",BASE.replace("COND=(4,LT,S1)","COND=(4,LT,S1),COND=(0,LE)"))
t("T4 tighten COND (4,LT)->(0,NE)",BASE.replace("COND=(4,LT,S1)","COND=(0,NE,S1)"))
t("T5 weaken COND (4,LT)->(8,LT)",BASE.replace("COND=(4,LT,S1)","COND=(8,LT,S1)"))
t("T6 consumer reads A.X instead of A.B (one of two links)",BASE.replace("//IN DD DSN=A.B","//IN DD DSN=A.X"))
t("T7 rename producer dataset A.B->A.Z (consumer unchanged)",BASE.replace("//OUT DD DSN=A.B","//OUT DD DSN=A.Z"))
t("T8 swap program GEN->IEFBR14",BASE.replace("PGM=GEN","PGM=IEFBR14"))
t("T9 append unrelated step at end",BASE+"//EXTRA EXEC PGM=IEFBR14\n")
t("T10 rename step S2->S2X (benign refactor)",BASE.replace("//S2 EXEC","//S2X EXEC"),False)
t("T11 DSN->DSNAME synonym (benign)",BASE.replace("DSN=A.B,DISP=SHR","DSNAME=A.B,DISP=SHR"),False)
t("T12 in-stream SYSIN content change",BASE+"//SYSIN DD *\n SORT FIELDS=(1,2,CH,A)\n/*\n".replace("A)","A)"),True)
m=BASE.replace("//S2 EXEC","//S2 EXEC",1)
t("T13 IF/THEN condition widened",hdr("//S1 EXEC PGM=A\n//IF1 IF (S1.RC = 0) THEN\n//S2 EXEC PGM=B\n//ENDIF ENDIF\n").replace("= 0","<= 4"),True) if False else None
a=hdr("//S1 EXEC PGM=A\n//IF1 IF (S1.RC = 0) THEN\n//S2 EXEC PGM=B\n//ENDIF ENDIF\n"); b=a.replace("= 0","<= 4")
print(f"{'T13 IF (RC=0) -> (RC<=4)':55s} flagged={d.predict(a,b,'x.jcl').flagged} (real change=True)")
a=hdr("//S1 EXEC PGM=A\n//S2 EXEC PGM=B\n"); b=a+"//SYSIN DD *\n X\n/*\n"
a2=a+"//SYSIN DD *\n SORT FIELDS=(1,2,CH,A)\n/*\n"; b2=a2.replace(",A)",",D)")
print(f"{'T12b in-stream utility control stmt A->D':55s} flagged={d.predict(a2,b2,'x.jcl').flagged} (real change=True)")
