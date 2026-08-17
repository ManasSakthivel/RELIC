# Pre-Remediation State Snapshot
# LEGACY-CONTRACT Research Platform
# Captured: 2025-07 (before final remediation pass)

---

## Repository Identity

- **Git status:** Not a Git repository (no `.git` directory; single deployment snapshot)
- **Git commit hash:** NO_GIT (work is a file snapshot, not a versioned commit)
- **Python version (required):** Python 3.11 (`python3.11 -m pytest`)
- **Platform:** darwin arm64

---

## Dependency State

Installed via `pip3.11 install -e .`:

| Package | Version |
|---|---|
| lark | 1.3.1 |
| loguru | 0.7.3 |
| networkx | 3.2.1 |
| numpy | 2.0.2 |
| pandas | 2.3.3 |
| pydantic | 2.13.3 |
| scipy | 1.13.1 |

`poetry.lock`: **NOT committed** (P2-8).

---

## Test Count (pre-remediation)

```
265 passed in 0.12s
```

All tests passing at snapshot time.

---

## Experiment Lock

- `results/experiment_lock.json` present
- Locked at: `2026-08-14T17:00:28.622894Z`
- Random seed: `42`
- Bootstrap n: `10,000`
- Ground truth hash: `72e4af88b358fcf0`

---

## Current Result Files

| File | Status |
|---|---|
| `results/rq1/rq1_summary.json` | COMPLETE (SELF_CONSISTENCY_ONLY) |
| `results/rq1/rq1.csv` | COMPLETE |
| `results/rq2/rq2_summary.json` | PARTIAL (static conditions complete; LLM/dynamic BLOCKED) |
| `results/rq2/rq2.csv` | COMPLETE (static conditions) |
| `results/rq3/rq3_dynamic_results.json` | COMPLETE (49.2% dynamic validation rate) |
| `results/rq3/rq3_summary.json` | STALE — contradicts rq3_dynamic_results.json (P1-3) |
| `results/ablation/` | PARTIAL |
| `results/generalization/` | BLOCKED (no OMP GT) |

---

## Key Result Values (frozen, do not modify)

| Metric | Value |
|---|---|
| RQ1 F1 | 1.000 (SELF_CONSISTENCY_ONLY) |
| RQ2 Baseline A F1 | 0.8878 |
| RQ2 Baseline B F1 | 0.0000 |
| RQ2 Baseline E F1 | 0.9619 |
| RQ2 Proposed (static BCG) F1 | 1.0000 |
| RQ3 dynamic validation rate | 49.2% (31/63 contracts) |
| RQ3 STATIC_DYNAMIC_CONFLICT | 1 |
| RQ3 NOT_OBSERVED | 31 |
| N mutations attempted | 440 |
| N mutations not applicable | 331 (75%) |
| N mutations evaluated | 109 |

---

## Current Manuscript State

`paper/paper.md`: Present.

- Abstract: **overclaims** (P2-1, P2-2)
- §4 H2/H3: **untestable hypotheses** (P1-1, P2-3)
- §11 RQ1: Self-consistency caveat present; headline claim qualified in same paragraph ✓
- §11 RQ2: `[RESULT_PENDING]` in LLM baselines ✓
- §11 RQ3: H3 status stated as PARTIAL_EVIDENCE_AVAILABLE (needs UNTESTABLE declaration)

---

## Scientific Integrity Issues Identified (Pre-Remediation)

| ID | Issue | Status |
|---|---|---|
| P0-2 | SI-01 guard: SYNTHETIC_STATIC pre-outcome check | **ALREADY FIXED** in engine.py (verified in code review) |
| P1-2 | artifact_mapping.py not in src/ | **TO FIX** |
| P1-3 | rq3_summary.json stale | **TO FIX** |
| P2-1 | Abstract overclaim: "four operators invisible" | **TO FIX** |
| P2-2 | F1=1.0 closed-set caveat missing in abstract | **TO FIX** |
| P2-3 | H3 untestable — not declared in paper | **TO FIX** |

---

## Trace Files (pre-remediation)

Located in `traces/dev/`:

| File | Source Type |
|---|---|
| EMPPAY_execution.json | EXECUTION (real GnuCOBOL) |
| DEPTPAY_execution.json | EXECUTION (real GnuCOBOL) |
| CARDFILE_jclsim.json | EXECUTION_SIMULATED |
| CBEXPORT_jclsim.json | EXECUTION_SIMULATED |
| CUSTFILE_jclsim.json | EXECUTION_SIMULATED |
| DEFGDGD_jclsim.json | EXECUTION_SIMULATED |
| DISCGRP_jclsim.json | EXECUTION_SIMULATED |
| DUSRSECJ_jclsim.json | EXECUTION_SIMULATED |
| PRTCATBL_jclsim.json | EXECUTION_SIMULATED |
| READACCT_jclsim.json | EXECUTION_SIMULATED |
| TCATBALF_jclsim.json | EXECUTION_SIMULATED |
| TRANBKP_jclsim.json | EXECUTION_SIMULATED |
| TRANCATG_jclsim.json | EXECUTION_SIMULATED |
| ACCTFILE_synthetic.json | SYNTHETIC_STATIC |
| CBACT01C_synthetic.json | SYNTHETIC_STATIC |
| REPORT_synthetic.json | SYNTHETIC_STATIC |

---

## Dockerfile State (pre-remediation)

Line 9 reads: `gnucobol` (already correct — pre-audit found `gnucobol3`; current file is correct).

---

*This snapshot was created BEFORE remediation changes and should not be modified.*
