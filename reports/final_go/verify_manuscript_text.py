"""Check that numbers printed in paper/RELIC_V2_PUBLICATION_FINAL/main.tex match the JSON outputs.
Rounding is half-up on the JSON value (JSON holds 4 decimals; e.g. 0.4875 -> 0.488, as in the paper).
Exit 1 on any mismatch. Run: python3 reports/final_go/verify_manuscript_text.py
"""
import json, os, sys
from decimal import Decimal, ROUND_HALF_UP
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
tex = open(os.path.join(ROOT, "paper/RELIC_V2_PUBLICATION_FINAL/main.tex"), encoding="utf-8").read()
boot = json.load(open(os.path.join(ROOT, "results/final_go/bootstrap_original_method.json")))
rob = json.load(open(os.path.join(ROOT, "results/final/statistics/robustness_checks.json")))
lb = json.load(open(os.path.join(ROOT, "results/final_go/llm_bounds_dedup_loo.json")))
fails = []
def r3(x):
    return str(Decimal(str(x)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))
def m(x):  # math-mode signed number as written in the table
    v = r3(x); return f"$-{v[1:]}$" if v.startswith("-") else v
import re
TRIPLE = re.compile(r"(-?\d\.\d{3}) \[(-?\d\.\d{3}), (-?\d\.\d{3})\]")
def need_triple(point, lo, hi, why):
    """Accept any printed 'x [a, b]' whose three numbers are within 0.0006 of the JSON values (tie-safe)."""
    for mt in TRIPLE.finditer(tex):
        vals = [float(v) for v in mt.groups()]
        if all(abs(v - w) <= 0.0006 for v, w in zip(vals, (point, lo, hi))): return
    fails.append(f"no printed interval matches JSON {point} [{lo}, {hi}] ({why})")
def need(s, why):
    if s not in tex: fails.append(f"MISSING in main.tex: {s!r} ({why})")
for L in ["L0", "L1", "L2", "L3"]:
    for det in ["relic_v2", "normalized_text_B"]:
        d = boot[L][det]
        need_triple(d['mcc_point'], d['mcc_ci95'][0], d['mcc_ci95'][1], f"{L} {det}")
    dl = boot[L]["delta_relic_minus_textB"]
    need(f"{m(dl['point'])} [{m(dl['ci95'][0])}, {m(dl['ci95'][1])}]", f"{L} delta")
for L, lab in [("L0", "0.015"), ("L1", "0.002"), ("L2", "0.010"), ("L3", "0.089")]:
    p = rob["cluster_swap"][L]["p_two_sided_exact"]
    if r3(p) != lab: fails.append(f"p-value {L}: JSON {p} -> {r3(p)} vs manuscript {lab}")
    need(f"p=${lab}$" if False else f"$p={lab}$", f"{L} exact p")
gaps = [boot[L]["delta_relic_minus_textB"]["point"] for L in ["L0", "L1", "L2", "L3"]]
if not (r3(max(gaps)) == "-0.170" and r3(min(gaps)) == "-0.336"):
    fails.append(f"gap extremes from JSON {r3(max(gaps))} {r3(min(gaps))}")
need("$-0.17$ to $-0.34$", "abstract gap range (rounded to two decimals)")
need(m(lb["dedup_L1_gap"]), "deduplicated L1 gap")
if r3(lb["dedup_L1_gap"]) != "-0.338": fails.append("dedup gap differs from JSON")
lo = lb["leave_one_program_out_L1"]
need(f"{m(lo['min'])} to {m(lo['max'])}", "leave-one-program-out range")
if r3(lo["min"]) != "-0.364" or r3(lo["max"]) != "-0.313": fails.append("leave-one-out range differs from JSON")
need(r3(lb["llm_worst_L1"]), "worst-case LLM MCC in limitations")
need(r3(lb["text_B_L1_180"]), "text B L1 MCC in limitations")
need("55 of the 78", "RELIC misses on L1")
print("failures:", len(fails))
for f in fails: print("FAIL", f)
sys.exit(1 if fails else 0)
