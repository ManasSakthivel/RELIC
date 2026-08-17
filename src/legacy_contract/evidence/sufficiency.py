"""
Evidence Sufficiency Analyzer.

Implements the evidence sufficiency experiment (E0–E7) from methodology.md:

E0: Source only
    Artifacts available as raw text. No parsed structure.
    Risk detection: impossible. Contract recovery: impossible.

E1: Source + structural dependencies
    Parsed IR entities and relations available.
    No contracts extracted yet. Risk detection: structural only.

E2: Source + static contracts
    IR + static contract candidates extracted.
    No provenance or dynamic evidence. Risk detection: structural + contract.

E3: Static BCG
    Full BCG built from static analysis with provenance.
    Contracts have STATIC_CANDIDATE state. No dynamic evidence.

E4: BCG + provenance
    BCG with complete provenance records on all contracts.
    Extraction method, source artifact, and source location recorded.

E5: BCG + dynamic evidence
    BCG with dynamic observations added from execution traces.
    Contracts reconciled: some STATIC_DYNAMIC_SUPPORTED, some NOT_OBSERVED.

E6: BCG + provenance + dynamic evidence
    Full BCG with both provenance and dynamic evidence.
    Contracts have reconciled validation states and updated confidence.

E7: BCG + provenance + dynamic evidence + LLM
    E6 + LLM-enriched contract explanations and implicit contract inference.
    LLM evidence is labelled separately; LLM assertions are never mixed
    silently with deterministic facts.

Research use:
    This module supports the evidence sufficiency experiment described in
    the paper methodology. It profiles a BCG at each evidence level to
    answer: "How much evidence is sufficient before additional evidence
    provides diminishing returns?"

    Results are reported as EvidenceSufficiencyProfile per level, and
    compare_levels() returns all levels for ablation study table generation.

Scientific constraints:
    - Evidence level definitions are fixed before the experiment begins.
    - Thresholds are not tuned on test data.
    - LLM evidence is always separately tracked.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from loguru import logger

from legacy_contract.bcg.model import BCG
from legacy_contract.contracts.model import (
    ContractType,
    ExtractionMethod,
    ValidationState,
)


# ---------------------------------------------------------------------------
# Evidence level taxonomy
# ---------------------------------------------------------------------------

class EvidenceLevel(str, Enum):
    """
    Evidence levels for the sufficiency experiment.

    Ordered from least to most evidence. The experiment measures
    how risk-detection capability changes as evidence is added.
    """
    E0_SOURCE_ONLY = "E0_SOURCE_ONLY"
    E1_SOURCE_STRUCTURAL = "E1_SOURCE_STRUCTURAL"
    E2_SOURCE_STATIC_CONTRACTS = "E2_SOURCE_STATIC_CONTRACTS"
    E3_STATIC_BCG = "E3_STATIC_BCG"
    E4_BCG_PROVENANCE = "E4_BCG_PROVENANCE"
    E5_BCG_DYNAMIC = "E5_BCG_DYNAMIC"
    E6_BCG_PROVENANCE_DYNAMIC = "E6_BCG_PROVENANCE_DYNAMIC"
    E7_BCG_PROVENANCE_DYNAMIC_LLM = "E7_BCG_PROVENANCE_DYNAMIC_LLM"


# ---------------------------------------------------------------------------
# Evidence sufficiency profile
# ---------------------------------------------------------------------------

@dataclass
class EvidenceSufficiencyProfile:
    """
    A profile of what contract information is available at a given evidence level
    for a specific BCG, and what risk-detection capability that enables.

    Metrics:
        total_entities:            number of entities in the BCG IR
        total_relations:           number of structural relations
        total_contracts:           total contracts in the BCG
        contracts_with_provenance: contracts with a non-None ProvenanceRecord
        contracts_with_static_evidence: contracts with >= 1 static EvidenceItem
        contracts_with_dynamic_evidence: contracts with >= 1 dynamic EvidenceItem
        contracts_with_llm_evidence: contracts extracted or enriched by LLM
        validated_contracts:       contracts in {STATIC_DYNAMIC_SUPPORTED,
                                   HUMAN_VALIDATED, GROUND_TRUTH}
        conflict_contracts:        contracts in STATIC_DYNAMIC_CONFLICT
        unobserved_contracts:      contracts in NOT_OBSERVED
        static_candidate_contracts: contracts still in STATIC_CANDIDATE
        dynamic_coverage_rate:     fraction of contracts with dynamic evidence
        mean_confidence:           mean confidence score across all contracts
        llm_contract_fraction:     fraction of contracts with LLM extraction method

        risk_detection_enabled:    True if mutation risk detection is possible
        contract_recovery_enabled: True if contract extraction is possible
        provenance_available:      True if provenance tracing is possible
        dynamic_validation_enabled: True if dynamic evidence is present
        llm_enrichment_present:    True if any LLM evidence exists

        level:                     the evidence level this profile represents
        notes:                     contextual notes about the evidence level
    """
    level: EvidenceLevel

    # Structural metrics
    total_entities: int = 0
    total_relations: int = 0

    # Contract metrics
    total_contracts: int = 0
    contracts_with_provenance: int = 0
    contracts_with_static_evidence: int = 0
    contracts_with_dynamic_evidence: int = 0
    contracts_with_llm_evidence: int = 0

    # Validation state breakdown
    validated_contracts: int = 0
    conflict_contracts: int = 0
    unobserved_contracts: int = 0
    static_candidate_contracts: int = 0

    # Aggregate metrics
    dynamic_coverage_rate: float = 0.0
    mean_confidence: float = 0.0
    llm_contract_fraction: float = 0.0

    # Capability flags
    risk_detection_enabled: bool = False
    contract_recovery_enabled: bool = False
    provenance_available: bool = False
    dynamic_validation_enabled: bool = False
    llm_enrichment_present: bool = False

    # Per-type contract breakdown
    contract_type_counts: dict[str, int] = field(default_factory=dict)

    # Contextual notes
    notes: str = ""
    limitations: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level.value,
            "total_entities": self.total_entities,
            "total_relations": self.total_relations,
            "total_contracts": self.total_contracts,
            "contracts_with_provenance": self.contracts_with_provenance,
            "contracts_with_static_evidence": self.contracts_with_static_evidence,
            "contracts_with_dynamic_evidence": self.contracts_with_dynamic_evidence,
            "contracts_with_llm_evidence": self.contracts_with_llm_evidence,
            "validated_contracts": self.validated_contracts,
            "conflict_contracts": self.conflict_contracts,
            "unobserved_contracts": self.unobserved_contracts,
            "static_candidate_contracts": self.static_candidate_contracts,
            "dynamic_coverage_rate": self.dynamic_coverage_rate,
            "mean_confidence": self.mean_confidence,
            "llm_contract_fraction": self.llm_contract_fraction,
            "risk_detection_enabled": self.risk_detection_enabled,
            "contract_recovery_enabled": self.contract_recovery_enabled,
            "provenance_available": self.provenance_available,
            "dynamic_validation_enabled": self.dynamic_validation_enabled,
            "llm_enrichment_present": self.llm_enrichment_present,
            "contract_type_counts": self.contract_type_counts,
            "notes": self.notes,
            "limitations": self.limitations,
        }

    def summary(self) -> str:
        return (
            f"[{self.level.value}] "
            f"entities={self.total_entities} "
            f"contracts={self.total_contracts} "
            f"validated={self.validated_contracts} "
            f"dynamic_coverage={self.dynamic_coverage_rate:.1%} "
            f"mean_conf={self.mean_confidence:.2f} "
            f"risk_detection={self.risk_detection_enabled}"
        )


# ---------------------------------------------------------------------------
# Evidence Sufficiency Analyzer
# ---------------------------------------------------------------------------

class EvidenceSufficiencyAnalyzer:
    """
    Profiles a BCG at each evidence level and determines what risk-detection
    capability is enabled at each level.

    The analyzer does NOT modify the BCG. All analysis is read-only.

    Usage:
        analyzer = EvidenceSufficiencyAnalyzer()
        profile = analyzer.analyze(bcg, EvidenceLevel.E5_BCG_DYNAMIC)
        all_profiles = analyzer.compare_levels(bcg)
    """

    def analyze(
        self, bcg: BCG, level: EvidenceLevel
    ) -> EvidenceSufficiencyProfile:
        """
        Profile the BCG at the specified evidence level.

        Each level applies a progressive filter: at E0 only entity counts
        are meaningful; at E3+ contracts are analyzed; at E5+ dynamic
        evidence metrics are included.
        """
        profile = EvidenceSufficiencyProfile(level=level)

        # Always count structural elements (present at all levels >= E1)
        if level not in {EvidenceLevel.E0_SOURCE_ONLY}:
            profile.total_entities = bcg.ir.entity_count()
            profile.total_relations = bcg.ir.relation_count()

        # Compute full contract metrics for E2 and above
        if level not in {EvidenceLevel.E0_SOURCE_ONLY, EvidenceLevel.E1_SOURCE_STRUCTURAL}:
            self._populate_contract_metrics(bcg, profile, level)

        # Set capability flags based on level and what is actually in the BCG
        self._set_capability_flags(profile, level)

        # Add level-specific notes and limitations
        self._add_level_notes(profile, level)

        logger.debug(f"EvidenceSufficiencyAnalyzer: {profile.summary()}")
        return profile

    def compare_levels(
        self, bcg: BCG
    ) -> dict[EvidenceLevel, EvidenceSufficiencyProfile]:
        """
        Produce profiles for all evidence levels for the given BCG.

        Returns a dict ordered by evidence level (E0 → E7).
        Suitable for generating Table 8 (ablation results) from the paper.
        """
        results: dict[EvidenceLevel, EvidenceSufficiencyProfile] = {}
        for level in EvidenceLevel:
            profile = self.analyze(bcg, level)
            results[level] = profile
        logger.info(
            f"EvidenceSufficiencyAnalyzer.compare_levels: "
            f"profiled BCG at {len(results)} levels"
        )
        return results

    # ------------------------------------------------------------------
    # Internal metric computation
    # ------------------------------------------------------------------

    def _populate_contract_metrics(
        self,
        bcg: BCG,
        profile: EvidenceSufficiencyProfile,
        level: EvidenceLevel,
    ) -> None:
        """Compute all contract-level metrics from the BCG."""
        contracts = list(bcg.contracts.values())
        profile.total_contracts = len(contracts)

        if not contracts:
            return

        # --- Provenance & evidence counting ---
        prov_count = 0
        static_ev_count = 0
        dynamic_ev_count = 0
        llm_count = 0

        for c in contracts:
            if c.provenance is not None:
                prov_count += 1
                if c.provenance.static_evidence:
                    static_ev_count += 1
                if c.provenance.dynamic_evidence:
                    dynamic_ev_count += 1
                if c.provenance.extraction_method == ExtractionMethod.LLM:
                    llm_count += 1
            # Also check evidence items for LLM extraction
            if c.provenance:
                for ev in c.provenance.static_evidence:
                    if ev.extraction_method == ExtractionMethod.LLM and c not in []:
                        llm_count = llm_count  # dedup handled below

        # Count LLM contracts by checking provenance extraction method
        llm_contract_ids = set()
        for c in contracts:
            if c.provenance and c.provenance.extraction_method == ExtractionMethod.LLM:
                llm_contract_ids.add(c.contract_id)
            if c.provenance:
                for ev in (
                    c.provenance.static_evidence + c.provenance.dynamic_evidence
                ):
                    if ev.extraction_method == ExtractionMethod.LLM:
                        llm_contract_ids.add(c.contract_id)
                        break

        profile.contracts_with_provenance = prov_count
        profile.contracts_with_static_evidence = static_ev_count
        profile.contracts_with_llm_evidence = len(llm_contract_ids)

        # Dynamic evidence — only meaningful at E5+
        if level in {
            EvidenceLevel.E5_BCG_DYNAMIC,
            EvidenceLevel.E6_BCG_PROVENANCE_DYNAMIC,
            EvidenceLevel.E7_BCG_PROVENANCE_DYNAMIC_LLM,
        }:
            profile.contracts_with_dynamic_evidence = dynamic_ev_count

        # --- Validation state breakdown ---
        validated_states = {
            ValidationState.STATIC_DYNAMIC_SUPPORTED,
            ValidationState.HUMAN_VALIDATED,
            ValidationState.GROUND_TRUTH,
        }
        for c in contracts:
            state = c.validation_state
            if state in validated_states:
                profile.validated_contracts += 1
            elif state == ValidationState.STATIC_DYNAMIC_CONFLICT:
                profile.conflict_contracts += 1
            elif state == ValidationState.NOT_OBSERVED:
                profile.unobserved_contracts += 1
            elif state == ValidationState.STATIC_CANDIDATE:
                profile.static_candidate_contracts += 1

        # --- Aggregate metrics ---
        profile.dynamic_coverage_rate = bcg.dynamic_coverage_rate()

        conf_sum = sum(c.confidence_score() for c in contracts)
        profile.mean_confidence = conf_sum / len(contracts) if contracts else 0.0

        profile.llm_contract_fraction = (
            len(llm_contract_ids) / len(contracts) if contracts else 0.0
        )

        # --- Per-type breakdown ---
        type_counts: dict[str, int] = {}
        for c in contracts:
            key = c.contract_type.value
            type_counts[key] = type_counts.get(key, 0) + 1
        profile.contract_type_counts = type_counts

    def _set_capability_flags(
        self,
        profile: EvidenceSufficiencyProfile,
        level: EvidenceLevel,
    ) -> None:
        """
        Set capability flags based on evidence level and actual BCG content.

        Capability rules (pre-specified, not tuned):

        risk_detection_enabled:
            True if level >= E2 AND contracts > 0

        contract_recovery_enabled:
            True if level >= E2 AND contracts > 0

        provenance_available:
            True if level >= E4 AND contracts_with_provenance > 0

        dynamic_validation_enabled:
            True if level >= E5 AND contracts_with_dynamic_evidence > 0

        llm_enrichment_present:
            True if level == E7 AND contracts_with_llm_evidence > 0
        """
        _level_order = {lvl: i for i, lvl in enumerate(EvidenceLevel)}
        lvl_idx = _level_order[level]
        e2_idx = _level_order[EvidenceLevel.E2_SOURCE_STATIC_CONTRACTS]
        e4_idx = _level_order[EvidenceLevel.E4_BCG_PROVENANCE]
        e5_idx = _level_order[EvidenceLevel.E5_BCG_DYNAMIC]
        e7_idx = _level_order[EvidenceLevel.E7_BCG_PROVENANCE_DYNAMIC_LLM]

        profile.risk_detection_enabled = (
            lvl_idx >= e2_idx and profile.total_contracts > 0
        )
        profile.contract_recovery_enabled = (
            lvl_idx >= e2_idx and profile.total_contracts > 0
        )
        profile.provenance_available = (
            lvl_idx >= e4_idx and profile.contracts_with_provenance > 0
        )
        profile.dynamic_validation_enabled = (
            lvl_idx >= e5_idx and profile.contracts_with_dynamic_evidence > 0
        )
        profile.llm_enrichment_present = (
            lvl_idx >= e7_idx and profile.contracts_with_llm_evidence > 0
        )

    def _add_level_notes(
        self,
        profile: EvidenceSufficiencyProfile,
        level: EvidenceLevel,
    ) -> None:
        """Add human-readable notes and known limitations for each evidence level."""
        notes_map: dict[EvidenceLevel, tuple[str, list[str]]] = {
            EvidenceLevel.E0_SOURCE_ONLY: (
                "Raw source artifacts only. No structural analysis performed. "
                "No contract extraction possible.",
                [
                    "Cannot detect modernization risks without parsing.",
                    "No entity or relation information available.",
                ],
            ),
            EvidenceLevel.E1_SOURCE_STRUCTURAL: (
                "Parsed IR with structural entities and relations. "
                "No behavioral contracts extracted.",
                [
                    "Can identify structural dependencies but not behavioral obligations.",
                    "Risk detection limited to structural changes only.",
                    "No semantic interpretation of ordering or resource constraints.",
                ],
            ),
            EvidenceLevel.E2_SOURCE_STATIC_CONTRACTS: (
                "Static contract candidates extracted from IR. "
                "Contracts are STATIC_CANDIDATE state (not validated).",
                [
                    "All contracts are inference candidates, not validated obligations.",
                    "False-positive rate may be high without dynamic evidence.",
                    "No provenance tracing — extraction location unknown.",
                ],
            ),
            EvidenceLevel.E3_STATIC_BCG: (
                "Full static BCG with entities, relations, and STATIC_CANDIDATE contracts. "
                "The primary static-analysis baseline.",
                [
                    "No dynamic validation — contracts not confirmed by execution.",
                    "Cannot distinguish executed from unexecuted paths.",
                    "Confidence scores rely on static heuristics only.",
                ],
            ),
            EvidenceLevel.E4_BCG_PROVENANCE: (
                "Static BCG with full provenance records. "
                "Every contract is traceable to source artifact and location.",
                [
                    "Provenance records extraction location but not execution confirmation.",
                    "LLM-extracted contracts are tracked separately.",
                    "Without dynamic evidence, validation state remains STATIC_CANDIDATE.",
                ],
            ),
            EvidenceLevel.E5_BCG_DYNAMIC: (
                "BCG with dynamic execution observations. "
                "Contracts reconciled against execution traces.",
                [
                    "Dynamic coverage depends on trace completeness.",
                    "Unobserved contracts (NOT_OBSERVED) are not contradicted — "
                    "absence of evidence ≠ evidence of absence.",
                    "Provenance not required at this level (evidence without full traceability).",
                ],
            ),
            EvidenceLevel.E6_BCG_PROVENANCE_DYNAMIC: (
                "Full BCG with provenance and dynamic evidence. "
                "This is the proposed system's primary operating mode.",
                [
                    "Dynamic coverage remains incomplete for uncovered execution paths.",
                    "STATIC_DYNAMIC_CONFLICT contracts require human investigation.",
                    "Confidence scores are evidence-strength estimates, not probabilities.",
                ],
            ),
            EvidenceLevel.E7_BCG_PROVENANCE_DYNAMIC_LLM: (
                "Full BCG with LLM-enriched implicit contract inference. "
                "LLM evidence is always tracked separately from deterministic evidence.",
                [
                    "LLM nondeterminism: results may vary across runs without seeding.",
                    "LLM-inferred contracts require human validation before use.",
                    "Token cost and latency may limit scalability.",
                    "LLM assertions must never be mixed silently with "
                    "deterministic or execution-based facts.",
                ],
            ),
        }

        note_text, limitations = notes_map.get(level, ("", []))
        profile.notes = note_text
        profile.limitations = limitations
