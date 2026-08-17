/**
 * API type definitions mirroring the FastAPI Pydantic response models.
 *
 * Scientific integrity notes (mirrored from backend):
 * - `confidence_score` is an evidence-strength score in [0,1], NOT a probability.
 * - `NOT_OBSERVED` ≠ `CONTRADICTED`.
 * - `STATIC_CANDIDATE` ≠ `GROUND_TRUTH`.
 * - `has_conflict=true` always comes with `conflict_explanation`.
 */

export interface SourceLocation {
  artifact_path: string;
  line_start: number;
  line_end: number;
  column_start: number;
  column_end: number;
  context: string;
}

export interface EvidenceItem {
  evidence_id: string;
  evidence_type: string;
  source_artifact: string;
  source_location: string;
  extraction_method: string;
  content: string;
  formal_content: string;
  timestamp: string;
  llm_model: string | null;
  llm_prompt_version: string | null;
}

export interface ProvenanceRecord {
  source_artifact: string;
  source_location: string;
  extraction_method: string;
  static_evidence: EvidenceItem[];
  dynamic_evidence: EvidenceItem[];
  model: string | null;
  prompt_version: string | null;
  timestamp: string;
  notes: string;
}

export interface ConfidenceVector {
  static_support: number;
  dynamic_support: number;
  cross_artifact_support: number;
  provenance_quality: number;
  human_validation: number;
  execution_frequency: number;
  ambiguity_penalty: number;
  /** Aggregated evidence-strength score [0,1]. NOT a probability. */
  aggregate_score: number;
}

export interface Entity {
  entity_id: string;
  name: string;
  entity_type: string;
  artifact_path: string;
  location: SourceLocation | null;
  attributes: Record<string, unknown>;
}

export interface Relation {
  relation_id: string;
  relation_type: string;
  source_id: string;
  target_id: string;
  /** 1.0 = deterministically parsed; <1.0 = inferred */
  confidence: number;
  attributes: Record<string, unknown>;
}

export type ValidationState =
  | "STATIC_CANDIDATE"
  | "DYNAMICALLY_OBSERVED"
  | "STATIC_DYNAMIC_SUPPORTED"
  | "STATIC_DYNAMIC_CONFLICT"
  | "HUMAN_VALIDATED"
  | "GROUND_TRUTH"
  | "UNRESOLVED"
  | "NOT_OBSERVED";

export type ContractType = "TEMPORAL" | "RESOURCE" | "CONTROL_FLOW" | "DATA" | "STATE" | "ERROR";

export interface ContractSummary {
  contract_id: string;
  contract_type: ContractType;
  subject_id: string;
  predicate: string;
  object_id: string;
  natural_language: string;
  validation_state: ValidationState;
  /** Evidence-strength score [0,1]. NOT a probability. */
  confidence_score: number;
  has_conflict: boolean;
  created_at: string;
}

export interface ContractDetail extends ContractSummary {
  formal_statement: string | null;
  scope: string;
  preconditions: string[];
  confidence: ConfidenceVector;
  conflict_explanation: string | null;
  provenance: ProvenanceRecord | null;
  metadata: Record<string, unknown>;
}

export interface ExecutionEvent {
  event_id: string;
  timestamp: string;
  execution_id: string;
  artifact_id: string;
  operation: string;
  resource: string | null;
  predecessor_events: string[];
  successor_events: string[];
  /** null = not captured; NOT zero/success */
  return_code: number | null;
  /** EXECUTION | EXECUTION_SIMULATED | SYNTHETIC_STATIC | HUMAN */
  source_type: string;
  metadata: Record<string, unknown>;
}

export interface BCGSummary {
  bcg_id: string;
  created_at: string;
  artifact_paths: string[];
  entity_count: number;
  relation_count: number;
  contract_count: number;
  observation_count: number;
  /** Fraction of contracts with ≥1 dynamic observation. NOT_OBSERVED ≠ CONTRADICTED. */
  dynamic_coverage_rate: number;
  contracts_by_type: Record<string, number>;
  contracts_by_state: Record<string, number>;
  conflict_count: number;
  validated_count: number;
}

export interface RiskEvidenceChain {
  change_description: string;
  affected_contract_id: string;
  affected_contract_natural_language: string;
  static_evidence_summary: string;
  dynamic_evidence_summary: string;
  reconciliation_outcome: string;
  affected_artifact_ids: string[];
  potential_consequence: string;
  /** Evidence-strength score [0,1]. NOT a probability. */
  confidence_score: number;
  validation_state: ValidationState;
}

export interface RiskReport {
  bcg_id: string;
  generated_at: string;
  total_risks: number;
  /** Risks with confidence_score >= 0.7 (threshold set pre-evaluation). */
  high_confidence_risks: number;
  evidence_chains: RiskEvidenceChain[];
}

export interface ContractDiffItem {
  contract_id: string;
  contract_type: ContractType;
  natural_language: string;
  validation_state: ValidationState;
  confidence_score: number;
  diff_category: "PRESERVED" | "BROKEN" | "ADDED";
}

export interface ModernizationDiff {
  bcg_id: string;
  original_artifact_count: number;
  modernized_artifact_count: number;
  preserved_count: number;
  broken_count: number;
  added_count: number;
  /** BROKEN contracts that were validated — highest review priority. */
  regression_candidate_count: number;
  contracts: ContractDiffItem[];
  warning: string;
}

export interface HealthStatus {
  status: string;
  version: string;
  bcg_store_count: number;
  description: string;
}
