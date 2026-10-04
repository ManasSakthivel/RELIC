"""
Detectors evaluated on source-level mutants.

Every detector implements ``predict(original_text, mutated_text, artifact_path)
-> Prediction``. It receives the two JCL texts and the artifact path only —
never the mutation operator, the mutation site, or the oracle label
(enforced by ``tests/evaluation/test_blindness.py``).

Detectors:

  relic_v1_0     RELIC as released (commit 024a3f2 behaviour, legacy_v1_0=True)
  relic_v1_1     RELIC with the post-hoc spec-conformance fixes (default code)
  static_bcg_E   Baseline E: static BCG diff, broken contracts only (v1.0 parser)
  structural_A   Baseline A: structural dependency-graph edge diff (v1.0 parser)
  complexity_B   Baseline B: artifact complexity score above threshold (v1.0 parser)
  textdiff       Reference: any change outside comment statements
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from functools import lru_cache

from loguru import logger

from baselines.complexity.complexity import ComplexityBaseline
from baselines.static_bcg.static_bcg import StaticBCGBaseline
from baselines.structural.structural import StructuralBaselineAnalyzer
from legacy_contract.bcg.builder import BCGBuilder
from legacy_contract.mutations.engine import FailureCategory, MutationOperator, MutationRecord
from legacy_contract.parsers.jcl_parser import JCLParser
from legacy_contract.risk.detector import RiskDetector
from legacy_contract.static_analysis.extractor import StaticContractExtractor

logger.remove()


@dataclass
class Prediction:
    flagged: bool | None              # None = no prediction (error / not run)
    status: str = "OK"                # OK, ERROR, NOT_RUN
    detail: dict = field(default_factory=dict)


def neutral_record() -> MutationRecord:
    """
    RiskDetector.detect() requires a MutationRecord for the *explanation* text
    of risk items. Detection itself never reads it (tested in
    tests/evaluation/test_blindness.py). A neutral placeholder is passed so that
    no information about the mutation reaches the detector.
    """
    return MutationRecord(
        mutation_id="source-diff",
        failure_category=FailureCategory.F1_JOB_ORDERING,
        source_evidence_ref="n/a",
        operator=MutationOperator.REORDER_JOBS,
        affected_entity_ids=[],
        affected_contract_ids=[],
        original_state="original source",
        mutated_state="modernized source",
        seed=0,
    )


def _parse(text: str, path: str, legacy: bool):
    _res, ir = JCLParser(legacy_v1_0=legacy).parse_lines(text.splitlines(), path)
    return ir


def _bcg(text: str, path: str, legacy: bool):
    ir = _parse(text, path, legacy)
    extraction = StaticContractExtractor(legacy_v1_0=legacy).extract(ir)
    return BCGBuilder().build(ir, extraction)


@lru_cache(maxsize=256)
def _bcg_cached(text: str, path: str, legacy: bool):
    return _bcg(text, path, legacy)


class RelicDetector:
    def __init__(self, legacy_v1_0: bool):
        self.legacy = legacy_v1_0
        self.name = "relic_v1_0" if legacy_v1_0 else "relic_v1_1"

    def predict(self, original: str, mutated: str, path: str) -> Prediction:
        try:
            b0 = _bcg_cached(original, path, self.legacy)
            b1 = _bcg(mutated, path, self.legacy)
            report = RiskDetector(legacy_v1_0=self.legacy).detect(b0, b1, neutral_record())
            n = len(report.risk_items) + len(report.false_positive_candidates)
            types = sorted({r.contract_type.value for r in
                            report.risk_items + report.false_positive_candidates})
            return Prediction(n > 0, detail={
                "n_risk_items": n,
                "violated_contract_types": types,
                "n_contracts_original": len(b0.contracts),
            })
        except Exception as exc:  # recorded, scored as "not flagged"
            return Prediction(None, "ERROR", {"error": repr(exc)[:300]})


class StaticBCGDetector:
    name = "static_bcg_E"

    def predict(self, original: str, mutated: str, path: str) -> Prediction:
        try:
            b0 = _bcg_cached(original, path, True)
            b1 = _bcg(mutated, path, True)
            res = StaticBCGBaseline().predict_from_bcgs(b0, b1, neutral_record())
            return Prediction(any(res.predictions.values()),
                              detail={"broken": res.metadata.get("broken_count", 0)})
        except Exception as exc:
            return Prediction(None, "ERROR", {"error": repr(exc)[:300]})


class StructuralDetector:
    name = "structural_A"

    def predict(self, original: str, mutated: str, path: str) -> Prediction:
        try:
            an = StructuralBaselineAnalyzer()
            s0 = an.analyze(_parse(original, path, True))
            s1 = an.analyze(_parse(mutated, path, True))
            risks = an.detect_risk(s0, s1)
            return Prediction(len(risks) > 0, detail={"missing_edges": len(risks)})
        except Exception as exc:
            return Prediction(None, "ERROR", {"error": repr(exc)[:300]})


class ComplexityDetector:
    """
    Baseline B scores the complexity of an artifact relative to its corpus.

    Two defects of the legacy harness are corrected here (weights and the 0.5
    threshold are unchanged — they were pre-specified and frozen):

    * it was handed ``mutation.affected_entity_ids`` (the answer key); here it
      receives a neutral record and scores the mutated artifact only;
    * it min-max normalised over the artifacts *in one IR*. The legacy harness
      built one IR per file, so every normalised metric was 0 and the baseline
      could never fire (F1 = 0.000 by construction). Here the mutated file is
      normalised against the whole subject corpus, as the baseline's design
      ("per-artifact metrics across all artifacts") intends.

    The baseline remains change-agnostic: it ranks risky artifacts, it does not
    inspect the change. It is kept as the non-semantic reference point.
    """
    name = "complexity_B"

    def __init__(self) -> None:
        self._corpus: dict[str, dict[str, object]] = {}

    def set_corpus(self, key: str, files: dict[str, str]) -> None:
        self._corpus[key] = {path: _parse(text, path, True) for path, text in files.items()}

    def predict(self, original: str, mutated: str, path: str, corpus_key: str | None = None) -> Prediction:
        try:
            from legacy_contract.ir.model import IRGraph
            merged = IRGraph()
            irs = dict(self._corpus.get(corpus_key or "", {}))
            irs[path] = _parse(mutated, path, True)
            for ap, ir in irs.items():
                merged.artifact_paths.append(ap)
                for e in ir.entities.values():
                    merged.add_entity(e)
                for r in ir.relations:
                    merged.add_relation(r)
            base = ComplexityBaseline()
            metrics = base.normalize(base.compute_metrics(merged))
            score = metrics[path].risk_score if path in metrics else 0.0
            from baselines.complexity.complexity import RISK_THRESHOLD
            return Prediction(score > RISK_THRESHOLD, detail={"risk_score": round(score, 4)})
        except Exception as exc:
            return Prediction(None, "ERROR", {"error": repr(exc)[:300]})


def _normalise(text: str) -> list[str]:
    out = []
    for line in text.splitlines():
        if line.startswith("//*"):
            continue
        out.append(line[:71].rstrip() if line.startswith("//") else line.rstrip())
    return out


class TextDiffDetector:
    """Flags any difference outside comment statements and sequence columns."""
    name = "textdiff"

    def predict(self, original: str, mutated: str, path: str) -> Prediction:
        return Prediction(_normalise(original) != _normalise(mutated))


def all_detectors() -> list:
    return [
        RelicDetector(legacy_v1_0=True),
        RelicDetector(legacy_v1_0=False),
        StaticBCGDetector(),
        StructuralDetector(),
        ComplexityDetector(),
        TextDiffDetector(),
    ]
