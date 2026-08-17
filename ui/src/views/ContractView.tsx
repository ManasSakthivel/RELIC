/**
 * ContractView — behavioral contract inspection panel.
 *
 * Left panel: filterable contract list.
 * Right panel: full contract detail — type, formal statement, static evidence,
 *   dynamic evidence, conflict banner, confidence breakdown, provenance.
 *
 * Scientific integrity:
 * - Confidence score always labeled as "evidence-strength score, NOT probability".
 * - STATIC_DYNAMIC_CONFLICT shown with explicit red banner and explanation.
 * - NOT_OBSERVED never displayed as CONTRADICTED.
 */

import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../api";
import type { ContractSummary, ContractDetail } from "../types";
import {
  Loading,
  ErrorMessage,
  ValidationStateBadge,
  ContractTypeBadge,
  ConfidenceBar,
  ConfidenceBreakdown,
  SectionTitle,
  ExtractionMethodChip,
} from "../components/shared";

interface ContractViewProps {
  bcgId: string;
}

export function ContractView({ bcgId }: ContractViewProps) {
  const { contractId: paramContractId } = useParams<{ contractId: string }>();
  const navigate = useNavigate();

  const [contracts, setContracts] = useState<ContractSummary[]>([]);
  const [listLoading, setListLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(paramContractId ?? null);
  const [detail, setDetail] = useState<ContractDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  // Filters
  const [typeFilter, setTypeFilter] = useState("ALL");
  const [stateFilter, setStateFilter] = useState("ALL");
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    api
      .contracts(bcgId)
      .then((c) => { setContracts(c); setListLoading(false); })
      .catch((e: Error) => { setListError(e.message); setListLoading(false); });
  }, [bcgId]);

  // Load detail whenever selectedId changes
  useEffect(() => {
    if (!selectedId) { setDetail(null); return; }
    setDetailLoading(true);
    setDetailError(null);
    api
      .contractDetail(bcgId, selectedId)
      .then((d) => { setDetail(d); setDetailLoading(false); })
      .catch((e: Error) => { setDetailError(e.message); setDetailLoading(false); });
  }, [bcgId, selectedId]);

  // Sync URL param → selectedId
  useEffect(() => {
    if (paramContractId) setSelectedId(paramContractId);
  }, [paramContractId]);

  const contractTypes = ["ALL", ...Array.from(new Set(contracts.map((c) => c.contract_type))).sort()];
  const validationStates = ["ALL", ...Array.from(new Set(contracts.map((c) => c.validation_state))).sort()];

  const filtered = contracts.filter((c) => {
    if (typeFilter !== "ALL" && c.contract_type !== typeFilter) return false;
    if (stateFilter !== "ALL" && c.validation_state !== stateFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        c.natural_language.toLowerCase().includes(q) ||
        c.contract_type.toLowerCase().includes(q) ||
        c.validation_state.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const s: Record<string, React.CSSProperties> = {
    root: { display: "flex", height: "100%", overflow: "hidden" },
    list: {
      width: 340,
      flexShrink: 0,
      borderRight: "1px solid var(--border)",
      display: "flex",
      flexDirection: "column",
      overflow: "hidden",
    },
    listHead: {
      padding: "12px 14px",
      borderBottom: "1px solid var(--border)",
      background: "var(--surface)",
    },
    listScroll: { flex: 1, overflow: "auto" },
    detail: { flex: 1, overflow: "auto", padding: "20px 24px" },
    filterRow: { display: "flex", gap: 6, flexWrap: "wrap" as const, marginTop: 8 },
    filterChip: (active: boolean): React.CSSProperties => ({
      padding: "2px 8px",
      borderRadius: 10,
      border: `1px solid ${active ? "var(--accent)" : "var(--border)"}`,
      background: active ? "rgba(88,166,255,0.12)" : "transparent",
      color: active ? "var(--accent)" : "var(--text-muted)",
      fontSize: 10,
      cursor: "pointer",
    }),
    contractItem: (active: boolean, hasConflict: boolean): React.CSSProperties => ({
      padding: "10px 14px",
      borderBottom: "1px solid var(--border)",
      cursor: "pointer",
      background: active ? "rgba(88,166,255,0.08)" : "transparent",
      borderLeft: `3px solid ${hasConflict ? "var(--red)" : active ? "var(--accent)" : "transparent"}`,
      transition: "background 0.15s",
    }),
  };

  return (
    <div style={s.root}>
      {/* Contract list */}
      <div style={s.list}>
        <div style={s.listHead}>
          <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.8px", color: "var(--text-muted)", marginBottom: 8 }}>
            Behavioral Contracts ({filtered.length} / {contracts.length})
          </div>
          <input
            type="text"
            placeholder="Search contracts…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: "100%",
              padding: "6px 10px",
              background: "var(--surface2)",
              border: "1px solid var(--border)",
              borderRadius: 6,
              color: "var(--text)",
              fontSize: 12,
              outline: "none",
            }}
          />
          <div style={s.filterRow}>
            {contractTypes.map((t) => (
              <button key={t} style={s.filterChip(typeFilter === t)} onClick={() => setTypeFilter(t)}>
                {t}
              </button>
            ))}
          </div>
          <div style={{ ...s.filterRow, marginTop: 4 }}>
            {validationStates.map((st) => (
              <button key={st} style={s.filterChip(stateFilter === st)} onClick={() => setStateFilter(st)}>
                {st.replace("STATIC_DYNAMIC_", "")}
              </button>
            ))}
          </div>
        </div>

        <div style={s.listScroll}>
          {listLoading ? (
            <Loading message="Loading contracts…" />
          ) : listError ? (
            <ErrorMessage message={listError} />
          ) : filtered.length === 0 ? (
            <div style={{ padding: 16, color: "var(--text-muted)", fontSize: 12 }}>No contracts match the current filters.</div>
          ) : (
            filtered.map((c) => (
              <div
                key={c.contract_id}
                style={s.contractItem(selectedId === c.contract_id, c.has_conflict)}
                onClick={() => {
                  setSelectedId(c.contract_id);
                  navigate(`/contracts/${c.contract_id}`, { replace: true });
                }}
              >
                <div style={{ display: "flex", gap: 6, alignItems: "center", marginBottom: 4 }}>
                  <ContractTypeBadge type={c.contract_type} />
                  {c.has_conflict && (
                    <span style={{ fontSize: 10, color: "var(--red)" }}>⚡ CONFLICT</span>
                  )}
                </div>
                <div style={{ fontSize: 12, color: "var(--text)", lineHeight: 1.4, marginBottom: 6 }}>
                  {c.natural_language.slice(0, 90)}{c.natural_language.length > 90 ? "…" : ""}
                </div>
                <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                  <ValidationStateBadge state={c.validation_state} />
                  <ConfidenceBar score={c.confidence_score} />
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Contract detail */}
      <div style={s.detail}>
        {!selectedId ? (
          <EmptyDetailState />
        ) : detailLoading ? (
          <Loading message="Loading contract detail…" />
        ) : detailError ? (
          <ErrorMessage message={detailError} />
        ) : detail ? (
          <ContractDetailPanel contract={detail} />
        ) : null}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Empty state
// ---------------------------------------------------------------------------

function EmptyDetailState() {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", color: "var(--text-muted)", gap: 8 }}>
      <div style={{ fontSize: 32, opacity: 0.3 }}>◈</div>
      <div style={{ fontSize: 13 }}>Select a contract to inspect its evidence chain</div>
      <div style={{ fontSize: 11 }}>
        Conflicts are marked with a ⚡ icon in the list
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Full contract detail panel
// ---------------------------------------------------------------------------

function ContractDetailPanel({ contract: c }: { contract: ContractDetail }) {
  return (
    <div style={{ maxWidth: 780 }}>
      {/* Header */}
      <div style={{ marginBottom: 20 }}>
        <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 10 }}>
          <ContractTypeBadge type={c.contract_type} />
          <ValidationStateBadge state={c.validation_state} />
        </div>
        <div style={{ fontSize: 11, color: "var(--text-muted)", fontFamily: "var(--mono)", marginBottom: 6 }}>
          {c.contract_id}
        </div>
        <div style={{ fontSize: 15, fontWeight: 600, color: "var(--text)", lineHeight: 1.5, marginBottom: 8 }}>
          {c.natural_language}
        </div>
        {c.formal_statement && (
          <div style={{
            background: "var(--surface2)",
            border: "1px solid var(--border)",
            borderRadius: 6,
            padding: "10px 14px",
            fontFamily: "var(--mono)",
            fontSize: 13,
            color: "var(--accent)",
            marginBottom: 8,
          }}>
            {c.formal_statement}
          </div>
        )}
        {c.scope && (
          <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
            <strong>Scope:</strong> {c.scope}
          </div>
        )}
        {c.preconditions.length > 0 && (
          <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>
            <strong>Preconditions:</strong> {c.preconditions.join("; ")}
          </div>
        )}
      </div>

      {/* Conflict banner — first-class research finding */}
      {c.has_conflict && (
        <div className="conflict-banner" style={{ marginBottom: 20 }}>
          <span className="icon">⚡</span>
          <div>
            <strong>STATIC / DYNAMIC CONFLICT</strong>
            <p style={{ marginTop: 4, fontSize: 12 }}>
              Static analysis and dynamic execution evidence disagree. This is a first-class
              research finding — it is not silently resolved. Review the evidence below.
            </p>
            {c.conflict_explanation && (
              <p style={{ marginTop: 8, fontSize: 12, fontFamily: "var(--mono)", lineHeight: 1.5 }}>
                {c.conflict_explanation}
              </p>
            )}
          </div>
        </div>
      )}

      {/* NOT_OBSERVED notice */}
      {c.validation_state === "NOT_OBSERVED" && (
        <div style={{
          background: "rgba(110,118,129,0.1)",
          border: "1px solid rgba(110,118,129,0.4)",
          borderRadius: 6,
          padding: "10px 14px",
          fontSize: 12,
          color: "var(--text-muted)",
          marginBottom: 20,
        }}>
          <strong>NOT_OBSERVED ≠ CONTRADICTED</strong>
          <p style={{ marginTop: 4 }}>
            No dynamic execution evidence is available for this contract.
            This does not mean the contract is invalid — only that no execution traces
            were available to validate it. Execution evidence is required before this
            contract can be promoted to STATIC_DYNAMIC_SUPPORTED.
          </p>
        </div>
      )}

      {/* Evidence */}
      <div style={{ marginBottom: 24 }}>
        <SectionTitle>Static Evidence</SectionTitle>
        {c.provenance?.static_evidence.length ? (
          c.provenance.static_evidence.map((ev) => (
            <div key={ev.evidence_id} className="evidence-block">
              <div style={{ display: "flex", gap: 8, marginBottom: 6, alignItems: "center" }}>
                <ExtractionMethodChip method={ev.extraction_method} />
                <span style={{ fontSize: 10, color: "var(--text-muted)" }}>{ev.evidence_type}</span>
              </div>
              <div>{ev.content}</div>
              {ev.formal_content && (
                <div className="formal">{ev.formal_content}</div>
              )}
              <div className="source">
                {ev.source_artifact} · {ev.source_location}
              </div>
            </div>
          ))
        ) : (
          <div style={{ fontSize: 12, color: "var(--text-muted)" }}>No static evidence recorded.</div>
        )}
      </div>

      <div style={{ marginBottom: 24 }}>
        <SectionTitle>Dynamic Evidence</SectionTitle>
        {c.provenance?.dynamic_evidence.length ? (
          c.provenance.dynamic_evidence.map((ev) => (
            <div key={ev.evidence_id} className="evidence-block" style={{
              borderColor: c.has_conflict ? "rgba(248,81,73,0.35)" : "var(--border)",
            }}>
              <div style={{ display: "flex", gap: 8, marginBottom: 6, alignItems: "center" }}>
                <ExtractionMethodChip method={ev.extraction_method} />
                <span style={{ fontSize: 10, color: "var(--text-muted)" }}>{ev.evidence_type}</span>
                {c.has_conflict && (
                  <span style={{ fontSize: 10, color: "var(--red)" }}>⚡ conflicts with static</span>
                )}
              </div>
              <div>{ev.content}</div>
              {ev.formal_content && (
                <div className="formal">{ev.formal_content}</div>
              )}
              <div className="source">
                {ev.source_artifact} · {ev.source_location}
              </div>
            </div>
          ))
        ) : (
          <div style={{ fontSize: 12, color: "var(--text-muted)", fontStyle: "italic" }}>
            No dynamic execution evidence available.
            NOT_OBSERVED — absence of observation is not evidence of absence.
          </div>
        )}
      </div>

      {/* Confidence breakdown */}
      <div style={{ marginBottom: 24 }}>
        <SectionTitle>Evidence-Strength Score (NOT a probability)</SectionTitle>
        <div className="panel">
          <div style={{ marginBottom: 12, fontSize: 12, color: "var(--text-muted)" }}>
            The aggregate score below is a normalized weighted sum of evidence dimensions [0,1].
            It is NOT a probability of contract validity. Weights were fixed before evaluation.
          </div>
          <ConfidenceBreakdown cv={c.confidence} />
        </div>
      </div>

      {/* Provenance */}
      {c.provenance && (
        <div style={{ marginBottom: 24 }}>
          <SectionTitle>Provenance</SectionTitle>
          <div className="panel" style={{ fontSize: 12 }}>
            <ProvenanceRow label="Source artifact" value={c.provenance.source_artifact} />
            <ProvenanceRow label="Source location" value={c.provenance.source_location} />
            <ProvenanceRow label="Extraction method" value={
              <ExtractionMethodChip method={c.provenance.extraction_method} />
            } />
            {c.provenance.model && (
              <ProvenanceRow label="Model" value={c.provenance.model} />
            )}
            {c.provenance.prompt_version && (
              <ProvenanceRow label="Prompt version" value={c.provenance.prompt_version} />
            )}
            <ProvenanceRow label="Timestamp" value={new Date(c.provenance.timestamp).toISOString()} />
            {c.provenance.notes && (
              <div style={{ marginTop: 8, padding: "8px 0", borderTop: "1px solid var(--border)", color: "var(--text-muted)", lineHeight: 1.5 }}>
                {c.provenance.notes}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Metadata */}
      {Object.keys(c.metadata).length > 0 && (
        <div style={{ marginBottom: 24 }}>
          <SectionTitle>Metadata</SectionTitle>
          <div className="panel">
            {Object.entries(c.metadata).map(([k, v]) => (
              <ProvenanceRow key={k} label={k} value={String(v)} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ProvenanceRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div style={{ display: "flex", gap: 12, marginBottom: 6, alignItems: "flex-start" }}>
      <span style={{ width: 160, flexShrink: 0, color: "var(--text-muted)", fontSize: 11 }}>{label}</span>
      <span style={{ color: "var(--text)", fontSize: 12, wordBreak: "break-all" }}>{value}</span>
    </div>
  );
}
