"""
Build the independent-review sample (INTERNAL tool - do not give to reviewers).

Deterministic: fixed SEED, fixed cell quotas, candidates sorted by mutation_id before
sampling.  Re-running reproduces KEY_DO_NOT_SHARE.csv, blind_review_form.csv, cards/ byte for byte.

Inputs (read-only):
  results/final/raw/evaluation_records.jsonl          (oracle labels, RELIC predictions, diffs)
  experiments/mutant_crosscheck_results.json          (failure-injection tier per mutant)
  experiments/split_job_sensitivity_results.json      (tier with job names/count stripped)
  experiments/feature_census_results.json             (D-004 / duplicate-step file lists)
  relic_eval.mutate.generate (deterministic)          (mutant text; diff in the record is only n=1 context)

Outputs (in this directory):
  KEY_DO_NOT_SHARE.csv      oracle label, categories, evidence, RELIC predictions, operator, tier, flags
  blind_review_form.csv     case_id/subject/file/card + EMPTY response columns (no labels, no predictions)
  cards/Rxxx.md             blind, self-contained review cards;  cards.jsonl  (same content, machine readable)
  sampling_frame.json       population counts per sampling cell (no per-case labels)

Run: cd RELIC && PYTHONPATH=$PWD/src:$PWD .venv/bin/python reports/v2/review_package/make_sample.py
"""
from __future__ import annotations

import csv
import difflib
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

from relic_eval.mutate import generate
from relic_eval.subjects import SUBJECTS

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SEED = 20251120                       # documented in INDEPENDENT_REVIEW_PACKAGE.md
EXP = HERE / "experiments"

# (label, operator, subject, n, [(hard_pool, k), ...]) -- hard picks are drawn first, rest uniformly.
CELLS = [
    ("EQUIVALENT", "INSERT_COMMENT",  "carddemo",   5, [("H_D004", 2)]),
    ("EQUIVALENT", "INSERT_COMMENT",  "genapp",     4, [("H_DUP", 2)]),
    ("EQUIVALENT", "INSERT_COMMENT",  "omp_course", 5, []),
    ("EQUIVALENT", "CHANGE_MSGCLASS", "carddemo",   7, [("H_D004", 2)]),
    ("EQUIVALENT", "CHANGE_MSGCLASS", "genapp",     7, [("H_DUP", 2)]),
    ("DIFFERENT",  "SWAP_ADJACENT_STEPS", "carddemo",   2, [("H_ABEND", 1)]),
    ("DIFFERENT",  "SWAP_ADJACENT_STEPS", "genapp",     3, [("H_ABEND", 1), ("H_DUP", 1)]),
    ("DIFFERENT",  "SWAP_ADJACENT_STEPS", "omp_course", 2, [("H_ABEND", 1)]),
    ("DIFFERENT",  "SPLIT_JOB", "carddemo",   2, [("H_D004", 1)]),
    ("DIFFERENT",  "SPLIT_JOB", "genapp",     3, [("H_DUP", 1)]),
    ("DIFFERENT",  "SPLIT_JOB", "omp_course", 1, []),
    ("DIFFERENT",  "DELETE_PRODUCER_STEP", "carddemo", 3, [("H_D004", 1)]),
    ("DIFFERENT",  "DELETE_PRODUCER_STEP", "genapp",   1, []),
    ("DIFFERENT",  "RENAME_OUTPUT_DATASET", "carddemo", 3, [("ANCHOR_D004", 2)]),
    ("DIFFERENT",  "RENAME_OUTPUT_DATASET", "genapp",   1, []),
    ("DIFFERENT",  "MOVE_CONSUMER_BEFORE_PRODUCER", "carddemo", 2, []),
    ("DIFFERENT",  "MOVE_CONSUMER_BEFORE_PRODUCER", "genapp",   1, []),
    ("DIFFERENT",  "REMOVE_COND", "carddemo",   1, []),
    ("DIFFERENT",  "REMOVE_COND", "genapp",     1, [("H_DUP", 1)]),
    ("DIFFERENT",  "REMOVE_COND", "omp_course", 1, []),
    ("DIFFERENT",  "ALTER_COND_THRESHOLD", "carddemo",   1, []),
    ("DIFFERENT",  "ALTER_COND_THRESHOLD", "genapp",     1, [("H_DUP", 1)]),
    ("DIFFERENT",  "ALTER_COND_THRESHOLD", "omp_course", 1, []),
]
# Mandatory anchors, always included (certainty items).
ANCHOR_IDS = [
    "carddemo/app/jcl/TXT2PDF1.JCL/ALTER_COND_THRESHOLD/0",   # EQUIVALENT COND edit (single-step job)
    "carddemo/app/jcl/TXT2PDF1.JCL/REMOVE_COND/0",            # EQUIVALENT COND edit (single-step job)
]
ANCHOR_D004 = [
    "carddemo/app/jcl/ESDSRRDS.jcl/RENAME_OUTPUT_DATASET/0",  # D-004 trade-off items
    "carddemo/app/jcl/DUSRSECJ.jcl/RENAME_OUTPUT_DATASET/0",
]


def load():
    recs = [json.loads(l) for l in open(ROOT / "results/final/raw/evaluation_records.jsonl")]
    ev = {r["mutation_id"]: r for r in recs if r["status"] == "EVALUABLE"}
    tier = json.load(open(EXP / "mutant_crosscheck_results.json"))
    tier2 = json.load(open(EXP / "split_job_sensitivity_results.json"))
    fb = json.load(open(EXP / "feature_census_results.json"))["files_by_feature"]
    return recs, ev, tier, tier2, set(fb["duplicate_step_names"]), set(fb["MOD,DELETE"])


def flags_for(r, tier, dup, d4):
    key = r["subject_system"] + "/" + r["file"]
    f = set()
    if r["oracle_result"] == "DIFFERENT" and r["oracle_result_no_abend"] != "DIFFERENT":
        f.add("H_ABEND")            # positive only when a step abends (no_abend: EQUIVALENT or UNDETERMINED)
    if key in dup:
        f.add("H_DUP")
    if key in d4:
        f.add("H_D004")
    if r["mutation_id"] in ANCHOR_D004:
        f.add("ANCHOR_D004")
    return f


def build_selection(ev, tier, dup, d4):
    rng = random.Random(SEED)
    chosen: dict[str, tuple[str, str]] = {}      # mid -> (cell, reason)
    for mid in ANCHOR_IDS:
        chosen[mid] = ("ANCHOR", "anchor")
    frame = {}
    for (label, op, subj, n, hards) in CELLS:
        pool = sorted(m for m, r in ev.items() if r["oracle_result"] == label
                      and r["mutation_type"] == op and r["subject_system"] == subj)
        cell = f"{label}|{op}|{subj}"
        frame[cell] = {"population": len(pool), "quota": n}
        picked = [m for m in pool if m in chosen]
        for pname, k in hards:
            hp = [m for m in pool if pname in flags_for(ev[m], tier, dup, d4) and m not in chosen]
            take = rng.sample(hp, min(k, len(hp)))
            for m in take:
                chosen[m] = (cell, pname)
                picked.append(m)
        rest = [m for m in pool if m not in chosen]
        need = n - len(picked)
        if need > len(rest):
            raise SystemExit(f"cell {cell} too small: need {need}, have {len(rest)}")
        for m in rng.sample(rest, need):
            chosen[m] = (cell, "random")
    # anchors do not belong to a CELLS row for COND edits: make sure counts are right
    return chosen, frame


# ---------------------------------------------------------------------------------------
# procedure sources (so a card is self-contained when a step invokes a corpus PROC)
# ---------------------------------------------------------------------------------------
def proc_index(subject):
    idx = {}
    for p in subject._all_files({".prc", ".proc", ".jcl"}):
        t = p.read_text(errors="replace")
        if re.search(r"^//\S*\s+JOB\b", t, re.M):
            continue
        for m in re.finditer(r"^//(\S*)\s+PROC\b", t, re.M):
            if m.group(1):
                idx.setdefault(m.group(1).upper(), (subject.rel(p), t))
        idx.setdefault(p.stem.upper(), (subject.rel(p), t))
    return idx


def referenced_procs(text, idx):
    out = {}
    for m in re.finditer(r"^//\S*\s+EXEC\s+(?:PROC=)?([A-Z0-9@#$]+)\s*(?:,|$|\s)", text, re.M | re.I):
        nm = m.group(1).upper()
        if nm.startswith("PGM"):
            continue
        if nm in idx:
            out[nm] = idx[nm]
    return out


def numbered(text):
    return "\n".join(f"{i:4d}| {l}" for i, l in enumerate(text.splitlines(), 1))


CARD_QUESTION = """\
## Questions (answer in `blind_review_form.csv`, one row per case)

1. **Q1 - normal completion.** Assume every step ends with return code 0 and nothing abends.
   Is the modified job's externally observable behaviour the same as the original's?
   `SAME` / `DIFFERENT` / `CANNOT_DETERMINE`
2. **Q2 - failure scenarios.** Now consider any single step ending with a non-zero return code
   or abending (what runs, what is bypassed, which datasets exist afterwards, which data each step reads).
   Is the behaviour the same in *every* such scenario?
   `SAME` / `DIFFERENT` / `CANNOT_DETERMINE`
3. **overall_label.** `EQUIVALENT` only if Q1 and Q2 are both SAME; `DIFFERENT` if either is DIFFERENT;
   otherwise `CANNOT_DETERMINE`.
4. `confidence` 1 (low) - 3 (high); `evidence` one or two sentences naming the step/DD/line that decides it.

Definitions, what counts as observable, and what to assume about unknown programs are in `RUBRIC.md`.
Do not consult anyone else about this case until all reviewers have submitted.
"""


def make_card(cid, r, orig, mut, subject, pidx):
    a, b = orig.splitlines(keepends=True), mut.splitlines(keepends=True)
    diff = "".join(difflib.unified_diff(a, b, fromfile=f"a/{r['file']}", tofile=f"b/{r['file']}", n=6))
    procs = referenced_procs(orig, pidx)
    md = [f"# Review card {cid}", "",
          f"* subject corpus: `{r['subject_system']}`",
          f"* file: `{r['file']}`", "",
          "Compare the **original** job with the **modified** job. The modification is shown as a unified diff; "
          "both full texts follow. Program sources (COBOL etc.) are not included unless stated; "
          "if the answer depends on what an unknown program does, say so.", "",
          "## Unified diff (original -> modified)", "", "```diff", diff.rstrip("\n"), "```", ""]
    if procs:
        md += ["## Procedures referenced by the original job (from the same corpus)", ""]
        for nm, (rel, t) in sorted(procs.items()):
            md += [f"### {nm}  (`{rel}`)", "", "```", t.rstrip("\n"), "```", ""]
    md += ["## Original job (line-numbered)", "", "```", numbered(orig), "```", "",
           "## Modified job (line-numbered)", "", "```", numbered(mut), "```", "", CARD_QUESTION]
    return "\n".join(md) + "\n", diff, sorted(procs)


def main():
    recs, ev, tier, tier2, dup, d4 = load()
    chosen, frame = build_selection(ev, tier, dup, d4)
    assert len(chosen) == sum(c[3] for c in CELLS) + len(ANCHOR_IDS), len(chosen)
    # regenerate mutant text deterministically
    texts = {}
    need_files = {(ev[m]["subject_system"], ev[m]["file"]) for m in chosen}
    for subj_key, rel in sorted(need_files):
        s = SUBJECTS[subj_key]
        orig = (s.root / rel).read_text(errors="replace")
        idx = Counter()
        for mu in generate(orig):
            i = idx[mu.operator]; idx[mu.operator] += 1
            mid = f"{subj_key}/{rel}/{mu.operator}/{i}"
            if mid in chosen:
                texts[mid] = (orig, mu.text)
    assert set(texts) == set(chosen), set(chosen) - set(texts)

    order = sorted(chosen)
    random.Random(SEED + 1).shuffle(order)                 # presentation order: shuffled
    pidx_cache = {k: proc_index(SUBJECTS[k]) for k in {ev[m]["subject_system"] for m in chosen}}
    (HERE / "cards").mkdir(exist_ok=True)
    key_rows, form_rows, cards_jsonl = [], [], []
    for n, mid in enumerate(order, 1):
        cid = f"R{n:03d}"
        r = ev[mid]
        orig, mut = texts[mid]
        md, diff, procs = make_card(cid, r, orig, mut, SUBJECTS[r["subject_system"]], pidx_cache[r["subject_system"]])
        (HERE / "cards" / f"{cid}.md").write_text(md)
        cards_jsonl.append({"case_id": cid, "subject": r["subject_system"], "file": r["file"],
                            "diff": diff, "original": orig, "modified": mut, "procedures": procs})
        fl = flags_for(r, tier, dup, d4)
        o = r["oracle"]
        key_rows.append({
            "case_id": cid, "mutation_id": mid, "subject": r["subject_system"], "file": r["file"],
            "operator": r["mutation_type"], "site": r["site"],
            "sampling_cell": chosen[mid][0], "selection_reason": chosen[mid][1],
            "hard_flags": ";".join(sorted(fl)),
            "oracle_label": r["oracle_result"], "oracle_label_no_abend": r["oracle_result_no_abend"],
            "oracle_tier": tier.get(mid, {}).get("tier") or "EQUIVALENT",
            "oracle_tier_jobname_stripped": tier2.get(mid, "EQUIVALENT"),
            "oracle_categories": ";".join(o["categories"]),
            "oracle_evidence": " || ".join(o["evidence"][:2]),
            "oracle_scenarios_checked": o["scenarios_checked"], "oracle_differing_scenarios": o["differing_scenarios"],
            "relic_v1_0_flagged": r["predictions"].get("relic_v1_0"),
            "relic_v1_1_flagged": r["predictions"].get("relic_v1_1"),
            "textdiff_flagged": r["predictions"].get("textdiff"),
        })
        form_rows.append({"case_id": cid, "subject": r["subject_system"], "file": r["file"],
                          "card": f"cards/{cid}.md", "reviewer_id": "", "q1_normal_completion": "",
                          "q2_failure_scenarios": "", "overall_label": "", "confidence": "",
                          "evidence": "", "minutes_spent": ""})
    key_rows.sort(key=lambda x: x["case_id"]); form_rows.sort(key=lambda x: x["case_id"])
    with open(HERE / "KEY_DO_NOT_SHARE.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(key_rows[0])); w.writeheader(); w.writerows(key_rows)
    with open(HERE / "blind_review_form.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(form_rows[0])); w.writeheader(); w.writerows(form_rows)
    with open(HERE / "cards.jsonl", "w") as fh:
        for c in cards_jsonl:
            fh.write(json.dumps(c, sort_keys=True) + "\n")
    json.dump({"seed": SEED, "cells": frame,
               "population_evaluable": len(ev),
               "population_by_label": dict(Counter(r["oracle_result"] for r in ev.values()))},
              open(HERE / "sampling_frame.json", "w"), indent=1, sort_keys=True)

    # --- leak check: reviewer-facing files must not contain oracle / RELIC / operator vocabulary ---
    banned = re.compile(r"oracle|RELIC|DIFFERENT_BY|SWAP_ADJACENT|SPLIT_JOB|DELETE_PRODUCER|RENAME_OUTPUT|"
                        r"MOVE_CONSUMER|REMOVE_COND|ALTER_COND|INSERT_COMMENT|CHANGE_MSGCLASS|EVALUABLE", re.I)
    bad = []
    for p in list((HERE / "cards").glob("*.md")) + [HERE / "blind_review_form.csv"]:
        t = p.read_text()
        # the original corpus text is allowed to contain arbitrary words; check only our own wrapper text
        wrapper = re.sub(r"```.*?```", "", t, flags=re.S) if p.suffix == ".md" else t
        if banned.search(wrapper):
            bad.append(p.name)
    assert not bad, f"leak check failed: {bad}"
    print(f"{len(chosen)} cases; labels:", dict(Counter(k['oracle_label'] for k in key_rows)))
    print("by subject:", dict(Counter(k['subject'] for k in key_rows)))
    print("by operator:", dict(Counter(k['operator'] for k in key_rows)))
    print("tiers (DIFFERENT only):", dict(Counter(k['oracle_tier'] for k in key_rows if k['oracle_label'] == 'DIFFERENT')))
    print("hard flags:", dict(Counter(f for k in key_rows for f in k['hard_flags'].split(';') if f)))


if __name__ == "__main__":
    main()
