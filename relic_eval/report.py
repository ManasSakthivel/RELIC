"""
Metrics, tables and generated documentation blocks.

``compute_all`` turns raw records into ``results/final/metrics.json``;
``write_all`` renders every table (Markdown + LaTeX) and rewrites the
generated blocks inside README.md, paper/paper.md and docs/*.md that are
delimited by

    <!-- BEGIN GENERATED:<name> -->  ...  <!-- END GENERATED:<name> -->

Text outside those markers is never touched. ``relic_eval.check_consistency``
verifies that every block equals a fresh rendering of metrics.json.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from relic_eval.metrics import cluster_bootstrap, confusion
from relic_eval.mutate import ALL_OPERATORS, NEGATIVE_OPERATORS
from relic_eval.pipeline import OUT, PRIMARY_DETECTOR, STATUSES
from relic_eval.subjects import ROOT, SUBJECTS

DETECTORS = ["relic_v1_0", "relic_v1_1", "static_bcg_E", "structural_A", "complexity_B", "textdiff"]
LLM_DETECTORS = ["llm_C", "llm_D"]
LLM_COMPARISON = ["llm_C", "llm_D", "relic_v1_0", "relic_v1_1", "structural_A", "textdiff"]
DETECTOR_LABELS = {
    "relic_v1_0": "RELIC v1.0.0 (as released; primary)",
    "relic_v1_1": "RELIC v1.1 (post-hoc spec fixes)",
    "static_bcg_E": "Baseline E: static BCG, broken-only",
    "structural_A": "Baseline A: structural edge diff",
    "complexity_B": "Baseline B: complexity score",
    "textdiff": "Reference: any non-comment text change",
    "llm_C": "Baseline C: LLM-only",
    "llm_D": "Baseline D: dependency + LLM",
}
POPULATIONS = ["carddemo", "omp_course", "genapp", "pooled"]
CONTRACT_TYPES = ["TEMPORAL", "RESOURCE", "CONTROL_FLOW", "NONE"]
TABLES_DIR = OUT / "tables"
TEX_DIR = ROOT / "paper" / "generated"


# ---------------------------------------------------------------------------
# Computation
# ---------------------------------------------------------------------------

def _pop(records: list[dict], pop: str) -> list[dict]:
    return records if pop == "pooled" else [r for r in records if r["subject_system"] == pop]


def _scored(records: list[dict], truth_key: str = "ground_truth") -> list[dict]:
    out = []
    for r in records:
        y = r.get(truth_key)
        if y is None:
            continue
        out.append({"truth": bool(y), "pred": r["predictions"], "cluster": f"{r['subject_system']}/{r['file']}",
                    "operator": r["mutation_type"], "ctype": r["contract_type"]})
    return out


def _detector_block(scored: list[dict], dets: list[str], missing: str = "negative") -> dict:
    return {d: confusion(scored, d, missing).as_dict() for d in dets}


def llm_section(records: list[dict], llm: dict) -> dict:
    # Failed / unanswered LLM calls are never scored. All detectors are compared on
    # the COMMON population: EVALUABLE mutants for which BOTH LLM baselines returned a
    # valid answer. Per-baseline results on that baseline's own answered set are
    # reported for completeness.
    llm_preds = llm.get("predictions", {})
    llm_res: dict = {"status": llm.get("status", {}), "results": {},
                     "comparison_detectors": LLM_COMPARISON}
    if any(v is not None for p in llm_preds.values() for v in p.values()):
        for pop in POPULATIONS:
            ev = [r for r in _pop(records, pop) if r["status"] == "EVALUABLE"]
            merged = [dict(r, predictions={**r["predictions"], **llm_preds.get(r["mutation_id"], {})})
                      for r in ev]
            answered = {d: sum(1 for r in merged if r["predictions"].get(d) is not None)
                        for d in LLM_DETECTORS}
            common = [r for r in merged if all(r["predictions"].get(d) is not None for d in LLM_DETECTORS)]
            scored_common = _scored(common)
            scored_all = _scored(merged)
            llm_res["results"][pop] = {
                "n_population": len(ev),
                "n_answered": answered,
                "n_common": len(common),
                "common_positives": sum(1 for s_ in scored_common if s_["truth"]),
                "common_negatives": sum(1 for s_ in scored_common if not s_["truth"]),
                "common_n_files": len({s_["cluster"] for s_ in scored_common}),
                "common": _detector_block(scored_common, LLM_COMPARISON),
                "common_bootstrap": cluster_bootstrap(
                    scored_common, LLM_COMPARISON,
                    [("relic_v1_0", "llm_C"), ("relic_v1_0", "llm_D"), ("llm_D", "llm_C")]),
                "own_answered": _detector_block(scored_all, LLM_DETECTORS, missing="exclude"),
            }
    return llm_res


def compute_all(records: list[dict], llm: dict) -> dict:
    m: dict = {
        "schema": "relic-final-metrics/1",
        "primary_detector": PRIMARY_DETECTOR,
        "primary_population": "carddemo",
        "detectors": DETECTORS,
        "detector_labels": DETECTOR_LABELS,
        "subjects": {k: {"title": s.title, "url": s.url, "license": s.license, "pinned": s.pinned,
                         "role": s.role, "n_jcl_job_files": len(s.jcl_files)} for k, s in SUBJECTS.items()},
    }

    # --- accounting ----------------------------------------------------------
    acc: dict = {}
    for pop in POPULATIONS:
        rs = _pop(records, pop)
        by_status = Counter(r["status"] for r in rs)
        reasons = Counter()
        for r in rs:
            if r["status"] == "EVALUABLE":
                continue
            reason = r["status_reason"]
            key = reason.split(":")[0] if r["status"] in {"OTHER", "INFRASTRUCTURE_FAILURE"} else reason
            if reason.startswith("DUPLICATE"):
                key = "DUPLICATE"
            reasons[f"{r['status']} | {key}"] += 1
        by_op: dict = {}
        for op in ALL_OPERATORS:
            c = Counter(r["status"] for r in rs if r["mutation_type"] == op)
            if c:
                by_op[op] = {s: c.get(s, 0) for s in STATUSES} | {"total": sum(c.values())}
        n = len(rs)
        acc[pop] = {
            "total": n,
            "by_status": {s: by_status.get(s, 0) for s in STATUSES},
            "non_evaluable_reasons": dict(sorted(reasons.items())),
            "percent_evaluable": round(100 * by_status.get("EVALUABLE", 0) / n, 1) if n else None,
            "percent_non_evaluable": round(100 * (n - by_status.get("EVALUABLE", 0)) / n, 1) if n else None,
            "by_operator": by_op,
        }
    m["accounting"] = acc

    # --- label distribution ----------------------------------------------------
    lab: dict = {}
    for pop in POPULATIONS:
        rs = [r for r in _pop(records, pop) if r["status"] == "EVALUABLE"]
        per_op: dict = {}
        for op in ALL_OPERATORS:
            c = Counter(r["oracle_result"] for r in rs if r["mutation_type"] == op)
            if c:
                per_op[op] = dict(c)
        all_labelled = [r for r in _pop(records, pop) if r["oracle_result"] is not None]
        lab[pop] = {
            "evaluable": len(rs),
            "positives": sum(1 for r in rs if r["ground_truth"]),
            "negatives": sum(1 for r in rs if r["ground_truth"] is False),
            "by_operator": per_op,
            "oracle_labels_all_candidates": dict(Counter(r["oracle_result"] for r in all_labelled)),
            "difference_categories": dict(Counter(
                c for r in rs if r["ground_truth"] for c in r["oracle"]["categories"])),
            "positives_only_failure_observable": sum(
                1 for r in rs if r["ground_truth"] and r["oracle_result_no_abend"] == "EQUIVALENT"),
        }
    m["labels"] = lab

    # --- main results ------------------------------------------------------------
    pairs = [("relic_v1_0", d) for d in DETECTORS if d != "relic_v1_0"] + [("relic_v1_1", "textdiff")]
    res: dict = {}
    for pop in POPULATIONS:
        scored = _scored([r for r in _pop(records, pop) if r["status"] == "EVALUABLE"])
        res[pop] = {
            "n": len(scored),
            "positives": sum(1 for s in scored if s["truth"]),
            "negatives": sum(1 for s in scored if not s["truth"]),
            "n_files": len({s["cluster"] for s in scored}),
            "detectors": _detector_block(scored, DETECTORS),
            "bootstrap": cluster_bootstrap(scored, DETECTORS, pairs),
        }
    m["results"] = res

    # --- breakdowns ---------------------------------------------------------------
    per_op: dict = {}
    per_ct: dict = {}
    for pop in POPULATIONS:
        scored = _scored([r for r in _pop(records, pop) if r["status"] == "EVALUABLE"])
        per_op[pop] = {op: _detector_block([s for s in scored if s["operator"] == op], DETECTORS)
                       for op in ALL_OPERATORS if any(s["operator"] == op for s in scored)}
        per_ct[pop] = {ct: _detector_block([s for s in scored if s["ctype"] == ct], DETECTORS)
                       for ct in CONTRACT_TYPES if any(s["ctype"] == ct for s in scored)}
    m["per_operator"] = per_op
    m["per_contract_type"] = per_ct

    # --- sensitivity ---------------------------------------------------------------
    sens: dict = {}
    for pop in POPULATIONS:
        rs = _pop(records, pop)
        ev = [r for r in rs if r["status"] == "EVALUABLE"]
        no_abend = []
        for r in ev:
            lab2 = r["oracle_result_no_abend"]
            if lab2 in ("DIFFERENT", "EQUIVALENT"):
                no_abend.append(dict(r, ground_truth_no_abend=(lab2 == "DIFFERENT")))
        oos = [r for r in rs if r["status"] == "OUT_OF_SCOPE" and r["ground_truth"] is not None]
        und = [r for r in rs if r["status"] == "OTHER" and r["oracle_result"] == "UNDETERMINED"]
        und_pos = [dict(r, ground_truth=True) for r in und]
        und_neg = [dict(r, ground_truth=False) for r in und]
        non_cosmetic = [r for r in ev if r["mutation_type"] not in NEGATIVE_OPERATORS]
        sens[pop] = {
            "no_abend_labels": {"n": len(no_abend), "detectors": _detector_block(
                _scored(no_abend, "ground_truth_no_abend"), DETECTORS)},
            "including_out_of_scope": {"n": len(ev) + len(oos), "n_out_of_scope_labelled": len(oos),
                                       "detectors": _detector_block(_scored(ev + oos), DETECTORS)},
            "undetermined_as_positive": {"n_undetermined": len(und),
                                         "detectors": _detector_block(_scored(ev + und_pos), DETECTORS)},
            "undetermined_as_negative": {"n_undetermined": len(und),
                                         "detectors": _detector_block(_scored(ev + und_neg), DETECTORS)},
            "excluding_cosmetic_negatives": {"n": len(non_cosmetic), "detectors": _detector_block(
                _scored(non_cosmetic), DETECTORS)},
            "out_of_scope_only": {"n": len(oos), "detectors": _detector_block(_scored(oos), DETECTORS)},
        }
    m["sensitivity"] = sens

    m["llm"] = llm_section(records, llm)

    # --- contract recovery ----------------------------------------------------------------
    cr_path = OUT / "contract_recovery.json"
    if cr_path.exists():
        cr = json.loads(cr_path.read_text())
        m["contract_recovery"] = {k: {"n_files": v["n_files"], "files_with_oracle_pairs": v["files_with_oracle_pairs"],
                                      "micro": v["micro"]} for k, v in cr["subjects"].items()}

    # --- legacy ------------------------------------------------------------------------
    m["legacy"] = legacy_section()

    # --- oracle sanity ------------------------------------------------------------------
    m["oracle_sanity"] = oracle_sanity()
    return m


def legacy_section() -> dict:
    out: dict = {}
    p = ROOT / "results" / "legacy" / "legacy_accounting_summary.json"
    if p.exists():
        out["rq2_accounting"] = json.loads(p.read_text())
    rq2 = json.loads((ROOT / "results" / "rq2" / "rq2_summary.json").read_text())
    out["previously_reported"] = {
        "relic_f1": rq2["static_bcg"]["f1"], "static_bcg_E_f1": rq2["static_bcg_baseline_E"]["f1"],
        "structural_A_f1": rq2["structural_baseline_A"]["f1"], "complexity_B_f1": rq2["complexity_baseline_B"]["f1"],
        "n_evaluated": rq2["n_evaluated_mutations"], "n_attempted": rq2["n_attempted_mutations"],
    }
    llm = {}
    for name, fn in (("llm_C", "llm_c_records_blinded.jsonl"), ("llm_D", "llm_d_records.jsonl")):
        rows = [json.loads(l) for l in open(ROOT / "results" / "rq2" / fn)]
        ok = [r for r in rows if not r.get("error")]
        correct = sum(1 for r in ok if bool(r["predicted_regression"]) == bool(r["ground_truth"]))
        rep = json.loads((ROOT / "results" / "rq2" / ("llm_c_results.json" if name == "llm_C" else "llm_d_results.json")).read_text())
        llm[name] = {
            "calls": len(rows), "failed_calls": len(rows) - len(ok), "successful_calls": len(ok),
            "successful_correct": correct,
            "reported_f1": rep["metrics"]["f1"],
            "failed_calls_scored_as_negative": True,
            "prompt_contained_source_code": False,
        }
    out["llm"] = llm
    return out


def oracle_sanity() -> dict:
    """Original files must simulate without JCL errors in the baseline scenario."""
    from jcl_oracle.judge import describe_file  # noqa: F401  (import check)
    from jcl_oracle.model import build_model
    from jcl_oracle.simulate import Scenario, Simulator, first_access_creates
    out: dict = {}
    for key, s in SUBJECTS.items():
        n_err = 0
        files_err = []
        for f in s.jcl_files:
            model = build_model(f.read_text(errors="replace"), s.proclib)
            sim = Simulator(model, s.cobol_sources, first_access_creates(model, s.cobol_sources))
            beh, _st = sim.run(Scenario())
            if any(t[1] == "JCLERR" for t in beh.termination):
                n_err += 1
                files_err.append(s.rel(f))
        out[key] = {"files": len(s.jcl_files), "original_baseline_jcl_errors": n_err,
                    "files_with_errors": files_err}
    return out


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def f3(x) -> str:
    return "n/a" if x is None else f"{x:.3f}"


def ci(x) -> str:
    return "n/a" if not x else f"[{x[0]:.2f}, {x[1]:.2f}]"


def table_accounting(m: dict) -> str:
    rows = ["| Subject | Candidates | EVALUABLE | OUT_OF_SCOPE | INVALID_MUTATION | INFRASTRUCTURE_FAILURE | OTHER | % evaluable |",
            "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for pop in POPULATIONS:
        a = m["accounting"][pop]
        b = a["by_status"]
        name = "**All subjects**" if pop == "pooled" else SUBJECTS[pop].title
        rows.append(f"| {name} | {a['total']} | {b['EVALUABLE']} | {b['OUT_OF_SCOPE']} | {b['INVALID_MUTATION']} | "
                    f"{b['INFRASTRUCTURE_FAILURE']} | {b['OTHER']} | {a['percent_evaluable']}% |")
    return "\n".join(rows)


def table_reasons(m: dict) -> str:
    rows = ["| Status / reason | CardDemo | OMP course | GenApp | All |", "|---|---:|---:|---:|---:|"]
    keys = sorted({k for pop in POPULATIONS for k in m["accounting"][pop]["non_evaluable_reasons"]})
    for k in keys:
        vals = [m["accounting"][p]["non_evaluable_reasons"].get(k, 0) for p in POPULATIONS]
        rows.append(f"| {k} | " + " | ".join(str(v) for v in vals) + " |")
    return "\n".join(rows)


def table_main(m: dict, pop: str) -> str:
    r = m["results"][pop]
    bs = r["bootstrap"]["f1_ci95"]
    rows = [f"Population: {('all subjects' if pop == 'pooled' else SUBJECTS[pop].title)}, EVALUABLE mutants "
            f"(n = {r['n']}: {r['positives']} behaviour-changing, {r['negatives']} behaviour-preserving; "
            f"{r['n_files']} files)",
            "",
            "| Detector | TP | FP | FN | TN | Precision | Recall | F1 | F1 95% CI (file bootstrap) | Specificity |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---|---:|"]
    for d in DETECTORS:
        c = r["detectors"][d]
        name = f"**{DETECTOR_LABELS[d]}**" if d == PRIMARY_DETECTOR else DETECTOR_LABELS[d]
        rows.append(f"| {name} | {c['tp']} | {c['fp']} | {c['fn']} | {c['tn']} | {f3(c['precision'])} | "
                    f"{f3(c['recall'])} | {f3(c['f1'])} | {ci(bs.get(d))} | {f3(c['specificity'])} |")
    return "\n".join(rows)


def table_subjects_f1(m: dict) -> str:
    rows = ["| Detector | " + " | ".join(("All subjects" if p == "pooled" else SUBJECTS[p].title) for p in POPULATIONS) + " |",
            "|---|" + "---:|" * len(POPULATIONS)]
    rows.append("| n (pos/neg) | " + " | ".join(
        f"{m['results'][p]['n']} ({m['results'][p]['positives']}/{m['results'][p]['negatives']})" for p in POPULATIONS) + " |")
    for d in DETECTORS:
        cells = []
        for p in POPULATIONS:
            c = m["results"][p]["detectors"][d]
            cells.append(f"F1 {f3(c['f1'])} (P {f3(c['precision'])}, R {f3(c['recall'])})")
        rows.append(f"| {DETECTOR_LABELS[d]} | " + " | ".join(cells) + " |")
    return "\n".join(rows)


def table_operator(m: dict, pop: str) -> str:
    dets = ["relic_v1_0", "relic_v1_1", "structural_A", "textdiff"]
    rows = ["| Operator | Contract type | n | violating | " + " | ".join(f"{DETECTOR_LABELS[d].split(' (')[0].split(':')[0]} TP/FN/FP/TN" for d in dets) + " |",
            "|---|---|---:|---:|" + "---|" * len(dets)]
    from relic_eval.mutate import OPERATOR_CONTRACT_TYPE
    for op in ALL_OPERATORS:  # fixed operator order, independent of JSON key order
        block = m["per_operator"][pop].get(op)
        if block is None:
            continue
        c0 = block[dets[0]]
        cells = [f"{block[d]['tp']}/{block[d]['fn']}/{block[d]['fp']}/{block[d]['tn']}" for d in dets]
        rows.append(f"| {op} | {OPERATOR_CONTRACT_TYPE[op]} | {c0['n']} | {c0['positives']} | " + " | ".join(cells) + " |")
    return "\n".join(rows)


def table_sensitivity(m: dict, pop: str) -> str:
    s = m["sensitivity"][pop]
    variants = [
        ("Primary (EVALUABLE, full oracle)", m["results"][pop]["detectors"], m["results"][pop]["n"]),
        ("Labels without abend scenarios", s["no_abend_labels"]["detectors"], s["no_abend_labels"]["n"]),
        ("+ OUT_OF_SCOPE mutants (labelled)", s["including_out_of_scope"]["detectors"], s["including_out_of_scope"]["n"]),
        ("UNDETERMINED counted as violating", s["undetermined_as_positive"]["detectors"],
         m["results"][pop]["n"] + s["undetermined_as_positive"]["n_undetermined"]),
        ("UNDETERMINED counted as preserving", s["undetermined_as_negative"]["detectors"],
         m["results"][pop]["n"] + s["undetermined_as_negative"]["n_undetermined"]),
        ("Without cosmetic negative operators", s["excluding_cosmetic_negatives"]["detectors"], s["excluding_cosmetic_negatives"]["n"]),
    ]
    dets = ["relic_v1_0", "relic_v1_1", "structural_A", "textdiff"]
    rows = ["| Variant | n | " + " | ".join(DETECTOR_LABELS[d].split(' (')[0] + " F1 / Spec." for d in dets) + " |",
            "|---|---:|" + "---|" * len(dets)]
    for name, block, n in variants:
        rows.append(f"| {name} | {n} | " + " | ".join(
            f"{f3(block[d]['f1'])} / {f3(block[d]['specificity'])}" for d in dets) + " |")
    return "\n".join(rows)


def table_contract_recovery(m: dict) -> str:
    cr = m.get("contract_recovery", {})
    rows = ["| Subject | Contract type | RELIC version | TP | FP | FN | Precision | Recall | F1 |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|"]
    for subj in ("carddemo", "omp_course", "genapp"):
        if subj not in cr:
            continue
        for ct in ("TEMPORAL", "RESOURCE", "CONTROL_FLOW", "CONTROL_FLOW_INCL_IF"):
            for v in ("relic_v1_0", "relic_v1_1"):
                c = cr[subj]["micro"][v][ct]
                label = "CONTROL_FLOW incl. IF/THEN (out of scope)" if ct == "CONTROL_FLOW_INCL_IF" else ct
                rows.append(f"| {SUBJECTS[subj].title} | {label} | {v} | {c['tp']} | {c['fp']} | {c['fn']} | "
                            f"{f3(c['precision'])} | {f3(c['recall'])} | {f3(c['f1'])} |")
    return "\n".join(rows)


def table_legacy(m: dict) -> str:
    leg = m["legacy"]
    prev = leg["previously_reported"]
    p = m["results"]["carddemo"]["detectors"]
    rows = ["| Quantity | Legacy harness (WITHDRAWN: BCG-level, circular) | Source-level benchmark (this version) |",
            "|---|---|---|",
            f"| Mutants scored | {prev['n_evaluated']} of {prev['n_attempted']} attempts | "
            f"{m['results']['carddemo']['n']} of {m['accounting']['carddemo']['total']} candidates (CardDemo) |",
            "| Ground truth | 'mutation was applied' (always positive) | independent JCL semantics oracle |",
            "| Negatives | 144 BCG edits that touch no contract | oracle-equivalent mutants (incl. fault operators) |",
            f"| RELIC F1 | {prev['relic_f1']:.3f} | {f3(p['relic_v1_0']['f1'])} (v1.0.0) / {f3(p['relic_v1_1']['f1'])} (v1.1) |",
            f"| Baseline E F1 | {prev['static_bcg_E_f1']:.3f} | {f3(p['static_bcg_E']['f1'])} |",
            f"| Baseline A F1 | {prev['structural_A_f1']:.3f} | {f3(p['structural_A']['f1'])} |",
            f"| Baseline B F1 | {prev['complexity_B_f1']:.3f} | {f3(p['complexity_B']['f1'])} |"]
    for k in LLM_DETECTORS:
        v = leg["llm"].get(k)
        if v is None:
            continue
        rows.append(f"| {DETECTOR_LABELS[k]} | F1 {v['reported_f1']:.4f}, but {v['failed_calls']}/{v['calls']} calls failed "
                    f"(HTTP 429) and were scored as 'no regression'; {v['successful_correct']}/{v['successful_calls']} "
                    f"successful calls were correct | {llm_cell(m, k)} |")
    return "\n".join(rows)


def llm_ran(m: dict) -> bool:
    return bool(m["llm"].get("results"))


def llm_cell(m: dict, k: str) -> str:
    if not llm_ran(m):
        return "not run (no LLM API credentials in the evaluation environment)"
    r = m["llm"]["results"]["pooled"]
    c = r["common"][k]
    return (f"F1 {f3(c['f1'])} on the {r['n_common']} mutants (all subjects) both LLM baselines answered "
            f"(of {r['n_population']} evaluable; see LLM table)")


def table_llm(m: dict) -> str:
    if not llm_ran(m):
        return "LLM baselines were not run in this version (no API credentials)."
    st = m["llm"]["status"]
    dec = st.get("decoding", {})
    lines = [f"Model: `{st.get('model')}` via {st.get('provider')} (prompt `{st.get('prompt_version')}`, "
             f"temperature {dec.get('temperature')}, reasoning effort {dec.get('reasoning_effort', 'n/a')}, "
             f"one sample per prompt). Failed or unparseable answers are excluded, never scored. "
             f"All detectors below are scored on the same mutants: those for which both LLM baselines "
             f"returned a valid answer.", ""]
    lines += ["| Population | Evaluable | Answered C / D | Common n (pos/neg) | Detector | TP | FP | FN | TN | "
              "Precision | Recall | F1 | F1 95% CI | Specificity |",
              "|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|---:|"]
    for pop in POPULATIONS:
        r = m["llm"]["results"][pop]
        bs = r["common_bootstrap"]["f1_ci95"]
        title = "All subjects" if pop == "pooled" else SUBJECTS[pop].title
        for i, d in enumerate(LLM_COMPARISON):
            c = r["common"][d]
            head = (f"| {title} | {r['n_population']} | {r['n_answered']['llm_C']} / {r['n_answered']['llm_D']} | "
                    f"{r['n_common']} ({r['common_positives']}/{r['common_negatives']}) |") if i == 0 else "| | | | |"
            lines.append(f"{head} {DETECTOR_LABELS[d]} | {c['tp']} | {c['fp']} | {c['fn']} | {c['tn']} | "
                         f"{f3(c['precision'])} | {f3(c['recall'])} | {f3(c['f1'])} | {ci(bs.get(d))} | "
                         f"{f3(c['specificity'])} |")
    return "\n".join(lines)


def headline(m: dict) -> str:
    r = m["results"]["carddemo"]
    c = r["detectors"][PRIMARY_DETECTOR]
    c1 = r["detectors"]["relic_v1_1"]
    t = r["detectors"]["textdiff"]
    a = m["accounting"]["pooled"]
    return (f"CardDemo (primary): n={r['n']} ({r['positives']} pos / {r['negatives']} neg) | "
            f"RELIC v1.0.0 P={f3(c['precision'])} R={f3(c['recall'])} F1={f3(c['f1'])} "
            f"(TP={c['tp']} FP={c['fp']} FN={c['fn']} TN={c['tn']}) | RELIC v1.1 F1={f3(c1['f1'])} | "
            f"textdiff F1={f3(t['f1'])} | all subjects: {a['total']} candidates, "
            f"{a['by_status']['EVALUABLE']} evaluable ({a['percent_evaluable']}%)")


def llm_summary(m: dict) -> str:
    withdrawn = ("earlier F1 0.0377 / 0.1091 figures were artifacts of rate-limited calls scored as "
                 "negatives and are withdrawn")
    if not llm_ran(m):
        return f"- **LLM baselines:** not run — no API credentials were available; the {withdrawn}."
    st = m["llm"]["status"]
    rp = m["llm"]["results"]["pooled"]
    c, d, rel = rp["common"]["llm_C"], rp["common"]["llm_D"], rp["common"]["relic_v1_0"]
    diffs = rp["common_bootstrap"]["diff_ci95"]
    coverage = (f"{rp['n_common']} of {rp['n_population']} evaluable mutants "
                f"({100 * rp['n_common'] / rp['n_population']:.1f}%), all subjects")
    partial = (" Coverage is limited by the provider quota of the API key used; the answered mutants are "
               "the first ones of a seeded random order, i.e. a random subsample."
               if st.get("overall") == "PARTIAL" else "")
    return (f"- **LLM baselines** (`{st.get('model')}`; scored only where both LLM baselines answered — "
            f"{coverage}): LLM-only F1 {f3(c['f1'])} (P {f3(c['precision'])}, R {f3(c['recall'])}, "
            f"specificity {f3(c['specificity'])}); dependency + LLM F1 {f3(d['f1'])} (P {f3(d['precision'])}, "
            f"R {f3(d['recall'])}, specificity {f3(d['specificity'])}); RELIC v1.0.0 on the same mutants "
            f"F1 {f3(rel['f1'])} (RELIC v1.0.0 − LLM-only F1 difference 95% CI {ci(diffs.get('relic_v1_0-llm_C'))}; "
            f"− dependency + LLM {ci(diffs.get('relic_v1_0-llm_D'))}).{partial} The {withdrawn}.")


def generated_blocks(m: dict) -> dict[str, str]:
    r = m["results"]["carddemo"]
    c = r["detectors"][PRIMARY_DETECTOR]
    c1 = r["detectors"]["relic_v1_1"]
    t = r["detectors"]["textdiff"]
    s = r["detectors"]["structural_A"]
    pooled = m["results"]["pooled"]
    cp = pooled["detectors"][PRIMARY_DETECTOR]
    a = m["accounting"]
    bs = r["bootstrap"]
    diff_t = bs["diff_ci95"].get("relic_v1_0-textdiff")
    summary = (
        f"- **Benchmark:** {a['pooled']['total']} candidate source-level mutants over 3 subject systems "
        f"({a['pooled']['by_status']['EVALUABLE']} evaluable, {a['pooled']['percent_evaluable']}%); "
        f"ground truth from an independent JCL execution-semantics oracle.\n"
        f"- **Primary result (CardDemo, RELIC v1.0.0 as released):** precision {f3(c['precision'])}, "
        f"recall {f3(c['recall'])}, F1 {f3(c['f1'])} (95% CI {ci(bs['f1_ci95'].get('relic_v1_0'))}; "
        f"TP {c['tp']}, FP {c['fp']}, FN {c['fn']}, TN {c['tn']}; n = {r['n']}).\n"
        f"- **RELIC v1.1** (spec-conformance fixes made *after* seeing these results): F1 {f3(c1['f1'])} on CardDemo.\n"
        f"- **Reference detector** that flags any non-comment text change: F1 {f3(t['f1'])} "
        f"(specificity {f3(t['specificity'])}); RELIC v1.0.0 − reference F1 difference 95% CI {ci(diff_t)}.\n"
        f"- **Structural baseline A:** F1 {f3(s['f1'])}.\n"
        f"- **All three subjects pooled:** RELIC v1.0.0 F1 {f3(cp['f1'])} (n = {pooled['n']}).\n"
        + llm_summary(m)
    )
    blocks = {
        "results-summary": summary,
        "table-main-carddemo": table_main(m, "carddemo"),
        "table-main-pooled": table_main(m, "pooled"),
        "table-subjects": table_subjects_f1(m),
        "table-accounting": table_accounting(m),
        "table-reasons": table_reasons(m),
        "table-operators-carddemo": table_operator(m, "carddemo"),
        "table-sensitivity-carddemo": table_sensitivity(m, "carddemo"),
        "table-contract-recovery": table_contract_recovery(m),
        "table-legacy": table_legacy(m),
        "table-llm": table_llm(m),
    }
    return blocks


def tex_numbers(m: dict) -> str:
    """LaTeX macros for every number used in paper/paper.tex prose."""
    r = m["results"]["carddemo"]
    d = r["detectors"]
    a = m["accounting"]
    pooled = m["results"]["pooled"]["detectors"]
    bs = r["bootstrap"]["f1_ci95"]
    vals = {
        "NCandidates": a["pooled"]["total"],
        "NEvaluable": a["pooled"]["by_status"]["EVALUABLE"],
        "PctEvaluable": f"{a['pooled']['percent_evaluable']}\\%",
        "NCardDemo": r["n"], "NCardDemoPos": r["positives"], "NCardDemoNeg": r["negatives"],
        "RelicPrecision": f3(d["relic_v1_0"]["precision"]), "RelicRecall": f3(d["relic_v1_0"]["recall"]),
        "RelicFOne": f3(d["relic_v1_0"]["f1"]), "RelicFOneCI": ci(bs.get("relic_v1_0")),
        "RelicTP": d["relic_v1_0"]["tp"], "RelicFP": d["relic_v1_0"]["fp"],
        "RelicFN": d["relic_v1_0"]["fn"], "RelicTN": d["relic_v1_0"]["tn"],
        "RelicOneOneFOne": f3(d["relic_v1_1"]["f1"]),
        "TextDiffFOne": f3(d["textdiff"]["f1"]), "TextDiffSpec": f3(d["textdiff"]["specificity"]),
        "StructuralFOne": f3(d["structural_A"]["f1"]), "ComplexityFOne": f3(d["complexity_B"]["f1"]),
        "PooledRelicFOne": f3(pooled["relic_v1_0"]["f1"]), "NPooled": m["results"]["pooled"]["n"],
    }
    lines = ["% Generated by relic_eval/report.py from results/final/metrics.json -- do not edit."]
    for k, v in vals.items():
        lines.append(f"\\newcommand{{\\{k}}}{{{v}}}")
    return "\n".join(lines) + "\n"


def _tex_escape(s: str) -> str:
    return (s.replace("\\", r"\textbackslash{}").replace("&", r"\&").replace("%", r"\%")
            .replace("_", r"\_").replace("#", r"\#").replace("**", ""))


def md_table_to_tex(md: str) -> str:
    lines = [l for l in md.splitlines() if l.startswith("|")]
    if len(lines) < 2:
        return ""
    head = [c.strip() for c in lines[0].strip("|").split("|")]
    body = [[c.strip() for c in l.strip("|").split("|")] for l in lines[2:]]
    spec = "l" + "r" * (len(head) - 1)
    out = [r"\begin{tabular}{" + spec + "}", r"\toprule",
           " & ".join(_tex_escape(h) for h in head) + r" \\", r"\midrule"]
    for row in body:
        out.append(" & ".join(_tex_escape(c) for c in row) + r" \\")
    out += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(out) + "\n"


GENERATED_DOCS = [
    ROOT / "README.md",
    ROOT / "paper" / "paper.md",
    ROOT / "docs" / "FINAL_RESEARCH_READINESS_REPORT.md",
    ROOT / "docs" / "evaluation" / "RESULTS.md",
    ROOT / "results" / "README.md",
]

# A block may be empty ("BEGIN\nEND") or populated ("BEGIN\n<content>\nEND").
# The content group is optional so that freshly added, empty blocks are found.
_BLOCK_RE = re.compile(
    r"(?P<begin><!-- BEGIN GENERATED:(?P<name>[a-z0-9-]+) -->)\n"
    r"(?:(?P<body>.*?)\n)?"
    r"(?P<end><!-- END GENERATED:(?P=name) -->)",
    re.S,
)
_BEGIN_RE = re.compile(r"<!-- BEGIN GENERATED:([a-z0-9-]+) -->")


def find_blocks(text: str) -> list[tuple[str, str]]:
    """(name, body) for every generated block; raises on an unmatched BEGIN marker."""
    found = [(mm.group("name"), mm.group("body") or "") for mm in _BLOCK_RE.finditer(text)]
    begins = _BEGIN_RE.findall(text)
    if len(begins) != len(found):
        missing = sorted((Counter(begins) - Counter(n for n, _ in found)).elements())
        raise ValueError(f"generated block(s) without a matching END marker: {missing}")
    return found


def strip_blocks(text: str) -> str:
    """Text with the content of every generated block removed (markers kept)."""
    return _BLOCK_RE.sub(lambda mm: mm.group("begin") + "\n" + mm.group("end"), text)


def render_into(text: str, blocks: dict[str, str]) -> str:
    find_blocks(text)  # validates markers

    def repl(mm: re.Match) -> str:
        name = mm.group("name")
        if name not in blocks:
            raise KeyError(f"unknown generated block {name!r}")
        body = blocks[name]
        return mm.group("begin") + "\n" + (body + "\n" if body else "") + mm.group("end")
    return _BLOCK_RE.sub(repl, text)


def write_all(m: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "metrics.json", "w") as fh:
        json.dump(m, fh, indent=2, sort_keys=True)
    # Render from exactly what was written (key order, float/int types), so that
    # check_consistency, which renders from metrics.json, gets identical output.
    m = json.loads((OUT / "metrics.json").read_text())
    blocks = generated_blocks(m)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    TEX_DIR.mkdir(parents=True, exist_ok=True)
    for name, md in blocks.items():
        (TABLES_DIR / f"{name}.md").write_text(md + "\n")
        if name.startswith("table-"):
            (TEX_DIR / f"{name}.tex").write_text(md_table_to_tex(md))
    (TEX_DIR / "numbers.tex").write_text(tex_numbers(m))
    for doc in GENERATED_DOCS:
        if doc.exists():
            text = doc.read_text()
            new = render_into(text, blocks)
            if new != text:
                doc.write_text(new)
    from relic_eval import figures
    figures.main(m)
