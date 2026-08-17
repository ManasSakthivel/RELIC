# LEGACY-CONTRACT

**Execution-Grounded Behavioral Contract Recovery for Legacy Batch Modernization Risk Detection**

![Python](https://img.shields.io/badge/python-3.11-blue)
![License](https://img.shields.io/badge/license-Apache%202.0-green)
![Tests](https://img.shields.io/badge/tests-305%20passing-brightgreen)

---

## At a Glance

| Artifact | Count |
|---|---|
| Legacy artifacts (JCL + COBOL + copybooks) | 161 |
| JCL files | 55 |
| COBOL programs | 44 |
| Copybooks | 62 |
| Evaluated contract-violating mutations | 104 |
| Semantics-preserving (negative) mutations | 144 |
| Tests | 305 |
| Dynamic validation rate | 91.8% |

> **Scope note:** All results are on the AWS CardDemo closed-set benchmark.
> They should not be interpreted as production-wide accuracy on arbitrary mainframe systems.

---

## Research Problem

Legacy COBOL/JCL batch systems encode implicit behavioral obligations across heterogeneous artifacts: step ordering constraints in JCL, dataset availability guarantees in DD disposition parameters, and return-code propagation guards in COND conditions. These obligations are never explicitly written down. When systems are modernized — migrated to cloud-native orchestration, translated to Java, re-hosted on Linux — these implicit contracts become invisible risks. The result is **semantic behavioral regression**: the modernized system runs without crashing but silently violates an obligation the original JCL enforced.

Existing tools identify *what depends on what* via structural dependency analysis. They cannot represent *what behavioral obligations must be preserved*.

---

## Key Idea

```
JCL + COBOL Artifacts
        ↓
   Parsers → IR (Intermediate Representation)
        ↓
Static Contract Extractor
  (TEMPORAL: A ≺ B, RESOURCE: produces→consumes, CONTROL_FLOW: RC guards)
        ↓
Behavioral Contract Graph  BCG = (V, E, C, P, D, Γ)
        ↓                              ↓
   BCGDiff                    Dynamic Evidence Adapter
   (broken + weakened             (GnuCOBOL traces +
    contracts)                     JCL simulation)
        ↓                              ↓
              Reconciliation Engine
           (SUPPORTED / CONFLICT / NOT_OBSERVED)
                        ↓
                  Risk Report
         (contract violations + evidence chains)
```

The discriminating contribution is **confidence-delta detection**: a contract can be *weakened* without being removed. Raising the COND threshold from `RC > 4` to `RC > 16` preserves the structural dependency graph but weakens the control-flow obligation. Structural analysis misses this. BCGDiff catches it.

---

## Research Contributions

1. **Formal BCG model** `BCG = (V, E, C, P, D, Γ)` — a provenance-aware intermediate representation for behavioral obligations across JCL and COBOL artifacts
2. **Static extraction pipeline** for TEMPORAL, RESOURCE, and CONTROL_FLOW contracts with deterministic, reproducible provenance
3. **Dynamic Evidence Adapter** with normalized `ExecutionEvent` schema and `ArtifactMapper` for deterministic program→step resolution
4. **Confidence-delta differencing** (`BCGDiff`) that detects both broken and weakened contracts — catching `ALTER_ERROR_BRANCH` mutations invisible to all structural baselines
5. **Fault-grounded mutation framework** with 8 operators (F1/F2/F3) and 5 semantics-preserving negative operators, derived from documented real-world modernization failures
6. **Empirical evaluation** on the AWS CardDemo benchmark with 305 tests, 104+144 mutation benchmark, and 91.8% dynamic validation rate

---

## Motivating Example

Original JCL:
```jcl
//STEP02 EXEC PGM=CBACT02C,
//  COND=(4,GT,STEP01)      ← skip STEP02 if STEP01 returned RC > 4
```

After `ALTER_ERROR_BRANCH` modernization mutation:
```jcl
//STEP02 EXEC PGM=CBACT02C,
//  COND=(16,GT,STEP01)     ← threshold raised: STEP02 now runs on soft errors
```

The structural dependency graph is **identical** in both versions (STEP02 still follows STEP01, same datasets). Structural Baseline A and BCG-without-confidence-delta (Baseline E) both miss this. BCG represents a CONTROL_FLOW contract with `static_support=1.0`; the mutation lowers it to `0.7`. `BCGDiff` detects `Δ=0.3 > θ` and raises a risk flag.

---

## Evaluation Results

All numbers are sourced from `results/FINAL_RESULTS_MANIFEST.json` (v1.4, frozen).

### RQ2 — Modernization Risk Detection (104 evaluated mutations, 144 negative)

| Method | F1 | TP | FN | FPR |
|---|---|---|---|---|
| **BCG (proposed)** | **1.0000** | **104** | **0** | **0.000** |
| Baseline E — Static BCG, no confidence-delta | 0.9600 | 96 | 8 | 0.000 |
| Baseline A — Structural dependency | 0.8995 | 85 | 19 | 0.000 |
| Baseline D — Dependency + LLM† | 0.1091 | 6 | 98 | 0.000 |
| Baseline C — LLM-only† | 0.0377 | 2 | 102 | 0.000 |
| Baseline B — Complexity metrics | 0.0000 | 0 | 104 | 0.000 |

† LLM baselines are lower bounds: 245/248 (C) and 241/248 (D) API calls failed. Model: Groq `llama-3.3-70b-versatile`, v2_blinded prompts. Results are benchmark-specific.

**Key finding:** The single architectural difference between BCG (F1=1.00) and Baseline E (F1=0.96) is `diff.modified` detection for `ALTER_ERROR_BRANCH` — 8 mutations that weaken a control-flow obligation without removing it.

### RQ1 — Contract Recovery (TEMPORAL only, independent oracle, 33 held-out JCL files)

| Metric | Value |
|---|---|
| Micro-F1 | 1.0000 |
| Micro-Precision | 1.0000 |
| Micro-Recall | 1.0000 |
| Macro-F1 | 0.5758 |
| 95% CI | [0.39, 0.73] |
| TP / FP / FN | 56 / 0 / 0 |

Scope: TEMPORAL contracts only. The oracle is an independent regex-based implementation (same JCL spec, no shared code with the extractor). RESOURCE and CONTROL_FLOW contracts require human annotation for independent evaluation.

### RQ3 — Dynamic Validation (40 traces: 2 real GnuCOBOL + 38 JCL-simulated; NOT z/OS)

| State | Count |
|---|---|
| STATIC_DYNAMIC_SUPPORTED | 56 (91.8%) |
| STATIC_DYNAMIC_CONFLICT | 1 (1.6%) |
| NOT_OBSERVED | 4 (6.6%) |

Coverage experiment: validation rate increases monotonically from 1.6% (10% traces) to 91.8% (100% traces), empirically confirming `NOT_OBSERVED ≠ CONTRADICTED`.

---

## Dataset

**Primary corpus:** AWS Mainframe Modernization CardDemo  
**Source:** https://github.com/aws-samples/aws-mainframe-modernization-carddemo  
**License:** Apache 2.0 (see `datasets/carddemo/extracted/.../LICENSE`)  
**Artifact counts:** 161 total — 55 JCL, 44 COBOL, 62 copybooks  
**Split:** 60/20/20 dev/validation/test, seed=42 (`datasets/carddemo/SPLITS_60_20_20.json`)

See [`datasets/carddemo/README.md`](datasets/carddemo/README.md) for full dataset documentation.

---

## Quickstart

```bash
# 1. Clone
git clone https://github.com/ManasSakthivel/RELIC.git legacy-contract
cd legacy-contract

# 2. Install dependencies (Python 3.11 required)
pip install poetry
poetry install

# 3. Run all tests
make test
# Expected: 305 passed

# 4. Reproduce all deterministic paper results
make reproduce-paper1
# Outputs: results/rq1/, results/rq2/, results/rq3/
```

**For LLM baselines (Baseline C and D):**
```bash
export GROQ_API_KEY="your-groq-api-key"
python3.11 scripts/run_llm_baselines.py
```

**Using Docker (no local GnuCOBOL required):**
```bash
docker-compose up research
```

See [`docs/reproduction.md`](docs/reproduction.md) for the complete reproduction guide.

---

## Repository Structure

```
legacy-contract/
├── src/legacy_contract/     # Source code
│   ├── parsers/             # JCL, COBOL, copybook parsers
│   ├── ir/                  # Intermediate representation
│   ├── static_analysis/     # Contract extraction (TEMPORAL/RESOURCE/CONTROL_FLOW)
│   ├── dynamic_analysis/    # GnuCOBOL adapter, ArtifactMapper, event schema
│   ├── bcg/                 # BCG model (V,E,C,P,D,Γ) and BCGBuilder
│   ├── reconciliation/      # Static/dynamic reconciliation engine
│   ├── mutations/           # Mutation engine (8 operators) + negative mutations
│   ├── risk/                # BCGDiff + RiskDetector
│   └── evaluation/          # Metrics, benchmark runner, experiment runner
├── baselines/               # Baselines A–E implementations
├── tests/                   # 305 tests: unit / integration / regression / scientific
├── scripts/                 # Reproduction scripts (run_rq1_independent.py, etc.)
├── datasets/                # CardDemo (Apache 2.0) + public COBOL
├── traces/                  # GnuCOBOL execution traces + JCL simulation traces
├── benchmark/               # Level-2 deterministic ground truth + annotation package
├── experiments/             # Frozen experiment configurations (rq1–rq3, ablation)
├── results/                 # All experimental results (JSON + CSV)
├── figures/                 # Figure generation scripts
├── paper/                   # Paper manuscript (paper.tex), tables, figures
├── docs/                    # Research documentation
│   ├── architecture.md
│   ├── methodology.md
│   ├── reproduction.md
│   ├── limitations.md
│   └── ...
└── examples/                # Quickstart examples
    └── quickstart/
```

---

## Reproducibility Map

| Research Question | Script | Result file | Paper section |
|---|---|---|---|
| RQ1 — Contract recovery | `scripts/run_rq1_independent.py` | `results/rq1/rq1_independent.json` | §10 |
| RQ2 — Risk detection (positive) | `scripts/run_rq2.py` | `results/rq2/rq2_summary.json` | §11 |
| RQ2 — Risk detection (negative) | `scripts/run_negative_mutations.py` | `results/rq2/negative_summary.json` | §11 |
| RQ2 — LLM baselines | `scripts/run_llm_baselines.py` | `results/rq2/llm_c_results.json`, `llm_d_results.json` | §11 |
| RQ3 — Dynamic reconciliation | `scripts/run_dynamic_reconciliation.py` | `results/rq3/rq3_dynamic_results.json` | §12 |
| RQ3 — Coverage experiment | `scripts/run_coverage_experiment.py` | `results/rq3/coverage_experiment.json` | §12 |

All results reproducible via: `make reproduce-paper1` (LLM baselines require `GROQ_API_KEY`).

---

## Limitations

The following limitations apply to all results in this repository. See [`docs/limitations.md`](docs/limitations.md) for full details.

1. **CardDemo-only evaluation** — all results are on one benchmark application; generalization to production enterprise systems has not been measured
2. **GnuCOBOL, not z/OS** — dynamic evidence is from GnuCOBOL 3.2.0 on Linux/macOS; IBM-specific CICS/DB2/IMS semantics are not executed
3. **Simulated traces** — 38 of 40 execution traces are JCL-ordering simulations, not real program execution
4. **TEMPORAL-only independent oracle** — RQ1 micro-F1=1.00 covers only TEMPORAL contracts; RESOURCE and CONTROL_FLOW require human annotation
5. **FPR=0 is a closed-set design consequence** — the negative benchmark is semantics-preserving by construction, not an open-world false-positive measurement
6. **LLM results are lower bounds** — 97–98% API error rates in the LLM baseline runs; results reflect infrastructure constraints, not LLM capability in principle
7. **Confidence score is not a calibrated probability** — the `ConfidenceVector` produces an evidence-weighted score in [0,1], not a Bayesian probability

---

## Research Questions

- **RQ1:** Can TEMPORAL behavioral contracts be automatically recovered with precision and recall sufficient for practical use, validated against an independently implemented oracle?
- **RQ2:** Does contract-aware BCG analysis improve modernization-risk detection compared with structural, complexity, LLM-based, and static-BCG baselines?
- **RQ3:** Does dynamic execution evidence increase contract validation coverage while preserving zero false positives on a semantics-preserving benchmark?

---

## Paper

Manuscript: [`paper/paper.tex`](paper/paper.tex) (ACM sigconf, double-blind, anonymous)  
Tables: [`paper/tables/`](paper/tables/) — 10 tables (Markdown + LaTeX)  
Figures: [`paper/figures/`](paper/figures/) — 6 figures (PDF + PNG)  
References: [`paper/references.bib`](paper/references.bib)

---

## Citation

```bibtex
@inproceedings{legacycontract2025,
  title     = {Execution-Grounded Behavioral Contract Recovery for
               Legacy Batch Modernization Risk Detection},
  author    = {Anonymous Authors},
  booktitle = {Proceedings of the 47th International Conference on
               Software Engineering (ICSE 2025)},
  year      = {2025},
  note      = {Citation will be updated after double-blind review.}
}
```

See [`CITATION.cff`](CITATION.cff) for machine-readable citation metadata.

---

## License

Project code: Apache License 2.0 — see [`LICENSE`](LICENSE).  
CardDemo dataset: Apache License 2.0, copyright Amazon.com, Inc. — see `datasets/carddemo/extracted/.../LICENSE`.  
Third-party dataset details: [`datasets/carddemo/README.md`](datasets/carddemo/README.md).
