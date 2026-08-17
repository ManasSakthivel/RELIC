/**
 * ExecutionOverlayView — Dynamic execution trace overlaid on the BCG.
 *
 * Shows the force-directed BCG with execution observations highlighted:
 * - Nodes observed in traces: orange pulsing ring
 * - Source type clearly labeled (EXECUTION_SIMULATED ≠ EXECUTION)
 * - Side panel: list of events, filterable by artifact/operation
 * - Selecting an event highlights corresponding BCG node
 */

import React, { useEffect, useState, useCallback } from "react";
import { api } from "../api";
import type { Entity, Relation, ContractSummary, ExecutionEvent } from "../types";
import { BCGGraph } from "../components/BCGGraph";
import { Loading, ErrorMessage, ExtractionMethodChip, SectionTitle } from "../components/shared";

interface ExecutionOverlayViewProps {
  bcgId: string;
}

const OP_COLORS: Record<string, string> = {
  STEP_START: "var(--accent)",
  STEP_END: "var(--accent)",
  EXECUTE: "var(--green)",
  PRODUCE: "var(--orange)",
  CONSUME: "var(--red)",
  READ: "var(--purple)",
  WRITE: "var(--yellow)",
  INITIALIZE: "var(--text-muted)",
  ERROR: "var(--red)",
  JOB_START: "var(--accent)",
  JOB_END: "var(--accent)",
  RETURN: "var(--text-muted)",
  FILE_ACCESS: "var(--orange)",
};

const SOURCE_TYPE_DESCRIPTIONS: Record<string, string> = {
  EXECUTION: "Real execution (GnuCOBOL or equivalent)",
  EXECUTION_SIMULATED: "JCL batch simulation — treated as dynamic evidence",
  SYNTHETIC_STATIC: "Statically derived — NOT real execution evidence",
  HUMAN: "Human-reconstructed trace",
};

export function ExecutionOverlayView({ bcgId }: ExecutionOverlayViewProps) {
  const [entities, setEntities] = useState<Entity[]>([]);
  const [relations, setRelations] = useState<Relation[]>([]);
  const [contracts, setContracts] = useState<ContractSummary[]>([]);
  const [events, setEvents] = useState<ExecutionEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedEvent, setSelectedEvent] = useState<ExecutionEvent | null>(null);
  const [highlightedNodeIds, setHighlightedNodeIds] = useState<Set<string>>(new Set());
  const [opFilter, setOpFilter] = useState("ALL");
  const [execIdFilter, setExecIdFilter] = useState("ALL");
  const [sourceTypeFilter, setSourceTypeFilter] = useState("ALL");

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.entities(bcgId),
      api.relations(bcgId),
      api.contracts(bcgId),
      api.observations(bcgId),
    ])
      .then(([e, r, c, obs]) => {
        setEntities(e);
        setRelations(r);
        setContracts(c);
        setEvents(obs);
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [bcgId]);

  // All artifact_ids observed across traces
  const allObservedIds = new Set(events.map((e) => e.artifact_id).filter(Boolean));

  // Operations present in data
  const allOps = ["ALL", ...Array.from(new Set(events.map((e) => e.operation))).sort()];
  const allExecIds = ["ALL", ...Array.from(new Set(events.map((e) => e.execution_id))).sort()];
  const allSourceTypes = ["ALL", ...Array.from(new Set(events.map((e) => e.source_type))).sort()];

  const filteredEvents = events.filter((e) => {
    if (opFilter !== "ALL" && e.operation !== opFilter) return false;
    if (execIdFilter !== "ALL" && e.execution_id !== execIdFilter) return false;
    if (sourceTypeFilter !== "ALL" && e.source_type !== sourceTypeFilter) return false;
    return true;
  });

  const handleEventClick = useCallback((event: ExecutionEvent) => {
    setSelectedEvent(event);
    const highlighted = new Set<string>();
    highlighted.add(event.artifact_id);
    // Also highlight predecessor/successor artifacts
    for (const predId of event.predecessor_events) {
      const pred = events.find((e) => e.event_id === predId);
      if (pred?.artifact_id) highlighted.add(pred.artifact_id);
    }
    for (const succId of event.successor_events) {
      const succ = events.find((e) => e.event_id === succId);
      if (succ?.artifact_id) highlighted.add(succ.artifact_id);
    }
    setHighlightedNodeIds(highlighted);
  }, [events]);

  const hasSynthetic = events.some((e) => e.source_type === "SYNTHETIC_STATIC");

  if (loading) return <Loading message="Loading execution overlay data…" />;
  if (error) return <ErrorMessage message={error} />;

  return (
    <div style={{ display: "flex", height: "100%", overflow: "hidden" }}>
      {/* BCG with overlay */}
      <div style={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>
        {/* Trace info bar */}
        <div
          style={{
            display: "flex",
            gap: 16,
            padding: "8px 16px",
            borderBottom: "1px solid var(--border)",
            background: "var(--surface)",
            fontSize: 12,
            flexShrink: 0,
            alignItems: "center",
            flexWrap: "wrap",
          }}
        >
          <span style={{ color: "var(--text-muted)" }}>
            <strong style={{ color: "var(--text)" }}>{events.length}</strong> execution events
          </span>
          <span style={{ color: "var(--text-muted)" }}>
            <strong style={{ color: "var(--orange)" }}>{allObservedIds.size}</strong> entities observed
          </span>
          <span style={{ color: "var(--text-muted)" }}>
            <strong style={{ color: "var(--text)" }}>{allExecIds.length - 1}</strong> execution runs
          </span>
          {hasSynthetic && (
            <span
              style={{
                background: "rgba(110,118,129,0.15)",
                border: "1px solid var(--border)",
                borderRadius: 10,
                padding: "2px 8px",
                color: "var(--gray)",
                fontSize: 11,
              }}
            >
              ⚠ SYNTHETIC_STATIC traces present — not real execution evidence
            </span>
          )}
          <span style={{ fontSize: 11, color: "var(--text-muted)", marginLeft: "auto" }}>
            🟠 Orange ring = observed in traces
          </span>
        </div>

        <div style={{ flex: 1, overflow: "hidden" }}>
          <AutoSizeBCGGraph
            entities={entities}
            relations={relations}
            contracts={contracts}
            observations={events}
            highlightedNodeIds={highlightedNodeIds}
          />
        </div>
      </div>

      {/* Right sidebar — event list */}
      <div
        style={{
          width: 360,
          flexShrink: 0,
          borderLeft: "1px solid var(--border)",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        {/* Filters */}
        <div
          style={{
            padding: "10px 12px",
            borderBottom: "1px solid var(--border)",
            display: "flex",
            flexDirection: "column",
            gap: 6,
            flexShrink: 0,
          }}
        >
          <SectionTitle>Execution Events</SectionTitle>
          <select
            value={opFilter}
            onChange={(e) => setOpFilter(e.target.value)}
            style={selectStyle}
          >
            {allOps.map((o) => <option key={o} value={o}>{o === "ALL" ? "All operations" : o}</option>)}
          </select>
          <select
            value={execIdFilter}
            onChange={(e) => setExecIdFilter(e.target.value)}
            style={selectStyle}
          >
            {allExecIds.map((o) => <option key={o} value={o}>{o === "ALL" ? "All runs" : `Run: ${o}`}</option>)}
          </select>
          <select
            value={sourceTypeFilter}
            onChange={(e) => setSourceTypeFilter(e.target.value)}
            style={selectStyle}
          >
            {allSourceTypes.map((o) => <option key={o} value={o}>{o === "ALL" ? "All source types" : o}</option>)}
          </select>
          <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
            {filteredEvents.length} / {events.length} events
          </div>
        </div>

        {/* Event list */}
        <div style={{ overflowY: "auto", flex: 1 }}>
          {filteredEvents.map((evt) => (
            <EventListItem
              key={evt.event_id}
              event={evt}
              isSelected={selectedEvent?.event_id === evt.event_id}
              onClick={() => handleEventClick(evt)}
            />
          ))}
        </div>

        {/* Selected event detail */}
        {selectedEvent && (
          <div
            style={{
              borderTop: "1px solid var(--border)",
              padding: 12,
              background: "var(--surface)",
              flexShrink: 0,
              maxHeight: 220,
              overflowY: "auto",
            }}
          >
            <SectionTitle>Event Detail</SectionTitle>
            <div style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12 }}>
              <DetailRow label="Event ID" value={selectedEvent.event_id} mono />
              <DetailRow label="Execution" value={selectedEvent.execution_id} />
              <DetailRow label="Artifact" value={selectedEvent.artifact_id} mono />
              <DetailRow label="Operation" value={selectedEvent.operation} />
              {selectedEvent.resource && <DetailRow label="Resource" value={selectedEvent.resource} />}
              <DetailRow
                label="Return code"
                value={selectedEvent.return_code === null ? "not captured" : String(selectedEvent.return_code)}
              />
              <DetailRow
                label="Source type"
                value={SOURCE_TYPE_DESCRIPTIONS[selectedEvent.source_type] ?? selectedEvent.source_type}
              />
              <div style={{ display: "flex", gap: 6 }}>
                <span style={{ color: "var(--text-muted)", width: 90, flexShrink: 0 }}>Source</span>
                <ExtractionMethodChip method={selectedEvent.source_type} />
              </div>
              {selectedEvent.metadata &&
                Object.entries(selectedEvent.metadata).map(([k, v]) => (
                  <DetailRow key={k} label={k} value={String(v)} />
                ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function EventListItem({
  event,
  isSelected,
  onClick,
}: {
  event: ExecutionEvent;
  isSelected: boolean;
  onClick: () => void;
}) {
  const opColor = OP_COLORS[event.operation] ?? "var(--text-muted)";
  const isSynthetic = event.source_type === "SYNTHETIC_STATIC";

  return (
    <button
      onClick={onClick}
      style={{
        width: "100%",
        background: isSelected ? "rgba(88,166,255,0.08)" : "transparent",
        border: "none",
        borderBottom: "1px solid var(--border)",
        borderLeft: isSelected ? "3px solid var(--accent)" : "3px solid transparent",
        padding: "8px 12px",
        textAlign: "left",
        cursor: "pointer",
        display: "flex",
        gap: 8,
        alignItems: "flex-start",
      }}
    >
      <span
        style={{
          width: 8,
          height: 8,
          borderRadius: "50%",
          background: opColor,
          flexShrink: 0,
          marginTop: 5,
        }}
      />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <span style={{ fontSize: 11, color: opColor, fontWeight: 600 }}>
            {event.operation}
          </span>
          {isSynthetic && (
            <span
              style={{ fontSize: 9, color: "var(--gray)", border: "1px solid var(--border)", borderRadius: 4, padding: "0 4px" }}
              title="SYNTHETIC_STATIC — not real execution evidence"
            >
              SYN
            </span>
          )}
        </div>
        <div
          style={{
            fontSize: 11,
            color: "var(--text-muted)",
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
        >
          {event.artifact_id}
          {event.resource && ` → ${event.resource}`}
        </div>
        <div style={{ fontSize: 10, color: "var(--gray)" }}>
          {new Date(event.timestamp).toISOString().slice(11, 23)}
          {event.return_code !== null && (
            <span
              style={{
                marginLeft: 6,
                color: event.return_code === 0 ? "var(--green)" : "var(--red)",
              }}
            >
              RC={event.return_code}
            </span>
          )}
        </div>
      </div>
    </button>
  );
}

function DetailRow({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div style={{ display: "flex", gap: 8 }}>
      <span style={{ color: "var(--text-muted)", width: 90, flexShrink: 0 }}>{label}</span>
      <span
        style={{
          color: "var(--text)",
          wordBreak: "break-all",
          fontFamily: mono ? "var(--mono)" : undefined,
          fontSize: mono ? 11 : 12,
        }}
      >
        {value}
      </span>
    </div>
  );
}

// AutoSize BCGGraph wrapper
function AutoSizeBCGGraph(props: Omit<React.ComponentProps<typeof BCGGraph>, "width" | "height">) {
  const containerRef = React.useRef<HTMLDivElement>(null);
  const [size, setSize] = React.useState({ width: 900, height: 600 });
  React.useEffect(() => {
    if (!containerRef.current) return;
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setSize({ width: entry.contentRect.width, height: entry.contentRect.height });
      }
    });
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);
  return (
    <div ref={containerRef} style={{ width: "100%", height: "100%" }}>
      <BCGGraph {...props} width={size.width} height={size.height} />
    </div>
  );
}

const selectStyle: React.CSSProperties = {
  background: "var(--surface2)",
  border: "1px solid var(--border)",
  borderRadius: 6,
  padding: "5px 8px",
  color: "var(--text)",
  fontSize: 12,
  width: "100%",
};
