/**
 * BCGGraph — D3.js force-directed Behavioral Contract Graph.
 *
 * Visual encoding:
 * - Nodes: colored by entity type; size by connectivity
 * - Structural edges: solid lines, labeled with relation type
 * - Contract edges: dashed lines, colored by validation state
 * - Execution overlay: pulsing halo on nodes observed in traces
 * - Conflict edges: red glow
 *
 * Interaction:
 * - Click node: onNodeClick callback
 * - Click contract edge: onContractClick callback
 * - Hover: tooltip with entity/contract info
 * - Zoom + pan: d3.zoom
 */

import React, { useEffect, useRef, useCallback } from "react";
import * as d3 from "d3";
import type { Entity, Relation, ContractSummary, ExecutionEvent } from "../types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface BCGGraphProps {
  entities: Entity[];
  relations: Relation[];
  contracts: ContractSummary[];
  observations?: ExecutionEvent[];
  onNodeClick?: (entity: Entity) => void;
  onContractClick?: (contract: ContractSummary) => void;
  highlightedNodeIds?: Set<string>;
  highlightedContractId?: string | null;
  width?: number;
  height?: number;
}

interface GraphNode extends d3.SimulationNodeDatum {
  id: string;
  entity: Entity;
  observed: boolean;
}

interface GraphLink extends d3.SimulationLinkDatum<GraphNode> {
  id: string;
  type: "relation" | "contract";
  label: string;
  relationObj?: Relation;
  contractObj?: ContractSummary;
  validationState?: string;
  isConflict: boolean;
}

// ---------------------------------------------------------------------------
// Color maps
// ---------------------------------------------------------------------------

const ENTITY_TYPE_COLORS: Record<string, string> = {
  JOB: "#58a6ff",
  STEP: "#79c0ff",
  PROGRAM: "#a5d6ff",
  DATASET: "#f0883e",
  FILE: "#f0883e",
  RECORD: "#ffa657",
  FIELD: "#ffb77c",
  PROCEDURE: "#bc8cff",
  SECTION: "#d2a8ff",
  PARAGRAPH: "#cae8ff",
  ERROR_CONDITION: "#f85149",
  COPYBOOK: "#3fb950",
  OPERATION: "#56d364",
  CONFIGURATION: "#8b949e",
  ARTIFACT: "#8b949e",
  DATABASE: "#d29922",
  TABLE: "#e3b341",
  JCL_DD: "#ffa657",
  JCL_PROC: "#58a6ff",
};

const VALIDATION_STATE_COLORS: Record<string, string> = {
  STATIC_DYNAMIC_SUPPORTED: "#3fb950",
  STATIC_DYNAMIC_CONFLICT: "#f85149",
  STATIC_CANDIDATE: "#58a6ff",
  NOT_OBSERVED: "#6e7681",
  HUMAN_VALIDATED: "#bc8cff",
  GROUND_TRUTH: "#56d364",
  DYNAMICALLY_OBSERVED: "#79c0ff",
  UNRESOLVED: "#d29922",
};

function entityColor(entity: Entity): string {
  return ENTITY_TYPE_COLORS[entity.entity_type] ?? "#8b949e";
}

function contractColor(state: string): string {
  return VALIDATION_STATE_COLORS[state] ?? "#8b949e";
}

// ---------------------------------------------------------------------------
// BCGGraph Component
// ---------------------------------------------------------------------------

export function BCGGraph({
  entities,
  relations,
  contracts,
  observations = [],
  onNodeClick,
  onContractClick,
  highlightedNodeIds,
  highlightedContractId,
  width = 900,
  height = 600,
}: BCGGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const simulationRef = useRef<d3.Simulation<GraphNode, GraphLink> | null>(null);

  // Set of entity_ids that appear in execution traces
  const observedIds = new Set(observations.map((e) => e.artifact_id).filter(Boolean));

  const draw = useCallback(() => {
    if (!svgRef.current || entities.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    // Zoom layer
    const g = svg.append("g").attr("class", "zoom-layer");

    svg.call(
      d3.zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.1, 4])
        .on("zoom", (event: d3.D3ZoomEvent<SVGSVGElement, unknown>) => {
          g.attr("transform", event.transform.toString());
        })
    );

    // Build node index
    const nodeById = new Map<string, GraphNode>();
    const nodes: GraphNode[] = entities.map((e) => {
      const n: GraphNode = {
        id: e.entity_id,
        entity: e,
        observed: observedIds.has(e.entity_id),
      };
      nodeById.set(e.entity_id, n);
      return n;
    });

    // Build links
    const links: GraphLink[] = [];

    for (const rel of relations) {
      if (nodeById.has(rel.source_id) && nodeById.has(rel.target_id)) {
        links.push({
          id: rel.relation_id,
          source: rel.source_id,
          target: rel.target_id,
          type: "relation",
          label: rel.relation_type,
          relationObj: rel,
          isConflict: false,
        });
      }
    }

    for (const contract of contracts) {
      if (nodeById.has(contract.subject_id) && nodeById.has(contract.object_id)) {
        links.push({
          id: contract.contract_id,
          source: contract.subject_id,
          target: contract.object_id,
          type: "contract",
          label: contract.predicate.replace(/_/g, " "),
          contractObj: contract,
          validationState: contract.validation_state,
          isConflict: contract.has_conflict,
        });
      }
    }

    // Arrow markers
    const defs = svg.append("defs");
    const markerTypes = [
      { id: "arrow-default", color: "#30363d" },
      { id: "arrow-contract-supported", color: "#3fb950" },
      { id: "arrow-contract-conflict", color: "#f85149" },
      { id: "arrow-contract-candidate", color: "#58a6ff" },
      { id: "arrow-contract-unobserved", color: "#6e7681" },
      { id: "arrow-contract-validated", color: "#bc8cff" },
    ];
    for (const m of markerTypes) {
      defs.append("marker")
        .attr("id", m.id)
        .attr("viewBox", "0 -4 8 8")
        .attr("refX", 18)
        .attr("refY", 0)
        .attr("markerWidth", 6)
        .attr("markerHeight", 6)
        .attr("orient", "auto")
        .append("path")
        .attr("d", "M0,-4L8,0L0,4")
        .attr("fill", m.color);
    }

    function arrowMarkerId(link: GraphLink): string {
      if (link.type === "relation") return "url(#arrow-default)";
      const s = link.validationState ?? "";
      if (s === "STATIC_DYNAMIC_CONFLICT") return "url(#arrow-contract-conflict)";
      if (s === "STATIC_DYNAMIC_SUPPORTED") return "url(#arrow-contract-supported)";
      if (s === "STATIC_CANDIDATE") return "url(#arrow-contract-candidate)";
      if (s === "HUMAN_VALIDATED" || s === "GROUND_TRUTH") return "url(#arrow-contract-validated)";
      return "url(#arrow-contract-unobserved)";
    }

    // Simulation
    const simulation = d3
      .forceSimulation<GraphNode>(nodes)
      .force("link", d3.forceLink<GraphNode, GraphLink>(links).id((d) => d.id).distance(120))
      .force("charge", d3.forceManyBody().strength(-400))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide(30))
      .alphaDecay(0.03);
    simulationRef.current = simulation;

    // Links
    const linkGroup = g.append("g").attr("class", "links");

    const linkEls = linkGroup
      .selectAll<SVGLineElement, GraphLink>("line")
      .data(links)
      .join("line")
      .attr("stroke-width", (d) => (d.type === "contract" ? 2 : 1.5))
      .attr("stroke", (d) => {
        if (d.type === "relation") return "#30363d";
        return contractColor(d.validationState ?? "");
      })
      .attr("stroke-dasharray", (d) => (d.type === "contract" ? "6 3" : "none"))
      .attr("stroke-opacity", (d) => {
        if (d.isConflict) return 1.0;
        return 0.7;
      })
      .attr("marker-end", arrowMarkerId)
      .attr("filter", (d) =>
        d.isConflict ? "drop-shadow(0 0 4px rgba(248,81,73,0.8))" : "none"
      )
      .style("cursor", (d) => (d.type === "contract" ? "pointer" : "default"))
      .on("click", (_event: MouseEvent, d: GraphLink) => {
        if (d.type === "contract" && d.contractObj && onContractClick) {
          onContractClick(d.contractObj);
        }
      });

    // Link labels
    const linkLabelGroup = g.append("g").attr("class", "link-labels");
    const linkLabels = linkLabelGroup
      .selectAll<SVGTextElement, GraphLink>("text")
      .data(links.filter((d) => d.type === "contract"))
      .join("text")
      .attr("font-size", 9)
      .attr("fill", (d) => contractColor(d.validationState ?? ""))
      .attr("text-anchor", "middle")
      .attr("dy", -3)
      .text((d) => d.label.length > 20 ? d.label.slice(0, 18) + "…" : d.label);

    // Nodes
    const nodeGroup = g.append("g").attr("class", "nodes");

    const nodeEls = nodeGroup
      .selectAll<SVGGElement, GraphNode>("g")
      .data(nodes)
      .join("g")
      .style("cursor", "pointer")
      .call(
        d3.drag<SVGGElement, GraphNode>()
          .on("start", (event: d3.D3DragEvent<SVGGElement, GraphNode, unknown>, d: GraphNode) => {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on("drag", (event: d3.D3DragEvent<SVGGElement, GraphNode, unknown>, d: GraphNode) => {
            d.fx = event.x;
            d.fy = event.y;
          })
          .on("end", (event: d3.D3DragEvent<SVGGElement, GraphNode, unknown>, d: GraphNode) => {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          })
      )
      .on("click", (_event: MouseEvent, d: GraphNode) => {
        if (onNodeClick) onNodeClick(d.entity);
      });

    // Observed pulse ring
    nodeEls
      .filter((d) => d.observed)
      .append("circle")
      .attr("r", 20)
      .attr("fill", "none")
      .attr("stroke", "var(--orange)")
      .attr("stroke-width", 1.5)
      .attr("stroke-opacity", 0.6)
      .attr("stroke-dasharray", "3 2");

    // Highlighted ring
    nodeEls
      .filter((d) => highlightedNodeIds?.has(d.id) ?? false)
      .append("circle")
      .attr("r", 22)
      .attr("fill", "none")
      .attr("stroke", "var(--accent)")
      .attr("stroke-width", 2.5);

    // Node circle
    nodeEls
      .append("circle")
      .attr("r", (d) => {
        // Larger for high-connectivity nodes
        const degree =
          links.filter((l) => {
            const s = (l.source as GraphNode).id ?? l.source;
            const t = (l.target as GraphNode).id ?? l.target;
            return s === d.id || t === d.id;
          }).length;
        return Math.max(10, Math.min(20, 10 + degree * 1.5));
      })
      .attr("fill", (d) => entityColor(d.entity))
      .attr("fill-opacity", 0.9)
      .attr("stroke", "#161b22")
      .attr("stroke-width", 1.5);

    // Node label
    nodeEls
      .append("text")
      .attr("dy", 30)
      .attr("text-anchor", "middle")
      .attr("font-size", 10)
      .attr("fill", "var(--text)")
      .attr("pointer-events", "none")
      .text((d) =>
        d.entity.name.length > 16 ? d.entity.name.slice(0, 14) + "…" : d.entity.name
      );

    // Node type chip
    nodeEls
      .append("text")
      .attr("dy", 41)
      .attr("text-anchor", "middle")
      .attr("font-size", 8)
      .attr("fill", "var(--text-muted)")
      .attr("pointer-events", "none")
      .text((d) => d.entity.entity_type);

    // Tooltip
    const tooltip = d3
      .select("body")
      .append("div")
      .attr("class", "bcg-tooltip")
      .style("position", "fixed")
      .style("background", "var(--surface)")
      .style("border", "1px solid var(--border)")
      .style("border-radius", "6px")
      .style("padding", "8px 12px")
      .style("font-size", "12px")
      .style("color", "var(--text)")
      .style("pointer-events", "none")
      .style("opacity", "0")
      .style("z-index", "9999")
      .style("max-width", "280px")
      .style("line-height", "1.5");

    nodeEls
      .on("mouseenter", (event: MouseEvent, d: GraphNode) => {
        const contractCount = contracts.filter(
          (c) => c.subject_id === d.id || c.object_id === d.id
        ).length;
        tooltip
          .style("opacity", "1")
          .html(
            `<strong>${d.entity.name}</strong><br>` +
              `Type: ${d.entity.entity_type}<br>` +
              `Artifact: ${d.entity.artifact_path.split("/").pop()}<br>` +
              `Contracts: ${contractCount}<br>` +
              (d.observed
                ? `<span style="color:var(--orange)">● Observed in execution traces</span>`
                : `<span style="color:var(--gray)">○ Not in traces</span>`)
          );
      })
      .on("mousemove", (event: MouseEvent) => {
        tooltip
          .style("left", `${event.clientX + 14}px`)
          .style("top", `${event.clientY - 10}px`);
      })
      .on("mouseleave", () => {
        tooltip.style("opacity", "0");
      });

    linkEls
      .filter((d) => d.type === "contract")
      .on("mouseenter", (event: MouseEvent, d: GraphLink) => {
        const c = d.contractObj;
        if (!c) return;
        tooltip
          .style("opacity", "1")
          .html(
            `<strong>${c.contract_type} CONTRACT</strong><br>` +
              `<span style="font-size:11px">${c.natural_language.slice(0, 120)}…</span><br>` +
              `State: ${c.validation_state}<br>` +
              `Confidence: ${(c.confidence_score * 100).toFixed(0)}%` +
              (c.has_conflict
                ? `<br><span style="color:var(--red)">⚡ STATIC/DYNAMIC CONFLICT</span>`
                : "")
          );
      })
      .on("mousemove", (event: MouseEvent) => {
        tooltip
          .style("left", `${event.clientX + 14}px`)
          .style("top", `${event.clientY - 10}px`);
      })
      .on("mouseleave", () => {
        tooltip.style("opacity", "0");
      });

    // Simulation tick
    simulation.on("tick", () => {
      linkEls
        .attr("x1", (d) => (d.source as GraphNode).x ?? 0)
        .attr("y1", (d) => (d.source as GraphNode).y ?? 0)
        .attr("x2", (d) => (d.target as GraphNode).x ?? 0)
        .attr("y2", (d) => (d.target as GraphNode).y ?? 0);

      linkLabels
        .attr(
          "x",
          (d) =>
            (((d.source as GraphNode).x ?? 0) + ((d.target as GraphNode).x ?? 0)) / 2
        )
        .attr(
          "y",
          (d) =>
            (((d.source as GraphNode).y ?? 0) + ((d.target as GraphNode).y ?? 0)) / 2
        );

      nodeEls.attr("transform", (d) => `translate(${d.x ?? 0},${d.y ?? 0})`);
    });

    // Legend
    const legendItems = Object.entries(ENTITY_TYPE_COLORS).slice(0, 8);
    const legend = svg.append("g").attr("transform", "translate(16, 16)");
    legend
      .append("rect")
      .attr("width", 140)
      .attr("height", 16 + legendItems.length * 18)
      .attr("fill", "var(--surface)")
      .attr("stroke", "var(--border)")
      .attr("rx", 4)
      .attr("opacity", 0.9);
    legendItems.forEach(([type, color], i) => {
      const row = legend.append("g").attr("transform", `translate(8, ${10 + i * 18})`);
      row.append("circle").attr("r", 5).attr("fill", color).attr("cx", 5).attr("cy", 4);
      row
        .append("text")
        .attr("x", 14)
        .attr("y", 8)
        .attr("font-size", 10)
        .attr("fill", "var(--text-muted)")
        .text(type);
    });

    // Contract legend
    const cLegend = svg
      .append("g")
      .attr("transform", `translate(${width - 160}, 16)`);
    cLegend
      .append("rect")
      .attr("width", 148)
      .attr("height", 130)
      .attr("fill", "var(--surface)")
      .attr("stroke", "var(--border)")
      .attr("rx", 4)
      .attr("opacity", 0.9);
    cLegend
      .append("text")
      .attr("x", 8)
      .attr("y", 16)
      .attr("font-size", 9)
      .attr("fill", "var(--text-muted)")
      .text("CONTRACT STATES");
    const states = [
      ["SUPPORTED", "#3fb950"],
      ["CONFLICT", "#f85149"],
      ["CANDIDATE", "#58a6ff"],
      ["NOT OBSERVED", "#6e7681"],
      ["HUMAN VALID.", "#bc8cff"],
      ["GROUND TRUTH", "#56d364"],
    ];
    states.forEach(([label, color], i) => {
      const row = cLegend.append("g").attr("transform", `translate(8, ${24 + i * 17})`);
      row
        .append("line")
        .attr("x1", 0).attr("y1", 5)
        .attr("x2", 20).attr("y2", 5)
        .attr("stroke", color)
        .attr("stroke-width", 2)
        .attr("stroke-dasharray", "5 3");
      row
        .append("text")
        .attr("x", 26)
        .attr("y", 9)
        .attr("font-size", 9)
        .attr("fill", "var(--text-muted)")
        .text(label);
    });

    // Cleanup tooltip on unmount
    return () => {
      tooltip.remove();
      simulation.stop();
    };
  }, [entities, relations, contracts, observations, highlightedNodeIds, highlightedContractId, width, height, onNodeClick, onContractClick]);

  useEffect(() => {
    const cleanup = draw();
    return () => {
      cleanup?.();
      simulationRef.current?.stop();
    };
  }, [draw]);

  return (
    <svg
      ref={svgRef}
      width={width}
      height={height}
      style={{ background: "var(--bg)", display: "block", borderRadius: 8 }}
    />
  );
}
