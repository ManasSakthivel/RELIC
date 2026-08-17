# Reproducibility Guide
## LEGACY-CONTRACT — Complete Reproducibility Protocol

---

## CORE PRINCIPLE

A researcher unfamiliar with this project should be able to:
1. Clone the repository
2. Run `make setup`
3. Run `make reproduce-paper1`
4. Obtain results matching those in the paper (within reported variance bounds for LLM components)

---

## REQUIREMENTS

### Software versions (pinned)

```
Python: 3.11.x (see pyproject.toml)
GnuCOBOL: 3.1.2
Node.js: 20.x (for UI)
Docker: 24.x
All Python packages: pinned in pyproject.toml [tool.poetry.dependencies]
```

### Hardware requirements

```
RAM: 8GB minimum (16GB recommended for large trace analysis)
CPU: Any modern x86-64 or ARM64
Storage: 10GB for datasets + traces + results
GPU: Not required
```

---

## DATASET PREPARATION

```bash
# Download CardDemo dataset
make download-carddemo
# Verifies checksums against datasets/carddemo/ARTIFACTS.json

# Download supplementary public COBOL datasets
make download-public-cobol
```

All datasets are cached locally after first download. Re-running uses cached versions.

---

## TRACE GENERATION

```bash
# Generate all development and validation traces
make generate-traces

# This runs:
# 1. GnuCOBOL compilation of batch programs
# 2. Instrumented execution with controlled inputs
# 3. JCL batch job simulation
# 4. Normalization to ExecutionEvent schema
# All outputs in traces/dev/ and traces/validation/
```

**Random seeds:** All input generation uses seed 42 by default. Use `SEED=<n> make generate-traces` for different seeds.

---

## EXPERIMENTS

```bash
# Run all Paper 1 experiments
make run-experiments

# Individual experiments
make rq1          # Contract recovery
make rq2          # Risk detection comparison
make rq3          # Dynamic evidence value
make ablation     # Ablation study
make generalize   # Generalization experiment
```

---

## FIGURE AND TABLE GENERATION

```bash
# Generate all figures and tables from results
make figures
make tables

# Outputs:
# figures/fig_*.pdf
# paper/tables/*.md
# paper/table_source/*.tex
```

---

## LLM EXPERIMENT REPRODUCIBILITY

LLM-involving baselines (C, D, E7) are not bit-for-bit reproducible across model versions. To reproduce:

1. Use the model version specified in `config/llm_config.yaml`
2. Use the exact prompts in `src/contracts/prompts/` (versioned)
3. Report variance across 5 runs (scripts provided)

The deterministic BCG pipeline (no LLM) is fully bit-for-bit reproducible.

---

## VERSION TRACKING

```
experiments/rq1/config.yaml      — frozen experiment configuration
experiments/rq2/config.yaml      — frozen experiment configuration
experiments/rq3/config.yaml      — frozen experiment configuration
results/RUN_LOG.jsonl             — log of every experiment run with timestamp, seed, version
paper/PAPER_RESULTS_SNAPSHOT.json — results snapshot used to generate figures/tables in paper
```

---

## DOCKER CONTAINERIZATION

```bash
# Full reproducibility in Docker
docker-compose up research

# This mounts datasets and traces, runs all experiments, generates figures
```

The Docker image pins all software versions and is uploaded to Docker Hub at `legacy-contract/research:v1.0`.
