#!/usr/bin/env python3
"""
JCL-SemBench Benchmark Generator and Oracle Validator.

Constructs 180 matched (original, transformed) JCL pairs across 12 distinct categories
(6 behaviour-preserving, 6 behaviour-changing).
Every pair is deterministically generated, accompanied by an explicit equivalence argument
or behavioural-change rationale citing the IBM z/OS MVS JCL Reference, and validated
using jcl_oracle.judge.compare_versions.

Outputs:
  - benchmarks/sembench/cases.jsonl
  - benchmarks/sembench/cases/<id>/original.jcl
  - benchmarks/sembench/cases/<id>/transformed.jcl
  - benchmarks/sembench/MANIFEST.sha256
  - benchmarks/sembench/oracle_validation.json
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "src"))

from jcl_oracle.judge import compare_versions
from relic_eval.subjects import get_subjects

SEMBENCH_DIR = ROOT_DIR / "benchmarks" / "sembench"
CASES_DIR = SEMBENCH_DIR / "cases"

# ---------------------------------------------------------------------------
# Base JCL Library (12 Diverse Handwritten Bases)
# ---------------------------------------------------------------------------

HANDWRITTEN_BASES: dict[str, str] = {
    "base_hw_01_etl": """//ETLJOB01 JOB (ACCT101,'FINANCE'),'NIGHTLY ETL',
//         CLASS=A,MSGCLASS=X,NOTIFY=&SYSUID
//* Clean up previous target dataset
//STEP10   EXEC PGM=IEFBR14
//OLDDEL   DD DSN=FIN.PROD.DAILY.TRANS,
//            DISP=(MOD,DELETE,DELETE),
//            UNIT=SYSDA,SPACE=(TRK,0)
//* Sort raw incoming transactions
//STEP20   EXEC PGM=SORT
//SORTIN   DD DSN=FIN.RAW.DAILY.TRANS,DISP=SHR
//SORTOUT  DD DSN=FIN.PROD.DAILY.TRANS,
//            DISP=(NEW,CATLG,DELETE),
//            UNIT=SYSDA,SPACE=(CYL,(10,5),RLSE),
//            DCB=(RECFM=FB,LRECL=120,BLKSIZE=27960)
//SYSOUT   DD SYSOUT=*
//SYSIN    DD *
  SORT FIELDS=(1,16,CH,A,17,8,PD,D)
  RECORD TYPE=F,LENGTH=120
/*
//* Backup newly created dataset
//STEP30   EXEC PGM=IDCAMS,COND=(0,NE,STEP20)
//SYSPRINT DD SYSOUT=*
//SYSIN    DD *
  REPRO -
    INDATASET(FIN.PROD.DAILY.TRANS) -
    OUTDATASET(FIN.BKUP.DAILY.TRANS)
/*
""",

    "base_hw_02_cond_chain": """//COND002  JOB (ACCT202,'BATCH'),'COND PIPELINE',
//         CLASS=B,MSGCLASS=A,NOTIFY=&SYSUID
//STEP1    EXEC PGM=SORT
//SORTIN   DD DSN=ACCT.DATA.INPUT,DISP=SHR
//SORTOUT  DD DSN=ACCT.DATA.SORTED,DISP=(NEW,CATLG,DELETE),
//            UNIT=SYSDA,SPACE=(CYL,(5,2))
//SYSOUT   DD SYSOUT=*
//SYSIN    DD *
  SORT FIELDS=(1,10,CH,A)
/*
//STEP2    EXEC PGM=IEBGENER,COND=(4,LT,STEP1)
//SYSUT1   DD DSN=ACCT.DATA.SORTED,DISP=SHR
//SYSUT2   DD DSN=ACCT.DATA.ARCHIVE,DISP=(NEW,CATLG,DELETE),
//            UNIT=SYSDA,SPACE=(CYL,(5,2))
//SYSPRINT DD SYSOUT=*
//SYSIN    DD DUMMY
//STEP3    EXEC PGM=IDCAMS,COND=(8,LE)
//SYSPRINT DD SYSOUT=*
//SYSIN    DD *
  PRINT INDATASET(ACCT.DATA.ARCHIVE) COUNT(100)
/*
//STEP4    EXEC PGM=IEFBR14,COND=EVEN
//CLEANUP  DD DSN=ACCT.DATA.SORTED,DISP=(MOD,DELETE,DELETE),
//            UNIT=SYSDA,SPACE=(TRK,0)
""",

    "base_hw_03_compile_link": """//CMPLNK03 JOB (ACCT303,'DEV'),'BUILD COBOL',
//         CLASS=A,MSGCLASS=X,NOTIFY=&SYSUID
//COMPILE  EXEC PGM=IGYCRCTL,PARM='NODECK,OBJECT,LIST'
//SYSIN    DD DSN=DEV.COBOL.SRC(BILLING),DISP=SHR
//SYSLIN   DD DSN=&&OBJSET,DISP=(NEW,PASS),
//            UNIT=SYSDA,SPACE=(CYL,(1,1))
//SYSPRINT DD SYSOUT=*
//SYSMDECK DD DSN=&&MDECK,DISP=(NEW,PASS),UNIT=SYSDA,SPACE=(TRK,(1,1))
//SYSUT1   DD UNIT=SYSDA,SPACE=(CYL,(1,1))
//SYSUT2   DD UNIT=SYSDA,SPACE=(CYL,(1,1))
//SYSUT3   DD UNIT=SYSDA,SPACE=(CYL,(1,1))
//SYSUT4   DD UNIT=SYSDA,SPACE=(CYL,(1,1))
//SYSUT5   DD UNIT=SYSDA,SPACE=(CYL,(1,1))
//SYSUT6   DD UNIT=SYSDA,SPACE=(CYL,(1,1))
//SYSUT7   DD UNIT=SYSDA,SPACE=(CYL,(1,1))
//BIND     EXEC PGM=IEWL,COND=(4,LT,COMPILE),
//         PARM='LIST,MAP,XREF,LET'
//SYSLIN   DD DSN=&&OBJSET,DISP=(OLD,DELETE)
//         DD DDNAME=SYSIN
//SYSLMOD  DD DSN=PROD.LOADLIB(BILLING),DISP=SHR
//SYSPRINT DD SYSOUT=*
//SYSUT1   DD UNIT=SYSDA,SPACE=(CYL,(1,1))
//SYSIN    DD *
  NAME BILLING(R)
/*
""",

    "base_hw_04_gdg_cycle": """//GDGCYC04 JOB (ACCT404,'STORAGE'),'GDG ROLLOVERS',
//         CLASS=A,MSGCLASS=H
//DEFGDG   EXEC PGM=IDCAMS
//SYSPRINT DD SYSOUT=*
//SYSIN    DD *
  DEFINE GDG (NAME(PROD.LOGS.MONTHLY) LIMIT(12) NOEMPTY SCRATCH)
/*
//MAKENEW  EXEC PGM=SORT,COND=(0,NE,DEFGDG)
//SORTIN   DD DSN=PROD.LOGS.DAILY,DISP=SHR
//SORTOUT  DD DSN=PROD.LOGS.MONTHLY(+1),
//            DISP=(NEW,CATLG,DELETE),
//            UNIT=SYSDA,SPACE=(CYL,(20,10))
//SYSOUT   DD SYSOUT=*
//SYSIN    DD *
  SORT FIELDS=COPY
/*
//READGEN  EXEC PGM=IEBGENER,COND=(4,LT,MAKENEW)
//SYSUT1   DD DSN=PROD.LOGS.MONTHLY(+1),DISP=SHR
//SYSUT2   DD DSN=PROD.LOGS.CURRENT.EXTRACT,
//            DISP=(NEW,CATLG,DELETE),
//            UNIT=SYSDA,SPACE=(CYL,(5,2))
//SYSPRINT DD SYSOUT=*
//SYSIN    DD DUMMY
""",

    "base_hw_05_multi_disp": """//MDISP005 JOB (ACCT505,'PROD'),'MULTI DISP TEST',
//         CLASS=C,MSGCLASS=Q
//ST1ALLOC EXEC PGM=IEFBR14
//NEWDS    DD DSN=STAGE.DATA.MASTER,
//            DISP=(NEW,CATLG,DELETE),
//            UNIT=SYSDA,SPACE=(CYL,(10,5))
//ST2POP   EXEC PGM=IEBGENER
//SYSUT1   DD DSN=STAGE.DATA.SOURCE,DISP=SHR
//SYSUT2   DD DSN=STAGE.DATA.MASTER,DISP=(OLD,KEEP,KEEP)
//SYSPRINT DD SYSOUT=*
//SYSIN    DD DUMMY
//ST3APPND EXEC PGM=IEBGENER,COND=(0,NE,ST2POP)
//SYSUT1   DD DSN=STAGE.DATA.EXTRA,DISP=SHR
//SYSUT2   DD DSN=STAGE.DATA.MASTER,DISP=(MOD,KEEP,KEEP)
//SYSPRINT DD SYSOUT=*
//SYSIN    DD DUMMY
//ST4ARCH  EXEC PGM=IEBGENER,COND=(0,NE,ST3APPND)
//SYSUT1   DD DSN=STAGE.DATA.MASTER,DISP=(OLD,DELETE,KEEP)
//SYSUT2   DD DSN=STAGE.DATA.VAULT,
//            DISP=(NEW,CATLG,DELETE),
//            UNIT=SYSDA,SPACE=(CYL,(15,5))
//SYSPRINT DD SYSOUT=*
//SYSIN    DD DUMMY
""",

    "base_hw_06_sort_merge": """//SRTMER06 JOB (ACCT606,'DATA'),'SORT AND MERGE',
//         CLASS=A,MSGCLASS=A
//SORTSTEP EXEC PGM=SORT
//SORTIN01 DD DSN=CORP.FEED.NORTH,DISP=SHR
//SORTIN02 DD DSN=CORP.FEED.SOUTH,DISP=SHR
//SORTIN03 DD DSN=CORP.FEED.WEST,DISP=SHR
//SORTOUT  DD DSN=CORP.FEED.COMBINED,
//            DISP=(NEW,CATLG,DELETE),
//            UNIT=SYSDA,SPACE=(CYL,(50,20))
//SORTWK01 DD UNIT=SYSDA,SPACE=(CYL,(10,5))
//SORTWK02 DD UNIT=SYSDA,SPACE=(CYL,(10,5))
//SORTWK03 DD UNIT=SYSDA,SPACE=(CYL,(10,5))
//SYSOUT   DD SYSOUT=*
//SYSIN    DD *
  MERGE FIELDS=(1,12,CH,A,20,4,BI,A)
/*
//COPYSTEP EXEC PGM=IEBGENER,COND=(0,NE,SORTSTEP)
//SYSUT1   DD DSN=CORP.FEED.COMBINED,DISP=SHR
//SYSUT2   DD DSN=CORP.FEED.BACKUP,
//            DISP=(NEW,CATLG,DELETE),
//            UNIT=SYSDA,SPACE=(CYL,(50,20))
//SYSPRINT DD SYSOUT=*
//SYSIN    DD DUMMY
""",

    "base_hw_07_idcams_catalog": """//CATMAN07 JOB (ACCT707,'ADMIN'),'IDCAMS CLUSTER OPS',
//         CLASS=S,MSGCLASS=X
//IDC1     EXEC PGM=IDCAMS
//SYSPRINT DD SYSOUT=*
//SYSIN    DD *
  DELETE CORP.VSAM.KSDS CLUSTER PURGE
  SET MAXCC = 0
  DEFINE CLUSTER (NAME(CORP.VSAM.KSDS) -
         INDEXED -
         KEYS(16 0) -
         RECORDSIZE(200 200) -
         CYLINDERS(20 5))
/*
//IDC2     EXEC PGM=IDCAMS,COND=(0,NE,IDC1)
//SYSPRINT DD SYSOUT=*
//SYSIN    DD *
  REPRO -
    INDATASET(CORP.FLAT.SEED) -
    OUTDATASET(CORP.VSAM.KSDS)
/*
//IDC3     EXEC PGM=IDCAMS,COND=(4,LT,IDC2)
//SYSPRINT DD SYSOUT=*
//SYSIN    DD *
  PRINT -
    INDATASET(CORP.VSAM.KSDS) -
    CHARACTER -
    COUNT(50)
/*
""",

    "base_hw_08_iebgener_copy": """//GENCPY08 JOB (ACCT808,'OPS'),'IEBGENER MULTICOPY',
//         CLASS=A,MSGCLASS=T
//COPY1    EXEC PGM=IEBGENER
//SYSUT1   DD DSN=WAREHOUSE.INVENTORY.RAW,DISP=SHR
//SYSUT2   DD DSN=WAREHOUSE.INVENTORY.TEMP,
//            DISP=(NEW,CATLG,DELETE),
//            UNIT=SYSDA,SPACE=(TRK,(50,20)),
//            DCB=(RECFM=FB,LRECL=80,BLKSIZE=800)
//SYSPRINT DD SYSOUT=*
//SYSIN    DD DUMMY
//COPY2    EXEC PGM=IEBGENER,COND=(0,NE,COPY1)
//SYSUT1   DD DSN=WAREHOUSE.INVENTORY.TEMP,DISP=SHR
//SYSUT2   DD DSN=WAREHOUSE.INVENTORY.FINAL,
//            DISP=(NEW,CATLG,DELETE),
//            UNIT=SYSDA,SPACE=(TRK,(50,20)),
//            DCB=(RECFM=FB,LRECL=80,BLKSIZE=800)
//SYSPRINT DD SYSOUT=*
//SYSIN    DD DUMMY
""",

    "base_hw_09_iebcopy_pds": """//PDSCOP09 JOB (ACCT909,'SYS'),'IEBCOPY COMPRESS AND CP',
//         CLASS=A,MSGCLASS=X
//CPYPDS   EXEC PGM=IEBCOPY
//INLIB    DD DSN=SYS3.TEST.PROCLIB,DISP=SHR
//OUTLIB   DD DSN=SYS3.PROD.PROCLIB,DISP=OLD
//SYSUT3   DD UNIT=SYSDA,SPACE=(CYL,(2,1))
//SYSUT4   DD UNIT=SYSDA,SPACE=(CYL,(2,1))
//SYSPRINT DD SYSOUT=*
//SYSIN    DD *
  COPY OUTDD=OUTLIB,INDD=INLIB
/*
//LISTPDS  EXEC PGM=IDCAMS,COND=(0,NE,CPYPDS)
//SYSPRINT DD SYSOUT=*
//SYSIN    DD *
  LISTCAT LEVEL(SYS3.PROD) ALL
/*
""",

    "base_hw_10_if_then_else": """//IFTHEN10 JOB (ACCT110,'LOGIC'),'IF THEN CONDITIONAL',
//         CLASS=A,MSGCLASS=A
//STP1     EXEC PGM=SORT
//SORTIN   DD DSN=LEDGER.BATCH.INPUT,DISP=SHR
//SORTOUT  DD DSN=LEDGER.BATCH.STAGED,
//            DISP=(NEW,CATLG,DELETE),
//            UNIT=SYSDA,SPACE=(CYL,(10,5))
//SYSOUT   DD SYSOUT=*
//SYSIN    DD *
  SORT FIELDS=(1,8,CH,A)
/*
//IF1      IF (STP1.RC = 0) THEN
//STP2A    EXEC PGM=IEBGENER
//SYSUT1   DD DSN=LEDGER.BATCH.STAGED,DISP=SHR
//SYSUT2   DD DSN=LEDGER.BATCH.POSTED,
//            DISP=(NEW,CATLG,DELETE),
//            UNIT=SYSDA,SPACE=(CYL,(10,5))
//SYSPRINT DD SYSOUT=*
//SYSIN    DD DUMMY
//ELSE     ELSE
//STP2B    EXEC PGM=IEFBR14
//ABORTDEL DD DSN=LEDGER.BATCH.STAGED,
//            DISP=(MOD,DELETE,DELETE),
//            UNIT=SYSDA,SPACE=(TRK,0)
//ENDIF    ENDIF
""",

    "base_hw_11_instream_sysin": """//INSTREAM JOB (ACCT111,'UTIL'),'IN-STREAM DATA',
//         CLASS=A,MSGCLASS=X
//DELSTEP  EXEC PGM=IEFBR14
//OLDREP   DD DSN=REPORT.SUMMARY.OUTPUT,
//            DISP=(MOD,DELETE,DELETE),
//            UNIT=SYSDA,SPACE=(TRK,0)
//GENREP   EXEC PGM=IEBGENER
//SYSUT1   DD *
=====================================================
MONTHLY AUDIT SUMMARY REPORT
PERIOD: 2025-01
STATUS: VERIFIED
=====================================================
/*
//SYSUT2   DD DSN=REPORT.SUMMARY.OUTPUT,
//            DISP=(NEW,CATLG,DELETE),
//            UNIT=SYSDA,SPACE=(TRK,(5,2)),
//            DCB=(RECFM=FB,LRECL=80,BLKSIZE=800)
//SYSPRINT DD SYSOUT=*
//SYSIN    DD DUMMY
""",

    "base_hw_12_parallel_prep": """//PARPRE12 JOB (ACCT112,'PREP'),'INDEPENDENT PREPARATION',
//         CLASS=M,MSGCLASS=Z
//PREPA    EXEC PGM=IEFBR14
//DDA1     DD DSN=WORK.RUNA.TEMP1,
//            DISP=(NEW,CATLG,DELETE),
//            UNIT=SYSDA,SPACE=(CYL,(5,1))
//DDA2     DD DSN=WORK.RUNA.TEMP2,
//            DISP=(NEW,CATLG,DELETE),
//            UNIT=SYSDA,SPACE=(CYL,(5,1))
//PREPB    EXEC PGM=IEFBR14
//DDB1     DD DSN=WORK.RUNB.TEMP1,
//            DISP=(NEW,CATLG,DELETE),
//            UNIT=SYSDA,SPACE=(CYL,(5,1))
//DDB2     DD DSN=WORK.RUNB.TEMP2,
//            DISP=(NEW,CATLG,DELETE),
//            UNIT=SYSDA,SPACE=(CYL,(5,1))
"""
}

# ---------------------------------------------------------------------------
# Case Specification Data Structure
# ---------------------------------------------------------------------------

@dataclass
class SemBenchCaseDef:
    id: str
    base_id: str
    source: str
    category: str
    subcategory: str
    expected_outcome: Literal["PRESERVING", "CHANGING"]
    relevant_jcl_semantics: str
    rationale: str
    equivalence_argument: str
    original_text: str
    transformed_text: str
    proclib_key: str | None = None
    override_confidence: str | None = None


def generate_all_cases() -> list[SemBenchCaseDef]:
    cases: list[SemBenchCaseDef] = []
    
    # Load corpus base texts
    corpus_texts: dict[str, tuple[str, str]] = {}
    subjects = {s.key: s for s in get_subjects()}
    
    for skey, sub in subjects.items():
        for p in sub.jcl_files:
            rel = sub.artifact_path(p)
            corpus_texts[f"corpus_{skey}_{p.stem.lower()}"] = (rel, p.read_text(errors="replace"))

    # =========================================================================
    # 1. PRESERVING: COMMENT EDITS (15 cases)
    # =========================================================================
    
    # sembench_001
    cases.append(SemBenchCaseDef(
        id="sembench_001",
        base_id="base_hw_01_etl",
        source="handwritten",
        category="comment_edit",
        subcategory="comment_header_addition",
        expected_outcome="PRESERVING",
        relevant_jcl_semantics="IBM z/OS MVS JCL Reference: Comment Statement (//*)",
        rationale="Adding full-line comments (//*) before and inside steps does not alter JCL job execution.",
        equivalence_argument="Lines starting with //* in columns 1-3 are comment statements and are ignored by the JES job converter and interpreter; step sequence and dataset dispositions are identical.",
        original_text=HANDWRITTEN_BASES["base_hw_01_etl"],
        transformed_text="""//*==================================================================*
//* NIGHTLY ETL BATCH JOB - PRODUCTION RUN
//* AUTHOR: DATA OPS TEAM
//*==================================================================*
""" + HANDWRITTEN_BASES["base_hw_01_etl"],
    ))

    # sembench_002
    cases.append(SemBenchCaseDef(
        id="sembench_002",
        base_id="base_hw_01_etl",
        source="handwritten",
        category="comment_edit",
        subcategory="comment_deletion",
        expected_outcome="PRESERVING",
        relevant_jcl_semantics="IBM z/OS MVS JCL Reference: Comment Statement (//*)",
        rationale="Deleting existing comment lines has zero effect on execution semantics.",
        equivalence_argument="Removing //* lines does not affect any EXEC, DD, or control statements processed by the interpreter.",
        original_text=HANDWRITTEN_BASES["base_hw_01_etl"],
        transformed_text="\n".join([line for line in HANDWRITTEN_BASES["base_hw_01_etl"].splitlines() if not line.startswith("//*")]) + "\n",
    ))

    # sembench_003
    cases.append(SemBenchCaseDef(
        id="sembench_003",
        base_id="base_hw_02_cond_chain",
        source="handwritten",
        category="comment_edit",
        subcategory="inline_step_comments",
        expected_outcome="PRESERVING",
        relevant_jcl_semantics="IBM z/OS MVS JCL Reference: Comment Statement (//*)",
        rationale="Inserting descriptive comments between chained COND steps.",
        equivalence_argument="Comments placed between step boundaries are ignored during execution; COND evaluation and step flow remain identical.",
        original_text=HANDWRITTEN_BASES["base_hw_02_cond_chain"],
        transformed_text=HANDWRITTEN_BASES["base_hw_02_cond_chain"].replace(
            "//STEP2    EXEC PGM=IEBGENER",
            "//* Check if STEP1 RC is strictly less than 4 before generating archive\n//STEP2    EXEC PGM=IEBGENER"
        ).replace(
            "//STEP4    EXEC PGM=IEFBR14",
            "//* Emergency cleanup runs even if previous steps abended\n//STEP4    EXEC PGM=IEFBR14"
        ),
    ))

    # sembench_004 to sembench_015: more comment edits
    bases_keys = list(HANDWRITTEN_BASES.keys())
    for i in range(12):
        case_num = 4 + i
        cid = f"sembench_{case_num:03d}"
        base_name = bases_keys[i % len(bases_keys)]
        orig = HANDWRITTEN_BASES[base_name]
        lines = orig.splitlines()
        lines.insert(2, f"//* AUDIT-LOG-TAG: REVISION-{case_num} TIMESTAMP-2025-01-01")
        lines.append("//* END OF JOB EXECUTION PIPELINE")
        mod = "\n".join(lines) + "\n"
        cases.append(SemBenchCaseDef(
            id=cid,
            base_id=base_name,
            source="handwritten",
            category="comment_edit",
            subcategory="banner_and_trailer_comments",
            expected_outcome="PRESERVING",
            relevant_jcl_semantics="IBM z/OS MVS JCL Reference: Comment Statement (//*)",
            rationale="Adding audit tags and trailing comments across distinct job types.",
            equivalence_argument="JCL comments have no operational effect on step execution, parameter binding, or dataset disposition.",
            original_text=orig,
            transformed_text=mod,
        ))

    # =========================================================================
    # 2. PRESERVING: WHITESPACE AND CONTINUATION REFLOW (16 cases)
    # =========================================================================
    
    # sembench_016
    cases.append(SemBenchCaseDef(
        id="sembench_016",
        base_id="base_hw_01_etl",
        source="handwritten",
        category="whitespace_and_continuation",
        subcategory="continuation_indentation",
        expected_outcome="PRESERVING",
        relevant_jcl_semantics="IBM z/OS MVS JCL Reference: Continuation Rules (Columns 4-16)",
        rationale="Changing continuation line indentation from column 12 to column 16.",
        equivalence_argument="According to IBM JCL syntax, continuation lines starting with // must have blanks in col 3 and continue operands anywhere in columns 4 through 16. Indentation change is semantically neutral.",
        original_text=HANDWRITTEN_BASES["base_hw_01_etl"],
        transformed_text=HANDWRITTEN_BASES["base_hw_01_etl"].replace(
            "//            DISP=(MOD,DELETE,DELETE),",
            "//                DISP=(MOD,DELETE,DELETE),"
        ).replace(
            "//            DISP=(NEW,CATLG,DELETE),",
            "//                DISP=(NEW,CATLG,DELETE),"
        ),
    ))

    # sembench_017: Splitting single-line DD onto continuation lines
    cases.append(SemBenchCaseDef(
        id="sembench_017",
        base_id="base_hw_02_cond_chain",
        source="handwritten",
        category="whitespace_and_continuation",
        subcategory="dd_split_continuation",
        expected_outcome="PRESERVING",
        relevant_jcl_semantics="IBM z/OS MVS JCL Reference: Statement Continuation",
        rationale="Splitting single-line DD statement parameters across multiple continuation lines with trailing commas.",
        equivalence_argument="A comma at the end of an operand signals continuation; parameters DSN and DISP are parsed identically whether on one line or split across continued lines.",
        original_text=HANDWRITTEN_BASES["base_hw_02_cond_chain"],
        transformed_text=HANDWRITTEN_BASES["base_hw_02_cond_chain"].replace(
            "//SORTIN   DD DSN=ACCT.DATA.INPUT,DISP=SHR",
            "//SORTIN   DD DSN=ACCT.DATA.INPUT,\n//            DISP=SHR"
        ),
    ))

    # sembench_018: Joining continuation lines into single line where length allows
    cases.append(SemBenchCaseDef(
        id="sembench_018",
        base_id="base_hw_04_gdg_cycle",
        source="handwritten",
        category="whitespace_and_continuation",
        subcategory="continuation_join",
        expected_outcome="PRESERVING",
        relevant_jcl_semantics="IBM z/OS MVS JCL Reference: Parameter Fields (cols 1-71)",
        rationale="Joining continuation lines into a single statement fitting within columns 1-71.",
        equivalence_argument="JCL statement operands concatenated with commas form the exact same parameter token list regardless of single-line vs continued-line formatting.",
        original_text=HANDWRITTEN_BASES["base_hw_04_gdg_cycle"],
        transformed_text=HANDWRITTEN_BASES["base_hw_04_gdg_cycle"].replace(
            "//SORTOUT  DD DSN=PROD.LOGS.MONTHLY(+1),\n//            DISP=(NEW,CATLG,DELETE),\n//            UNIT=SYSDA,SPACE=(CYL,(20,10))",
            "//SORTOUT  DD DSN=PROD.LOGS.MONTHLY(+1),DISP=(NEW,CATLG,DELETE),UNIT=SYSDA,SPACE=(CYL,(20,10))"
        ),
    ))

    # sembench_019 to sembench_031: Additional whitespace and continuation cases
    for i in range(13):
        case_num = 19 + i
        cid = f"sembench_{case_num:03d}"
        bkey = bases_keys[i % len(bases_keys)]
        orig = HANDWRITTEN_BASES[bkey]
        
        lines = []
        for line in orig.splitlines():
            if line.startswith("//STEP") or line.startswith("//ST") or line.startswith("//CP") or line.startswith("//IDC"):
                parts = line.split(maxsplit=2)
                if len(parts) >= 2 and parts[1] == "EXEC":
                    line = f"{parts[0]:<14} {parts[1]} {parts[2] if len(parts) > 2 else ''}".rstrip()
            elif line.startswith("//") and not line.startswith("//*") and " DD " in line:
                parts = line.split(" DD ", 1)
                line = f"{parts[0]:<12} DD {parts[1]}"
            lines.append(line)
        mod = "\n".join(lines) + "\n"
        
        cases.append(SemBenchCaseDef(
            id=cid,
            base_id=bkey,
            source="handwritten",
            category="whitespace_and_continuation",
            subcategory="column_reformatting_safe",
            expected_outcome="PRESERVING",
            relevant_jcl_semantics="IBM z/OS MVS JCL Reference: JCL Statement Fields and Delimiters",
            rationale="Reformatting whitespace columns between statement name, operation (EXEC/DD), and operand field.",
            equivalence_argument="JCL fields are delimited by one or more blanks (before column 72); variable whitespace padding between name, op, and operands produces identical tokens.",
            original_text=orig,
            transformed_text=mod,
        ))

    # =========================================================================
    # 3. PRESERVING: SYNTAX & EQUIVALENT PARAMETER REPRESENTATIONS (20 cases)
    # =========================================================================

    # sembench_032: DSN= vs DSNAME=
    cases.append(SemBenchCaseDef(
        id="sembench_032",
        base_id="base_hw_01_etl",
        source="handwritten",
        category="syntax_representation",
        subcategory="dsn_dsname_synonym",
        expected_outcome="PRESERVING",
        relevant_jcl_semantics="IBM z/OS MVS JCL Reference: DD Statement DSNAME Parameter",
        rationale="DSNAME is the full keyword name for DSN parameter.",
        equivalence_argument="IBM z/OS JCL defines DSN and DSNAME as exact synonyms. Replacing DSN with DSNAME preserves dataset identification and allocation.",
        original_text=HANDWRITTEN_BASES["base_hw_01_etl"],
        transformed_text=HANDWRITTEN_BASES["base_hw_01_etl"].replace("DSN=FIN.RAW.DAILY.TRANS", "DSNAME=FIN.RAW.DAILY.TRANS"),
    ))

    # sembench_033: DISP=SHR vs DISP=(SHR)
    cases.append(SemBenchCaseDef(
        id="sembench_033",
        base_id="base_hw_01_etl",
        source="handwritten",
        category="syntax_representation",
        subcategory="disp_single_subparam_parens",
        expected_outcome="PRESERVING",
        relevant_jcl_semantics="IBM z/OS MVS JCL Reference: DISP Parameter Syntax",
        rationale="Single positional subparameters in DISP can be enclosed in parentheses or unparenthesized.",
        equivalence_argument="DISP=SHR and DISP=(SHR) both specify status=SHR with default normal disposition KEEP and default abnormal disposition KEEP for an existing dataset.",
        original_text=HANDWRITTEN_BASES["base_hw_01_etl"],
        transformed_text=HANDWRITTEN_BASES["base_hw_01_etl"].replace("DISP=SHR", "DISP=(SHR)"),
    ))

    # sembench_034: Keyword order in DD statement
    cases.append(SemBenchCaseDef(
        id="sembench_034",
        base_id="base_hw_01_etl",
        source="handwritten",
        category="syntax_representation",
        subcategory="keyword_operand_order",
        expected_outcome="PRESERVING",
        relevant_jcl_semantics="IBM z/OS MVS JCL Reference: Keyword Parameter Syntax",
        rationale="Keyword parameters on DD statements are order-independent.",
        equivalence_argument="JCL keyword parameters (such as UNIT, SPACE, DISP, DCB) are evaluated as key-value pairs; their textual sequence within the DD operand field does not affect dataset allocation.",
        original_text=HANDWRITTEN_BASES["base_hw_01_etl"],
        transformed_text=HANDWRITTEN_BASES["base_hw_01_etl"].replace(
            "            UNIT=SYSDA,SPACE=(CYL,(10,5),RLSE),",
            "            SPACE=(CYL,(10,5),RLSE),UNIT=SYSDA,"
        ),
    ))

    # sembench_035: COND single test parentheses forms COND=((4,LT,STEP1)) vs COND=(4,LT,STEP1)
    cases.append(SemBenchCaseDef(
        id="sembench_035",
        base_id="base_hw_02_cond_chain",
        source="handwritten",
        category="syntax_representation",
        subcategory="cond_parentheses_nesting",
        expected_outcome="PRESERVING",
        relevant_jcl_semantics="IBM z/OS MVS JCL Reference: EXEC COND Parameter",
        rationale="Single COND tests can be enclosed with single or double parentheses.",
        equivalence_argument="COND=(4,LT,STEP1) and COND=((4,LT,STEP1)) represent the identical condition test list containing one 3-tuple (4, LT, STEP1).",
        original_text=HANDWRITTEN_BASES["base_hw_02_cond_chain"],
        transformed_text=HANDWRITTEN_BASES["base_hw_02_cond_chain"].replace("COND=(4,LT,STEP1)", "COND=((4,LT,STEP1))"),
    ))

    # sembench_036: PARM formatting
    cases.append(SemBenchCaseDef(
        id="sembench_036",
        base_id="base_hw_03_compile_link",
        source="handwritten",
        category="syntax_representation",
        subcategory="parm_quoting_and_parens",
        expected_outcome="PRESERVING",
        relevant_jcl_semantics="IBM z/OS MVS JCL Reference: EXEC PARM Parameter",
        rationale="PARM string formatting with quotes vs unquoted comma-separated list.",
        equivalence_argument="PARM values passed to IGYCRCTL resolve to the identical character parameter string 'NODECK,OBJECT,LIST'. NOTE: The simulator hashes PARM text directly into the dataflow version, leading to an oracle disagreement despite documented semantic equivalence.",
        original_text=HANDWRITTEN_BASES["base_hw_03_compile_link"],
        transformed_text=HANDWRITTEN_BASES["base_hw_03_compile_link"].replace("PARM='NODECK,OBJECT,LIST'", "PARM=(NODECK,OBJECT,LIST)"),
    ))

    # sembench_037 to sembench_051: More syntax representations
    for i in range(15):
        case_num = 37 + i
        cid = f"sembench_{case_num:03d}"
        bkey = bases_keys[(i + 2) % len(bases_keys)]
        orig = HANDWRITTEN_BASES[bkey]
        
        if "DISP=SHR" in orig and i % 3 == 0:
            mod = orig.replace("DISP=SHR", "DISP=(SHR,KEEP)", 1)
            cat_sub = "disp_explicit_keep_default"
            sem = "IBM z/OS MVS JCL Reference: DISP Parameter Defaults"
            rat = "Explicitly specifying KEEP normal disposition for SHR dataset matches IBM default."
            arg = "For existing datasets with status SHR, the default normal disposition is KEEP. Writing DISP=(SHR,KEEP) is semantically identical."
        elif "DSN=" in orig and i % 3 == 1:
            mod = orig.replace("DSN=", "DSNAME=", 1)
            cat_sub = "dsn_dsname_synonym"
            sem = "IBM z/OS MVS JCL Reference: DSNAME Synonym"
            rat = "Replacing DSN with DSNAME in dataset allocation."
            arg = "DSN is the documented short abbreviation for DSNAME; z/OS JCL interprets both identically."
        else:
            mod = orig.replace("DISP=(NEW,CATLG,DELETE),\n//            UNIT=SYSDA,SPACE=", "UNIT=SYSDA,DISP=(NEW,CATLG,DELETE),\n//            SPACE=")
            cat_sub = "dd_keyword_order"
            sem = "IBM z/OS MVS JCL Reference: Keyword Parameter Sequence"
            rat = "Swapping UNIT and DISP keyword order."
            arg = "Keyword parameters are associative and unordered; placing UNIT before DISP does not alter dataset disposition or allocation properties."
            if mod == orig:
                mod = orig.replace("DISP=SHR", "DISP=(SHR)")
                cat_sub = "disp_parens"
                sem = "IBM z/OS MVS JCL Reference: DISP Parameter Syntax"
                rat = "Parenthesizing SHR"
                arg = "DISP=(SHR) is identical to DISP=SHR."

        cases.append(SemBenchCaseDef(
            id=cid,
            base_id=bkey,
            source="handwritten",
            category="syntax_representation",
            subcategory=cat_sub,
            expected_outcome="PRESERVING",
            relevant_jcl_semantics=sem,
            rationale=rat,
            equivalence_argument=arg,
            original_text=orig,
            transformed_text=mod,
        ))

    # =========================================================================
    # 4. PRESERVING: JOB CARD REFACTORING (12 cases)
    # =========================================================================
    
    # sembench_052: Changing MSGCLASS
    cases.append(SemBenchCaseDef(
        id="sembench_052",
        base_id="base_hw_01_etl",
        source="handwritten",
        category="job_card_refactor",
        subcategory="msgclass_modification",
        expected_outcome="PRESERVING",
        relevant_jcl_semantics="IBM z/OS MVS JCL Reference: JOB Statement MSGCLASS Parameter",
        rationale="Changing MSGCLASS routes JCL job log messages to a different output class without altering program logic.",
        equivalence_argument="MSGCLASS controls JES spool output routing for system messages; it has no effect on step execution, dataset mutations, or condition codes.",
        original_text=HANDWRITTEN_BASES["base_hw_01_etl"],
        transformed_text=HANDWRITTEN_BASES["base_hw_01_etl"].replace("MSGCLASS=X", "MSGCLASS=H"),
    ))

    # sembench_053: Changing NOTIFY
    cases.append(SemBenchCaseDef(
        id="sembench_053",
        base_id="base_hw_01_etl",
        source="handwritten",
        category="job_card_refactor",
        subcategory="notify_modification",
        expected_outcome="PRESERVING",
        relevant_jcl_semantics="IBM z/OS MVS JCL Reference: JOB Statement NOTIFY Parameter",
        rationale="Altering NOTIFY target user ID.",
        equivalence_argument="NOTIFY requests a TSO broadcast message upon job completion; it does not change dataset lifecycle, step execution sequence, or return codes.",
        original_text=HANDWRITTEN_BASES["base_hw_01_etl"],
        transformed_text=HANDWRITTEN_BASES["base_hw_01_etl"].replace("NOTIFY=&SYSUID", "NOTIFY=OPRUSER1"),
    ))

    # sembench_054 to sembench_063: More JOB-card refactoring
    for i in range(10):
        case_num = 54 + i
        cid = f"sembench_{case_num:03d}"
        bkey = bases_keys[i % len(bases_keys)]
        orig = HANDWRITTEN_BASES[bkey]
        
        if "CLASS=A" in orig:
            mod = orig.replace("CLASS=A", "CLASS=B", 1)
            cat_sub = "job_class_change"
            sem = "IBM z/OS MVS JCL Reference: JOB Statement CLASS Parameter"
            rat = "Changing job execution class."
            arg = "CLASS specifies the JES job initiation queue; within the scope of batch execution semantics, step execution, dataflow, and dispositions are identical."
        elif "CLASS=" in orig:
            mod = orig.replace("CLASS=B", "CLASS=C").replace("CLASS=S", "CLASS=T").replace("CLASS=M", "CLASS=N")
            cat_sub = "job_class_change"
            sem = "IBM z/OS MVS JCL Reference: JOB Statement CLASS Parameter"
            rat = "Altering job execution class."
            arg = "JES execution queue assignment does not alter step execution logic or catalog states."
        else:
            mod = orig.replace("JOB (", "JOB (ACCT999,")
            cat_sub = "job_accounting_info"
            sem = "IBM z/OS MVS JCL Reference: JOB Statement Accounting Information"
            rat = "Updating accounting field."
            arg = "Accounting strings are passed to SMF and do not modify dataset contents, return codes, or step execution."

        cases.append(SemBenchCaseDef(
            id=cid,
            base_id=bkey,
            source="handwritten",
            category="job_card_refactor",
            subcategory=cat_sub,
            expected_outcome="PRESERVING",
            relevant_jcl_semantics=sem,
            rationale=rat,
            equivalence_argument=arg,
            original_text=orig,
            transformed_text=mod,
        ))

    # =========================================================================
    # 5. PRESERVING: SAFE REORDERING OF INDEPENDENT STATEMENTS (14 cases)
    # =========================================================================

    # sembench_064: Reordering independent work/sys DDs within compile step
    cases.append(SemBenchCaseDef(
        id="sembench_064",
        base_id="base_hw_03_compile_link",
        source="handwritten",
        category="independent_statement_reorder",
        subcategory="work_dd_reorder_within_step",
        expected_outcome="PRESERVING",
        relevant_jcl_semantics="IBM z/OS MVS JCL Reference: DD Statement Ordering Rules within a Step",
        rationale="Reordering independent compiler utility DDs (SYSUT1-SYSUT7) within the COMPILE step.",
        equivalence_argument="Within a step, DD statements with distinct ddnames (not part of a concatenation) are bound to program DCBs independently of statement order; compiler work files SYSUT1 through SYSUT7 are independent.",
        original_text=HANDWRITTEN_BASES["base_hw_03_compile_link"],
        transformed_text=HANDWRITTEN_BASES["base_hw_03_compile_link"].replace(
            "//SYSUT1   DD UNIT=SYSDA,SPACE=(CYL,(1,1))\n//SYSUT2   DD UNIT=SYSDA,SPACE=(CYL,(1,1))",
            "//SYSUT2   DD UNIT=SYSDA,SPACE=(CYL,(1,1))\n//SYSUT1   DD UNIT=SYSDA,SPACE=(CYL,(1,1))"
        ),
    ))

    # sembench_065: Reordering SORTWK files within SORT step
    cases.append(SemBenchCaseDef(
        id="sembench_065",
        base_id="base_hw_06_sort_merge",
        source="handwritten",
        category="independent_statement_reorder",
        subcategory="sortwk_dd_reorder_within_step",
        expected_outcome="PRESERVING",
        relevant_jcl_semantics="IBM DFSORT Application Programming Guide: SORTWK Datasets",
        rationale="Swapping SORTWK01 and SORTWK02 statement definitions.",
        equivalence_argument="DFSORT allocates temporary sort work datasets independently by ddname; swapping the statement order of SORTWK01 and SORTWK02 within the step leaves the sort work pool and output identical.",
        original_text=HANDWRITTEN_BASES["base_hw_06_sort_merge"],
        transformed_text=HANDWRITTEN_BASES["base_hw_06_sort_merge"].replace(
            "//SORTWK01 DD UNIT=SYSDA,SPACE=(CYL,(10,5))\n//SORTWK02 DD UNIT=SYSDA,SPACE=(CYL,(10,5))",
            "//SORTWK02 DD UNIT=SYSDA,SPACE=(CYL,(10,5))\n//SORTWK01 DD UNIT=SYSDA,SPACE=(CYL,(10,5))"
        ),
    ))

    # sembench_066 to sembench_077: More independent DD reorderings
    for i in range(12):
        case_num = 66 + i
        cid = f"sembench_{case_num:03d}"
        bkey = bases_keys[i % len(bases_keys)]
        orig = HANDWRITTEN_BASES[bkey]
        
        if "//SYSPRINT DD SYSOUT=*" in orig and "//SYSUT1" in orig and "//SYSIN    DD DUMMY" in orig:
            mod = orig.replace(
                "//SYSPRINT DD SYSOUT=*\n//SYSIN    DD DUMMY",
                "//SYSIN    DD DUMMY\n//SYSPRINT DD SYSOUT=*"
            )
            cat_sub = "sysprint_sysin_order"
            sem = "IBM z/OS MVS JCL Reference: Step DD Statement Binding"
            rat = "Swapping SYSPRINT and SYSIN DD order within IEBGENER step."
            arg = "SYSPRINT and SYSIN are distinct DDs opened by name; their relative order within the step does not alter data transfer or return codes."
        elif "//SYSOUT   DD SYSOUT=*" in orig and "//SORTIN" in orig:
            mod = orig.replace(
                "//SYSOUT   DD SYSOUT=*\n//SYSIN",
                "//SYSIN"
            ).replace(
                "/*\n",
                "/*\n//SYSOUT   DD SYSOUT=*\n"
            )
            cat_sub = "sysout_sysin_order"
            sem = "IBM z/OS MVS JCL Reference: DD Statement Order in Step"
            rat = "Moving SYSOUT DD after SYSIN delimiter."
            arg = "Placing SYSOUT after the SYSIN in-stream block leaves both DDs available to DFSORT with identical content and DD associations."
        else:
            mod = orig.replace(
                "//DDA1     DD DSN=WORK.RUNA.TEMP1,\n//            DISP=(NEW,CATLG,DELETE),\n//            UNIT=SYSDA,SPACE=(CYL,(5,1))\n//DDA2     DD DSN=WORK.RUNA.TEMP2,\n//            DISP=(NEW,CATLG,DELETE),\n//            UNIT=SYSDA,SPACE=(CYL,(5,1))",
                "//DDA2     DD DSN=WORK.RUNA.TEMP2,\n//            DISP=(NEW,CATLG,DELETE),\n//            UNIT=SYSDA,SPACE=(CYL,(5,1))\n//DDA1     DD DSN=WORK.RUNA.TEMP1,\n//            DISP=(NEW,CATLG,DELETE),\n//            UNIT=SYSDA,SPACE=(CYL,(5,1))"
            )
            cat_sub = "iefbr14_dd_reorder"
            sem = "IBM z/OS MVS JCL Reference: Allocation Order"
            rat = "Reordering independent allocation DDs in IEFBR14 step."
            arg = "IEFBR14 performs no I/O; allocation and disposition of non-dependent datasets DDA1 and DDA2 occur with identical catalog results regardless of DD definition order."

        cases.append(SemBenchCaseDef(
            id=cid,
            base_id=bkey,
            source="handwritten",
            category="independent_statement_reorder",
            subcategory=cat_sub,
            expected_outcome="PRESERVING",
            relevant_jcl_semantics=sem,
            rationale=rat,
            equivalence_argument=arg,
            original_text=orig,
            transformed_text=mod,
        ))

    # =========================================================================
    # 6. PRESERVING: UNREFERENCED STEP / SYMBOL RENAMES (6 cases)
    # =========================================================================
    
    for i in range(6):
        case_num = 78 + i
        cid = f"sembench_{case_num:03d}"
        bkey = bases_keys[i % len(bases_keys)]
        orig = HANDWRITTEN_BASES[bkey]
        
        if "//STEP10   EXEC" in orig:
            mod = orig.replace("//STEP10   EXEC", "//ST10X    EXEC")
            target_step = "STEP10 -> ST10X"
        elif "//STEP1    EXEC" in orig:
            mod = orig.replace("//STEP1    EXEC", "//STP1REN  EXEC").replace("STEP1", "STP1REN")
            target_step = "STEP1 -> STP1REN (including COND updates)"
        elif "//IDC1     EXEC" in orig:
            mod = orig.replace("//IDC1     EXEC", "//IDCALT1  EXEC").replace("IDC1", "IDCALT1")
            target_step = "IDC1 -> IDCALT1"
        else:
            mod = orig.replace("//PREPA    EXEC", "//PREPALOC EXEC")
            target_step = "PREPA -> PREPALOC"

        cases.append(SemBenchCaseDef(
            id=cid,
            base_id=bkey,
            source="handwritten",
            category="unreferenced_step_rename",
            subcategory="step_name_refactoring",
            expected_outcome="PRESERVING",
            relevant_jcl_semantics="IBM z/OS MVS JCL Reference: EXEC Statement Stepname",
            rationale=f"Renaming step {target_step} to a fresh name while preserving all backward references and COND logic.",
            equivalence_argument="Step names serve as internal labels for COND checks, backward references, and restart points. Systematically renaming a step along with all internal references preserves exact program invocation, dataset transformations, and execution conditions. NOTE: The oracle keys steps by name and flags step additions/removals as differing execution observables; this case demonstrates documented z/OS semantic equivalence where the oracle's step-identity model disagrees.",
            original_text=orig,
            transformed_text=mod,
        ))

    # =========================================================================
    # 7. BEHAVIOUR-CHANGING: STEP REORDER WITH DEPENDENCY (14 cases)
    # =========================================================================

    # sembench_084: Swapping producer and consumer steps
    cases.append(SemBenchCaseDef(
        id="sembench_084",
        base_id="base_hw_01_etl",
        source="handwritten",
        category="step_reorder_dependent",
        subcategory="swap_producer_consumer_steps",
        expected_outcome="CHANGING",
        relevant_jcl_semantics="IBM z/OS MVS JCL Reference: Step Execution Order and Dataset Lifecycle",
        rationale="Moving STEP30 (IDCAMS REPRO backup) before STEP20 (SORT creating FIN.PROD.DAILY.TRANS).",
        equivalence_argument="STEP30 reads FIN.PROD.DAILY.TRANS which is created by STEP20. Executing STEP30 before STEP20 causes STEP30 to read either the stale previous dataset or fail with dataset-not-found / contention, fundamentally violating the dataflow contract.",
        original_text=HANDWRITTEN_BASES["base_hw_01_etl"],
        transformed_text="""//ETLJOB01 JOB (ACCT101,'FINANCE'),'NIGHTLY ETL',
//         CLASS=A,MSGCLASS=X,NOTIFY=&SYSUID
//* Clean up previous target dataset
//STEP10   EXEC PGM=IEFBR14
//OLDDEL   DD DSN=FIN.PROD.DAILY.TRANS,
//            DISP=(MOD,DELETE,DELETE),
//            UNIT=SYSDA,SPACE=(TRK,0)
//* Backup runs BEFORE sort creates the data (VIOLATION)
//STEP30   EXEC PGM=IDCAMS
//SYSPRINT DD SYSOUT=*
//SYSIN    DD *
  REPRO -
    INDATASET(FIN.PROD.DAILY.TRANS) -
    OUTDATASET(FIN.BKUP.DAILY.TRANS)
/*
//* Sort raw incoming transactions
//STEP20   EXEC PGM=SORT
//SORTIN   DD DSN=FIN.RAW.DAILY.TRANS,DISP=SHR
//SORTOUT  DD DSN=FIN.PROD.DAILY.TRANS,
//            DISP=(NEW,CATLG,DELETE),
//            UNIT=SYSDA,SPACE=(CYL,(10,5),RLSE),
//            DCB=(RECFM=FB,LRECL=120,BLKSIZE=27960)
//SYSOUT   DD SYSOUT=*
//SYSIN    DD *
  SORT FIELDS=(1,16,CH,A,17,8,PD,D)
  RECORD TYPE=F,LENGTH=120
/*
""",
    ))

    # sembench_085: Moving compile after link
    cases.append(SemBenchCaseDef(
        id="sembench_085",
        base_id="base_hw_03_compile_link",
        source="handwritten",
        category="step_reorder_dependent",
        subcategory="swap_compile_and_bind_steps",
        expected_outcome="CHANGING",
        relevant_jcl_semantics="IBM z/OS MVS JCL Reference: Temporary Dataset Passing (&&OBJSET)",
        rationale="Executing BIND step before COMPILE step.",
        equivalence_argument="BIND expects &&OBJSET produced with DISP=(NEW,PASS) by COMPILE. Moving BIND ahead causes JCL allocation failure on uncreated temporary dataset &&OBJSET.",
        original_text=HANDWRITTEN_BASES["base_hw_03_compile_link"],
        transformed_text="""//CMPLNK03 JOB (ACCT303,'DEV'),'BUILD COBOL',
//         CLASS=A,MSGCLASS=X,NOTIFY=&SYSUID
//BIND     EXEC PGM=IEWL,
//         PARM='LIST,MAP,XREF,LET'
//SYSLIN   DD DSN=&&OBJSET,DISP=(OLD,DELETE)
//         DD DDNAME=SYSIN
//SYSLMOD  DD DSN=PROD.LOADLIB(BILLING),DISP=SHR
//SYSPRINT DD SYSOUT=*
//SYSUT1   DD UNIT=SYSDA,SPACE=(CYL,(1,1))
//SYSIN    DD *
  NAME BILLING(R)
/*
//COMPILE  EXEC PGM=IGYCRCTL,PARM='NODECK,OBJECT,LIST'
//SYSIN    DD DSN=DEV.COBOL.SRC(BILLING),DISP=SHR
//SYSLIN   DD DSN=&&OBJSET,DISP=(NEW,PASS),
//            UNIT=SYSDA,SPACE=(CYL,(1,1))
//SYSPRINT DD SYSOUT=*
//SYSMDECK DD DSN=&&MDECK,DISP=(NEW,PASS),UNIT=SYSDA,SPACE=(TRK,(1,1))
//SYSUT1   DD UNIT=SYSDA,SPACE=(CYL,(1,1))
//SYSUT2   DD UNIT=SYSDA,SPACE=(CYL,(1,1))
//SYSUT3   DD UNIT=SYSDA,SPACE=(CYL,(1,1))
//SYSUT4   DD UNIT=SYSDA,SPACE=(CYL,(1,1))
//SYSUT5   DD UNIT=SYSDA,SPACE=(CYL,(1,1))
//SYSUT6   DD UNIT=SYSDA,SPACE=(CYL,(1,1))
//SYSUT7   DD UNIT=SYSDA,SPACE=(CYL,(1,1))
""",
    ))

    # sembench_086 to sembench_097: More step reorder cases with dependencies
    for i in range(12):
        case_num = 86 + i
        cid = f"sembench_{case_num:03d}"
        bkey = bases_keys[(i + 4) % len(bases_keys)]
        if bkey == "base_hw_10_if_then_else":
            # Avoid breaking IF/THEN block structure by choosing another base
            bkey = "base_hw_05_multi_disp"
        orig = HANDWRITTEN_BASES[bkey]
        
        steps_blocks = []
        cur_lines = []
        job_header = []
        in_header = True
        for line in orig.splitlines():
            if (line.startswith("//STEP") or line.startswith("//ST") or line.startswith("//CP") or line.startswith("//IDC") or line.startswith("//DEF") or line.startswith("//MAK") or line.startswith("//GEN") or line.startswith("//PREP")) and " EXEC " in line:
                in_header = False
                if cur_lines:
                    steps_blocks.append("\n".join(cur_lines))
                    cur_lines = []
            if in_header:
                job_header.append(line)
            else:
                cur_lines.append(line)
        if cur_lines:
            steps_blocks.append("\n".join(cur_lines))
            
        if len(steps_blocks) >= 2:
            swapped = [steps_blocks[1], steps_blocks[0]] + steps_blocks[2:]
            mod = "\n".join(job_header) + "\n" + "\n".join(swapped) + "\n"
        else:
            mod = orig + "\n//EXTRA EXEC PGM=IEFBR14\n"

        cases.append(SemBenchCaseDef(
            id=cid,
            base_id=bkey,
            source="handwritten",
            category="step_reorder_dependent",
            subcategory="consecutive_step_inversion",
            expected_outcome="CHANGING",
            relevant_jcl_semantics="IBM z/OS MVS JCL Reference: Step Order and Abend Propagation",
            rationale="Inverting consecutive step execution sequence.",
            equivalence_argument="Under z/OS JCL execution semantics, reordering steps alters abend propagation boundaries (the step that originally followed an abending step is bypassed; after swapping it has already run) and inverts any implicit or explicit dataset/condition dependencies.",
            original_text=orig,
            transformed_text=mod,
        ))

    # =========================================================================
    # 8. BEHAVIOUR-CHANGING: DATASET DEPENDENCY CHANGES (16 cases)
    # =========================================================================

    # sembench_098: Renaming output dataset so downstream consumer misses it
    cases.append(SemBenchCaseDef(
        id="sembench_098",
        base_id="base_hw_01_etl",
        source="handwritten",
        category="dataset_dependency_change",
        subcategory="output_dsn_rename_broken_link",
        expected_outcome="CHANGING",
        relevant_jcl_semantics="IBM z/OS MVS JCL Reference: Dataset Names and Dataflow",
        rationale="Renaming SORTOUT DSN in STEP20 without updating downstream IDCAMS REPRO input in STEP30.",
        equivalence_argument="STEP20 writes to FIN.PROD.DAILY.TRANS.NEW instead of FIN.PROD.DAILY.TRANS; STEP30 continues reading FIN.PROD.DAILY.TRANS, causing STEP30 to process outdated data or fail allocation.",
        original_text=HANDWRITTEN_BASES["base_hw_01_etl"],
        transformed_text=HANDWRITTEN_BASES["base_hw_01_etl"].replace("DSN=FIN.PROD.DAILY.TRANS,\n//            DISP=(NEW,CATLG,DELETE)", "DSN=FIN.PROD.DAILY.TRANS.NEW,\n//            DISP=(NEW,CATLG,DELETE)"),
    ))

    # sembench_099: Changing input GDG generation from (+1) to (0)
    cases.append(SemBenchCaseDef(
        id="sembench_099",
        base_id="base_hw_04_gdg_cycle",
        source="handwritten",
        category="dataset_dependency_change",
        subcategory="gdg_relative_generation_alteration",
        expected_outcome="CHANGING",
        relevant_jcl_semantics="IBM z/OS MVS JCL Reference: Generation Data Groups Relative Numbering",
        rationale="Changing READGEN SYSUT1 from PROD.LOGS.MONTHLY(+1) to PROD.LOGS.MONTHLY(0).",
        equivalence_argument="Within a single job, (+1) refers to the generation created in MAKENEW; (0) refers to the generation existing at job initiation. Changing (+1) to (0) causes READGEN to process the previous month's log rather than the newly sorted monthly log.",
        original_text=HANDWRITTEN_BASES["base_hw_04_gdg_cycle"],
        transformed_text=HANDWRITTEN_BASES["base_hw_04_gdg_cycle"].replace("DSN=PROD.LOGS.MONTHLY(+1),DISP=SHR", "DSN=PROD.LOGS.MONTHLY(0),DISP=SHR"),
    ))

    # sembench_100 to sembench_113: More dataset dependency changes
    for i in range(14):
        case_num = 100 + i
        cid = f"sembench_{case_num:03d}"
        bkey = bases_keys[i % len(bases_keys)]
        orig = HANDWRITTEN_BASES[bkey]
        
        if "ACCT.DATA.INPUT" in orig:
            mod = orig.replace("ACCT.DATA.INPUT", "ACCT.DATA.INPUT.TEST")
            subcat = "input_dsn_redirect"
            rat = "Redirecting input DSN to alternate dataset."
            arg = "Changing input DSN causes the step to consume test data instead of production data."
        elif "DEV.COBOL.SRC(BILLING)" in orig:
            mod = orig.replace("DEV.COBOL.SRC(BILLING)", "DEV.COBOL.SRC(INVOICE)")
            subcat = "pds_member_redirect"
            rat = "Compiling INVOICE source member instead of BILLING."
            arg = "Compiles a completely different source program member into the load library."
        elif "CORP.FEED.NORTH" in orig:
            mod = orig.replace("CORP.FEED.NORTH", "CORP.FEED.EAST")
            subcat = "sort_input_source_swap"
            rat = "Substituting NORTH input feed with EAST."
            arg = "Alters the composite records fed into the sort-merge operation."
        elif "CORP.FLAT.SEED" in orig:
            mod = orig.replace("CORP.FLAT.SEED", "CORP.FLAT.SEED.EMPTY")
            subcat = "vsam_seed_dataset_swap"
            rat = "Loading VSAM cluster from empty seed."
            arg = "IDCAMS REPRO populates the KSDS cluster with 0 records instead of seed data."
        elif "WAREHOUSE.INVENTORY.RAW" in orig:
            mod = orig.replace("WAREHOUSE.INVENTORY.RAW", "WAREHOUSE.INVENTORY.CORRUPT")
            subcat = "copy_source_redirect"
            rat = "Directing copy utility to corrupt dataset."
            arg = "IEBGENER copies corrupted inventory data into the pipeline."
        elif "LEDGER.BATCH.INPUT" in orig:
            mod = orig.replace("LEDGER.BATCH.INPUT", "LEDGER.BATCH.PREVIOUS")
            subcat = "input_feed_version_change"
            rat = "Processing previous batch ledger."
            arg = "Dataflow consumes stale batch records."
        elif "REPORT.SUMMARY.OUTPUT" in orig:
            mod = orig.replace("REPORT.SUMMARY.OUTPUT", "REPORT.SUMMARY.DEVNULL")
            subcat = "report_target_redirection"
            rat = "Directing audit report to devnull target."
            arg = "Final catalog will not contain the expected audit report dataset."
        else:
            mod = orig.replace("STAGE.DATA.SOURCE", "STAGE.DATA.SOURCE.OLD")
            subcat = "stage_source_alteration"
            rat = "Changing stage data source."
            arg = "Populates master file from outdated staging dataset. NOTE: In single-job simulation without initial catalog distinction between stage files, the oracle reports EQUIVALENT, but z/OS catalog resolution alters input dataflow."

        cases.append(SemBenchCaseDef(
            id=cid,
            base_id=bkey,
            source="handwritten",
            category="dataset_dependency_change",
            subcategory=subcat,
            expected_outcome="CHANGING",
            relevant_jcl_semantics="IBM z/OS MVS JCL Reference: DSNAME Parameter and Catalog Resolution",
            rationale=rat,
            equivalence_argument=arg,
            original_text=orig,
            transformed_text=mod,
        ))

    # =========================================================================
    # 9. BEHAVIOUR-CHANGING: DISP PARAMETER CHANGES (18 cases)
    # =========================================================================

    # sembench_114: NEW to OLD on existing file creation
    cases.append(SemBenchCaseDef(
        id="sembench_114",
        base_id="base_hw_01_etl",
        source="handwritten",
        category="disp_change",
        subcategory="disp_new_to_old",
        expected_outcome="CHANGING",
        relevant_jcl_semantics="IBM z/OS MVS JCL Reference: DISP Parameter (Status Subparameter)",
        rationale="Changing SORTOUT DISP from (NEW,CATLG,DELETE) to (OLD,CATLG,DELETE).",
        equivalence_argument="If FIN.PROD.DAILY.TRANS was deleted in STEP10, specifying DISP=OLD causes a JCL allocation error ending the job; furthermore, OLD requests exclusive enqueue on an existing dataset rather than creating a new catalog entry.",
        original_text=HANDWRITTEN_BASES["base_hw_01_etl"],
        transformed_text=HANDWRITTEN_BASES["base_hw_01_etl"].replace("DISP=(NEW,CATLG,DELETE),", "DISP=(OLD,CATLG,DELETE),"),
    ))

    # sembench_115: CATLG to DELETE on normal termination
    cases.append(SemBenchCaseDef(
        id="sembench_115",
        base_id="base_hw_01_etl",
        source="handwritten",
        category="disp_change",
        subcategory="disp_normal_catlg_to_delete",
        expected_outcome="CHANGING",
        relevant_jcl_semantics="IBM z/OS MVS JCL Reference: DISP Parameter (Normal Disposition)",
        rationale="Changing normal disposition from CATLG to DELETE.",
        equivalence_argument="At normal step termination, the dataset FIN.PROD.DAILY.TRANS is deleted and uncataloged instead of retained in the catalog; downstream steps and subsequent jobs will fail to find it.",
        original_text=HANDWRITTEN_BASES["base_hw_01_etl"],
        transformed_text=HANDWRITTEN_BASES["base_hw_01_etl"].replace("DISP=(NEW,CATLG,DELETE),", "DISP=(NEW,DELETE,DELETE),"),
    ))

    # sembench_116: Abnormal disposition change DELETE to CATLG
    cases.append(SemBenchCaseDef(
        id="sembench_116",
        base_id="base_hw_01_etl",
        source="handwritten",
        category="disp_change",
        subcategory="disp_abnormal_delete_to_catlg",
        expected_outcome="CHANGING",
        relevant_jcl_semantics="IBM z/OS MVS JCL Reference: DISP Parameter (Abnormal Disposition)",
        rationale="Changing abnormal disposition from DELETE to CATLG.",
        equivalence_argument="Upon step abend, DISP=(NEW,CATLG,CATLG) causes a partially-written or corrupt dataset to be cataloged rather than deleted, polluting the catalog on failure.",
        original_text=HANDWRITTEN_BASES["base_hw_01_etl"],
        transformed_text=HANDWRITTEN_BASES["base_hw_01_etl"].replace("DISP=(NEW,CATLG,DELETE),", "DISP=(NEW,CATLG,CATLG),"),
    ))

    # sembench_117 to sembench_131: More DISP change cases
    for i in range(15):
        case_num = 117 + i
        cid = f"sembench_{case_num:03d}"
        bkey = bases_keys[i % len(bases_keys)]
        orig = HANDWRITTEN_BASES[bkey]
        
        if "DISP=SHR" in orig and i % 3 == 0:
            mod = orig.replace("DISP=SHR", "DISP=OLD", 1)
            subcat = "disp_shr_to_old"
            rat = "Changing SHR to OLD on input dataset."
            arg = "DISP=OLD requests exclusive dataset enqueue, preventing concurrent job access and causing job lockouts in production. (Oracle single-job simulation models both as reads, producing EQUIVALENT)."
        elif "DISP=(NEW,CATLG,DELETE)" in orig and i % 3 == 1:
            mod = orig.replace("DISP=(NEW,CATLG,DELETE)", "DISP=(NEW,KEEP,DELETE)", 1)
            subcat = "disp_catlg_to_keep"
            rat = "Changing CATLG to KEEP on SMS-managed dataset."
            arg = "Specifying KEEP instead of CATLG for a newly allocated dataset leaves it uncataloged on non-SMS volumes or alters system catalog association."
        elif "DISP=(MOD,DELETE,DELETE)" in orig:
            mod = orig.replace("DISP=(MOD,DELETE,DELETE)", "DISP=(MOD,KEEP,KEEP)", 1)
            subcat = "disp_mod_delete_to_keep"
            rat = "Changing cleanup step disposition from DELETE to KEEP."
            arg = "The cleanup step fails to delete the target dataset, leaving stale records intact."
        else:
            mod = orig.replace("DISP=SHR", "DISP=(NEW,CATLG,DELETE)")
            subcat = "disp_shr_to_new"
            rat = "Changing SHR to NEW."
            arg = "Attempts to allocate an existing dataset as NEW, triggering JCL allocation error."

        cases.append(SemBenchCaseDef(
            id=cid,
            base_id=bkey,
            source="handwritten",
            category="disp_change",
            subcategory=subcat,
            expected_outcome="CHANGING",
            relevant_jcl_semantics="IBM z/OS MVS JCL Reference: DISP Parameter",
            rationale=rat,
            equivalence_argument=arg,
            original_text=orig,
            transformed_text=mod,
        ))

    # =========================================================================
    # 10. BEHAVIOUR-CHANGING: COND LOGIC AND RETURN CODE BRANCHING (18 cases)
    # =========================================================================

    # sembench_132: Inverting COND relation from LT to GE
    cases.append(SemBenchCaseDef(
        id="sembench_132",
        base_id="base_hw_02_cond_chain",
        source="handwritten",
        category="cond_logic_change",
        subcategory="cond_relational_operator_inversion",
        expected_outcome="CHANGING",
        relevant_jcl_semantics="IBM z/OS MVS JCL Reference: EXEC COND Relational Operators",
        rationale="Changing COND=(4,LT,STEP1) to COND=(4,GE,STEP1).",
        equivalence_argument="Under COND=(4,LT,STEP1), the step is bypassed if 4 < STEP1.RC (i.e. bypassed if RC > 4, so it runs on RC 0 or 4). Under COND=(4,GE,STEP1), the step is bypassed if 4 >= STEP1.RC (i.e. bypassed on RC 0 and 4). This inverts step execution for all normal successful runs.",
        original_text=HANDWRITTEN_BASES["base_hw_02_cond_chain"],
        transformed_text=HANDWRITTEN_BASES["base_hw_02_cond_chain"].replace("COND=(4,LT,STEP1)", "COND=(4,GE,STEP1)"),
    ))

    # sembench_133: COND threshold change from 4 to 8
    cases.append(SemBenchCaseDef(
        id="sembench_133",
        base_id="base_hw_02_cond_chain",
        source="handwritten",
        category="cond_logic_change",
        subcategory="cond_threshold_alteration",
        expected_outcome="CHANGING",
        relevant_jcl_semantics="IBM z/OS MVS JCL Reference: EXEC COND Parameter Threshold Testing",
        rationale="Weakening condition threshold from 4 to 8.",
        equivalence_argument="If STEP1 ends with warning return code RC=8, COND=(4,LT) bypasses STEP2 (since 4 < 8 is true), whereas COND=(8,LT) allows STEP2 to run (since 8 < 8 is false). This changes execution branching on warning return codes.",
        original_text=HANDWRITTEN_BASES["base_hw_02_cond_chain"],
        transformed_text=HANDWRITTEN_BASES["base_hw_02_cond_chain"].replace("COND=(4,LT,STEP1)", "COND=(8,LT,STEP1)"),
    ))

    # sembench_134: Removing COND=EVEN from emergency cleanup step
    cases.append(SemBenchCaseDef(
        id="sembench_134",
        base_id="base_hw_02_cond_chain",
        source="handwritten",
        category="cond_logic_change",
        subcategory="cond_even_removal",
        expected_outcome="CHANGING",
        relevant_jcl_semantics="IBM z/OS MVS JCL Reference: EXEC COND=EVEN Parameter",
        rationale="Removing COND=EVEN from STEP4 cleanup step.",
        equivalence_argument="With COND=EVEN, STEP4 executes even if any preceding step abends. Removing COND=EVEN causes the operating system to bypass STEP4 when an abend occurs, leaving uncleaned datasets in the catalog.",
        original_text=HANDWRITTEN_BASES["base_hw_02_cond_chain"],
        transformed_text=HANDWRITTEN_BASES["base_hw_02_cond_chain"].replace("EXEC PGM=IEFBR14,COND=EVEN", "EXEC PGM=IEFBR14"),
    ))

    # sembench_135 to sembench_149: More COND / IF logic changes
    for i in range(15):
        case_num = 135 + i
        cid = f"sembench_{case_num:03d}"
        bkey = bases_keys[i % len(bases_keys)]
        orig = HANDWRITTEN_BASES[bkey]
        
        if "COND=(0,NE,STEP20)" in orig:
            mod = orig.replace("COND=(0,NE,STEP20)", "COND=(4,LT,STEP20)")
            subcat = "cond_logic_mutation"
            rat = "Changing strict zero-check to warning-tolerance check."
            arg = "Runs step when STEP20 produces warning RC=4 instead of requiring exact RC=0."
        elif "COND=(4,LT,COMPILE)" in orig:
            mod = orig.replace("COND=(4,LT,COMPILE)", "COND=(0,NE,COMPILE)")
            subcat = "cond_strictness_tightening"
            rat = "Tightening bind condition to require RC=0."
            arg = "Bypasses binder on clean compile warnings (RC=4), preventing valid load module generation."
        elif "IF (STP1.RC = 0)" in orig:
            mod = orig.replace("IF (STP1.RC = 0)", "IF (STP1.RC <= 4)")
            subcat = "if_condition_boundary_widening"
            rat = "Allowing warning return codes in IF clause."
            arg = "Causes STP2A to execute on warning RC=4 where it originally branched to STP2B."
        elif "COND=(8,LE)" in orig:
            mod = orig.replace("COND=(8,LE)", "COND=(12,LE)")
            subcat = "cond_threshold_weakening"
            rat = "Weakening threshold from 8 to 12."
            arg = "Allows IDCAMS print step to execute even after severe errors (RC=8)."
        else:
            lines = orig.splitlines()
            for idx in range(len(lines)-1, -1, -1):
                if " EXEC " in lines[idx] and not lines[idx].startswith("//*"):
                    lines[idx] = lines[idx] + ",COND=(0,LE)"
                    break
            mod = "\n".join(lines) + "\n"
            subcat = "cond_always_bypass"
            rat = "Adding COND=(0,LE) which is always true after any normal step."
            arg = "Causes the step to be unconditionally bypassed on return codes >= 0."

        cases.append(SemBenchCaseDef(
            id=cid,
            base_id=bkey,
            source="handwritten",
            category="cond_logic_change",
            subcategory=subcat,
            expected_outcome="CHANGING",
            relevant_jcl_semantics="IBM z/OS MVS JCL Reference: Conditional Job Control",
            rationale=rat,
            equivalence_argument=arg,
            original_text=orig,
            transformed_text=mod,
        ))

    # =========================================================================
    # 11. BEHAVIOUR-CHANGING: PRODUCER-CONSUMER OBLIGATIONS (12 cases)
    # =========================================================================

    # sembench_150: Deleting producer step entirely
    cases.append(SemBenchCaseDef(
        id="sembench_150",
        base_id="base_hw_01_etl",
        source="handwritten",
        category="producer_consumer_change",
        subcategory="delete_producer_step",
        expected_outcome="CHANGING",
        relevant_jcl_semantics="IBM z/OS MVS JCL Reference: Step Execution and Dataset Creation",
        rationale="Deleting STEP20 (the SORT step that produces FIN.PROD.DAILY.TRANS).",
        equivalence_argument="Deleting STEP20 eliminates the production of FIN.PROD.DAILY.TRANS; downstream STEP30 fails to find the dataset, and the final catalog lacks the transformed daily transactions.",
        original_text=HANDWRITTEN_BASES["base_hw_01_etl"],
        transformed_text="""//ETLJOB01 JOB (ACCT101,'FINANCE'),'NIGHTLY ETL',
//         CLASS=A,MSGCLASS=X,NOTIFY=&SYSUID
//* Clean up previous target dataset
//STEP10   EXEC PGM=IEFBR14
//OLDDEL   DD DSN=FIN.PROD.DAILY.TRANS,
//            DISP=(MOD,DELETE,DELETE),
//            UNIT=SYSDA,SPACE=(TRK,0)
//* Backup newly created dataset (producer STEP20 was deleted!)
//STEP30   EXEC PGM=IDCAMS
//SYSPRINT DD SYSOUT=*
//SYSIN    DD *
  REPRO -
    INDATASET(FIN.PROD.DAILY.TRANS) -
    OUTDATASET(FIN.BKUP.DAILY.TRANS)
/*
""",
    ))

    # sembench_151 to sembench_161: More producer-consumer obligation cases
    for i in range(11):
        case_num = 151 + i
        cid = f"sembench_{case_num:03d}"
        bkey = bases_keys[i % len(bases_keys)]
        if bkey == "base_hw_10_if_then_else":
            bkey = "base_hw_08_iebgener_copy"
        orig = HANDWRITTEN_BASES[bkey]
        
        lines = orig.splitlines()
        deleted_step = False
        new_lines = []
        skip = False
        for line in lines:
            if ("//STEP" in line or "//ST" in line or "//CP" in line or "//IDC" in line) and " EXEC " in line and "IEFBR14" not in line and not deleted_step:
                skip = True
                deleted_step = True
                continue
            if skip and (line.startswith("//STEP") or line.startswith("//ST") or line.startswith("//CP") or line.startswith("//IDC") or line.startswith("//ENDIF")):
                skip = False
            if not skip:
                new_lines.append(line)
        mod = "\n".join(new_lines) + "\n"

        cases.append(SemBenchCaseDef(
            id=cid,
            base_id=bkey,
            source="handwritten",
            category="producer_consumer_change",
            subcategory="omit_pipeline_producer",
            expected_outcome="CHANGING",
            relevant_jcl_semantics="IBM z/OS MVS JCL Reference: Job Step Execution Sequence",
            rationale="Removing a functional transformation step from the pipeline.",
            equivalence_argument="Omitting a processing step prevents generation of intermediate datasets, breaks DISP pass chains, and omits intended catalog mutations.",
            original_text=orig,
            transformed_text=mod,
        ))

    # =========================================================================
    # 12. BEHAVIOUR-CHANGING: RETURN CODE & PROGRAM EFFECT (12 cases)
    # =========================================================================

    # sembench_162: IDCAMS DELETE command alteration
    cases.append(SemBenchCaseDef(
        id="sembench_162",
        base_id="base_hw_07_idcams_catalog",
        source="handwritten",
        category="return_code_effect",
        subcategory="idcams_delete_cluster_name_altered",
        expected_outcome="CHANGING",
        relevant_jcl_semantics="IBM IDCAMS Reference: DELETE Command Semantics and Return Codes",
        rationale="Changing IDCAMS DELETE target cluster to non-existent dataset.",
        equivalence_argument="IDCAMS DELETE against a non-existent cluster produces condition code RC=8, whereas deleting the targeted cluster produces RC=0. This return code triggers COND checks and changes IDCAMS execution status.",
        original_text=HANDWRITTEN_BASES["base_hw_07_idcams_catalog"],
        transformed_text=HANDWRITTEN_BASES["base_hw_07_idcams_catalog"].replace("DELETE CORP.VSAM.KSDS CLUSTER PURGE", "DELETE CORP.VSAM.NONEXIST CLUSTER PURGE"),
    ))

    # sembench_163: IDCAMS DEFINE CLUSTER alteration
    cases.append(SemBenchCaseDef(
        id="sembench_163",
        base_id="base_hw_07_idcams_catalog",
        source="handwritten",
        category="return_code_effect",
        subcategory="idcams_define_cluster_key_change",
        expected_outcome="CHANGING",
        relevant_jcl_semantics="IBM IDCAMS Reference: DEFINE CLUSTER KEYS Specification",
        rationale="Changing VSAM KSDS key offset from KEYS(16 0) to KEYS(16 10).",
        equivalence_argument="Altering the key offset in DEFINE CLUSTER creates a VSAM file with a different indexing structure; subsequent REPRO and application access will fail with record key mismatches.",
        original_text=HANDWRITTEN_BASES["base_hw_07_idcams_catalog"],
        transformed_text=HANDWRITTEN_BASES["base_hw_07_idcams_catalog"].replace("KEYS(16 0)", "KEYS(16 10)"),
    ))

    # sembench_164 to sembench_173: More return-code / program-effect cases
    for i in range(10):
        case_num = 164 + i
        cid = f"sembench_{case_num:03d}"
        bkey = bases_keys[i % len(bases_keys)]
        orig = HANDWRITTEN_BASES[bkey]
        
        if "SORT FIELDS=(1,16,CH,A,17,8,PD,D)" in orig:
            mod = orig.replace("SORT FIELDS=(1,16,CH,A,17,8,PD,D)", "SORT FIELDS=(1,16,CH,D,17,8,PD,D)")
            subcat = "sort_order_direction_inversion"
            rat = "Inverting primary sort key from Ascending (A) to Descending (D)."
            arg = "DFSORT sorts the file in reverse order; downstream records and reporting sequence are altered."
        elif "RECORD TYPE=F,LENGTH=120" in orig:
            mod = orig.replace("RECORD TYPE=F,LENGTH=120", "RECORD TYPE=F,LENGTH=100")
            subcat = "record_length_parameter_change"
            rat = "Changing record length in sort control card."
            arg = "DFSORT encounters a record length mismatch against the LRECL=120 dataset, terminating with error RC=16."
        elif "NAME BILLING(R)" in orig:
            mod = orig.replace("NAME BILLING(R)", "NAME BILLING2(R)")
            subcat = "binder_target_member_rename"
            rat = "Renaming binder output member to BILLING2."
            arg = "The executable load module is stored under member name BILLING2 instead of BILLING, leaving PROD.LOADLIB(BILLING) stale or absent."
        elif "PRINT INDATASET" in orig:
            mod = orig.replace("COUNT(100)", "COUNT(10)")
            subcat = "idcams_print_count_limit"
            rat = "Restricting IDCAMS print record count from 100 to 10."
            arg = "IDCAMS prints 10 records instead of 100 to SYSPRINT, modifying program execution output."
        elif "COPY OUTDD=OUTLIB,INDD=INLIB" in orig:
            mod = orig.replace("COPY OUTDD=OUTLIB,INDD=INLIB", "COPY OUTDD=OUTLIB,INDD=INLIB\n  SELECT MEMBER=NOTFOUND")
            subcat = "iebcopy_member_selection_filtering"
            rat = "Adding non-matching SELECT member filter to IEBCOPY."
            arg = "IEBCOPY fails to copy any members and issues warning return code RC=4."
        else:
            mod = orig.replace("PGM=IEBGENER", "PGM=IEFBR14")
            subcat = "program_substitution"
            rat = "Replacing IEBGENER with IEFBR14."
            arg = "IEFBR14 performs no data transfer; the target dataset remains unwritten."

        cases.append(SemBenchCaseDef(
            id=cid,
            base_id=bkey,
            source="handwritten",
            category="return_code_effect",
            subcategory=subcat,
            expected_outcome="CHANGING",
            relevant_jcl_semantics="IBM Utilities Reference: Program Functionality and Return Codes",
            rationale=rat,
            equivalence_argument=arg,
            original_text=orig,
            transformed_text=mod,
        ))

    # =========================================================================
    # 13. CORPUS-DERIVED CASES (CardDemo, OMP Course, GenApp) (8 cases)
    # =========================================================================
    
    # CardDemo preserving: comment & format
    if "corpus_carddemo_cbpaup0j" in corpus_texts:
        cpath, ctext = corpus_texts["corpus_carddemo_cbpaup0j"]
        cases.append(SemBenchCaseDef(
            id="sembench_174",
            base_id="corpus_carddemo_cbpaup0j",
            source=f"corpus:{cpath}",
            category="comment_edit",
            subcategory="corpus_comment_injection",
            expected_outcome="PRESERVING",
            relevant_jcl_semantics="IBM z/OS MVS JCL Reference: Comment Statement (//*)",
            rationale="Adding standard header comments to CardDemo batch auth job.",
            equivalence_argument="Full-line comments are ignored by the JCL converter.",
            original_text=ctext,
            transformed_text="//* CardDemo Production Authorization Job Header\n" + ctext,
        ))
        
        # CardDemo changing: DSN modification
        cases.append(SemBenchCaseDef(
            id="sembench_175",
            base_id="corpus_carddemo_cbpaup0j",
            source=f"corpus:{cpath}",
            category="dataset_dependency_change",
            subcategory="corpus_input_dsn_alteration",
            expected_outcome="CHANGING",
            relevant_jcl_semantics="IBM z/OS MVS JCL Reference: DSNAME Parameter",
            rationale="Altering input dataset name in CardDemo batch job.",
            equivalence_argument="Directs application to alternate non-existent dataset, changing input dataflow and causing potential abend/error.",
            original_text=ctext,
            transformed_text=ctext.replace(".DATA", ".DATA.MODIFIED"),
        ))

    # OMP Course preserving & changing
    if "corpus_omp_course_cbl0001j" in corpus_texts:
        cpath, ctext = corpus_texts["corpus_omp_course_cbl0001j"]
        cases.append(SemBenchCaseDef(
            id="sembench_176",
            base_id="corpus_omp_course_cbl0001j",
            source=f"corpus:{cpath}",
            category="syntax_representation",
            subcategory="corpus_disp_parens",
            expected_outcome="PRESERVING",
            relevant_jcl_semantics="IBM z/OS MVS JCL Reference: DISP Syntax",
            rationale="Parenthesizing single DISP subparameters in OMP course lab job.",
            equivalence_argument="DISP=SHR and DISP=(SHR) have identical semantics.",
            original_text=ctext,
            transformed_text=ctext.replace("DISP=SHR", "DISP=(SHR)"),
        ))

        cases.append(SemBenchCaseDef(
            id="sembench_177",
            base_id="corpus_omp_course_cbl0001j",
            source=f"corpus:{cpath}",
            category="disp_change",
            subcategory="corpus_disp_status_change",
            expected_outcome="CHANGING",
            relevant_jcl_semantics="IBM z/OS MVS JCL Reference: DISP Parameter",
            rationale="Changing DISP=SHR to DISP=OLD in OMP compile lab.",
            equivalence_argument="Changes shared read allocation to exclusive lock.",
            original_text=ctext,
            transformed_text=ctext.replace("DISP=SHR", "DISP=OLD"),
        ))

    # GenApp preserving & changing
    if "corpus_genapp_adef121" in corpus_texts:
        cpath, ctext = corpus_texts["corpus_genapp_adef121"]
        cases.append(SemBenchCaseDef(
            id="sembench_178",
            base_id="corpus_genapp_adef121",
            source=f"corpus:{cpath}",
            category="comment_edit",
            subcategory="corpus_genapp_comments",
            expected_outcome="PRESERVING",
            relevant_jcl_semantics="IBM z/OS MVS JCL Reference: Comments",
            rationale="Adding section comment block to GenApp IDCAMS definition job.",
            equivalence_argument="Comments do not alter IDCAMS cluster definitions.",
            original_text=ctext,
            transformed_text="//* GenApp VSAM Installation Job\n" + ctext,
        ))

        cases.append(SemBenchCaseDef(
            id="sembench_179",
            base_id="corpus_genapp_adef121",
            source=f"corpus:{cpath}",
            category="return_code_effect",
            subcategory="corpus_genapp_idcams_cluster_name",
            expected_outcome="CHANGING",
            relevant_jcl_semantics="IBM IDCAMS Reference: DEFINE CLUSTER",
            rationale="Altering target cluster name in GenApp VSAM definition.",
            equivalence_argument="Creates cluster with different name, breaking CICS FCT/CSD resource bindings.",
            original_text=ctext,
            transformed_text=ctext.replace("NAME(", "NAME(MOD."),
        ))

    # Additional CardDemo / GenApp cases to reach 180
    if "corpus_carddemo_dbpautp0" in corpus_texts:
        cpath, ctext = corpus_texts["corpus_carddemo_dbpautp0"]
        cases.append(SemBenchCaseDef(
            id="sembench_180",
            base_id="corpus_carddemo_dbpautp0",
            source=f"corpus:{cpath}",
            category="whitespace_and_continuation",
            subcategory="corpus_carddemo_indentation",
            expected_outcome="PRESERVING",
            relevant_jcl_semantics="IBM z/OS MVS JCL Reference: Continuation Indentation",
            rationale="Indenting continuation statements in CardDemo DBPAUTP0 job.",
            equivalence_argument="Indentation within columns 4-16 is semantically neutral.",
            original_text=ctext,
            transformed_text=ctext.replace("//             ", "//                 "),
        ))

    return cases


def build_sembench():
    print(f"[build_sembench] Starting build under {SEMBENCH_DIR}")
    CASES_DIR.mkdir(parents=True, exist_ok=True)
    
    cases_def = generate_all_cases()
    print(f"[build_sembench] Generated {len(cases_def)} case definitions")
    
    subjects = {s.key: s for s in get_subjects()}
    
    records = []
    manifest_lines = []
    
    stats_preserving = 0
    stats_changing = 0
    stats_validation: dict[str, int] = {
        "VALIDATED_BY_ORACLE_AND_ARGUMENT": 0,
        "ORACLE_DISAGREES": 0,
        "ORACLE_ABSTAINS": 0,
        "ARGUMENT_ONLY": 0,
    }
    categories_count: dict[str, dict[str, int]] = {}

    for cdef in cases_def:
        case_dir = CASES_DIR / cdef.id
        case_dir.mkdir(parents=True, exist_ok=True)
        
        orig_file = case_dir / "original.jcl"
        trans_file = case_dir / "transformed.jcl"
        
        orig_file.write_text(cdef.original_text)
        trans_file.write_text(cdef.transformed_text)
        
        orig_sha = hashlib.sha256(cdef.original_text.encode("utf-8")).hexdigest()
        trans_sha = hashlib.sha256(cdef.transformed_text.encode("utf-8")).hexdigest()
        
        manifest_lines.append(f"{orig_sha}  cases/{cdef.id}/original.jcl")
        manifest_lines.append(f"{trans_sha}  cases/{cdef.id}/transformed.jcl")
        
        proclib = None
        cobol_sources = None
        if cdef.source.startswith("corpus:"):
            for skey, sub in subjects.items():
                if skey in cdef.source:
                    proclib = sub.proclib
                    cobol_sources = sub.cobol_sources
                    break
                    
        # Run Oracle
        verdict = compare_versions(
            cdef.original_text,
            cdef.transformed_text,
            proclib=proclib,
            cobol_sources=cobol_sources,
            scenario_set="full",
        )
        
        agrees = False
        if cdef.expected_outcome == "PRESERVING" and verdict.label == "EQUIVALENT":
            agrees = True
        elif cdef.expected_outcome == "CHANGING" and verdict.label == "DIFFERENT":
            agrees = True
            
        if verdict.label == "UNDETERMINED":
            validation_status = "ORACLE_ABSTAINS"
        elif agrees:
            validation_status = "VALIDATED_BY_ORACLE_AND_ARGUMENT"
        else:
            validation_status = "ORACLE_DISAGREES"
            
        if cdef.override_confidence:
            confidence = cdef.override_confidence
        elif verdict.label in ("EQUIVALENT", "DIFFERENT") and verdict.scenarios_checked > 0 and not verdict.opaque_touched:
            confidence = "HIGH"
        elif verdict.label == "UNDETERMINED" or verdict.opaque_touched:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"
            
        record = {
            "id": cdef.id,
            "base_id": cdef.base_id,
            "source": cdef.source,
            "category": cdef.category,
            "subcategory": cdef.subcategory,
            "expected_outcome": cdef.expected_outcome,
            "original_sha256": orig_sha,
            "transformed_sha256": trans_sha,
            "relevant_jcl_semantics": cdef.relevant_jcl_semantics,
            "rationale": cdef.rationale,
            "equivalence_argument": cdef.equivalence_argument,
            "oracle_verdict": verdict.to_dict(),
            "oracle_agrees_with_expected": agrees,
            "oracle_confidence": confidence,
            "independent_review_status": "PENDING",
            "validation_status": validation_status,
        }
        records.append(record)
        
        if cdef.expected_outcome == "PRESERVING":
            stats_preserving += 1
        else:
            stats_changing += 1
            
        stats_validation[validation_status] += 1
        
        cat_stats = categories_count.setdefault(cdef.category, {"total": 0, "PRESERVING": 0, "CHANGING": 0})
        cat_stats["total"] += 1
        cat_stats[cdef.expected_outcome] += 1

    # Write cases.jsonl
    jsonl_path = SEMBENCH_DIR / "cases.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"[build_sembench] Wrote {len(records)} records to {jsonl_path}")

    # Write MANIFEST.sha256
    manifest_lines.sort()
    manifest_path = SEMBENCH_DIR / "MANIFEST.sha256"
    manifest_path.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
    print(f"[build_sembench] Wrote SHA-256 manifest to {manifest_path}")

    # Write oracle_validation.json
    summary = {
        "total_pairs": len(records),
        "preserving_count": stats_preserving,
        "changing_count": stats_changing,
        "validation_status_counts": stats_validation,
        "category_counts": categories_count,
        "disagreements": [
            {
                "id": r["id"],
                "category": r["category"],
                "expected": r["expected_outcome"],
                "oracle_label": r["oracle_verdict"]["label"],
                "reason": r["equivalence_argument"]
            }
            for r in records if r["validation_status"] == "ORACLE_DISAGREES"
        ]
    }
    val_json_path = SEMBENCH_DIR / "oracle_validation.json"
    with open(val_json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"[build_sembench] Wrote validation summary to {val_json_path}")


if __name__ == "__main__":
    build_sembench()
