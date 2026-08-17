.PHONY: all setup download-carddemo download-public-cobol generate-traces \
        run-experiments rq1 rq2 rq3 ablation generalize \
        figures tables ui reproduce-paper1 test lint clean

PYTHON = python3.11
SEED ?= 42

all: test

setup:
	poetry install
	@echo "Setup complete."

download-carddemo:
	$(PYTHON) -m legacy_contract.datasets.download carddemo

download-public-cobol:
	$(PYTHON) -m legacy_contract.datasets.download public_cobol

generate-traces:
	SEED=$(SEED) $(PYTHON) -m legacy_contract.dynamic_analysis.generate_traces \
		--dataset datasets/carddemo \
		--output traces/dev \
		--split dev \
		--seed $(SEED)
	SEED=$(SEED) $(PYTHON) -m legacy_contract.dynamic_analysis.generate_traces \
		--dataset datasets/carddemo \
		--output traces/validation \
		--split validation \
		--seed $(SEED)

rq1:
	$(PYTHON) -m legacy_contract.evaluation.run_experiment \
		--config experiments/rq1/config.yaml \
		--seed $(SEED) \
		--output results/rq1/

rq2:
	$(PYTHON) -m legacy_contract.evaluation.run_experiment \
		--config experiments/rq2/config.yaml \
		--seed $(SEED) \
		--output results/rq2/

rq3:
	$(PYTHON) -m legacy_contract.evaluation.run_experiment \
		--config experiments/rq3/config.yaml \
		--seed $(SEED) \
		--output results/rq3/

ablation:
	$(PYTHON) -m legacy_contract.evaluation.run_experiment \
		--config experiments/ablation/config.yaml \
		--seed $(SEED) \
		--output results/ablation/

generalize:
	$(PYTHON) -m legacy_contract.evaluation.run_experiment \
		--config experiments/generalization/config.yaml \
		--seed $(SEED) \
		--output results/generalization/

# Updated RQ experiments use standalone scripts (reproducible, no module import issues)
run-rq1-independent:
	$(PYTHON) scripts/run_rq1_independent.py

run-rq2-positive:
	$(PYTHON) scripts/run_rq2.py

run-rq2-negative:
	$(PYTHON) scripts/run_negative_mutations.py

run-rq3-dynamic:
	$(PYTHON) scripts/run_dynamic_reconciliation.py

run-rq3-coverage:
	$(PYTHON) scripts/run_coverage_experiment.py

run-experiments: run-rq1-independent run-rq2-positive run-rq2-negative run-rq3-dynamic run-rq3-coverage

figures:
	$(PYTHON) figures/generate_all.py --results results/ --output figures/

tables:
	$(PYTHON) paper/table_source/generate_all.py --results results/ \
		--md-output paper/tables/ \
		--tex-output paper/table_source/

ui:
	cd ui && npm install && npm run dev

reproduce-paper1: ## Full reproduction of all paper results (deterministic; LLM baselines require GROQ_API_KEY)
	@echo "=== LEGACY-CONTRACT Paper 1 Full Reproduction ==="
	@echo "Step 1/5: Running RQ1 independent oracle evaluation..."
	$(PYTHON) scripts/run_rq1_independent.py
	@echo "Step 2/5: Running RQ2 positive mutation benchmark..."
	$(PYTHON) scripts/run_rq2.py
	@echo "Step 3/5: Running RQ2 negative mutation benchmark (FPR/TN)..."
	$(PYTHON) scripts/run_negative_mutations.py
	@echo "Step 4/5: Running RQ3 dynamic reconciliation..."
	$(PYTHON) scripts/run_dynamic_reconciliation.py
	@echo "Step 5/5: Running coverage experiment..."
	$(PYTHON) scripts/run_coverage_experiment.py
	@echo ""
	@echo "=== ALL EXPERIMENTS COMPLETE ==="
	@echo "Results written to:"
	@echo "  results/rq1/rq1_independent.json  (RQ1 independent oracle)"
	@echo "  results/rq2/rq2_summary.json       (RQ2 positive benchmark)"
	@echo "  results/rq2/negative_summary.json   (RQ2 negative benchmark, FPR)"
	@echo "  results/rq3/rq3_dynamic_results.json (RQ3 dynamic reconciliation)"
	@echo "  results/rq3/coverage_experiment.json (RQ3 coverage experiment)"
	@echo ""
	@echo "Key results:"
	@python3.11 -c "import json; r=json.load(open('results/rq1/rq1_independent.json')); print(f'  RQ1: micro-F1={r[\"micro_f1\"]:.4f}, macro-F1={r[\"macro_f1\"]:.4f} CI=[{r[\"f1_ci_lower\"]:.2f},{r[\"f1_ci_upper\"]:.2f}]')"
	@python3.11 -c "import json; r=json.load(open('results/rq2/rq2_summary.json')); print(f'  RQ2: static_bcg F1={r[\"static_bcg\"][\"f1\"]:.4f}, structural F1={r[\"structural_baseline_A\"][\"f1\"]:.4f}')"
	@python3.11 -c "import json; r=json.load(open('results/rq2/negative_summary.json')); print(f'  RQ2-NEG: TN={r[\"tn\"]}, FP={r[\"fp\"]}, FPR={r[\"fpr\"]:.4f}')"
	@python3.11 -c "import json; r=json.load(open('results/rq3/rq3_dynamic_results.json')); print(f'  RQ3: validation_rate={r[\"dynamic_validation_rate\"]:.4f}, SUPPORTED={r[\"contracts\"][\"STATIC_DYNAMIC_SUPPORTED\"]}')"

test:
	pytest tests/ -v

lint:
	black --check src/ tests/
	ruff check src/ tests/
	mypy src/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache
