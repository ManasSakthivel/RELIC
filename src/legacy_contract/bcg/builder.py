"""
BCG Builder — constructs a BCG from parsed IR + static extraction results + dynamic traces.

Pipeline:
  1. Accept IRGraph (from parsers)
  2. Accept StaticExtractionResult (from static_analysis.extractor)
  3. Accept optional list[ExecutionTrace] (from dynamic_analysis)
  4. Build BCG = (V, E, C, P, D, Γ)
  5. Run reconciliation if traces are provided
  6. Return populated BCG

Usage:
  builder = BCGBuilder()
  bcg = builder.build(ir, static_result, traces=[trace1, trace2])
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from loguru import logger

from legacy_contract.bcg.model import BCG
from legacy_contract.dynamic_analysis.model import ExecutionTrace
from legacy_contract.ir.model import IRGraph
from legacy_contract.reconciliation.engine import ReconciliationEngine
from legacy_contract.static_analysis.extractor import StaticExtractionResult


class BCGBuilder:
    """
    Constructs a Behavioral Contract Graph from IR and analysis results.

    The builder is stateless — each call to ``build`` produces an independent BCG.
    It does NOT modify the input IR or StaticExtractionResult in place.

    Steps
    -----
    1. Copy the provided IRGraph into the BCG (entities V and relations E).
    2. Populate all static candidate contracts from StaticExtractionResult (set C).
    3. If execution traces are provided, ingest all events into D and run
       the ReconciliationEngine to update contract validation states (Γ).
    """

    def __init__(self) -> None:
        self._reconciler = ReconciliationEngine()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(
        self,
        ir: IRGraph,
        static_result: StaticExtractionResult,
        traces: list[ExecutionTrace] | None = None,
    ) -> BCG:
        """
        Build and return a populated BCG.

        Parameters
        ----------
        ir:
            Parsed intermediate representation graph (all artifact entities +
            structural relations).
        static_result:
            Contracts extracted by StaticContractExtractor from *ir*.
        traces:
            Optional dynamic execution traces.  When provided, each event is
            added to BCG.dynamic_observations and the ReconciliationEngine
            updates every contract's validation_state and confidence.

        Returns
        -------
        BCG
            A fully populated BCG ready for risk detection and diff analysis.
        """
        bcg_id = str(uuid.uuid4())
        created_at = datetime.now(tz=timezone.utc).isoformat()

        bcg = BCG(
            ir=ir,
            artifact_paths=list(ir.artifact_paths),
            bcg_id=bcg_id,
            created_at=created_at,
            metadata={
                "entity_count": ir.entity_count(),
                "relation_count": ir.relation_count(),
                "has_dynamic_traces": traces is not None and len(traces) > 0,
            },
        )

        logger.info(
            f"BCGBuilder: building BCG {bcg_id} | "
            f"{ir.entity_count()} entities | {ir.relation_count()} relations"
        )

        self._populate_contracts(bcg, static_result)

        if traces:
            self._populate_observations(bcg, traces)
            self._reconciler.reconcile(bcg, traces)
        else:
            logger.info(
                "BCGBuilder: no dynamic traces provided — "
                "contracts remain STATIC_CANDIDATE"
            )

        logger.info(bcg.summary())
        return bcg

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _populate_entities(self, bcg: BCG, ir: IRGraph) -> None:
        """
        Ensure all IR entities are accessible through the BCG.

        The BCG.ir field already holds the IRGraph reference, so this method
        exists as an explicit hook for future subclasses that may need to
        augment entity metadata during construction.  In the base builder it
        is a no-op: the IRGraph is already attached to the BCG in ``build``.
        """
        # The IRGraph is stored by reference in BCG.ir; no copy needed.
        logger.debug(
            f"BCGBuilder._populate_entities: "
            f"{ir.entity_count()} entities accessible via BCG.ir"
        )

    def _populate_contracts(
        self, bcg: BCG, static_result: StaticExtractionResult
    ) -> None:
        """
        Add all static candidate contracts from *static_result* into the BCG.

        Every contract arriving here has:
        - validation_state = STATIC_CANDIDATE
        - confidence.dynamic_support = 0.0  (not yet reconciled)
        - provenance.extraction_method = DETERMINISTIC

        These invariants are set by the extractors and are not modified here.
        """
        all_contracts = static_result.all_contracts
        for contract in all_contracts:
            bcg.add_contract(contract)

        logger.info(
            f"BCGBuilder._populate_contracts: added {len(all_contracts)} contracts "
            f"(temporal={len(static_result.temporal_contracts)}, "
            f"resource={len(static_result.resource_contracts)}, "
            f"control_flow={len(static_result.control_flow_contracts)})"
        )

    def _populate_observations(
        self, bcg: BCG, traces: list[ExecutionTrace]
    ) -> None:
        """
        Ingest all events from *traces* into BCG.dynamic_observations.

        Each ExecutionEvent is stored by its event_id.  Duplicate event_ids
        are skipped with a warning — this can happen when the same trace file
        is supplied twice.

        PROVENANCE NOTE: source_type is preserved as-is from each event.
        This builder never re-labels EXECUTION_SIMULATED as EXECUTION.
        """
        loaded = 0
        skipped_duplicate = 0

        for trace in traces:
            for event in trace.events:
                if event.event_id in bcg.dynamic_observations:
                    skipped_duplicate += 1
                    logger.warning(
                        f"BCGBuilder._populate_observations: duplicate event_id "
                        f"{event.event_id!r} — skipping"
                    )
                    continue
                bcg.add_observation(event)
                loaded += 1

        logger.info(
            f"BCGBuilder._populate_observations: "
            f"{loaded} events loaded from {len(traces)} traces "
            f"({skipped_duplicate} duplicates skipped)"
        )
