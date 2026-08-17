/**
 * Shared UI components for LEGACY-CONTRACT.
 */

import React from "react";
import type { ValidationState, ContractType, ConfidenceVector } from "../types";

// ---------------------------------------------------------------------------
// Validation State Badge
// ---------------------------------------------------------------------------

const STATE_CONFIG: Record<
  ValidationState,
  { label: string; className: string; title: string }
> = {
  STATIC_DYNAMIC_CONFLICT: {
    label: "CONFLICT",
    className: "badge badge-conflict",
    title: "Static analysis and dynamic execution evidence disagree.",
  },
  STATIC_DYNAMIC_SUPPORTED: {
    label: "SUPPORTED",
    className: "badge badge-supported",
    title: "Static analysis and dynamic execution evidence both support this contract.",
  },
  STATIC_CANDIDATE: {
    label: "STATIC CANDIDATE",
    className: "badge badge-candidate",
    title: "Inferred from static analysis only. Not confirmed by execution.",
  },
  DYNAMICALLY_OBSERVED: {
    label: "DYN OBSERVED",
    className: "badge badge-validated",
    title: "Observed in execution traces. Not yet cross-validated statically.",
  },
  HUMAN_VALIDATED: {
    label: "HUMAN VALIDATED",
    className: "badge badge-validated",
    title: "Confirmed by expert annotation.",
  },
  GROUND_TRUTH: {
    label: "GROUND TRUTH",
    className: "badge badge-ground",
    title: "Verified by deterministic analysis or execution oracle.",
  },
  UNRESOLVED: {
    label: "UNRESOLVED",
    className: "badge badge-unobserved",
    title: "Ambiguous — requires investigation.",
  },
  NOT_OBSERVED: {
    label: "NOT OBSERVED",
    className: "badge badge-unobserved",
    title:
      "No dynamic evidence available. NOT_OBSERVED ≠ CONTRADICTED — absence of observation is not evidence of absence.",
  },
};

export function ValidationStateBadge({ state }: { state: ValidationState }) {
  const cfg = STATE_CONFIG[state] ?? {
    label: state,
    className: "badge badge-unobserved",
    title: state,
  };
  return (
    <span className={cfg.className} title={cfg.title}>
      {cfg.label}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Contract Type Badge
// ---------------------------------------------------------------------------

const TYPE_CLASS: Record<ContractType, string> = {
  TEMPORAL: "badge badge-temporal",
  RESOURCE: "badge badge-resource",
  CONTROL_FLOW: "badge badge-control",
  DATA: "badge badge-unobserved",
  STATE: "badge badge-unobserved",
  ERROR: "badge badge-conflict",
};

export function ContractTypeBadge({ type }: { type: ContractType }) {
  return (
    <span className={TYPE_CLASS[type] ?? "badge badge-unobserved"}>
      {type.replace("_", " ")}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Confidence Bar
// ---------------------------------------------------------------------------

function confidenceColor(score: number): string {
  if (score >= 0.7) return "var(--green)";
  if (score >= 0.4) return "var(--orange)";
  return "var(--red)";
}

export function ConfidenceBar({
  score,
  label,
}: {
  score: number;
  label?: string;
}) {
  const color = confidenceColor(score);
  return (
    <span className="confidence-bar" title="Evidence-strength score [0,1]. NOT a probability.">
      <span className="confidence-bar-track">
        <span
          className="confidence-bar-fill"
          style={{ width: `${Math.round(score * 100)}%`, background: color }}
        />
      </span>
      <span style={{ fontSize: 12, color, fontVariantNumeric: "tabular-nums" }}>
        {(score * 100).toFixed(0)}%
      </span>
      {label && (
        <span style={{ fontSize: 11, color: "var(--text-muted)" }}>{label}</span>
      )}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Confidence Vector Breakdown
// ---------------------------------------------------------------------------

export function ConfidenceBreakdown({ cv }: { cv: ConfidenceVector }) {
  const dimensions: [string, number, string][] = [
    ["Static support", cv.static_support, "Evidence from static analysis"],
    ["Dynamic support", cv.dynamic_support, "Evidence from execution traces"],
    ["Cross-artifact", cv.cross_artifact_support, "Corroboration across multiple artifact types"],
    ["Provenance quality", cv.provenance_quality, "Completeness of provenance record"],
    ["Human validation", cv.human_validation, "Expert annotator confidence"],
    ["Execution frequency", cv.execution_frequency, "Frequency observed in traces"],
    ["Ambiguity penalty", cv.ambiguity_penalty, "Penalty for ambiguous extraction (subtracted)"],
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      {dimensions.map(([name, value, title]) => (
        <div
          key={name}
          style={{ display: "flex", alignItems: "center", gap: 8 }}
          title={title}
        >
          <span
            style={{
              width: 150,
              fontSize: 12,
              color: "var(--text-muted)",
              flexShrink: 0,
            }}
          >
            {name}
          </span>
          <span className="confidence-bar-track" style={{ width: 120 }}>
            <span
              className="confidence-bar-fill"
              style={{
                width: `${Math.round(value * 100)}%`,
                background:
                  name === "Ambiguity penalty" ? "var(--orange)" : confidenceColor(value),
              }}
            />
          </span>
          <span
            style={{
              fontSize: 12,
              color: confidenceColor(value),
              fontVariantNumeric: "tabular-nums",
              width: 32,
            }}
          >
            {(value * 100).toFixed(0)}%
          </span>
        </div>
      ))}
      <div
        style={{
          marginTop: 4,
          paddingTop: 8,
          borderTop: "1px solid var(--border)",
          fontSize: 11,
          color: "var(--text-muted)",
        }}
      >
        Aggregate: <strong style={{ color: confidenceColor(cv.aggregate_score) }}>
          {(cv.aggregate_score * 100).toFixed(1)}%
        </strong>{" "}
        — evidence-strength score, NOT a probability.
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Loading / Error helpers
// ---------------------------------------------------------------------------

export function Loading({ message = "Loading…" }: { message?: string }) {
  return (
    <div className="loading-spinner">
      <span>{message}</span>
    </div>
  );
}

export function ErrorMessage({ message }: { message: string }) {
  return <div className="error-message">⚠ {message}</div>;
}

// ---------------------------------------------------------------------------
// Section header
// ---------------------------------------------------------------------------

export function SectionTitle({ children }: { children: React.ReactNode }) {
  return <div className="section-title">{children}</div>;
}

// ---------------------------------------------------------------------------
// Extraction method chip
// ---------------------------------------------------------------------------

const EXTRACTION_COLORS: Record<string, string> = {
  DETERMINISTIC: "var(--green)",
  LLM: "var(--purple)",
  HUMAN: "var(--accent)",
  EXECUTION: "var(--orange)",
  EXECUTION_SIMULATED: "var(--orange)",
  SYNTHETIC_STATIC: "var(--gray)",
  COMBINED: "var(--text-muted)",
};

export function ExtractionMethodChip({ method }: { method: string }) {
  const color = EXTRACTION_COLORS[method] ?? "var(--text-muted)";
  return (
    <span
      style={{
        fontSize: 10,
        padding: "1px 6px",
        borderRadius: 8,
        border: `1px solid ${color}`,
        color,
        textTransform: "uppercase",
        letterSpacing: "0.4px",
        fontWeight: 600,
      }}
      title={`Extraction method: ${method}`}
    >
      {method.replace("_", " ")}
    </span>
  );
}
