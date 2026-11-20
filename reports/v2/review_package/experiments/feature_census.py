"""
Read-only census of JCL features in the 121 evaluation-unit files (files with a JOB statement)
and of the oracle/RELIC-parser statement gap.  Output: feature_census_results.json + stdout.
Run: cd RELIC && PYTHONPATH=$PWD/src:$PWD .venv/bin/python reports/v2/review_package/experiments/feature_census.py
"""
import json, re, collections
from pathlib import Path
from jcl_oracle.lexer import lex, parse_operands
from jcl_oracle.model import build_model
from legacy_contract.parsers.jcl_parser import JCLParser
from relic_eval.subjects import get_subjects

OUT = Path(__file__).with_name("feature_census_results.json")
feat = collections.defaultdict(set)   # feature -> set(files)
cnt = collections.Counter()
gap = collections.Counter()
gap_ex = []
for subj in get_subjects():
    for f in subj.jcl_files:
        t = f.read_text(errors="replace"); rel = subj.key + "/" + subj.rel(f)
        lines = t.splitlines()
        U = t.upper()
        st = lex(t)
        S = [s for s in st if s.kind == "STMT"]
        def add(k, cond=True):
            if cond: feat[k].add(rel)
        add("continuation_lines(>=1 operand ends with comma)", any(s.last_line > s.first_line and s.op in {"EXEC","DD","JOB"} for s in S))
        add("tab_character", "\t" in t)
        add("lowercase_in_statement", any(l.startswith("//") and not l.startswith("//*") and re.search(r"[a-z]", l[:71]) for l in lines))
        add("text_in_cols_73_80", any(l.startswith("//") and len(l.rstrip()) > 72 for l in lines))
        add("line_gt_80", any(len(l) > 80 for l in lines))
        add("instream_DD_star_or_DATA", any(s.op == "DD" and s.data for s in S))
        add("DLM=", "DLM=" in U)
        add("DISP_omitted_status (,CATLG..)", bool(re.search(r"DISP=\(\s*,", U)))
        add("DD_with_DSN_but_no_DISP", any(s.op == "DD" and (lambda kw: ("DSN" in kw or "DSNAME" in kw) and "DISP" not in kw)(parse_operands(s.operands)[1]) for s in S))
        add("DSNAME=", "DSNAME=" in U)
        add("COND=_on_EXEC", any(s.op == "EXEC" and "COND=" in s.operands.upper() for s in S))
        add("COND=EVEN/ONLY", bool(re.search(r"COND=\(?(EVEN|ONLY)|,\s*(EVEN|ONLY)\)", U)))
        add("COND_multi_test", bool(re.search(r"COND=\(\(", U)))
        add("COND_with_stepname", bool(re.search(r"COND=\(?\(?\d+,\s*[A-Z]{2},\s*[A-Z0-9@#$]+", U)))
        add("COND.procstep=", bool(re.search(r"COND\.[A-Z0-9@#$]+=", U)))
        add("JOB_COND", any(s.op == "JOB" and "COND=" in s.operands.upper() for s in S))
        add("IF/THEN", any(s.op == "IF" for s in S))
        add("ELSE", any(s.op == "ELSE" for s in S))
        add("PROC_instream", any(s.op == "PROC" for s in S))
        add("EXEC_PROC_or_positional", any(s.op == "EXEC" and "PGM=" not in s.operands.upper() for s in S))
        add("INCLUDE", any(s.op == "INCLUDE" for s in S))
        add("JCLLIB", any(s.op == "JCLLIB" for s in S))
        add("SET_symbolic", any(s.op == "SET" for s in S))
        add("symbolic_&NAME_in_operands", bool(re.search(r"(?<!&)&[A-Z@#$][A-Z0-9@#$]{0,7}", "\n".join(s.operands.upper() for s in S))))
        add("temp_dataset_&&", "&&" in U)
        add("GDG_(+1)/(0)/(-1)", bool(re.search(r"\([+-]?\d\)", U)) and bool(re.search(r"DSN=[^,\s]*\([+-]?\d+\)", U)))
        add("MOD,DELETE", bool(re.search(r"DISP=\(MOD,\s*DELETE", U)))
        add("DISP=OLD,DELETE", bool(re.search(r"DISP=\(OLD,\s*DELETE", U)))
        add("DISP_PASS", "PASS" in U)
        add("DD_concatenation(unnamed DD)", any(s.op == "DD" and not s.name for s in S))
        add("DD_DUMMY/NULLFILE", "DUMMY" in U or "NULLFILE" in U)
        add("DD_referback(*.)", "DSN=*." in U or "=*." in U)
        add("stepname.ddname_override", any(s.op == "DD" and "." in s.name for s in S))
        add("unnamed_step", any(s.op == "EXEC" and not s.name for s in S))
        names = [s.name for s in S if s.op == "EXEC" and s.name]
        add("duplicate_step_names", len(names) != len(set(names)))
        add("multiple_JOB_cards", sum(1 for s in S if s.op == "JOB") > 1)
        pgms = set()
        for s in S:
            if s.op == "EXEC":
                m = re.search(r"PGM=([A-Z0-9@#$*.]+)", s.operands.upper())
                if m: pgms.add(m.group(1))
        for p in pgms:
            add("PGM=" + (p if p in {"IDCAMS","IEFBR14","SORT","IEBGENER","IKJEFT01","IKJEFT1B","IGYCRCTL","IEWL","DFSRRC00","IEBCOPY","ICETOOL","ICEGENER","IEBUPDTE","FTP","IRXJCL","BPXBATCH","DSNUTILB","IEFBR14"} else "OTHER_USER_PGM"))
        # statement gap oracle vs RELIC default parser
        res, ir = JCLParser().parse_lines(lines, rel)
        rk = {t.line_number for t in res.tokens}
        for s in S:
            if s.op in {"EXEC","DD","JOB"} and (s.first_line + 1) not in rk:
                gap[(s.op, "stepname.ddname" if "." in s.name else "other")] += 1
                if "." not in s.name and len(gap_ex) < 10:
                    gap_ex.append((rel, s.first_line + 1, s.op, s.name))
print("files:", len({r for v in feat.values() for r in v} | set()), "(feature-carrying)")
rows = {k: len(v) for k, v in sorted(feat.items())}
for k, v in rows.items(): print(f"{v:4d}  {k}")
print("statement gap oracle-only (default parser):", dict(gap), gap_ex)
OUT.write_text(json.dumps(dict(file_counts=rows, gap={f"{a}|{b}": n for (a, b), n in gap.items()}, gap_other_examples=gap_ex,
                               files_by_feature={k: sorted(v) for k, v in feat.items() if k in {"duplicate_step_names","multiple_JOB_cards","stepname.ddname_override","IF/THEN","PROC_instream","INCLUDE","COND=EVEN/ONLY","MOD,DELETE","DSNAME=","DD_with_DSN_but_no_DISP","JOB_COND"}}), indent=1))
