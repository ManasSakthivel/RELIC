"""
Read-only experiment on every regenerated mutant (relic_eval.mutate.generate is deterministic):

 (a) lexer cross-check on MUTANT text: ordered EXEC-name sequence and DD-statement count as
     seen by the oracle lexer (shared with the mutator) vs RELIC's parser (independent code);
 (b) 'failure-injection tier' of every oracle DIFFERENT label, recomputed with the public
     oracle classes (no code modified):
        T0_BASELINE   differs already with no injected failure (Scenario())
        T1_RC_ONLY    not at baseline; differs when some step ends with an injected RC (no abend)
        T2_ABEND_ONLY differs only when a step abends (oracle_result_no_abend != DIFFERENT)
 (c) mutant-vs-original expected-structure check for SWAP / DELETE / SPLIT / negatives using
     RELIC's tokens (independent of the mutator's block model).

Output: mutant_crosscheck_results.json (per mutation_id) + stdout summary.
Run: cd RELIC && PYTHONPATH=$PWD/src:$PWD .venv/bin/python reports/v2/review_package/experiments/mutant_crosscheck.py
"""
import json, collections
from pathlib import Path
from jcl_oracle.lexer import lex
from jcl_oracle.model import build_model
from jcl_oracle.simulate import Scenario, Simulator, first_access_creates
from legacy_contract.parsers.jcl_parser import JCLParser
from relic_eval.mutate import generate
from relic_eval.subjects import get_subjects

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).with_name("mutant_crosscheck_results.json")
REC = {json.loads(l)["mutation_id"]: json.loads(l) for l in open(ROOT / "results/final/raw/evaluation_records.jsonl")}


def o_seq(text):
    S = [s for s in lex(text) if s.kind == "STMT"]
    return [s.name.upper() or "#" for s in S if s.op == "EXEC"], sum(1 for s in S if s.op == "DD"), sum(1 for s in S if s.op == "JOB")


def r_seq(text, rel):
    res, _ = JCLParser().parse_lines(text.splitlines(), rel)
    t = res.tokens
    return [x.name.upper() or "#" for x in t if x.operation == "EXEC"], sum(1 for x in t if x.operation == "DD"), sum(1 for x in t if x.operation == "JOB")


def baseline_differs(orig, mut, proclib, cobol):
    m1, m2 = build_model(orig, proclib), build_model(mut, proclib)
    init = first_access_creates(m1, cobol)
    for k, v in first_access_creates(m2, cobol).items():
        init.setdefault(k, v)
    s1, s2 = Simulator(m1, cobol, init), Simulator(m2, cobol, init)
    return s1.behaviors(Scenario()) != s2.behaviors(Scenario())


stats = collections.Counter(); out = {}; ex = []
for subj in get_subjects():
    for f in subj.jcl_files:
        orig = f.read_text(errors="replace"); rel = subj.rel(f)
        oe, od, oj = o_seq(orig)
        re_, rd, rj = r_seq(orig, subj.artifact_path(f))
        idx = collections.Counter()
        for mu in generate(orig):
            i = idx[mu.operator]; idx[mu.operator] += 1
            mid = f"{subj.key}/{rel}/{mu.operator}/{i}"
            rec = REC.get(mid)
            if rec is None or mu.text is None or rec["status"] not in ("EVALUABLE", "OUT_OF_SCOPE"):
                continue
            me, md, mj = o_seq(mu.text)
            rme, rmd, rmj = r_seq(mu.text, subj.artifact_path(f))
            stats["mutants"] += 1
            stats["lexer_exec_seq_agree"] += int(me == rme)
            stats["lexer_dd_count_agree"] += int(md == rmd)
            stats["lexer_job_count_agree"] += int(mj == rmj)
            if me != rme and len(ex) < 8:
                ex.append((mid, me[:6], rme[:6]))
            # structure expectations from RELIC's tokens
            ok = None
            if mu.operator == "SWAP_ADJACENT_STEPS":
                diff = [k for k in range(len(rme)) if k < len(re_) and rme[k] != re_[k]]
                ok = (sorted(rme) == sorted(re_)) and (len(diff) in (2, 0))
            elif mu.operator == "DELETE_PRODUCER_STEP":
                ok = len(rme) == len(re_) - 1
            elif mu.operator in ("SPLIT_JOB",):
                ok = (rmj == rj + 1) if rj else None
            elif mu.operator in ("INSERT_COMMENT", "CHANGE_MSGCLASS", "REMOVE_COND", "ALTER_COND_THRESHOLD", "RENAME_OUTPUT_DATASET", "MOVE_CONSUMER_BEFORE_PRODUCER"):
                ok = (len(rme) == len(re_)) and (rmd == rd)
            if ok is not None:
                stats["struct_checked"] += 1; stats["struct_ok"] += int(ok)
                if not ok and len(ex) < 16:
                    ex.append(("STRUCT", mid, len(re_), len(rme), rj, rmj))
            tier = None
            if rec["oracle_result"] == "DIFFERENT":
                try:
                    if baseline_differs(orig, mu.text, subj.proclib, subj.cobol_sources):
                        tier = "T0_BASELINE"
                    elif rec["oracle_result_no_abend"] == "DIFFERENT":
                        tier = "T1_RC_ONLY"
                    else:
                        tier = "T2_ABEND_ONLY"
                except Exception as e:
                    tier = "ERR"
                stats[tier] += 1
                stats[("tier_by_op", mu.operator, tier)] += 1
            out[mid] = dict(tier=tier, mut_exec_agree=me == rme)
OUT.write_text(json.dumps(out, indent=0))
print({str(k): v for k, v in sorted(stats.items(), key=str)})
print(ex)
