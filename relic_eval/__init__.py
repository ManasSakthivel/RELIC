"""
relic_eval — the single authoritative evaluation pipeline for RELIC.

    subjects  ->  source-level mutants  ->  oracle labels (jcl_oracle)
              ->  detector predictions (RELIC + baselines, blind)
              ->  manifest + raw results  ->  metrics  ->  tables / figures / docs

Entry point: ``python -m relic_eval.pipeline`` (see Makefile target
``reproduce``). Every number reported in README.md, paper/ and docs/ is read
from ``results/final/metrics.json`` written by this package.
"""
