# Final Reproducibility Report

**System:** LEGACY-CONTRACT  
**Date:** 2026-08-14  
**Platform:** macOS arm64 (Apple Silicon)  

---

## Environment

| Component | Version | Path |
|---|---|---|
| Python | 3.11.15 | `python3` |
| GnuCOBOL | 3.2.0 | `cobc` |
| pytest | 9.1.1 | (installed in Python 3.11 venv) |
| OS | macOS / darwin 25.6.0 arm64 | — |

### Install GnuCOBOL (macOS)
```bash
brew install gnucobol
cobc --version  # should show 3.2.0+
```

### Python dependencies
```bash
cd legacy-contract
pip install -e ".[dev]"
# or: pip install -r requirements.txt
```

---

## Reproducing RQ1 (Contract Recovery)

```bash
cd legacy-contract

# Step 1: Build Level-2 deterministic ground truth
PYTHONPATH=src python3 scripts/build_ground_truth.py
# Output: benchmark/ground_truth/level2_deterministic.json (463 items)

# Step 2: Run RQ1 via ExperimentRunner
PYTHONPATH=src python3 -c "
import sys; sys.path.insert(0,'src'); sys.path.insert(0,'.')
from legacy_contract.evaluation.runner import ExperimentRunner
runner = ExperimentRunner(project_root='.')
runner.run('experiments/rq1/config.yaml', force=True)
"
# Output: results/rq1/metrics.json, results/rq1/per_type.csv
```

**Expected result:** F1=1.0000 (tautological — same extractor built GT).  
**Seed:** 42 (config frozen in `results/experiment_lock.json`)

---

## Reproducing RQ2 (Mutation Benchmark)

```bash
cd legacy-contract
PYTHONPATH=src python3 scripts/run_rq2.py
# Output: results/rq2/rq2_summary.json, results/rq2/rq2.csv
```

**Expected result:**
- static_bcg: P=1.0, R=1.0, F1=1.0 (TP=109, FP=0, FN=0)
- Baseline A (structural): P=1.0, R=0.7982, F1=0.8878
- 55 JCL files, 440 mutation attempts, 109 evaluated

---

## Reproducing Execution Traces

```bash
cd legacy-contract
PYTHONPATH=src python3 scripts/generate_execution_traces.py
# Output: traces/dev/EMPPAY_execution.json (EXECUTION — real GnuCOBOL run)
#         traces/dev/DEPTPAY_execution.json (EXECUTION — real GnuCOBOL run)
#         traces/dev/*_jclsim.json (11 files, EXECUTION_SIMULATED)
#         traces/dev/manifest_execution.json
```

**Requires:** GnuCOBOL 3.2.0 at `cobc`

---

## Reproducing Dynamic Reconciliation

```bash
cd legacy-contract
PYTHONPATH=src python3 scripts/run_dynamic_reconciliation.py
# Output: results/rq3/rq3_dynamic_results.json
```

**Expected result:** Dynamic validation rate = 0% (artifact_id mismatch — see FINAL_PROJECT_STATE.md for fix).

---

## Running the Test Suite

```bash
cd legacy-contract
PYTHONPATH=src python3 -m pytest tests/ -v
# Expected: 265 passed in ~0.15s
```

Test coverage includes:
- 48 scientific integrity tests (SI-01 through SI-12)
- Parser unit tests (JCL + COBOL)
- Contract model tests
- Reconciliation engine tests
- Mutation engine tests
- Baseline tests
- Integration pipeline tests
- Regression tests (known contracts always detectable)

---

## Docker Reproduction

```bash
cd legacy-contract
docker build -t legacy-contract:v1 .
docker run --rm legacy-contract:v1 \
  python3 -m pytest tests/ -q
```

Note: GnuCOBOL must be included in the Dockerfile (add `RUN brew install gnucobol` or equivalent for the target Linux base image).

---

## What Cannot Be Reproduced Without External Resources

| Item | Requirement | Workaround |
|---|---|---|
| Baselines C/D (LLM) | OpenAI API key (`OPENAI_API_KEY`) | Stubs run in offline mode, return [RESULT_PENDING] |
| CardDemo dynamic execution | DB2/CICS/IMS execution environment | Use EMPPAY/DEPTPAY standalone programs |
| Level-3 human annotation | Human annotators with JCL/COBOL expertise | Annotation protocol in `docs/annotation_protocol.md` |
| Production-grade RQ3 | Full CardDemo execution environment | Future work |

---

## Random Seed Policy

All experiments use `seed = 42`. This value is:
- Set in `experiments/*/config.yaml`
- Frozen in `results/experiment_lock.json`
- Used in `scripts/run_rq2.py` (`SEED = 42`)
- Used in dataset splits (`datasets/*/SPLITS_60_20_20.json`)

Do not change the seed without regenerating all splits, re-running all experiments, and updating `experiment_lock.json`.

---

## Confidence Weights

Weights are locked in `config/confidence_weights.yaml` (`locked: true`, `locked_at: 2026-08-14T22:00:00Z`). They must not be changed without:
1. Documenting the change in `docs/research_decisions.md`
2. Re-running all experiments from scratch
3. Updating `experiment_lock.json`

Changing weights after seeing results constitutes data leakage.

---

*This report documents the exact steps to reproduce the Paper 1 experimental results.*  
*Generated: 2026-08-14.*
