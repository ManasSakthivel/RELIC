"""
External-repository validation harness (RELIC final sprint, Agent 3).

Runs the UNMODIFIED, frozen pipeline components on JCL files from public
repositories that are not part of the development corpora:

    relic_eval.mutate.generate          -> mutants (deterministic, exhaustive sites)
    jcl_oracle.judge.compare_versions   -> oracle label (full + no_abend scenarios)
    relic_eval.detectors                -> relic_v1_0, relic_v1_1, relic_v2, textdiff
    relic_eval.v2_eval                  -> textdiff_ignore_job_parameters (diagnostic)

The accounting statuses mirror ``relic_eval.pipeline.run_benchmark`` exactly
(EVALUABLE / OUT_OF_SCOPE / INVALID_MUTATION / INFRASTRUCTURE_FAILURE / OTHER);
``tests/external/test_external_eval.py`` checks equivalence against the real
pipeline on a tiny generated subject.

CAVEATS (stated again in reports/v2/EXTERNAL_VALIDATION_RESULTS.md):
  * Labels come from the SAME, non-independent oracle used in development. The
    run therefore measures generalisation of parser + detector to unseen
    files, NOT agreement with independent ground truth.
  * Repositories were "screened by aggregate counts/fragments"; nothing here
    is blind.

Two phases (the freeze phase never imports a detector or runs the oracle):

    python -m relic_eval.external_eval freeze --clones /tmp/relic_ext_final
    python -m relic_eval.external_eval run    --clones /tmp/relic_ext_final

Outputs (results/external/): SUBJECT_FREEZE.json, metrics.json,
predictions.jsonl, exclusions.json, run_info.json.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import re
import signal
import subprocess
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from jcl_oracle.lexer import lex
from relic_eval.subjects import ROOT

OUT = ROOT / "results" / "external"
FREEZE_PATH = OUT / "SUBJECT_FREEZE.json"
DEV_DATASETS = ROOT / "datasets"
DEV_METRICS = ROOT / "results" / "v2" / "v2_metrics.json"

SCHEMA = "relic-external-eval/1"
DETECTORS = ["relic_v1_0", "relic_v1_1", "relic_v2", "textdiff", "textdiff_ignore_job_parameters"]

# ---------------------------------------------------------------------------
# Pre-registered criteria (fixed before any detector/oracle result was seen)
# ---------------------------------------------------------------------------

MIN_EXEC_STEPS = 2
MAX_LINES = 2000          # files dominated by in-stream data are excluded
MAX_EXEC_STEPS = 40       # bounds oracle scenario cost
PER_FILE_TIMEOUT_S = 900  # infrastructure guard; a timeout is recorded, never patched
ROBUSTNESS_TIMEOUT_S = 120

ROLE_EFFECTIVENESS = "effectiveness"
ROLE_ROBUSTNESS = "robustness_only"

# key, github, directory name inside --clones, role, SPDX, licence file, notes
REPOS: list[dict] = [
    dict(key="IBM_dbb", github="IBM/dbb", dir="IBM_dbb", role=ROLE_EFFECTIVENESS,
         spdx="Apache-2.0", license_file="LICENSE",
         provenance="IBM Dependency Based Build samples (Git ISPF client, jclToZBuilder sample)",
         exposure="screened by aggregate counts (earlier-sprint Agent 3 protocol: file/COND/EXEC counts) "
                  "and by lexer-level file/EXEC/line counts in this sprint; NOT blind"),
    dict(key="IBM_zopeneditor-sample", github="IBM/zopeneditor-sample", dir="IBM_zopeneditor-sample",
         role=ROLE_EFFECTIVENESS, spdx="Apache-2.0", license_file="LICENSE",
         provenance="IBM sample project for Z Open Editor; file headers say 'LICENSED MATERIALS - PROPERTY OF "
                    "IBM' (consistency with the Apache-2.0 grant UNVERIFIED; analysis only, no redistribution)",
         exposure="screened by aggregate counts AND fragments (earlier-sprint Agent 3 read the head of "
                  "JCL/ALLOCATE.jcl; repo named as rejected candidate in docs/archive secondary_system_selection.md); "
                  "NOT blind"),
    dict(key="mainframed_Enumeration", github="mainframed/Enumeration", dir="mainframed_Enumeration",
         role=ROLE_EFFECTIVENESS, spdx="MIT", license_file="LICENSE",
         provenance="Mainframe security enumeration scripts and JCL (discovered this sprint via gh code search)",
         exposure="screened by aggregate counts in this sprint (listing, file/JOB/EXEC/line counts); "
                  "not named in any RELIC document; NOT blind"),
    dict(key="vlachoudis_brexx", github="vlachoudis/brexx", dir="vlachoudis_brexx",
         role=ROLE_EFFECTIVENESS, spdx="GPL-2.0", license_file="COPYING",
         provenance="BREXX REXX interpreter for MVS 3.8j; build/install JCL (discovered this sprint via gh "
                    "code search). GPL-2.0: analysis only, no file redistribution",
         exposure="screened by aggregate counts in this sprint; not named in any RELIC document; NOT blind"),
    dict(key="walmartlabs_zECS", github="walmartlabs/zECS", dir="walmartlabs_zECS",
         role=ROLE_EFFECTIVENESS, spdx="Apache-2.0", license_file="LICENSE",
         provenance="Walmart z/OS Enterprise Cache Service CICS install/build JCL (last commit 2017; "
                    "discovered this sprint via gh code search)",
         exposure="screened by aggregate counts in this sprint; not named in any RELIC document; NOT blind"),
    dict(key="yetacp_mvs_sysgen", github="yetacp/mvs_sysgen", dir="yetacp_mvs_sysgen",
         role=ROLE_EFFECTIVENESS, spdx="MIT", license_file="LICENSE",
         provenance="MVS 3.8j sysgen jobs for Hercules; README says 'heavily based on Jay Moseley sysgen' - "
                    "UPSTREAM LICENCE/PROVENANCE UNVERIFIED (MIT on a derivative may not cover upstream text). "
                    "Included in pooled effectiveness metrics with a pre-declared sensitivity analysis "
                    "(pooled without this repo)",
         exposure="screened by aggregate counts (earlier-sprint Agent 3 protocol + this sprint); NOT blind"),
    dict(key="zowe_zowe-cli", github="zowe/zowe-cli", dir="zowe_zowe-cli", role=ROLE_EFFECTIVENESS,
         spdx="EPL-2.0", license_file="LICENSE",
         provenance="Zowe CLI zosjobs test fixtures (test artefacts, not realistic batch streams)",
         exposure="screened by aggregate counts (earlier-sprint Agent 3 protocol) and lexer-level counts in "
                  "this sprint; name appears in the protocol; NOT blind"),
    dict(key="zowe_zowe-install-packaging", github="zowe/zowe-install-packaging",
         dir="zowe_zowe-install-packaging", role=ROLE_EFFECTIVENESS, spdx="EPL-2.0", license_file="LICENSE",
         provenance="Zowe SMP/E build and install JCL (branch v3.x/staging)",
         exposure="screened by aggregate counts (earlier-sprint Agent 3 protocol) and lexer-level counts in "
                  "this sprint; NOT blind"),
    dict(key="MartinPacker_Db2-DDF-Analysis-Tool", github="MartinPacker/Db2-DDF-Analysis-Tool",
         dir="MartinPacker_Db2-DDF-Analysis-Tool", role=ROLE_EFFECTIVENESS, spdx="MIT",
         license_file="LICENSE",
         provenance="Db2 DDF analysis REXX/JCL (discovered this sprint via gh code search)",
         exposure="screened by aggregate counts in this sprint; NOT blind"),
    dict(key="zosconnect_zosconnect-sample-wola-batch", github="zosconnect/zosconnect-sample-wola-batch",
         dir="zosconnect_zosconnect-sample-wola-batch", role=ROLE_EFFECTIVENESS, spdx="Apache-2.0",
         license_file="LICENSE",
         provenance="z/OS Connect WOLA batch sample (discovered this sprint via gh code search)",
         exposure="screened by aggregate counts in this sprint; NOT blind"),
    dict(key="cschneid-the-elder_mapa", github="cschneid-the-elder/mapa", dir="cschneid-the-elder_mapa",
         role=ROLE_ROBUSTNESS, spdx="MIT", license_file="LICENSE",
         provenance="jcl/testdata is SYNTHETIC parser regression/stress data for an ANTLR JCL grammar; "
                    "excluded from every effectiveness metric, used for parser-robustness counts only",
         exposure="screened by aggregate counts AND fragments (earlier-sprint Agent 3 read test0100.jcl); "
                  "NOT blind"),
]

# Repositories seen but NOT used for effectiveness (recorded in the freeze with the reason).
NOT_ACQUIRED = [
    dict(github="MVS-sysgen/sysgen", reason="no licence (GitHub API licence=null; no LICENSE file per protocol). "
         "A clone was started and aborted; repo excluded from effectiveness metrics until a licence is confirmed."),
    dict(github="MVS-sysgen/NETSOL", reason="no licence (GitHub API licence=null); not cloned"),
    dict(github="moshix/mvs", reason="no licence (GitHub API licence=null); not cloned"),
    dict(github="mainframed/usstable", reason="no licence (GitHub API licence=null); not cloned"),
    dict(github="mainframed/logica", reason="no licence (GitHub API licence=null); not cloned"),
    dict(github="mainframed/DC30_Workshop", reason="no licence (GitHub API licence=null); not cloned"),
    dict(github="zedsec390/NJElib", reason="no licence (GitHub API licence=null); not cloned"),
    dict(github="mvslovers/jcc", reason="GitHub API licence=NOASSERTION; not cloned"),
    dict(github="pdos-project/pdos", reason="GitHub API licence=null (a public-domain statement, if any, "
         "was not verified in time); not cloned"),
    dict(github="IBM/IBM-Z-zOS", reason="clone aborted by timeout; per earlier protocol 5 .jcl files, none "
         "multi-step (0 expected eligible)"),
]


# ---------------------------------------------------------------------------
# helpers shared by freeze and run
# ---------------------------------------------------------------------------

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_text(t: str) -> str:
    return sha256_bytes(t.encode())


def normalised_text(text: str) -> str:
    """Whitespace/sequence/comment-insensitive form used for duplicate detection."""
    out = []
    for line in text.splitlines():
        if line.startswith("//*"):
            continue
        s = line[:72].rstrip()
        if s:
            out.append(s)
    return "\n".join(out)


def git(args: list[str], cwd: Path) -> str:
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)
    return r.stdout.strip()


def jcl_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*")
                  if p.is_file() and p.suffix.lower() == ".jcl" and ".git" not in p.relative_to(root).parts)


def file_stats(text: str) -> dict:
    stmts = lex(text)
    return {
        "lines": len(text.splitlines()),
        "n_job": sum(1 for s in stmts if s.kind == "STMT" and s.op == "JOB"),
        "n_exec": sum(1 for s in stmts if s.kind == "STMT" and s.op == "EXEC"),
    }


def dev_hashes() -> dict[str, set[str]]:
    """sha256 (raw bytes and normalised text) of every file under datasets/."""
    raw: set[str] = set()
    norm: set[str] = set()
    for p in sorted(DEV_DATASETS.rglob("*")):
        if not p.is_file() or p.suffix.lower() == ".zip":
            continue
        b = p.read_bytes()
        raw.add(sha256_bytes(b))
        if p.suffix.lower() in {".jcl", ".prc", ".proc", ".cntl", ".txt", ".cbl", ".cob", ".cpy", ".md", ""}:
            norm.add(sha256_text(normalised_text(b.decode("utf-8", errors="replace"))))
    return {"raw": raw, "norm": norm}


def harness_hashes() -> dict[str, str]:
    """sha256 of the frozen code (detectors, oracle, mutator, metrics, pipeline, subjects, src/).
    The harness itself (external_eval.py) is hashed separately (``harness_sha256``)."""
    files = [ROOT / "relic_eval" / n for n in
             ("detectors.py", "mutate.py", "v2_eval.py", "metrics.py", "pipeline.py", "subjects.py")]
    files += sorted((ROOT / "jcl_oracle").glob("*.py"))
    files += sorted(p for p in (ROOT / "src").rglob("*.py") if "__pycache__" not in p.parts)
    return {str(p.relative_to(ROOT)): sha256_bytes(p.read_bytes()) for p in files}


# ---------------------------------------------------------------------------
# freeze
# ---------------------------------------------------------------------------

DESIGN_DECISION = (
    "Decided BEFORE any detector or oracle output on any external file was produced (only the jcl_oracle "
    "lexer was used to count JOB/EXEC statements and lines; file/EXEC/line aggregates and file listings WERE "
    "seen, hence 'screened by aggregate counts/fragments', never 'blind'). (1) Evaluation unit = a .jcl file "
    "with >=1 JOB statement and >=2 EXEC steps, <=2000 lines, <=40 EXEC steps (bounded in-stream data / oracle "
    "cost). (2) Only repositories with a licence text read at the pinned commit are used; licence-unverified "
    "repositories are excluded from effectiveness metrics. (3) mapa jcl/testdata is synthetic parser-stress "
    "data: robustness counts only, no effectiveness metric. (4) Files whose raw or normalised sha256 equals a "
    "development-corpus file (datasets/) are excluded; within the external pool the first occurrence in "
    "(repo key, path) order is kept. (5) The frozen detectors (relic_v1_0, relic_v1_1, relic_v2) and the text "
    "baselines (textdiff, textdiff_ignore_job_parameters) are run exactly as defined in relic_eval/detectors.py "
    "and relic_eval/v2_eval.py; nothing is tuned or patched after results are seen; oracle/generator crashes "
    "are recorded as INFRASTRUCTURE_FAILURE, detector errors as ERROR (scored as 'not flagged' and reported "
    "separately with an error-as-wrong bound). (6) Reported populations: pooled effectiveness; per repository; "
    "pooled without yetacp/mvs_sysgen (upstream-provenance sensitivity); leave-one-repository-out. With ~7 "
    "contributing repositories, no repository-level generalisation claim is made. (7) A negative or "
    "inconclusive outcome is reported as such."
)

ANALYSIS_PLAN = {
    "primary": "per-detector confusion (TP/FP/FN/TN), precision, recall, F1, specificity, MCC on EVALUABLE "
               "mutants of effectiveness repositories; Wilson 95% CIs (mutant level, optimistic) and "
               "file-level cluster bootstrap 95% CIs for F1 (10,000 resamples, seed 20261004)",
    "baselines": ["textdiff", "textdiff_ignore_job_parameters"],
    "sensitivity": ["pooled_excluding_yetacp_mvs_sysgen", "leave_one_repo_out", "detector_error_as_wrong"],
    "accounting": "status counts per repo (EVALUABLE/OUT_OF_SCOPE/INVALID_MUTATION/INFRASTRUCTURE_FAILURE/OTHER)",
    "robustness": "parse/lex/model/detector exceptions on every .jcl file of every cloned repo (incl. mapa)",
    "non_goals": "no tuning; no re-run after viewing results; no claim of independent ground truth",
}


def build_freeze(clones: Path) -> dict:
    dev = dev_hashes()
    pool_seen: dict[str, str] = {}
    repos_out = []
    tot = Counter()
    for repo in sorted(REPOS, key=lambda r: r["key"]):
        root = clones / repo["dir"]
        if not (root / ".git").exists():
            raise SystemExit(f"missing clone: {root}")
        sha = git(["rev-parse", "HEAD"], root)
        lic_path = root / repo["license_file"]
        lic_bytes = lic_path.read_bytes()
        first_line = next((ln.strip() for ln in lic_bytes.decode(errors="replace").splitlines() if ln.strip()), "")
        files_out = []
        for p in jcl_files(root):
            text = p.read_text(errors="replace")
            raw = sha256_bytes(p.read_bytes())
            norm = sha256_text(normalised_text(text))
            st = file_stats(text)
            reasons: list[str] = []
            if st["n_job"] < 1:
                reasons.append("NO_JOB_STATEMENT")
            if st["n_exec"] < MIN_EXEC_STEPS:
                reasons.append("FEWER_THAN_2_EXEC_STEPS")
            if st["lines"] > MAX_LINES:
                reasons.append("EXCEEDS_MAX_LINES_2000")
            if st["n_exec"] > MAX_EXEC_STEPS:
                reasons.append("EXCEEDS_MAX_EXEC_STEPS_40")
            if raw in dev["raw"] or norm in dev["norm"]:
                reasons.append("DUPLICATE_OF_DEVELOPMENT_CORPUS_FILE")
            if repo["role"] != ROLE_EFFECTIVENESS:
                reasons.append("REPO_ROBUSTNESS_ONLY_SYNTHETIC")
            if norm in pool_seen and not reasons:
                reasons.append(f"DUPLICATE_WITHIN_EXTERNAL_POOL_OF {pool_seen[norm]}")
            rel = str(p.relative_to(root))
            if not reasons:
                pool_seen[norm] = f"{repo['key']}/{rel}"
            files_out.append({"path": rel, "sha256": raw, "normalised_sha256": norm, **st,
                              "eligible": not reasons, "exclusion_reasons": reasons})
            tot[(repo["role"], "total")] += 1
            tot[(repo["role"], "eligible")] += (not reasons)
        repos_out.append({
            "key": repo["key"], "url": f"https://github.com/{repo['github']}", "role": repo["role"],
            "pinned_sha": sha, "branch": git(["rev-parse", "--abbrev-ref", "HEAD"], root),
            "license_spdx": repo["spdx"], "license_file": repo["license_file"],
            "license_file_sha256": sha256_bytes(lic_bytes), "license_first_line": first_line,
            "provenance": repo["provenance"], "exposure": repo["exposure"],
            "n_jcl_files": len(files_out), "n_eligible": sum(f["eligible"] for f in files_out),
            "files": files_out,
        })
    diff = git(["diff", "--stat", "HEAD", "--", "src", "jcl_oracle", "relic_eval/detectors.py",
                "relic_eval/mutate.py", "relic_eval/v2_eval.py", "relic_eval/metrics.py",
                "relic_eval/pipeline.py", "relic_eval/subjects.py"], ROOT)
    return {
        "schema": SCHEMA,
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "relic_commit": git(["rev-parse", "HEAD"], ROOT),
        "relic_branch": git(["rev-parse", "--abbrev-ref", "HEAD"], ROOT),
        "frozen_code_uncommitted_diff_vs_HEAD": diff or "none",
        "frozen_code_sha256": harness_hashes(),
        "harness_sha256": sha256_bytes(Path(__file__).read_bytes()),
        "frozen_detectors": ["relic_v1_0", "relic_v1_1", "relic_v2",
                             "textdiff", "textdiff_ignore_job_parameters"],
        "design_decision_before_results": DESIGN_DECISION,
        "analysis_plan": ANALYSIS_PLAN,
        "criteria": {
            "eligible_file": f"extension .jcl; >=1 JOB statement; >={MIN_EXEC_STEPS} EXEC steps; "
                             f"<={MAX_LINES} lines; <={MAX_EXEC_STEPS} EXEC steps; not a duplicate of a "
                             "development-corpus file (raw or normalised sha256); first occurrence kept "
                             "inside the external pool",
            "eligible_repo": "licence text read at the pinned SHA; role=effectiveness",
            "robustness_only_repo": "synthetic parser-stress data (mapa jcl/testdata)",
            "evaluation_units_note": "extension scan only; extensionless/.prc/.cntl/.job members are not "
                                     "evaluation units (same rule as relic_eval/subjects.py)",
            "max_lines": MAX_LINES, "max_exec_steps": MAX_EXEC_STEPS, "min_exec_steps": MIN_EXEC_STEPS,
            "per_file_timeout_s": PER_FILE_TIMEOUT_S,
        },
        "development_corpus": {
            "root": "datasets/",
            "n_raw_hashes": len(dev["raw"]), "n_normalised_hashes": len(dev["norm"]),
            "raw_hash_set_sha256": sha256_text("\n".join(sorted(dev["raw"]))),
        },
        "exposure_statement": (
            "No external repository is blind. Agent 3 of the earlier sprint saw aggregate counts (and, for "
            "mapa/test0100.jcl and zopeneditor-sample/JCL/ALLOCATE.jcl, text fragments); this sprint's "
            "Agent 3 additionally saw file listings and lexer-level file/EXEC/line counts before the freeze. "
            "No oracle label or detector output on any external file had been produced at freeze time."),
        "repos": repos_out,
        "repos_not_acquired": NOT_ACQUIRED,
        "totals": {
            "effectiveness_jcl_files": tot[(ROLE_EFFECTIVENESS, "total")],
            "effectiveness_eligible_files": tot[(ROLE_EFFECTIVENESS, "eligible")],
            "robustness_only_jcl_files": tot[(ROLE_ROBUSTNESS, "total")],
        },
    }


# ---------------------------------------------------------------------------
# syntax prevalence (per file, from the project's own lexer)
# ---------------------------------------------------------------------------

_SYMBOL_RE = re.compile(r"(?<!&)&[A-Z@#$][A-Z0-9@#$]*", re.I)
_GDG_RE = re.compile(r"\((?:[+-]\d+|0)\)")
SYNTAX_FEATURES = ["PROC_USE", "PROC_DEFINITION", "INCLUDE", "IF_THEN_ELSE", "MULTI_JOB",
                   "INSTREAM_JCL_DATA", "SYMBOLIC_PARAMETERS", "GDG_REFERENCE", "JCLLIB", "COND_PARAMETER",
                   "SET_STATEMENT"]


def syntax_features(text: str) -> set[str]:
    out: set[str] = set()
    stmts = lex(text)
    njob = 0
    for s in stmts:
        if s.kind != "STMT":
            continue
        ops = s.operands.upper()
        if s.op == "JOB":
            njob += 1
        elif s.op == "EXEC":
            if not re.search(r"(^|,)PGM=", ops):
                out.add("PROC_USE")
            if re.search(r"(^|,)COND=", ops):
                out.add("COND_PARAMETER")
        elif s.op in ("PROC", "PEND"):
            out.add("PROC_DEFINITION")
        elif s.op == "INCLUDE":
            out.add("INCLUDE")
        elif s.op in ("IF", "ELSE", "ENDIF"):
            out.add("IF_THEN_ELSE")
        elif s.op == "JCLLIB":
            out.add("JCLLIB")
        elif s.op == "SET":
            out.add("SET_STATEMENT")
        elif s.op == "DD":
            if _GDG_RE.search(ops):
                out.add("GDG_REFERENCE")
            if (ops.split(",", 1)[0].strip() == "DATA" or "DLM=" in ops) and \
                    any(d.startswith("//") for d in s.data):
                out.add("INSTREAM_JCL_DATA")
        if _SYMBOL_RE.search(s.operands):
            out.add("SYMBOLIC_PARAMETERS")
    if njob > 1:
        out.add("MULTI_JOB")
    return out


# ---------------------------------------------------------------------------
# per-file execution (mirrors relic_eval.pipeline.run_benchmark)
# ---------------------------------------------------------------------------

class _FileTimeout(BaseException):
    """BaseException so that the detectors' broad `except Exception` cannot swallow it."""


def _alarm(seconds: int):
    def handler(_signum, _frame):
        raise _FileTimeout()
    signal.signal(signal.SIGALRM, handler)
    signal.alarm(seconds)


_SUBJ_CACHE: dict[str, tuple] = {}


def repo_context(repo_key: str, root: str):
    """(proclib, cobol_sources) of a repository, built like Subject.proclib / Subject.cobol_sources."""
    if repo_key not in _SUBJ_CACHE:
        from relic_eval.subjects import Subject
        subj = Subject(key=repo_key, title=repo_key, root=Path(root), url="", license="", pinned="",
                       role="external", exclude=("/.git/",))
        _SUBJ_CACHE[repo_key] = (subj.proclib, subj.cobol_sources)
    return _SUBJ_CACHE[repo_key]


def _detectors():
    from relic_eval.detectors import RelicDetector, TextDiffDetector
    from relic_eval.v2_eval import TextDiffIgnoreJobCard
    return [RelicDetector(legacy_v1_0=True), RelicDetector(legacy_v1_0=False),
            RelicDetector(legacy_v1_0=False, v2=True), TextDiffDetector(), TextDiffIgnoreJobCard()]


def evaluate_text(repo_key: str, rel: str, original: str, proclib, cobol_sources,
                  detectors=None) -> list[dict]:
    """All candidate-mutant records of one file (same status logic as pipeline.run_benchmark)."""
    import traceback

    from jcl_oracle.judge import compare_versions
    from relic_eval.mutate import OPERATOR_CATEGORY, OPERATOR_CONTRACT_TYPE, generate
    detectors = detectors or _detectors()
    ap = f"{repo_key}/{rel}"
    records: list[dict] = []
    try:
        mutants = generate(original)
    except Exception as exc:
        return [{"mutation_id": f"{repo_key}/{rel}/GENERATOR/0", "repo": repo_key, "file": rel,
                 "operator": "GENERATOR", "status": "INFRASTRUCTURE_FAILURE",
                 "status_reason": f"generator crashed: {exc!r}"[:300], "oracle_label": None,
                 "truth": None, "pred": {}, "pred_status": {}}]
    per_op: dict[str, int] = {}
    seen: dict[str, str] = {}
    for mu in mutants:
        idx = per_op.get(mu.operator, 0)
        per_op[mu.operator] = idx + 1
        mid = f"{repo_key}/{rel}/{mu.operator}/{idx}"
        rec = {"mutation_id": mid, "repo": repo_key, "file": rel, "operator": mu.operator,
               "failure_category": OPERATOR_CATEGORY[mu.operator],
               "contract_type": OPERATOR_CONTRACT_TYPE[mu.operator], "site": mu.site,
               "scope": "OUT_OF_SCOPE" if mu.scope_note else "IN_SCOPE",
               "mutant_sha256": sha256_text(mu.text)[:16] if mu.text is not None else None,
               "oracle_label": None, "oracle_label_no_abend": None, "oracle_model_errors": [],
               "truth": None, "pred": {}, "pred_status": {}}
        status, reason = None, ""
        verdict = None
        if mu.text is None:
            status, reason = "INVALID_MUTATION", mu.invalid_reason
        elif mu.text in seen:
            status, reason = "OTHER", f"DUPLICATE of {seen[mu.text]} (identical mutant text)"
        if mu.text is not None and mu.text not in seen:
            seen[mu.text] = mid
        if status is None:
            try:
                verdict = compare_versions(original, mu.text, proclib, cobol_sources)
                v2 = compare_versions(original, mu.text, proclib, cobol_sources, scenario_set="no_abend")
                rec["oracle_label"] = verdict.label
                rec["oracle_label_no_abend"] = v2.label
                rec["oracle_model_errors"] = verdict.model_errors[:3]
            except Exception:
                status = "INFRASTRUCTURE_FAILURE"
                reason = "oracle crashed: " + traceback.format_exc(limit=2)[-300:]
        if status is None:
            for d in detectors:
                p = d.predict(original, mu.text, ap)
                rec["pred"][d.name] = p.flagged
                rec["pred_status"][d.name] = p.status
            label = rec["oracle_label"]
            if label == "INVALID":
                status, reason = "INVALID_MUTATION", "mutant is not well-formed JCL: " + "; ".join(verdict.model_errors)
            elif mu.scope_note:
                status, reason = "OUT_OF_SCOPE", mu.scope_note
            elif label == "UNDETERMINED":
                status = "OTHER"
                reason = ("ORACLE_UNDETERMINED: no modelled observable differs, but opaque step(s) changed "
                          "context: " + ", ".join(verdict.opaque_touched))
            else:
                status, reason = "EVALUABLE", f"oracle={label}"
        if rec["oracle_label"] in ("DIFFERENT", "EQUIVALENT"):
            rec["truth"] = rec["oracle_label"] == "DIFFERENT"
        rec["status"] = status
        rec["status_reason"] = reason[:300]
        records.append(rec)
    return records


def process_file(job: dict) -> dict:
    """Worker: one frozen file -> records (+ file-level outcome). Never raises."""
    repo_key, rel, root = job["repo"], job["path"], job["root"]
    out = {"repo": repo_key, "file": rel, "outcome": "OK", "detail": "", "records": [],
           "features": [], "oracle_model_errors_on_original": []}
    try:
        path = Path(root) / rel
        if sha256_bytes(path.read_bytes()) != job["sha256"]:
            out.update(outcome="FREEZE_MISMATCH", detail="file sha256 differs from SUBJECT_FREEZE.json")
            return out
        original = path.read_text(errors="replace")   # same decoding as Subject.jcl_files
        out["features"] = sorted(syntax_features(original))
        _alarm(PER_FILE_TIMEOUT_S)
        proclib, cobol = repo_context(repo_key, root)
        from jcl_oracle.model import build_model
        out["oracle_model_errors_on_original"] = build_model(original, proclib).errors[:3]
        out["records"] = evaluate_text(repo_key, rel, original, proclib, cobol)
    except _FileTimeout:
        out.update(outcome="TIMEOUT", detail=f"per-file timeout {PER_FILE_TIMEOUT_S}s; partial records discarded",
                   records=[])
    except Exception as exc:  # recorded, not patched
        out.update(outcome="EXCEPTION", detail=repr(exc)[:300], records=[])
    finally:
        signal.alarm(0)
    return out


def robustness_file(job: dict) -> dict:
    """Parser/oracle/detector robustness on an UNMUTATED file (no labels involved)."""
    repo_key, rel, root = job["repo"], job["path"], job["root"]
    res = {"repo": repo_key, "file": rel, "lex": "OK", "oracle_model": "OK", "oracle_model_errors": 0,
           "generator": "OK", "detectors": {}, "features": []}
    try:
        text = (Path(root) / rel).read_text(errors="replace")
        _alarm(ROBUSTNESS_TIMEOUT_S)
        try:
            res["features"] = sorted(syntax_features(text))
        except Exception as exc:
            res["lex"] = f"EXCEPTION {exc!r}"[:200]
        try:
            from jcl_oracle.model import build_model
            proclib, _cob = repo_context(repo_key, root)
            res["oracle_model_errors"] = len(build_model(text, proclib).errors)
        except Exception as exc:
            res["oracle_model"] = f"EXCEPTION {exc!r}"[:200]
        try:
            from relic_eval.mutate import generate
            generate(text)
        except Exception as exc:
            res["generator"] = f"EXCEPTION {exc!r}"[:200]
        for d in _detectors()[:3]:
            p = d.predict(text, text, f"{repo_key}/{rel}")
            res["detectors"][d.name] = p.status if p.status == "OK" else f"ERROR {p.detail.get('error', '')}"[:200]
    except _FileTimeout:
        res["lex"] = "TIMEOUT"
    except Exception as exc:
        res["lex"] = f"EXCEPTION {exc!r}"[:200]
    finally:
        signal.alarm(0)
    return res


# ---------------------------------------------------------------------------
# metrics
# ---------------------------------------------------------------------------

def mcc(c: dict) -> float | None:
    tp, fp, fn, tn = c["tp"], c["fp"], c["fn"], c["tn"]
    den = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    return None if den == 0 else round((tp * tn - fp * fn) / den, 4)


def _block(rows: list[dict], with_bootstrap: bool = True) -> dict:
    from relic_eval.metrics import cluster_bootstrap, confusion
    dets = {}
    for d in DETECTORS:
        c = confusion(rows, d).as_dict()
        c["mcc"] = mcc(c)
        c["balanced_accuracy"] = (None if None in (c["recall"], c["specificity"])
                                  else round((c["recall"] + c["specificity"]) / 2, 4))
        # error-as-wrong bound: a detector ERROR on a positive is a miss (already FN); on a negative a FP
        n_err_pos = sum(1 for r in rows if r["pred"].get(d) is None and r["truth"])
        n_err_neg = sum(1 for r in rows if r["pred"].get(d) is None and not r["truth"])
        c["errors_on_positives"] = n_err_pos
        c["errors_on_negatives"] = n_err_neg
        c["error_as_wrong"] = {"fn": c["fn"], "fp": c["fp"] + n_err_neg}
        dets[d] = c
    block = {"n": len(rows), "positives": sum(r["truth"] for r in rows),
             "negatives": sum(not r["truth"] for r in rows),
             "n_files": len({r["cluster"] for r in rows}), "detectors": dets}
    if with_bootstrap:
        pairs = [("relic_v2", "relic_v1_1"), ("relic_v2", "relic_v1_0"), ("relic_v2", "textdiff"),
                 ("relic_v2", "textdiff_ignore_job_parameters")]
        block["bootstrap"] = cluster_bootstrap(rows, DETECTORS, pairs)
    return block


def compute_metrics(records: list[dict], file_results: list[dict], robustness: list[dict],
                    freeze: dict) -> dict:
    roles = {r["key"]: r["role"] for r in freeze["repos"]}
    eff_repos = sorted(k for k, v in roles.items() if v == ROLE_EFFECTIVENESS)
    by_repo: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        by_repo[r["repo"]].append(r)

    evaluable = [{"truth": bool(r["truth"]), "pred": r["pred"], "operator": r["operator"],
                  "repo": r["repo"], "cluster": f"{r['repo']}/{r['file']}"}
                 for r in records if r["status"] == "EVALUABLE" and r["repo"] in eff_repos]

    pops: dict = {"pooled_effectiveness": _block(evaluable)}
    pops["per_repo"] = {k: _block([r for r in evaluable if r["repo"] == k]) for k in eff_repos
                        if any(r["repo"] == k for r in evaluable)}
    pops["pooled_excluding_yetacp_mvs_sysgen"] = _block([r for r in evaluable
                                                        if r["repo"] != "yetacp_mvs_sysgen"])
    pops["leave_one_repo_out"] = {
        k: _block([r for r in evaluable if r["repo"] != k], with_bootstrap=False)
        for k in sorted({r["repo"] for r in evaluable})}
    per_op = {}
    for op in sorted({r["operator"] for r in evaluable}):
        per_op[op] = _block([r for r in evaluable if r["operator"] == op], with_bootstrap=False)
    pops["per_operator_pooled"] = per_op

    # ---- accounting
    accounting: dict = {}
    for k in eff_repos:
        rs = by_repo.get(k, [])
        frepo = next(r for r in freeze["repos"] if r["key"] == k)
        fres = [f for f in file_results if f["repo"] == k]
        status = Counter(r["status"] for r in rs)
        reasons = Counter()
        for r in rs:
            if r["status"] == "OTHER":
                reasons["ORACLE_UNDETERMINED" if r["status_reason"].startswith("ORACLE_UNDETERMINED")
                        else "DUPLICATE_MUTANT_TEXT"] += 1
            elif r["status"] in ("INVALID_MUTATION", "OUT_OF_SCOPE", "INFRASTRUCTURE_FAILURE"):
                reasons[f"{r['status']}:{r['status_reason'][:70]}"] += 1
        labels = Counter(r["oracle_label"] for r in rs if r["oracle_label"])
        det_err = {d: sum(1 for r in rs if r["pred_status"].get(d) == "ERROR") for d in DETECTORS}
        det_err_eval = {d: sum(1 for r in rs if r["status"] == "EVALUABLE" and r["pred_status"].get(d) == "ERROR")
                        for d in DETECTORS}
        files_with_eval = {r["file"] for r in rs if r["status"] == "EVALUABLE"}
        n_cand = len(rs)
        accounting[k] = {
            "files": {"jcl_total": frepo["n_jcl_files"],
                      "with_job": sum(1 for f in frepo["files"] if f["n_job"] >= 1),
                      "eligible_frozen": frepo["n_eligible"],
                      "excluded_frozen": frepo["n_jcl_files"] - frepo["n_eligible"],
                      "exclusion_reason_counts": dict(sorted(Counter(
                          x.split(" OF ")[0] for f in frepo["files"] for x in f["exclusion_reasons"]).items())),
                      "run_ok": sum(1 for f in fres if f["outcome"] == "OK"),
                      "run_timeout": sum(1 for f in fres if f["outcome"] == "TIMEOUT"),
                      "run_exception": sum(1 for f in fres if f["outcome"] == "EXCEPTION"),
                      "run_freeze_mismatch": sum(1 for f in fres if f["outcome"] == "FREEZE_MISMATCH"),
                      "with_at_least_one_evaluable_mutant": len(files_with_eval),
                      "oracle_model_errors_on_original": sum(1 for f in fres if f["oracle_model_errors_on_original"])},
            "mutants": {"candidates": n_cand, "status": {s: status.get(s, 0) for s in
                        ["EVALUABLE", "OUT_OF_SCOPE", "INVALID_MUTATION", "INFRASTRUCTURE_FAILURE", "OTHER"]},
                        "status_reasons": dict(sorted(reasons.items())),
                        "oracle_labels": dict(sorted(labels.items())),
                        "oracle_abstain_undetermined": labels.get("UNDETERMINED", 0),
                        "coverage_evaluable_over_candidate_mutants":
                            None if n_cand == 0 else round(status.get("EVALUABLE", 0) / n_cand, 4)},
            "file_coverage_eligible_files_with_evaluable_over_all_jcl_files":
                None if frepo["n_jcl_files"] == 0 else round(len(files_with_eval) / frepo["n_jcl_files"], 4),
            "detector_ERROR_counts_all_candidates": det_err,
            "detector_ERROR_counts_evaluable": det_err_eval,
        }
    tot_status = Counter()
    for k in eff_repos:
        tot_status.update(accounting[k]["mutants"]["status"])
    tot_cand = sum(tot_status.values())
    accounting["_total"] = {
        "candidate_mutants": tot_cand, "status": dict(tot_status),
        "coverage_evaluable_over_candidate_mutants":
            None if tot_cand == 0 else round(tot_status["EVALUABLE"] / tot_cand, 4),
        "jcl_files_total": sum(accounting[k]["files"]["jcl_total"] for k in eff_repos),
        "eligible_frozen": sum(accounting[k]["files"]["eligible_frozen"] for k in eff_repos),
        "files_with_evaluable": sum(accounting[k]["files"]["with_at_least_one_evaluable_mutant"] for k in eff_repos),
        "run_timeout": sum(accounting[k]["files"]["run_timeout"] for k in eff_repos),
        "run_exception": sum(accounting[k]["files"]["run_exception"] for k in eff_repos),
    }

    # ---- unsupported-syntax prevalence (per repo; denominator = .jcl files with a JOB statement,
    #      and separately = frozen eligible files)
    prevalence: dict = {}
    rob_by_key = {(r["repo"], r["file"]): r for r in robustness}
    for repo in freeze["repos"]:
        k = repo["key"]
        job_files = [f for f in repo["files"] if f["n_job"] >= 1]
        elig = [f for f in repo["files"] if f["eligible"]]

        def feats(fl):
            c = Counter()
            for f in fl:
                for x in rob_by_key.get((k, f["path"]), {}).get("features", []):
                    c[x] += 1
            return {x: c.get(x, 0) for x in SYNTAX_FEATURES}
        prevalence[k] = {"role": repo["role"], "files_with_job": len(job_files),
                         "counts_over_files_with_job": feats(job_files),
                         "eligible_files": len(elig), "counts_over_eligible_files": feats(elig)}

    # ---- robustness
    rob: dict = {}
    for repo in freeze["repos"]:
        k = repo["key"]
        rs = [r for r in robustness if r["repo"] == k]
        rob[k] = {
            "files": len(rs),
            "lex_exceptions": sum(1 for r in rs if r["lex"] != "OK"),
            "oracle_model_exceptions": sum(1 for r in rs if r["oracle_model"] != "OK"),
            "oracle_model_error_files": sum(1 for r in rs if r["oracle_model"] == "OK" and r["oracle_model_errors"]),
            "generator_exceptions": sum(1 for r in rs if r["generator"] != "OK"),
            "detector_parse_ERRORs": {d: sum(1 for r in rs if r["detectors"].get(d, "OK") != "OK")
                                      for d in ("relic_v1_0", "relic_v1_1", "relic_v2")},
        }

    dev_ref = None
    if DEV_METRICS.exists():
        dm = json.loads(DEV_METRICS.read_text())
        dev_ref = {"source": "results/v2/v2_metrics.json (development replay, same oracle)",
                   "pooled": {d: {k: dm["populations"]["pooled"]["detectors"][d][k]
                                  for k in ("tp", "fp", "fn", "tn", "precision", "recall", "f1", "specificity")}
                              for d in DETECTORS},
                   "per_subject_f1": {s: {d: dm["populations"][s]["detectors"][d]["f1"] for d in DETECTORS}
                                      for s in ("carddemo", "genapp", "omp_course")}}
    return {
        "schema": SCHEMA,
        "caveats": [
            "Labels come from the same, non-independent jcl_oracle used in development: this tests "
            "generalisation of the parser/detector to unseen files, NOT independent ground truth.",
            "Repositories are 'screened by aggregate counts/fragments', never blind.",
            "Few repositories contribute: no repository-level generalisation claim; CIs at file level are "
            "cluster-bootstrap over files and are optimistic regarding repository heterogeneity.",
            "Ground-truth positives/negatives follow the oracle: negatives are mostly comment/MSGCLASS "
            "edits plus oracle-equivalent fault mutants (see dev adequacy note in results/v2).",
        ],
        "freeze_relic_commit": freeze["relic_commit"],
        "detectors": DETECTORS,
        "populations": pops,
        "accounting": accounting,
        "unsupported_syntax_prevalence": prevalence,
        "robustness": rob,
        "dev_reference": dev_ref,
    }


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------

def verify_freeze(freeze: dict, clones: Path) -> None:
    for repo in freeze["repos"]:
        root = clones / next(r["dir"] for r in REPOS if r["key"] == repo["key"])
        head = git(["rev-parse", "HEAD"], root)
        if head != repo["pinned_sha"]:
            raise SystemExit(f"{repo['key']}: clone HEAD {head} != frozen SHA {repo['pinned_sha']}")


def run(clones: Path, freeze_path: Path, out: Path, workers: int) -> dict:
    freeze = json.loads(freeze_path.read_text())
    verify_freeze(freeze, clones)
    dirs = {r["key"]: str(clones / r["dir"]) for r in REPOS}
    eff_jobs, rob_jobs = [], []
    for repo in freeze["repos"]:
        for f in repo["files"]:
            base = {"repo": repo["key"], "path": f["path"], "root": dirs[repo["key"]], "sha256": f["sha256"]}
            rob_jobs.append(base)
            if f["eligible"]:
                eff_jobs.append(base)
    eff_jobs.sort(key=lambda j: (j["repo"], j["path"]))
    rob_jobs.sort(key=lambda j: (j["repo"], j["path"]))
    os.environ.setdefault("PYTHONHASHSEED", "0")
    print(f"effectiveness files: {len(eff_jobs)}; robustness files: {len(rob_jobs)}", flush=True)
    with ProcessPoolExecutor(max_workers=workers) as ex:
        file_results = []
        for i, res in enumerate(ex.map(process_file, eff_jobs, chunksize=1)):
            file_results.append(res)
            print(f"[{i + 1}/{len(eff_jobs)}] {res['repo']}/{res['file']} {res['outcome']} "
                  f"{len(res['records'])} mutants", flush=True)
        robustness = list(ex.map(robustness_file, rob_jobs, chunksize=4))
    file_results.sort(key=lambda r: (r["repo"], r["file"]))
    robustness.sort(key=lambda r: (r["repo"], r["file"]))
    records = sorted((r for f in file_results for r in f["records"]), key=lambda r: r["mutation_id"])
    metrics = compute_metrics(records, file_results, robustness, freeze)
    write_outputs(out, records, file_results, robustness, freeze, metrics)
    return metrics


def write_outputs(out: Path, records, file_results, robustness, freeze, metrics) -> None:
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "metrics.json", "w") as fh:
        json.dump(metrics, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(out / "predictions.jsonl", "w") as fh:
        for r in records:
            fh.write(json.dumps(r, sort_keys=True) + "\n")
    exclusions = {
        "schema": SCHEMA,
        "excluded_at_freeze": [
            {"repo": repo["key"], "file": f["path"], "reasons": f["exclusion_reasons"]}
            for repo in freeze["repos"] for f in repo["files"] if not f["eligible"]],
        "run_failures": [
            {"repo": f["repo"], "file": f["file"], "outcome": f["outcome"], "detail": f["detail"]}
            for f in file_results if f["outcome"] != "OK"],
        "oracle_model_errors_on_original": [
            {"repo": f["repo"], "file": f["file"], "errors": f["oracle_model_errors_on_original"]}
            for f in file_results if f["oracle_model_errors_on_original"]],
        "infrastructure_failures": [
            {"mutation_id": r["mutation_id"], "reason": r["status_reason"]}
            for r in records if r["status"] == "INFRASTRUCTURE_FAILURE"],
        "robustness_failures": [
            r for r in robustness
            if r["lex"] != "OK" or r["oracle_model"] != "OK" or r["generator"] != "OK"
            or any(v != "OK" for v in r["detectors"].values())],
        "repos_not_acquired": freeze["repos_not_acquired"],
    }
    with open(out / "exclusions.json", "w") as fh:
        json.dump(exclusions, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(out / "run_info.json", "w") as fh:
        json.dump({
            "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "python": sys.version.split()[0], "platform": platform.platform(),
            "relic_commit_at_run": git(["rev-parse", "HEAD"], ROOT),
            "relic_commit_at_freeze": freeze["relic_commit"],
            "frozen_code_sha256_at_run": harness_hashes(),
            "frozen_code_unchanged_since_freeze": harness_hashes() == freeze["frozen_code_sha256"],
            "harness_sha256_at_freeze": freeze.get("harness_sha256"),
            "harness_sha256_at_run": sha256_bytes(Path(__file__).read_bytes()),
            "per_file_timeout_s": PER_FILE_TIMEOUT_S, "PYTHONHASHSEED": os.environ.get("PYTHONHASHSEED"),
            "n_candidate_mutants": len(records),
            "metrics_sha256": sha256_bytes((out / "metrics.json").read_bytes()),
            "predictions_sha256": sha256_bytes((out / "predictions.jsonl").read_bytes()),
        }, fh, indent=2, sort_keys=True)
        fh.write("\n")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("freeze", help="write results/external/SUBJECT_FREEZE.json (no detector/oracle run)")
    f.add_argument("--clones", required=True, type=Path)
    f.add_argument("--out", type=Path, default=FREEZE_PATH)
    r = sub.add_parser("run", help="run the frozen subjects")
    r.add_argument("--clones", required=True, type=Path)
    r.add_argument("--freeze", type=Path, default=FREEZE_PATH)
    r.add_argument("--out", type=Path, default=OUT)
    r.add_argument("--workers", type=int, default=4)
    args = ap.parse_args(argv)
    if args.cmd == "freeze":
        if args.out.exists():
            raise SystemExit(f"{args.out} already exists: the freeze is write-once")
        fr = build_freeze(args.clones)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(fr, indent=2, sort_keys=True) + "\n")
        t = fr["totals"]
        print(f"frozen: {t['effectiveness_eligible_files']} eligible of {t['effectiveness_jcl_files']} "
              f"effectiveness-repo files; {t['robustness_only_jcl_files']} robustness-only files")
    else:
        m = run(args.clones, args.freeze, args.out, args.workers)
        p = m["populations"]["pooled_effectiveness"]
        for d in DETECTORS:
            c = p["detectors"][d]
            print(f"{d:32s} TP {c['tp']:4d} FP {c['fp']:3d} FN {c['fn']:4d} TN {c['tn']:4d} "
                  f"P {c['precision']} R {c['recall']} F1 {c['f1']}")


if __name__ == "__main__":
    main()
