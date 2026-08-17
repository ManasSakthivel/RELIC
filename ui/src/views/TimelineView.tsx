/**
 * TimelineView — execution event timeline.
 *
 * Displays a chronological timeline of execution events from the BCG's
 * dynamic observation set. Selecting an event highlights it and shows
 * the artifact + contract relationship in context.
 *
 * Groups events by execution_id (run). For each run, shows the ordered
 * event sequence with timestamps, operations, return codes, and source types.
 *
 * Source type is always displayed — SYNTHETIC_STATIC events are prominently
 * labeled so they are never confused with real execution evidence.
 */

import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import type { ExecutionEvent, ContractSummary } from "../types";
import {
  Loading,
  ErrorMessage,
  ExtractionMethodChip,
  SectionTitle,
} from "../components/shared";

interface TimelineViewProps {
  bcgId: string;
}

const OP_ICONS: Record<string, string> = {
  JOB_START: "▶",
  JOB_END: "■",
  STEP_START: "▷",
  STEP_END: "◀",
  EXECUTE: "⚙",
  PRODUCE: "📤",
  CONSUME: "📥",
  READ: "👁",
  WRITE: "✏",
  INITIALIZE: "⚡",
  ERROR: "✗",
  RETURN: "↩",
  FILE_ACCESS: "📄",
  DATABASE_ACCESS: "🗄",
};

const OP_COLORS: Record<string, string> = {
  JOB_START: "var(--accent)",
  JOB_END: "var(--accent)",
  STEP_START: "#79c0ff",
  STEP_END: "#79c0ff",
  EXECUTE: "var(--green)",
  PRODUCE: "var(--orange)",
  CONSUME: "#f0883e",
  READ: "var(--purple)",
  WRITE: "var(--purple)",
  INITIALIZE: "var(--text-muted)",
  ERROR: "var(--red)",
  RETURN: "var(--text-muted)",
  FILE_ACCESS: "var(--orange)",
  DATABASE_ACCESS: "var(--orange)",
};

export function TimelineView({ bcgId }: TimelineViewProps) {
  const navigate = useNavigate();
  const [events, setEvents] = useState<ExecutionEvent[]>([]);
  const [contracts, setContracts] = useState<ContractSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<ExecutionEvent | null>(null);
  const [execIdFilter, setExecIdFilter] = useState<string>("ALL");
  const [showSynthetic, setShowSynthetic] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([api.observations(bcgId), api.contracts(bcgId)])
      .then(([obs, c]) => {
        setEvents(obs);
        setContracts(c);
        setLoading(false);
      })
      .catch((e: Error) => { setError(e.message); setLoading(false); });
  }, [bcgId]);

  const execIds = ["ALL", ...Array.from(new Set(events.map((e) => e.execution_id))).sort()];

  const filtered = events.filter((e) => {
    if (execIdFilter !== "ALL" && e.execution_id !== execIdFilter) return false;
    if (!showSynthetic && e.source_type === "SYNTHETIC_STATIC") return false;
    return true;
  });

  // Group by execution_id
  const groupedMap = new Map<string, ExecutionEvent[]>();
  for (const evt of filtered) {
    const key = evt.execution_id || "(no run id)";
    const group = groupedMap.get(key) ?? [];
    group.push(evt);
    groupedMap.set(key, group);
  }
  const groups = Array.from(groupedMap.entries()).sort((a, b) => a[0].localeCompare(b[0]));

  // Contracts involving selected event's artifact
  const relatedContracts = selectedEvent
    ? contracts.filter(
        (c) =>
          c.subject_id === selectedEvent.artifact_id ||
          c.object_id === selectedEvent.artifact_id
      )
    : [];

  // Predecessor/successor events for selected
  const predecessorEvents = selectedEvent
    ? events.filter((e) => selectedEvent.predecessor_events.includes(e.event_id))
    : [];
  const successorEvents = selectedEvent
    ? events.filter((e) => selectedEvent.successor_events.includes(e.event_id))
    : [];

  if (loading) return <Loading message="Loading execution timeline…" />;
  if (error) return <ErrorMessage message={error} />;

  const hasSynthetic = events.some((e) => e.source_type === "SYNTHETIC_STATIC");
  const hasSimulated = events.some((e) => e.source_type === "EXECUTION_SIMULATED");

  return (
    <div style={{ display: "flex", height: "100%", overflow: "hidden" }}>
      {/* Timeline */}
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          borderRight: "1px solid var(--border)",
        }}
      >
        {/* Toolbar */}
        <div
          style={{
            padding: "10px 16px",
            borderBottom: "1px solid var(--border)",
            background: "var(--surface)",
            display: "flex",
            gap: 12,
            alignItems: "center",
            flexShrink: 0,
            flexWrap: "wrap",
          }}
        >
          <select
            value={execIdFilter}
            onChange={(e) => setExecIdFilter(e.target.value)}
            style={{
              background: "var(--surface2)",
              border: "1px solid var(--border)",
              borderRadius: 6,
              padding: "4px 8px",
              color: "var(--text)",
              fontSize: 12,
            }}
          >
            {execIds.map((id) => (
              <option key={id} value={id}>
                {id === "ALL" ? "All execution runs" : `Run: ${id}`}
              </option>
            ))}
          </select>
          {hasSynthetic && (
            <label style={{ fontSize: 12, color: "var(--text-muted)", display: "flex", gap: 6, alignItems: "center" }}>
              <input
                type="checkbox"
                checked={showSynthetic}
                onChange={(e) => setShowSynthetic(e.target.checked)}
              />
              Show SYNTHETIC_STATIC events
            </label>
          )}
          <div style={{ marginLeft: "auto", fontSize: 12, color: "var(--text-muted)" }}>
            {filtered.length} events
          </div>
        </div>

        {/* Evidence source notice */}
        {(hasSynthetic || hasSimulated) && (
          <div
            style={{
              padding: "6px 16px",
              background: "rgba(110,118,129,0.08)",
              borderBottom: "1px solid var(--border)",
              fontSize: 11,
              color: "var(--text-muted)",
              display: "flex",
              gap: 12,
            }}
          >
            {hasSimulated && (
              <span>
                <span style={{ color: "var(--orange)" }}>EXECUTION_SIMULATED</span> — JCL batch
                simulation evidence
              </span>
            )}
            {hasSynthetic && (
              <span>
                <span style={{ color: "var(--gray)" }}>SYNTHETIC_STATIC</span> — statically
                derived, NOT real execution evidence
              </span>
            )}
          </div>
        )}

        <div style={{ flex: 1, overflow: "auto", padding: "0 0 24px 0" }}>
          {groups.length === 0 ? (
            <div style={{ padding: 24, color: "var(--text-muted)", fontSize: 13 }}>
              No execution events available.
            </div>
          ) : (
            groups.map(([runId, runEvents]) => (
              <div key={runId} style={{ marginBottom: 4 }}>
                {/* Run header */}
                <div
                  style={{
                    padding: "8px 20px",
                    background: "var(--surface2)",
                    borderBottom: "1px solid var(--border)",
                    borderTop: "1px solid var(--border)",
                    fontSize: 11,
                    color: "var(--text-muted)",
                    fontWeight: 600,
                    letterSpacing: "0.4px",
                    textTransform: "uppercase",
                    display: "flex",
                    gap: 12,
                    alignItems: "center",
                  }}
                >
                  <span>Run: {runId}</span>
                  <span>{runEvents.length} events</span>
                  <ExtractionMethodChip method={runEvents[0]?.source_type ?? "EXECUTION"} />
                </div>

                {/* Timeline spine */}
                <div style={{ position: "relative", paddingLeft: 40 }}>
                  {/* Vertical spine line */}
                  <div
                    style={{
                      position: "absolute",
                      left: 20,
                      top: 0,
                      bottom: 0,
                      width: 2,
                      background: "var(--border)",
                    }}
                  />

                  {runEvents.map((evt, idx) => {
                    const isSelected = selectedEvent?.event_id === evt.event_id;
                    const isPredecessor = predecessorEvents.some((p) => p.event_id === evt.event_id);
                    const isSuccessor = successorEvents.some((s) => s.event_id === evt.event_id);
                    const opColor = OP_COLORS[evt.operation] ?? "var(--text-muted)";
                    const isSynthetic = evt.source_type === "SYNTHETIC_STATIC";

                    return (
                      <div
                        key={evt.event_id}
                        onClick={() =>
                          setSelectedEvent(isSelected ? null : evt)
                        }
                        style={{
                          position: "relative",
                          padding: "10px 16px 10px 20px",
                          borderBottom: "1px solid var(--border)",
                          cursor: "pointer",
                          background: isSelected
                            ? "rgba(88,166,255,0.06)"
                            : isPredecessor
                            ? "rgba(248,81,73,0.04)"
                            : isSuccessor
                            ? "rgba(63,185,80,0.04)"
                            : "transparent",
                          transition: "background 0.1s",
                        }}
                      >
                        {/* Spine dot */}
                        <div
                          style={{
                            position: "absolute",
                            left: -8,
                            top: "50%",
                            transform: "translateY(-50%)",
                            width: 12,
                            height: 12,
                            borderRadius: "50%",
                            background: opColor,
                            border: isSelected ? "2px solid var(--accent)" : "2px solid var(--surface)",
                            zIndex: 1,
                          }}
                        />

                        <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                          {/* Timestamp */}
                          <div
                            style={{
                              fontSize: 10,
                              color: "var(--text-muted)",
                              fontFamily: "var(--mono)",
                              width: 90,
                              flexShrink: 0,
                              paddingTop: 2,
                            }}
                          >
                            {new Date(evt.timestamp).toISOString().slice(11, 23)}
                          </div>

                          {/* Operation + details */}
                          <div style={{ flex: 1 }}>
                            <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
                              <span style={{ fontSize: 12, fontWeight: 600, color: opColor }}>
                                {OP_ICONS[evt.operation] ?? "◉"} {evt.operation}
                              </span>
                              {evt.return_code !== null && (
                                <span
                                  style={{
                                    fontSize: 10,
                                    color: evt.return_code === 0 ? "var(--green)" : "var(--red)",
                                    padding: "1px 5px",
                                    border: `1px solid ${evt.return_code === 0 ? "rgba(63,185,80,0.3)" : "rgba(248,81,73,0.3)"}`,
                                    borderRadius: 4,
                                  }}
                                >
                                  RC={evt.return_code}
                                </span>
                              )}
                              {isSynthetic && (
                                <span
                                  style={{
                                    fontSize: 9,
                                    color: "var(--gray)",
                                    border: "1px solid var(--border)",
                                    borderRadius: 3,
                                    padding: "0 4px",
                                  }}
                                  title="SYNTHETIC_STATIC — not real execution evidence"
                                >
                                  SYNTHETIC
                                </span>
                              )}
                              {isPredecessor && (
                                <span style={{ fontSize: 9, color: "var(--red)", border: "1px solid rgba(248,81,73,0.3)", borderRadius: 3, padding: "0 4px" }}>
                                  predecessor
                                </span>
                              )}
                              {isSuccessor && (
                                <span style={{ fontSize: 9, color: "var(--green)", border: "1px solid rgba(63,185,80,0.3)", borderRadius: 3, padding: "0 4px" }}>
                                  successor
                                </span>
                              )}
                            </div>
                            <div
                              style={{
                                fontSize: 11,
                                color: "var(--text-muted)",
                                fontFamily: "var(--mono)",
                                marginTop: 2,
                              }}
                            >
                              {evt.artifact_id}
                              {evt.resource && (
                                <span style={{ color: "var(--orange)" }}> → {evt.resource}</span>
                              )}
                            </div>
                            {/* Predecessor/successor links */}
                            {evt.predecessor_events.length > 0 && (
                              <div style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 1 }}>
                                ↑ from: {evt.predecessor_events.join(", ")}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Right panel — event detail + related contracts */}
      <div
        style={{
          width: 320,
          flexShrink: 0,
          overflow: "auto",
          padding: 16,
          display: "flex",
          flexDirection: "column",
          gap: 16,
        }}
      >
        {!selectedEvent ? (
          <div style={{ color: "var(--text-muted)", fontSize: 12, paddingTop: 16 }}>
            Click an event to see its details and related behavioral contracts.
          </div>
        ) : (
          <>
            <div>
              <SectionTitle>Event Detail</SectionTitle>
              <div className="panel" style={{ fontSize: 12 }}>
                <DetailRow label="Event ID" value={selectedEvent.event_id} mono />
                <DetailRow label="Run" value={selectedEvent.execution_id} />
                <DetailRow label="Artifact" value={selectedEvent.artifact_id} mono />
                <DetailRow label="Operation" value={selectedEvent.operation} />
                {selectedEvent.resource && (
                  <DetailRow label="Resource" value={selectedEvent.resource} />
                )}
                <DetailRow
                  label="Return code"
                  value={
                    selectedEvent.return_code === null
                      ? "not captured (≠ zero)"
                      : String(selectedEvent.return_code)
                  }
                />
                <DetailRow label="Source type">
                  <ExtractionMethodChip method={selectedEvent.source_type} />
                </DetailRow>
                <DetailRow
                  label="Timestamp"
                  value={new Date(selectedEvent.timestamp).toISOString()}
                  mono
                />
                {Object.entries(selectedEvent.metadata).map(([k, v]) => (
                  <DetailRow key={k} label={k} value={String(v)} />
                ))}
              </div>
            </div>

            {/* Ordering context */}
            {(predecessorEvents.length > 0 || successorEvents.length > 0) && (
              <div>
                <SectionTitle>Observed Ordering</SectionTitle>
                <div style={{ fontSize: 12, color: "var(--text-muted)", lineHeight: 1.6 }}>
                  {predecessorEvents.length > 0 && (
                    <div>
                      <strong style={{ color: "var(--red)" }}>Predecessors:</strong>{" "}
                      {predecessorEvents.map((e) => `${e.operation}(${e.artifact_id})`).join(", ")}
                    </div>
                  )}
                  {successorEvents.length > 0 && (
                    <div style={{ marginTop: 4 }}>
                      <strong style={{ color: "var(--green)" }}>Successors:</strong>{" "}
                      {successorEvents.map((e) => `${e.operation}(${e.artifact_id})`).join(", ")}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Related contracts */}
            <div>
              <SectionTitle>Related Contracts ({relatedContracts.length})</SectionTitle>
              {relatedContracts.length === 0 ? (
                <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
                  No contracts reference this artifact.
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {relatedContracts.map((c) => (
                    <div
                      key={c.contract_id}
                      onClick={() => navigate(`/contracts/${c.contract_id}`)}
                      style={{
                        background: c.has_conflict
                          ? "rgba(248,81,73,0.06)"
                          : "var(--surface2)",
                        border: `1px solid ${c.has_conflict ? "rgba(248,81,73,0.3)" : "var(--border)"}`,
                        borderRadius: 6,
                        padding: "8px 10px",
                        cursor: "pointer",
                        fontSize: 12,
                      }}
                    >
                      <div style={{ display: "flex", gap: 6, marginBottom: 4 }}>
                        <span
                          style={{
                            fontSize: 9,
                            color: "var(--text-muted)",
                            textTransform: "uppercase",
                            letterSpacing: "0.4px",
                            border: "1px solid var(--border)",
                            borderRadius: 3,
                            padding: "0 4px",
                          }}
                        >
                          {c.contract_type}
                        </span>
                        {c.has_conflict && (
                          <span style={{ fontSize: 10, color: "var(--red)" }}>⚡ CONFLICT</span>
                        )}
                      </div>
                      <div style={{ color: "var(--text)", lineHeight: 1.4 }}>
                        {c.natural_language.slice(0, 80)}…
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function DetailRow({
  label,
  value,
  children,
  mono,
}: {
  label: string;
  value?: string;
  children?: React.ReactNode;
  mono?: boolean;
}) {
  return (
    <div style={{ display: "flex", gap: 8, marginBottom: 5 }}>
      <span style={{ color: "var(--text-muted)", width: 90, flexShrink: 0, fontSize: 11 }}>
        {label}
      </span>
      {children ?? (
        <span
          style={{
            color: "var(--text)",
            wordBreak: "break-all",
            fontSize: mono ? 10 : 12,
            fontFamily: mono ? "var(--mono)" : undefined,
          }}
        >
          {value}
        </span>
      )}
    </div>
  );
}
