"""
Baseline E — Static BCG Only.

Runs the full static extraction pipeline (JCL parser → COBOL parser →
StaticContractExtractor → BCGBuilder) WITHOUT adding any dynamic evidence,
then uses BCG.diff() to identify contracts broken by a mutation.

Scientific purpose: direct comparator for RQ3 — "does dynamic evidence
(ReconciliationEngine) improve on static-only contract detection?"
Comparing Baseline E vs the full system (which adds dynamic traces) isolates
the contribution of dynamic grounding.

DESIGN INVARIANT:
- ReconciliationEngine is NEVER called here.
- dynamic_observations is always empty.
- All contracts remain STATIC_CANDIDATE after BCGBuilder.build().
- As a consequence, no contract in this baseline can ever have
  validation_state == STATIC_DYNAMIC_SUPPORTED.

Contract confidence:
    confidence = contract.confidence_score()  (static_support only, ≈ 0.25
    for temporal / ≈ 0.25 for resource because only the static_support
    dimension of ConfidenceVector is non-zero at this point)

Predictions:
    contract_id in BCGDiff.broken  → predicted_violated = True
    otherwise                       → predicted_violated = False
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from legacy_contract.bcg.builder import BCGBuilder
from legacy_contract.bcg.model import BCG
from legacy_contract.contracts.model import ValidationState
from legacy_contract.ir.model import IRGraph
from legacy_contract.static_analysis.extractor import StaticContractExtractor
from baselines.base import BaselineResult


class StaticBCGBaseline:
    """
    Baseline E: Static BCG Only.

    Usage::

        baseline = StaticBCGBaseline()
        result = baseline.predict(
            original_ir=ir_original,
            mutated_ir=ir_mutated,
            mutation=mutation_record,
            contract_ids=all_contract_ids,
        )

    Alternatively, if you have two BCGs already built without dynamic traces::

        result = baseline.predict_from_bcgs(
            original_bcg=bcg_orig,
            mutated_bcg=bcg_mut,
            mutation=mutation_record,
        )
    """

    def __init__(self) -> None:
        self._extractor = StaticContractExtractor()
        self._builder = BCGBuilder()

    # ------------------------------------------------------------------
    # Build helpers (static-only, NO dynamic traces)
    # ------------------------------------------------------------------

    def build_static_bcg(self, ir: IRGraph) -> BCG:
        """
        Build a BCG from an IR graph using static analysis only.

        Postcondition: all contracts have validation_state == STATIC_CANDIDATE.
        The BCGBuilder is called with traces=None so ReconciliationEngine is
        never invoked.
        """
        static_result = self._extractor.extract(ir)
        bcg = self._builder.build(ir, static_result, traces=None)

        # Verify the invariant
        for contract in bcg.contracts.values():
            assert contract.validation_state in {
                ValidationState.STATIC_CANDIDATE,
                ValidationState.NOT_OBSERVED,
            }, (
                f"StaticBCGBaseline invariant violated: contract {contract.contract_id} "
                f"has state {contract.validation_state} — dynamic evidence must not "
                f"be present in this baseline."
            )

        return bcg

    # ------------------------------------------------------------------
    # Main API
    # ------------------------------------------------------------------

    def predict(
        self,
        original_ir: IRGraph,
        mutated_ir: IRGraph,
        mutation: Any,          # MutationRecord
        contract_ids: list[str] | None = None,
    ) -> BaselineResult:
        """
        Build static BCGs for original and mutated IR, diff them, and return
        a BaselineResult flagging broken contracts as predicted violations.

        Parameters
        ----------
        original_ir:
            IRGraph for the original (pre-mutation) system.
        mutated_ir:
            IRGraph for the mutated (post-mutation) system.
        mutation:
            MutationRecord describing the mutation that was applied.
        contract_ids:
            Optional override list of contract IDs to produce predictions for.
            If None, uses all contract IDs from original_bcg.

        Returns
        -------
        BaselineResult with method="static_bcg".
        """
        original_bcg = self.build_static_bcg(original_ir)
        mutated_bcg  = self.build_static_bcg(mutated_ir)
        return self.predict_from_bcgs(original_bcg, mutated_bcg, mutation, contract_ids)

    def predict_from_bcgs(
        self,
        original_bcg: BCG,
        mutated_bcg: BCG,
        mutation: Any,          # MutationRecord
        contract_ids: list[str] | None = None,
    ) -> BaselineResult:
        """
        Diff two static-only BCGs and return a BaselineResult.

        This variant accepts pre-built BCGs (useful in tests and when the
        IRGraph is not available after BCG construction).

        The caller is responsible for ensuring the BCGs were built without
        dynamic traces; this method does NOT verify that invariant.
        """
        run_id    = str(uuid.uuid4())[:12]
        timestamp = datetime.now(tz=timezone.utc).isoformat()

        diff = original_bcg.diff(mutated_bcg)

        broken_ids: set[str] = {c.contract_id for c in diff.broken}

        # Use caller-supplied IDs or fall back to all IDs in original BCG
        if contract_ids is None:
            cids = list(original_bcg.contracts.keys())
        else:
            cids = contract_ids

        predictions: dict[str, bool]  = {}
        confidence: dict[str, float] = {}

        for cid in cids:
            predicted = cid in broken_ids
            predictions[cid] = predicted
            # Use the contract's own confidence_score as the baseline confidence.
            # For static-only BCGs this reflects the static_support dimension only.
            orig_contract = original_bcg.contracts.get(cid)
            conf = orig_contract.confidence_score() if orig_contract else 0.0
            confidence[cid] = round(conf, 4)

        return BaselineResult(
            method="static_bcg",
            predictions=predictions,
            confidence=confidence,
            metadata={
                "bcg_diff_summary":        diff.summary(),
                "broken_count":            len(diff.broken),
                "preserved_count":         len(diff.preserved),
                "added_count":             len(diff.added),
                "modified_count":          len(diff.modified),
                "broken_contract_ids":     list(broken_ids),
                "original_contract_count": len(original_bcg.contracts),
                "mutated_contract_count":  len(mutated_bcg.contracts),
                "has_dynamic_evidence":    False,
                "mutation_operator":       str(getattr(mutation, "operator", "?")),
                "mutation_id":             str(getattr(mutation, "mutation_id", "?")),
            },
            run_id=run_id,
            timestamp=timestamp,
        )
