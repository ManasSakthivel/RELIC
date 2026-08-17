/**
 * SystemView — artifact graph overview.
 *
 * Shows the full BCG as a D3 force-directed graph with:
 * - Summary stats panel
 * - Entity type filter
 * - Click-through to contract panel on node selection
 */

import React, { useEffect, useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import type { BCGSummary, Entity, Relation, ContractSummary, ExecutionEvent } from "../types";
import { BCGGraph } from "../components/BCGGraph";
import { Loading, ErrorMessage, ValidationStateBadge, ConfidenceBar } from "../components/shared";

interface SystemViewProps {
  bcgId: string;
  summary: BCGSummary | null;
}

export function SystemView({ bcgId, summary }: SystemViewProps) {
  const navigate = useNavigate();
  const containerRef = useRef<HTMLDivElement>(null);
  const [dims, setDims] = useState({ width: 900, height: 560 });

  const [entities, setEntities] = useState<Entity[]>([]);
  const [relations, setRelations] = useState<Relation[]>([]);
  const [contracts, setContracts] = useState<ContractSummary[]>([]);
  const [observations, setObservations] = useState<ExecutionEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedEntity, setSelectedEntity] = useState<Entity | null>(null);
  const [entityFilter, setEntityFilter] = useState<string>("ALL");

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.entities(bcgId),
      api.relations(bcgId),
      api.contracts(bcgId),
      api.observations(bcgId),
    ])
      .then(([e, r, c, o]) => {
        setEntities(e);
        setRelations(r);
        setContracts(c);
        setObservations(o);
        setLoading(false);
      })
      .catch((err: Error) => {
        setError(err.message);
        setLoading(false);
      });
  }, [bcgId]);

  // Observe container size for responsive graph
  useEffect(() => {
    if (!containerRef.current) return;
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setDims({
          width: Math.floor(entry.contentRect.width),
          height: Math.floor(entry.contentRect.height),
        });
      }
    });
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  const entityTypes = ["ALL", ...Array.from(new Set(entities.map((e) => e.entity_type))).sort()];

  const filteredEntities =
    entityFilter === "ALL"
      ? entities
      : entities.filter((e) => e.entity_type === entityFilter);

  const entityContracts = selectedEntity
    ? contracts.filter(
        (c) => c.subject_id === selectedEntity.entity_id || c.object_id === selectedEntity.entity_id
      )
    : [];

  const s: Record<string, React.CSSProperties> = {
    root: {
      display: "flex",
      height: "100%",
      overflow: "hidden",
    },
    sidebar: {
      width: 280,
      flexShrink: 0,
      borderRight: "1px solid var(--border)",
      display: "flex",
      flexDirection: "column",
      overflow: "hidden",
    },
    sidebarHead: {
      padding: "16px 16px 12px",
      borderBottom: "1px solid var(--border)",
    },
    sidebarScroll: {
      flex: 1,
      overflow: "auto",
      padding: "12px 16px",
    },
    graphArea: {
      flex: 1,
      display: "flex",
      flexDirection: "column",
      overflow: "hidden",
      position: "relative",
    },
    toolbar: {
      display: "flex",
      alignItems: "center",
      gap: 8,
      padding: "10px 16px",
      borderBottom: "1px solid var(--border)",
      background: "var(--surface)",
      flexShrink: 0,
    },
    graphContainer: {
      flex: 1,
      overflow: "hidden",
    },
    statGrid: {
      display: "grid",
      gridTemplateColumns: "1fr 1fr",
      gap: 8,
      marginBottom: 16,
    },
    statCard: {
      background: "var(--surface2)",
      border: "1px solid var(--border)",
      borderRadius: 6,
      padding: "8px 10px",
    },
    statValue: {
      fontSize: 22,
      fontWeight: 700,
      color: "var(--text)",
      lineHeight: 1.2,
    },
    statLabel: {
      fontSize: 10,
      color: "var(--text-muted)",
      textTransform: "uppercase" as const,
      letterSpacing: "0.6px",
    },
    filterBtn: (active: boolean): React.CSSProperties => ({
      padding: "3px 10px",
      borderRadius: 12,
      border: `1px solid ${active ? "var(--accent)" : "var(--border)"}`,
      background: active ? "rgba(88,166,255,0.15)" : "transparent",
      color: active ? "var(--accent)" : "var(--text-muted)",
      fontSize: 11,
      cursor: "pointer",
      transition: "all 0.15s",
    }),
  };

  return (
    <div style={s.root}>
      {/* Sidebar */}
      <div style={s.sidebar}>
        <div style={s.sidebarHead}>
          <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.8px", color: "var(--text-muted)", marginBottom: 12 }}>
            System Overview
          </div>
          {summary && (
            <div style={s.statGrid}>
              <div style={s.statCard}>
                <div style={s.statValue}>{summary.entity_count}</div>
                <div style={s.statLabel}>Entities</div>
              </div>
              <div style={s.statCard}>
                <div style={s.statValue}>{summary.contract_count}</div>
                <div style={s.statLabel}>Contracts</div>
              </div>
              <div style={s.statCard}>
                <div style={{ ...s.statValue, color: summary.conflict_count > 0 ? "var(--red)" : "var(--green)" }}>
                  {summary.conflict_count}
                </div>
                <div style={s.statLabel}>Conflicts</div>
              </div>
              <div style={s.statCard}>
                <div style={s.statValue}>{(summary.dynamic_coverage_rate * 100).toFixed(0)}%</div>
                <div style={s.statLabel}>Dyn. Coverage</div>
              </div>
            </div>
          )}

          {summary && (
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 10, color: "var(--text-muted)", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.6px" }}>
                Contracts by state
              </div>
              {Object.entries(summary.contracts_by_state).map(([state, count]) => (
                <div key={state} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                  <ValidationStateBadge state={state as any} />
                  <span style={{ fontSize: 12, color: "var(--text-muted)" }}>{count}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div style={s.sidebarScroll}>
          {/* Selected entity detail */}
          {selectedEntity ? (
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.8px", marginBottom: 10 }}>
                Selected Entity
              </div>
              <div style={{ background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: 6, padding: "10px 12px", marginBottom: 12 }}>
                <div style={{ fontWeight: 600, marginBottom: 4 }}>{selectedEntity.name}</div>
                <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 2 }}>
                  Type: {selectedEntity.entity_type}
                </div>
                <div style={{ fontSize: 11, color: "var(--text-muted)", wordBreak: "break-all" }}>
                  {selectedEntity.artifact_path}
                </div>
                {selectedEntity.location && (
                  <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>
                    Line {selectedEntity.location.line_start}
                  </div>
                )}
              </div>

              {entityContracts.length > 0 && (
                <div>
                  <div style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.6px", marginBottom: 8 }}>
                    Related contracts ({entityContracts.length})
                  </div>
                  {entityContracts.map((c) => (
                    <div
                      key={c.contract_id}
                      onClick={() => navigate(`/contracts/${c.contract_id}`)}
                      style={{
                        background: "var(--surface2)",
                        border: `1px solid ${c.has_conflict ? "rgba(248,81,73,0.4)" : "var(--border)"}`,
                        borderRadius: 6,
                        padding: "8px 10px",
                        marginBottom: 6,
                        cursor: "pointer",
                        transition: "border-color 0.15s",
                      }}
                    >
                      <div style={{ fontSize: 11, color: "var(--text)", marginBottom: 4, lineHeight: 1.4 }}>
                        {c.natural_language.slice(0, 80)}…
                      </div>
                      <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                        <ValidationStateBadge state={c.validation_state} />
                        <ConfidenceBar score={c.confidence_score} />
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <button
                onClick={() => setSelectedEntity(null)}
                style={{
                  marginTop: 8,
                  padding: "4px 12px",
                  fontSize: 11,
                  background: "transparent",
                  border: "1px solid var(--border)",
                  borderRadius: 4,
                  color: "var(--text-muted)",
                }}
              >
                Clear selection
              </button>
            </div>
          ) : (
            <div style={{ fontSize: 12, color: "var(--text-muted)", lineHeight: 1.6 }}>
              Click any node in the graph to inspect its contracts and provenance.
              <br /><br />
              <span style={{ color: "var(--orange)" }}>●</span> Pulsing ring = observed in execution traces.
              <br />
              <span style={{ color: "var(--red)" }}>— — —</span> Red dashed edge = CONFLICT contract.
              <br />
              <span style={{ color: "var(--green)" }}>— — —</span> Green dashed edge = SUPPORTED contract.
              <br />
              <span style={{ color: "var(--accent)" }}>— — —</span> Blue dashed edge = STATIC CANDIDATE.
            </div>
          )}
        </div>
      </div>

      {/* Graph area */}
      <div style={s.graphArea}>
        <div style={s.toolbar}>
          <span style={{ fontSize: 11, color: "var(--text-muted)", marginRight: 4 }}>Filter:</span>
          {entityTypes.map((t) => (
            <button key={t} style={s.filterBtn(entityFilter === t)} onClick={() => setEntityFilter(t)}>
              {t}
            </button>
          ))}
          <div style={{ flex: 1 }} />
          <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
            {filteredEntities.length} nodes · {relations.length} relations · {contracts.length} contracts
          </span>
        </div>

        <div ref={containerRef} style={s.graphContainer}>
          {loading ? (
            <Loading message="Loading BCG…" />
          ) : error ? (
            <ErrorMessage message={error} />
          ) : (
            <BCGGraph
              entities={filteredEntities}
              relations={relations}
              contracts={contracts}
              observations={observations}
              onNodeClick={setSelectedEntity}
              onContractClick={(c) => navigate(`/contracts/${c.contract_id}`)}
              width={dims.width}
              height={dims.height}
            />
          )}
        </div>
      </div>
    </div>
  );
}
