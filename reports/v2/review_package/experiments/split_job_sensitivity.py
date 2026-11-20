"""
Read-only sensitivity experiment: the oracle's 'termination' observable is
tuple(sorted((job.name,)+reason)) per job (jcl_oracle/simulate.py:316), so a mutant with an
extra JOB card differs from its original in the 'baseline' scenario *by construction*.
Recompute oracle labels / failure-injection tiers with job NAMES and the NUMBER of jobs stripped
from the termination observable (only non-OK termination reasons kept), using only public oracle classes.

Output: split_job_sensitivity_results.json + stdout.
Run: cd RELIC && PYTHONPATH=$PWD/src:$PWD .venv/bin/python reports/v2/review_package/experiments/split_job_sensitivity.py
"""
import json, collections
from pathlib import Path
from jcl_oracle.model import build_model
from jcl_oracle.judge import _scenarios
from jcl_oracle.simulate import Scenario, Simulator, first_access_creates, ABEND
from relic_eval.mutate import generate
from relic_eval.subjects import get_subjects

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).with_name("split_job_sensitivity_results.json")
REC = {}
for l in open(ROOT / "results/final/raw/evaluation_records.jsonl"):
    r = json.loads(l); REC[r["mutation_id"]] = r


def reduce(bset):
    out = set()
    for b in bset:
        # drop job names AND the number of jobs: keep only the set of non-OK termination reasons
        term = frozenset(tuple(t[1:]) for t in b.termination if tuple(t[1:]) != ("OK",))
        out.add((b.steps, b.reads, b.final, term))
    return frozenset(out)


res = collections.Counter(); per = {}
for subj in get_subjects():
    for f in subj.jcl_files:
        orig = f.read_text(errors="replace"); rel = subj.rel(f)
        idx = collections.Counter(); m1 = None
        for mu in generate(orig):
            i = idx[mu.operator]; idx[mu.operator] += 1
            mid = f"{subj.key}/{rel}/{mu.operator}/{i}"
            rec = REC.get(mid)
            if rec is None or rec["status"] != "EVALUABLE" or rec["oracle_result"] != "DIFFERENT":
                continue
            m1 = build_model(orig, subj.proclib); m2 = build_model(mu.text, subj.proclib)
            init = first_access_creates(m1, subj.cobol_sources)
            for k, v in first_access_creates(m2, subj.cobol_sources).items():
                init.setdefault(k, v)
            s1, s2 = Simulator(m1, subj.cobol_sources, init), Simulator(m2, subj.cobol_sources, init)
            tier = None
            for sc in _scenarios(m1, m2, "full"):
                if reduce(s1.behaviors(sc)) != reduce(s2.behaviors(sc)):
                    kind = "T0_BASELINE" if sc.target is None else ("T2_ABEND_ONLY" if sc.value == ABEND else "T1_RC")
                    order = {"T0_BASELINE": 0, "T1_RC": 1, "T2_ABEND_ONLY": 2}
                    if tier is None or order[kind] < order[tier]:
                        tier = kind
                    if tier == "T0_BASELINE":
                        break
            tier = tier or "EQUIVALENT_after_stripping_job_names"
            res[(mu.operator, tier)] += 1; res[("ALL", tier)] += 1
            per[mid] = tier
OUT.write_text(json.dumps(per, indent=0))
for k, v in sorted(res.items()): print(k, v)
