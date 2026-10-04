"""
Consistency checks between raw results, metrics, tables, figures and documentation.

    python -m relic_eval.check_consistency        (make check)

Fails (exit 1) if
  1. metrics.json differs from metrics recomputed from the raw records;
  2. any generated block in README / paper / docs, any table file under
     results/final/tables, or any LaTeX table under paper/generated differs from
     a fresh rendering of metrics.json;
  3. a statement the documentation relies on is not true of the raw records
     (e.g. "RELIC v1.0.0 and Baseline E make identical decisions");
  4. active (non-archived) documentation contains a withdrawn number
     (F1 = 1.000, 104/104, 0.0377, 0.1091, 305 tests, 91.8%, ...) outside a
     generated block or a line that explicitly marks it as legacy/withdrawn;
  5. an expected figure is missing.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from relic_eval import llm_baselines, report
from relic_eval.pipeline import OUT, load_records
from relic_eval.subjects import ROOT

STALE_PATTERNS = [
    (r"F1\s*[=:]?\s*1\.0(00)?\b", "legacy F1 = 1.000"),
    (r"104\s*/\s*104", "legacy 104/104"),
    (r"0\.0377|0\.1091|\b0\.038\b|\b0\.109\b", "legacy LLM F1"),
    (r"\b305\s*(/\s*305\s*)?tests?\b|305/305", "legacy test count"),
    (r"91\.8\s*%", "legacy dynamic validation rate"),
    (r"FPR\s*=\s*0(\.0+)?\b", "legacy FPR = 0"),
    (r"zero false positives", "legacy zero-FP claim"),
    (r"\b0\.960\b|\b0\.96\b", "legacy Baseline E F1"),
    (r"336\s*N/A|76\.4\s*%", "legacy N/A rate"),
]
ALLOW_LINE = re.compile(r"withdrawn|legacy|Legacy|LEGACY|previously|superseded|Superseded|were reported|was reported|pre-remediation|v1 manuscript", re.I)
SCAN_GLOBS = ["README.md", "CITATION.cff", "docs/*.md", "docs/evaluation/*.md", "paper/paper.md",
              "paper/paper.tex", "results/README.md", "examples/**/*.md", "docs/assets/*.svg"]
EXPECTED_FIGURES = ["figures/final/f1_carddemo.svg", "figures/final/accounting.svg",
                    "figures/final/operator_recall.svg", "docs/assets/relic-results.svg"]


def _norm(x):
    return json.loads(json.dumps(x, sort_keys=True))


def check_generated_docs(blocks: dict[str, str], docs=None) -> list[str]:
    """Every generated doc must exist, contain >= 1 block, no empty or stale block."""
    errors: list[str] = []
    for doc in (report.GENERATED_DOCS if docs is None else docs):
        name = doc.relative_to(ROOT) if doc.is_relative_to(ROOT) else doc
        if not doc.exists():
            errors.append(f"{name}: generated document is missing")
            continue
        text = doc.read_text()
        try:
            found = report.find_blocks(text)
        except ValueError as exc:
            errors.append(f"{name}: {exc}")
            continue
        if not found:
            errors.append(f"{name}: contains no generated block")
        for block, body in found:
            if block not in blocks:
                errors.append(f"{name}: unknown generated block {block!r}")
            elif not body.strip():
                errors.append(f"{name}: generated block {block!r} is empty")
            elif body != blocks[block]:
                errors.append(f"{name}: generated block {block!r} differs from metrics.json")
    return errors


def check_figures(metrics: dict) -> list[str]:
    import tempfile

    from relic_eval import figures
    errors: list[str] = []
    saved_out = figures.OUT
    with tempfile.TemporaryDirectory() as tmp:
        figures.OUT = Path(tmp)
        try:
            figures.f1_plot(metrics)
            figures.accounting_plot(metrics)
            figures.operator_plot(metrics)
        finally:
            figures.OUT = saved_out
        for fresh in sorted(Path(tmp).glob("*.svg")):
            committed = ROOT / "figures" / "final" / fresh.name
            if committed.exists() and committed.read_bytes() != fresh.read_bytes():
                errors.append(f"figures/final/{fresh.name} differs from a fresh rendering of metrics.json")
    copy = ROOT / "docs" / "assets" / "relic-results.svg"
    src = ROOT / "figures" / "final" / "f1_carddemo.svg"
    if copy.exists() and src.exists() and copy.read_bytes() != src.read_bytes():
        errors.append("docs/assets/relic-results.svg is not a copy of figures/final/f1_carddemo.svg")
    return errors


def check() -> list[str]:
    errors: list[str] = []
    metrics = json.loads((OUT / "metrics.json").read_text())
    records = load_records()

    # 1. recompute
    fresh = report.compute_all(records, llm_baselines.load_llm_predictions())
    if _norm(fresh) != _norm(metrics):
        diff_keys = [k for k in fresh if _norm(fresh.get(k)) != _norm(metrics.get(k))]
        errors.append(f"metrics.json is stale or hand-edited (differs in: {diff_keys})")

    # 2. generated blocks / tables
    blocks = report.generated_blocks(metrics)
    errors += check_generated_docs(blocks)
    for name, md in blocks.items():
        p = report.TABLES_DIR / f"{name}.md"
        if not p.exists() or p.read_text() != md + "\n":
            errors.append(f"{p.relative_to(ROOT)} differs from metrics.json")
        if name.startswith("table-"):
            t = report.TEX_DIR / f"{name}.tex"
            if not t.exists() or t.read_text() != report.md_table_to_tex(md):
                errors.append(f"{t.relative_to(ROOT)} differs from metrics.json")

    nt = report.TEX_DIR / "numbers.tex"
    if not nt.exists() or nt.read_text() != report.tex_numbers(metrics):
        errors.append("paper/generated/numbers.tex differs from metrics.json")

    # 3. statements the documentation relies on
    ev = [r for r in records if r["status"] == "EVALUABLE"]
    if any(r["predictions"]["relic_v1_0"] != r["predictions"]["static_bcg_E"] for r in ev):
        errors.append("docs claim relic_v1_0 and static_bcg_E decide identically, but they differ")
    if any(d.get("status") == "ERROR" for r in records for d in r.get("prediction_details", {}).values()):
        errors.append("docs claim no detector errors occurred, but some did")
    if any(r["status"] == "INFRASTRUCTURE_FAILURE" for r in records):
        errors.append("docs claim no infrastructure failures occurred, but some did")
    if any(v["original_baseline_jcl_errors"] for v in metrics["oracle_sanity"].values()):
        errors.append("an original file does not simulate cleanly (oracle sanity)")

    # 4. stale numbers in active documentation
    for pattern in SCAN_GLOBS:
        for path in sorted(ROOT.glob(pattern)):
            text = report.strip_blocks(path.read_text(errors="replace"))
            for i, line in enumerate(text.splitlines(), 1):
                if ALLOW_LINE.search(line):
                    continue
                for rx, what in STALE_PATTERNS:
                    if re.search(rx, line):
                        errors.append(f"{path.relative_to(ROOT)}:{i}: {what}: {line.strip()[:100]}")

    # 5. figures: present and identical to a fresh rendering of metrics.json
    for f in EXPECTED_FIGURES:
        if not (ROOT / f).exists():
            errors.append(f"missing figure {f}")
    errors += check_figures(metrics)
    return errors


def main() -> None:
    errors = check()
    if errors:
        print("CONSISTENCY CHECK FAILED")
        for e in errors:
            print("  -", e)
        sys.exit(1)
    print("Consistency check passed: metrics, tables, figures and documentation agree with raw results.")


if __name__ == "__main__":
    main()
