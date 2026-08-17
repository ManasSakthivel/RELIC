/**
 * RiskExplanationView — full evidence chain for each modernization risk.
 *
 * Each risk entry shows the complete chain:
 * CHANGE → CONTRACT → STATIC EVIDENCE → DYNAMIC EVIDENCE →
 * CONFLICT/SUPPORT → AFFECTED ARTIFACTS → CONSEQUENCE → CONFIDENCE
 *
 * No bare numeric scores — every score has a full explanation.
 * Confidence is labeled as "evidence-strength score, NOT probability."
 */

import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import type { RiskReport, RiskEvidenceChain } from "../types";
import {
  Loading,
  ErrorMessage,
  ConfidenceBar,
  ValidationStateBadge,
  SectionTitle,
} from "../components/shared";

interface RiskExplanationViewProps {
  bcgId: string;
}

const RECONCILIATION_COLORS: Record<string, string> = {
  CONTRADICTED: "var(--red)",
  SUPPORTED: "var(--green)",
  UNOBSERVED: "var(--gray)",
  PARTIALLY_SUPPORTED: "var(--orange)",
  AMBIGUOUS: "var(--orange)",
};

const RECONCILIATION_DESCRIPTIONS: Record<string, string> = {
  CONTRADICTED:
    "Static analysis and dynamic execution evidence directly disagree. This is a STATIC_DYNAMIC_CONFLICT.",
  SUPPORTED:
    "Both static analysis and dynamic execution evidence confirm this behavioral obligation.",
  UNOBSERVED:
    "This contract was inferred statically. No execution evidence was available to validate it. " +
    "NOT_OBSERVED ≠ CONTRADICTED.",
  PARTIALLY_SUPPORTED:
    "Some but not all execution evidence supports this contract.",
  AMBIGUOUS:
    "Evidence is present but insufficient to determine a clear outcome. Requires human review.",
};

export function RiskExplanationView({ bcgId }: RiskExplanationViewProps) {
  const navigate = useNavigate();
  const [report, setReport] = useState<RiskReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [minConfidence, setMinConfidence] = useState(0.0);
  const [reconciliationFilter, setReconciliationFilter] = useState("ALL");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    api
      .riskReport(bcgId, minConfidence)
      .then((r) => { setReport(r); setLoading(false); })
      .catch((e: Error) => { setError(e.message); setLoading(false); });
  }, [bcgId, minConfidence]);

  if (loading) return <Loading message="Generating risk report…" />;
  if (error) return <ErrorMessage message={error} />;
  if (!report) return null;

  const allOutcomes = [
    "ALL",
    ...Array.from(new Set(report.evidence_chains.map((c) => c.reconciliation_outcome))).sort(),
  ];

  const filtered = report.evidence_chains.filter((c) => {
    if (reconciliationFilter !== "ALL" && c.reconciliation_outcome !== reconciliationFilter)
      return false;
    return true;
  });

  return (
    <div style={{ height: "100%", overflow: "auto" }}>
      <div style={{ maxWidth: 880, margin: "0 auto", padding: 24 }}>
        {/* Header */}
        <div style={{ marginBottom: 20 }}>
          <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 4 }}>
            Modernization Risk Report
          </h2>
          <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
            BCG: {report.bcg_id} · Generated: {new Date(report.generated_at).toISOString()}
          </div>
        </div>

        {/* Scientific notice */}
        <div
          style={{
            background: "var(--surface2)",
            border: "1px solid var(--border)",
            borderRadius: 6,
            padding: "10px 14px",
            fontSize: 12,
            color: "var(--text-muted)",
            marginBottom: 20,
            lineHeight: 1.6,
          }}
        >
          <strong style={{ color: "var(--text)" }}>Scientific integrity notice:</strong>{" "}
          Every risk entry below contains a full evidence chain. Confidence scores are
          normalized evidence-strength scores [0,1] — they are{" "}
          <strong>NOT probabilities</strong> of risk occurrence. NOT_OBSERVED contracts are
          surfaced as unvalidated obligations, not confirmed risks.
        </div>

        {/* Summary cards */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            gap: 12,
            marginBottom: 24,
          }}
        >
          <SummaryCard label="Total risks" value={report.total_risks} color="var(--text)" />
          <SummaryCard
            label="High evidence strength (≥70%)"
            value={report.high_confidence_risks}
            color="var(--red)"
          />
          <SummaryCard
            label="Conflicts"
            value={report.evidence_chains.filter((c) => c.reconciliation_outcome === "CONTRADICTED").length}
            color="var(--red)"
            note="STATIC_DYNAMIC_CONFLICT"
          />
        </div>

        {/* Filters */}
        <div
          style={{
            display: "flex",
            gap: 12,
            marginBottom: 20,
            flexWrap: "wrap",
            alignItems: "center",
          }}
        >
          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <span style={{ fontSize: 12, color: "var(--text-muted)" }}>Min. evidence strength:</span>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={minConfidence}
              onChange={(e) => setMinConfidence(parseFloat(e.target.value))}
              style={{ width: 120 }}
            />
            <span
              style={{
                fontSize: 12,
                fontVariantNumeric: "tabular-nums",
                color: "var(--accent)",
                minWidth: 36,
              }}
            >
              {(minConfidence * 100).toFixed(0)}%
            </span>
          </div>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {allOutcomes.map((o) => (
              <button
                key={o}
                onClick={() => setReconciliationFilter(o)}
                style={{
                  padding: "3px 10px",
                  borderRadius: 10,
                  border: `1px solid ${
                    reconciliationFilter === o
                      ? RECONCILIATION_COLORS[o] ?? "var(--accent)"
                      : "var(--border)"
                  }`,
                  background:
                    reconciliationFilter === o
                      ? `rgba(${
                          o === "CONTRADICTED"
                            ? "248,81,73"
                            : o === "SUPPORTED"
                            ? "63,185,80"
                            : "88,166,255"
                        },0.12)`
                      : "transparent",
                  color:
                    reconciliationFilter === o
                      ? RECONCILIATION_COLORS[o] ?? "var(--accent)"
                      : "var(--text-muted)",
                  fontSize: 11,
                  cursor: "pointer",
                }}
              >
                {o}
              </button>
            ))}
          </div>
          <span style={{ marginLeft: "auto", fontSize: 12, color: "var(--text-muted)" }}>
            {filtered.length} / {report.total_risks} risks shown
          </span>
        </div>

        {/* Risk chain list */}
        {filtered.length === 0 ? (
          <div style={{ color: "var(--text-muted)", fontSize: 13, textAlign: "center", padding: "32px 0" }}>
            No risks match the current filters.
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {filtered.map((chain) => (
              <RiskChainCard
                key={chain.affected_contract_id}
                chain={chain}
                isExpanded={expandedId === chain.affected_contract_id}
                onToggle={() =>
                  setExpandedId(
                    expandedId === chain.affected_contract_id ? null : chain.affected_contract_id
                  )
                }
                onViewContract={() => navigate(`/contracts/${chain.affected_contract_id}`)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Risk chain card
// ---------------------------------------------------------------------------

function RiskChainCard({
  chain,
  isExpanded,
  onToggle,
  onViewContract,
}: {
  chain: RiskEvidenceChain;
  isExpanded: boolean;
  onToggle: () => void;
  onViewContract: () => void;
}) {
  const outcomeColor = RECONCILIATION_COLORS[chain.reconciliation_outcome] ?? "var(--text-muted)";
  const isConflict = chain.reconciliation_outcome === "CONTRADICTED";

  return (
    <div
      style={{
        background: "var(--surface)",
        border: `1px solid ${isConflict ? "rgba(248,81,73,0.3)" : "var(--border)"}`,
        borderRadius: 8,
        overflow: "hidden",
      }}
    >
      {/* Collapsed header — always visible */}
      <div
        onClick={onToggle}
        style={{
          padding: "14px 16px",
          cursor: "pointer",
          display: "flex",
          gap: 12,
          alignItems: "flex-start",
          borderLeft: `4px solid ${outcomeColor}`,
          background: isConflict ? "rgba(248,81,73,0.04)" : "transparent",
        }}
      >
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 6, flexWrap: "wrap" }}>
            <span
              style={{
                fontSize: 11,
                fontWeight: 700,
                color: outcomeColor,
                textTransform: "uppercase",
                letterSpacing: "0.4px",
              }}
            >
              {chain.reconciliation_outcome}
            </span>
            <ValidationStateBadge state={chain.validation_state} />
            <ConfidenceBar score={chain.confidence_score} label="evidence strength" />
          </div>
          <div style={{ fontSize: 13, color: "var(--text)", lineHeight: 1.4, marginBottom: 4 }}>
            {chain.change_description}
          </div>
          <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
            Contract:{" "}
            <code style={{ color: "var(--accent)", fontSize: 11 }}>
              {chain.affected_contract_id}
            </code>
          </div>
        </div>
        <span style={{ fontSize: 16, color: "var(--text-muted)", flexShrink: 0 }}>
          {isExpanded ? "▲" : "▼"}
        </span>
      </div>

      {/* Expanded — full evidence chain */}
      {isExpanded && (
        <div style={{ padding: "0 16px 16px", borderTop: "1px solid var(--border)" }}>
          {/* Outcome description */}
          <div
            style={{
              background: "var(--surface2)",
              borderRadius: 6,
              padding: "8px 12px",
              fontSize: 12,
              color: "var(--text-muted)",
              margin: "12px 0 16px",
              lineHeight: 1.5,
            }}
          >
            <strong style={{ color: outcomeColor }}>
              Reconciliation: {chain.reconciliation_outcome}
            </strong>{" "}
            — {RECONCILIATION_DESCRIPTIONS[chain.reconciliation_outcome] ?? ""}
          </div>

          {/* Full evidence chain — visual pipeline */}
          <div style={{ display: "flex", flexDirection: "column", gap: 2, marginBottom: 16 }}>
            <ChainStep step="CHANGE" color="var(--purple)">
              {chain.change_description}
            </ChainStep>
            <ChainArrow />
            <ChainStep step="CONTRACT" color="var(--accent)">
              {chain.affected_contract_natural_language}
            </ChainStep>
            <ChainArrow />
            <ChainStep step="STATIC EVIDENCE" color="var(--accent)">
              {chain.static_evidence_summary}
            </ChainStep>
            <ChainArrow />
            <ChainStep
              step="DYNAMIC EVIDENCE"
              color={isConflict ? "var(--red)" : "var(--orange)"}
            >
              {chain.dynamic_evidence_summary}
            </ChainStep>
            <ChainArrow />
            <ChainStep step={`RECONCILIATION: ${chain.reconciliation_outcome}`} color={outcomeColor}>
              {RECONCILIATION_DESCRIPTIONS[chain.reconciliation_outcome] ?? ""}
            </ChainStep>
            <ChainArrow />
            <ChainStep step="AFFECTED ARTIFACTS" color="var(--text-muted)">
              {chain.affected_artifact_ids.join(", ")}
            </ChainStep>
            <ChainArrow />
            <ChainStep step="POTENTIAL CONSEQUENCE" color="var(--orange)">
              {chain.potential_consequence}
            </ChainStep>
            <ChainArrow />
            <ChainStep step="EVIDENCE STRENGTH" color="var(--text-muted)">
              <ConfidenceBar score={chain.confidence_score} />
              <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>
                This is a normalized evidence-strength score [0,1], NOT a probability of risk
                occurrence.
              </div>
            </ChainStep>
          </div>

          {/* Actions */}
          <button
            onClick={onViewContract}
            style={{
              padding: "6px 14px",
              background: "var(--accent-dim)",
              border: "1px solid var(--accent)",
              borderRadius: 6,
              color: "var(--text)",
              fontSize: 12,
              cursor: "pointer",
            }}
          >
            View full contract →
          </button>
        </div>
      )}
    </div>
  );
}

function ChainStep({
  step,
  color,
  children,
}: {
  step: string;
  color: string;
  children: React.ReactNode;
}) {
  return (
    <div
      style={{
        display: "flex",
        gap: 12,
        alignItems: "flex-start",
      }}
    >
      <div
        style={{
          width: 180,
          flexShrink: 0,
          fontSize: 10,
          fontWeight: 700,
          color,
          textTransform: "uppercase",
          letterSpacing: "0.5px",
          paddingTop: 2,
        }}
      >
        {step}
      </div>
      <div
        style={{
          flex: 1,
          fontSize: 12,
          color: "var(--text)",
          lineHeight: 1.5,
          background: "var(--surface2)",
          border: "1px solid var(--border)",
          borderRadius: 4,
          padding: "6px 10px",
        }}
      >
        {children}
      </div>
    </div>
  );
}

function ChainArrow() {
  return (
    <div style={{ paddingLeft: 90, color: "var(--border)", fontSize: 14, lineHeight: 1 }}>↓</div>
  );
}

function SummaryCard({
  label,
  value,
  color,
  note,
}: {
  label: string;
  value: number;
  color: string;
  note?: string;
}) {
  return (
    <div className="panel">
      <div style={{ fontSize: 26, fontWeight: 700, color }}>{value}</div>
      <div style={{ fontSize: 12, color: "var(--text)", marginTop: 2 }}>{label}</div>
      {note && <div style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 2 }}>{note}</div>}
    </div>
  );
}
