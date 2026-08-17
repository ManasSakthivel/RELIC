import React, { useEffect, useState } from "react";
import { BrowserRouter, Link, NavLink, Route, Routes, useLocation } from "react-router-dom";
import { api } from "./api";
import type { BCGSummary } from "./types";

import { SystemView } from "./views/SystemView";
import { ContractView } from "./views/ContractView";
import { ExecutionOverlayView } from "./views/ExecutionOverlayView";
import { ModernizationDiffView } from "./views/ModernizationDiffView";
import { RiskExplanationView } from "./views/RiskExplanationView";
import { TimelineView } from "./views/TimelineView";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Demo BCG ID — populated by the API at startup from CardDemo artifacts. */
const DEMO_BCG_ID = "demo-carddemo-v1";

// ---------------------------------------------------------------------------
// Shared context — the active BCG ID propagates to all views
// ---------------------------------------------------------------------------

export const BcgContext = React.createContext<{
  bcgId: string;
  summary: BCGSummary | null;
}>({ bcgId: DEMO_BCG_ID, summary: null });

// ---------------------------------------------------------------------------
// Nav
// ---------------------------------------------------------------------------

const NAV_LINKS = [
  { to: "/", label: "System", title: "Artifact graph overview" },
  { to: "/contracts", label: "Contracts", title: "Behavioral contracts with evidence panel" },
  { to: "/execution", label: "Execution Overlay", title: "Dynamic trace overlaid on BCG" },
  { to: "/diff", label: "Modernization Diff", title: "Original vs. modernized contract comparison" },
  { to: "/risk", label: "Risk", title: "Full evidence chain for each risk finding" },
  { to: "/timeline", label: "Timeline", title: "Execution event timeline" },
];

function NavBar({ summary }: { summary: BCGSummary | null }) {
  const styles: Record<string, React.CSSProperties> = {
    nav: {
      display: "flex",
      alignItems: "center",
      gap: 0,
      background: "var(--surface)",
      borderBottom: "1px solid var(--border)",
      padding: "0 20px",
      height: 52,
      flexShrink: 0,
    },
    brand: {
      fontWeight: 700,
      fontSize: 14,
      color: "var(--text)",
      marginRight: 32,
      letterSpacing: "-0.3px",
      textDecoration: "none",
      display: "flex",
      alignItems: "center",
      gap: 8,
    },
    links: {
      display: "flex",
      gap: 2,
      flex: 1,
    },
    meta: {
      display: "flex",
      gap: 16,
      alignItems: "center",
      fontSize: 12,
      color: "var(--text-muted)",
    },
    badge: {
      display: "inline-flex",
      alignItems: "center",
      gap: 4,
      padding: "2px 8px",
      borderRadius: 10,
      background: "var(--surface2)",
      border: "1px solid var(--border)",
      fontSize: 11,
    },
  };

  return (
    <nav style={styles.nav}>
      <Link to="/" style={styles.brand}>
        <span style={{ color: "var(--accent)" }}>◈</span>
        LEGACY-CONTRACT
      </Link>
      <div style={styles.links}>
        {NAV_LINKS.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            title={l.title}
            end={l.to === "/"}
            style={({ isActive }) => ({
              padding: "0 14px",
              height: 52,
              display: "flex",
              alignItems: "center",
              fontSize: 13,
              color: isActive ? "var(--text)" : "var(--text-muted)",
              borderBottom: isActive ? "2px solid var(--accent)" : "2px solid transparent",
              transition: "color 0.15s, border-color 0.15s",
              textDecoration: "none",
              whiteSpace: "nowrap",
            })}
          >
            {l.label}
          </NavLink>
        ))}
      </div>
      {summary && (
        <div style={styles.meta}>
          <span style={styles.badge} title="BCG ID">
            <span style={{ color: "var(--accent)" }}>◈</span>
            {summary.bcg_id}
          </span>
          <span style={styles.badge}>
            <span style={{ color: "var(--text-muted)" }}>E</span>
            {summary.entity_count} entities
          </span>
          <span style={styles.badge}>
            <span style={{ color: "var(--text-muted)" }}>C</span>
            {summary.contract_count} contracts
          </span>
          {summary.conflict_count > 0 && (
            <span
              style={{
                ...styles.badge,
                background: "rgba(248,81,73,0.1)",
                border: "1px solid rgba(248,81,73,0.4)",
                color: "var(--red)",
              }}
              title="STATIC_DYNAMIC_CONFLICT contracts"
            >
              ⚡ {summary.conflict_count} conflicts
            </span>
          )}
        </div>
      )}
    </nav>
  );
}

// ---------------------------------------------------------------------------
// Root layout
// ---------------------------------------------------------------------------

function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        overflow: "hidden",
      }}
    >
      {children}
    </div>
  );
}

function AppContent() {
  const [summary, setSummary] = useState<BCGSummary | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    api
      .bcgSummary(DEMO_BCG_ID)
      .then(setSummary)
      .catch((e: Error) => setLoadError(e.message));
  }, []);

  return (
    <BcgContext.Provider value={{ bcgId: DEMO_BCG_ID, summary }}>
      <Layout>
        <NavBar summary={summary} />
        {loadError && (
          <div
            style={{
              padding: "12px 20px",
              background: "rgba(248,81,73,0.08)",
              borderBottom: "1px solid rgba(248,81,73,0.3)",
              color: "var(--red)",
              fontSize: 12,
            }}
          >
            ⚠ API unavailable: {loadError}. Start the FastAPI server with{" "}
            <code>make api</code>.
          </div>
        )}
        <div style={{ flex: 1, overflow: "hidden" }}>
          <Routes>
            <Route path="/" element={<SystemView bcgId={DEMO_BCG_ID} summary={summary} />} />
            <Route path="/contracts" element={<ContractView bcgId={DEMO_BCG_ID} />} />
            <Route path="/contracts/:contractId" element={<ContractView bcgId={DEMO_BCG_ID} />} />
            <Route path="/execution" element={<ExecutionOverlayView bcgId={DEMO_BCG_ID} />} />
            <Route path="/diff" element={<ModernizationDiffView bcgId={DEMO_BCG_ID} />} />
            <Route path="/risk" element={<RiskExplanationView bcgId={DEMO_BCG_ID} />} />
            <Route path="/timeline" element={<TimelineView bcgId={DEMO_BCG_ID} />} />
          </Routes>
        </div>
      </Layout>
    </BcgContext.Provider>
  );
}

// ---------------------------------------------------------------------------
// App
// ---------------------------------------------------------------------------

export default function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  );
}
