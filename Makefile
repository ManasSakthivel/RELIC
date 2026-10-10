# RELIC — reproducible workflow (macOS and Linux; needs Python >= 3.11).
#
#   make setup        create .venv and install pinned dependencies
#   make test         run the full test suite
#   make reproduce    regenerate every reported number, table and figure
#   make check        verify docs/tables/metrics are consistent with raw results
#   make llm-baselines  run LLM baselines C/D (needs an API key; optional)

# Bootstrap interpreter: first Python >= 3.11 on PATH, else one managed by uv, else python3.
PY_BOOT ?= $(shell command -v python3.11 || command -v python3.12 || command -v python3.13 || \
             (command -v uv >/dev/null 2>&1 && uv python find '>=3.11' 2>/dev/null) || echo python3)
VENV    ?= .venv
PYTHON  ?= $(if $(wildcard $(VENV)/bin/python),$(VENV)/bin/python,$(PY_BOOT))
export PYTHONPATH := $(CURDIR)/src:$(CURDIR)

.PHONY: setup test reproduce metrics check llm-baselines figures-legacy reproduce-legacy reproduce-paper1 clean

setup:
	$(PY_BOOT) -c 'import sys; assert sys.version_info >= (3, 11), "Python >= 3.11 required (found %s); set PY_BOOT=/path/to/python3.11" % sys.version.split()[0]'
	$(PY_BOOT) -m venv $(VENV)
	$(VENV)/bin/python -m pip install --upgrade pip
	$(VENV)/bin/python -m pip install -r requirements.lock
	@echo "Setup complete. (Alternative: uv venv --python 3.11 && uv pip install -r requirements.lock)"

test:
	$(PYTHON) -m pytest tests/ -q

# Full evaluation: mutants -> oracle labels -> detector predictions -> manifest
# -> metrics -> tables (Markdown + LaTeX) -> figures -> generated doc blocks.
#
# LLM step: if a provider key is set (RELIC_LLM_PROVIDER / GROQ_API_KEY /
# OPENAI_API_KEY / ANTHROPIC_API_KEY), queries the model for any uncached
# mutant and extends the cache.  Without a key the LLM step is skipped and
# the committed cache (results/final/raw/llm_cache/) is used to re-score the
# 383 already-answered mutants — offline, no API calls.
reproduce:
	$(PYTHON) -m relic_eval.pipeline
	$(PYTHON) -m relic_eval.llm_baselines --offline-if-no-key
	$(PYTHON) -m relic_eval.pipeline --skip-benchmark
	$(PYTHON) -m relic_eval.check_consistency

# Recompute metrics/tables/figures from the committed raw records only.
metrics:
	$(PYTHON) -m relic_eval.pipeline --skip-benchmark

check:
	$(PYTHON) -m relic_eval.check_consistency

llm-baselines:
	$(PYTHON) -m relic_eval.llm_baselines
	$(PYTHON) -m relic_eval.pipeline --skip-benchmark

# Deprecated name kept for old instructions.
reproduce-paper1: reproduce

# Legacy (pre-remediation) experiments, kept for provenance. Their RQ2 numbers
# are withdrawn; see docs/remediation/PRE_REMEDIATION_AUDIT.md.
reproduce-legacy:
	$(PYTHON) scripts/run_rq1_independent.py
	$(PYTHON) scripts/run_rq2.py
	$(PYTHON) scripts/run_negative_mutations.py
	$(PYTHON) scripts/run_dynamic_reconciliation.py
	$(PYTHON) scripts/run_coverage_experiment.py

figures-legacy:
	$(PYTHON) figures/generate_all.py --results results/ --output figures/

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache
