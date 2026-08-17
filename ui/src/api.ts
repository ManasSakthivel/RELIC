/**
 * API client for the LEGACY-CONTRACT FastAPI backend.
 * All functions are typed against the Pydantic response models.
 */

import type {
  BCGSummary,
  ContractDetail,
  ContractSummary,
  Entity,
  ExecutionEvent,
  HealthStatus,
  ModernizationDiff,
  Relation,
  RiskReport,
} from "./types";

const BASE = "/api";

async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${path} — ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health(): Promise<HealthStatus> {
    return apiFetch("/health");
  },

  bcgSummary(bcgId: string): Promise<BCGSummary> {
    return apiFetch(`/bcg/${bcgId}/summary`);
  },

  entities(bcgId: string, entityType?: string): Promise<Entity[]> {
    const q = entityType ? `?entity_type=${entityType}` : "";
    return apiFetch(`/bcg/${bcgId}/entities${q}`);
  },

  relations(bcgId: string, relationType?: string): Promise<Relation[]> {
    const q = relationType ? `?relation_type=${relationType}` : "";
    return apiFetch(`/bcg/${bcgId}/relations${q}`);
  },

  contracts(
    bcgId: string,
    filters?: { contractType?: string; validationState?: string; minConfidence?: number }
  ): Promise<ContractSummary[]> {
    const params = new URLSearchParams();
    if (filters?.contractType) params.set("contract_type", filters.contractType);
    if (filters?.validationState) params.set("validation_state", filters.validationState);
    if (filters?.minConfidence !== undefined)
      params.set("min_confidence", String(filters.minConfidence));
    const q = params.toString() ? `?${params.toString()}` : "";
    return apiFetch(`/bcg/${bcgId}/contracts${q}`);
  },

  contractDetail(bcgId: string, contractId: string): Promise<ContractDetail> {
    return apiFetch(`/bcg/${bcgId}/contracts/${contractId}`);
  },

  observations(
    bcgId: string,
    filters?: { artifactId?: string; operation?: string; sourceType?: string }
  ): Promise<ExecutionEvent[]> {
    const params = new URLSearchParams();
    if (filters?.artifactId) params.set("artifact_id", filters.artifactId);
    if (filters?.operation) params.set("operation", filters.operation);
    if (filters?.sourceType) params.set("source_type", filters.sourceType);
    const q = params.toString() ? `?${params.toString()}` : "";
    return apiFetch(`/bcg/${bcgId}/observations${q}`);
  },

  conflicts(bcgId: string): Promise<ContractDetail[]> {
    return apiFetch(`/bcg/${bcgId}/conflicts`);
  },

  riskReport(bcgId: string, minConfidence?: number): Promise<RiskReport> {
    const q = minConfidence !== undefined ? `?min_confidence=${minConfidence}` : "";
    return apiFetch(`/bcg/${bcgId}/risk${q}`);
  },

  modernizationDiff(bcgId: string, modernizedBcgId?: string): Promise<ModernizationDiff> {
    const q = modernizedBcgId ? `?modernized_bcg_id=${modernizedBcgId}` : "";
    return apiFetch(`/bcg/${bcgId}/diff${q}`);
  },
};
