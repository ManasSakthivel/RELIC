/**
 * ModernizationDiffView — Original vs. modernized contract comparison.
 *
 * Shows the BCGDiff result:
 *   PRESERVED contracts — behavioral obligations that survive modernization
 *   BROKEN contracts — regression CANDIDATES (require validation to confirm)
 *   ADDED contracts — new obligations introduced by modernization
 *
 * BROKEN ≠ confirmed regression — always surfaced with this caveat.
 * Regression candidates (validated + broken) are the highest priority items.
 */

import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import type { ModernizationDiff, ContractDiffItem } from "../types";
import {
  ValidationStateBadge,
  ContractTypeBadge,
  ConfidenceBar,
  Loading,
  ErrorMessage,
  SectionTitle,
} from "../components/shared";

interface ModernizationDiffViewProps {
  bcgId: string;
}

type DiffCategory = "ALL" | "PRESERVED" | "BROKEN" | "ADDED";

const DIFF_COLORS: Record<ContractDiffItem["diff_category"], string> = {
  PRESERVED: "var(--green)",
  BROKEN: "var(--red)",
  ADDED: "var(--orange)",
};

const DIFF_DESCRIPTIONS: Record<ContractDiffItem["diff_category"], string> = {
  PRESERVED: "Present in both original and modernized BCG.",
  BROKEN:
    "Present in original but absent in modernized BCG. Regression CANDIDATE — requires execution oracle or human validation.",
  ADDED: "Newly introduced behavioral obligation in the modernized system.",
};

export function ModernizationDiffView({ bcgId }: ModernizationDiffViewProps) {
  const navigate = useNavigate();
  const [diff, setDiff] = useState<ModernizationDiff | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [categoryFilter, setCategoryFilter] = useState<DiffCategory>("ALL");
  const [showValidatedOnly, setShowValidatedOnly] = useState(false);

  useEffect(() => {
    setLoading(true);
    api
      .modernizationDiff(bcgId)
      .then(setDiff)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [bcgId]);

  if (loading) return <Loading message="Loading modernization diff…" />;
  if (error) return <ErrorMessage message={error} />;
  if (!diff) return null;

  const filtered = diff.contracts.filter((c) => {
    if (categoryFilter !== "ALL" && c.diff_category !== categoryFilter) return false;
    if (showValidatedOnly) {
      const validatedStates = [
        "STATIC_DYNAMIC_SUPPORTED",
        "HUMAN_VALIDATED",
        "GROUND_TRUTH",
      ];
      if (!validatedStates.includes(c.validation_state)) return false;
    }
    return true;
  });

  const brokenValidated = diff.contracts.filter(
    (c) =>
      c.diff_category === "BROKEN" &&
      ["STATIC_DYNAMIC_SUPPORTED", "HUMAN_VALIDATED", "GROUND_TRUTH"].includes(
        c.validation_state
      )
  );

  return (
    <div style={{ height: "100%", overflowY: "auto" }}>
      <div style={{ maxWidth: 900, margin: "0 auto", padding: 20 }}>
        {/* Header */}
        <div style={{ marginBottom: 20 }}>
          <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 4 }}>
            Modernization Diff — {bcgId}
          </h2>
          <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
            Artifacts: {diff.original_artifact_count} original
            {diff.modernized_artifact_count > 0
              ? ` → ${diff.modernized_artifact_count} modernized`
              : " (no modernized BCG provided — showing current contract inventory)"}
          </div>
        </div>

        {/* Caveat banner */}
        <div
          style={{
            background: "rgba(210,153,34,0.08)",
            border: "1px solid rgba(210,153,34,0.3)",
            borderRadius: 6,
            padding: "10px 14px",
            fontSize: 12,
            color: "var(--orange)",
            marginBottom: 20,
          }}
        >
          ⚠ <strong>BROKEN contracts are regression CANDIDATES, not confirmed regressions.</strong>{" "}
          {diff.warning}
        </div>

        {/* Summary stats */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(4, 1fr)",
            gap: 12,
            marginBottom: 24,
          }}
        >
          <StatCard
            label="Preserved"
            value={diff.preserved_count}
            color="var(--green)"
            description="Contracts in both BCGs"
          />
          <StatCard
            label="Broken"
            value={diff.broken_count}
            color="var(--red)"
            description="Absent in modernized BCG"
          />
          <StatCard
            label="Added"
            value={diff.added_count}
            color="var(--orange)"
            description="New obligations in modernized"
          />
          <StatCard
            label="Regression candidates"
            value={diff.regression_candidate_count}
            color="var(--red)"
            description="Broken + previously validated"
            highlight
          />
        </div>

        {/* Regression candidate priority list */}
        {brokenValidated.length > 0 && (
          <div
            style={{
              background: "rgba(248,81,73,0.06)",
              border: "1px solid rgba(248,81,73,0.3)",
              borderRadius: 8,
              padding: 16,
              marginBottom: 24,
            }}
          >
            <SectionTitle>⚡ Priority Review — Regression Candidates ({brokenValidated.length})</SectionTitle>
            <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 12 }}>
              These contracts were validated (STATIC_DYNAMIC_SUPPORTED / HUMAN_VALIDATED / GROUND_TRUTH)
              in the original BCG and are absent in the modernized version.
              They are the highest-priority items for human review and execution oracle testing.
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {brokenValidated.map((c) => (
                <DiffContractRow
                  key={c.contract_id}
                  item={c}
                  onClick={() => navigate(`/contracts/${c.contract_id}`)}
                />
              ))}
            </div>
          </div>
        )}

        {/* Filters */}
        <div
          style={{
            display: "flex",
            gap: 8,
            marginBottom: 16,
            flexWrap: "wrap",
            alignItems: "center",
          }}
        >
          {(["ALL", "BROKEN", "PRESERVED", "ADDED"] as DiffCategory[]).map((cat) => (
            <button
              key={cat}
              onClick={() => setCategoryFilter(cat)}
              style={{
                background:
                  categoryFilter === cat
                    ? cat === "ALL"
                      ? "var(--accent-dim)"
                      : `rgba(${cat === "BROKEN" ? "248,81,73" : cat === "ADDED" ? "210,153,34" : "63,185,80"},0.15)`
                    : "var(--surface2)",
                border: `1px solid ${
                  categoryFilter === cat
                    ? cat === "ALL"
                      ? "var(--accent)"
                      : DIFF_COLORS[cat as ContractDiffItem["diff_category"]]
                    : "var(--border)"
                }`,
                borderRadius: 6,
                padding: "5px 12px",
                color: categoryFilter === cat ? "var(--text)" : "var(--text-muted)",
                fontSize: 12,
                fontWeight: categoryFilter === cat ? 600 : 400,
              }}
            >
              {cat}
            </button>
          ))}
          <label style={{ fontSize: 12, color: "var(--text-muted)", display: "flex", gap: 6, alignItems: "center", marginLeft: 8 }}>
            <input
              type="checkbox"
              checked={showValidatedOnly}
              onChange={(e) => setShowValidatedOnly(e.target.checked)}
            />
            Validated contracts only
          </label>
          <span style={{ marginLeft: "auto", fontSize: 12, color: "var(--text-muted)" }}>
            {filtered.length} / {diff.contracts.length} contracts
          </span>
        </div>

        {/* Contract list */}
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {filtered.map((c) => (
            <DiffContractRow
              key={c.contract_id}
              item={c}
              onClick={() => navigate(`/contracts/${c.contract_id}`)}
              showDescription
            />
          ))}
          {filtered.length === 0 && (
            <div style={{ fontSize: 13, color: "var(--text-muted)", padding: "24px 0", textAlign: "center" }}>
              No contracts match the current filters.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatCard({
  label,
  value,
  color,
  description,
  highlight,
}: {
  label: string;
  value: number;
  color: string;
  description: string;
  highlight?: boolean;
}) {
  return (
    <div
      className="panel"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 4,
        background: highlight && value > 0 ? "rgba(248,81,73,0.06)" : undefined,
        borderColor: highlight && value > 0 ? "rgba(248,81,73,0.3)" : undefined,
      }}
    >
      <div style={{ fontSize: 26, fontWeight: 700, color }}>{value}</div>
      <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text)" }}>{label}</div>
      <div style={{ fontSize: 11, color: "var(--text-muted)", lineHeight: 1.4 }}>{description}</div>
    </div>
  );
}

function DiffContractRow({
  item,
  onClick,
  showDescription,
}: {
  item: ContractDiffItem;
  onClick: () => void;
  showDescription?: boolean;
}) {
  const leftBorderColor = DIFF_COLORS[item.diff_category];

  return (
    <button
      onClick={onClick}
      style={{
        width: "100%",
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderLeft: `4px solid ${leftBorderColor}`,
        borderRadius: 6,
        padding: "10px 14px",
        textAlign: "left",
        cursor: "pointer",
        display: "flex",
        flexDirection: "column",
        gap: 6,
      }}
    >
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
        <span
          style={{
            fontSize: 11,
            fontWeight: 700,
            color: leftBorderColor,
            textTransform: "uppercase",
            letterSpacing: "0.4px",
          }}
        >
          {item.diff_category}
        </span>
        <ContractTypeBadge type={item.contract_type as any} />
        <ValidationStateBadge state={item.validation_state as any} />
        <ConfidenceBar score={item.confidence_score} />
      </div>
      <div style={{ fontSize: 13, color: "var(--text)", lineHeight: 1.4 }}>
        {item.natural_language.slice(0, 160)}
        {item.natural_language.length > 160 ? "…" : ""}
      </div>
      {showDescription && (
        <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
          {DIFF_DESCRIPTIONS[item.diff_category]}
        </div>
      )}
    </button>
  );
}
