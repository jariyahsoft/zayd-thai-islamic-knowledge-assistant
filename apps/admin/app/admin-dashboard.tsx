"use client";

import type { CSSProperties, ReactElement } from "react";
import { useState } from "react";
import { getAdminDashboard, type AdminDashboardSummary } from "./admin-data.js";

const WINDOWS = [15, 60, 240, 1440] as const;

export function AdminDashboard(props: { readonly apiBaseUrl: string }): ReactElement {
  const [token, setToken] = useState("");
  const [windowMinutes, setWindowMinutes] = useState<number>(60);
  const [summary, setSummary] = useState<AdminDashboardSummary | null>(null);
  const [generatedAt, setGeneratedAt] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function refresh(): Promise<void> {
    setLoading(true);
    try {
      const dashboard = await getAdminDashboard(props.apiBaseUrl, token.trim(), windowMinutes);
      setSummary(dashboard.summary);
      setGeneratedAt(dashboard.generated_at);
      setNotice(null);
    } catch (error) {
      setSummary(null);
      setGeneratedAt(null);
      setNotice(error instanceof Error ? error.message : "Dashboard telemetry is unavailable.");
    } finally {
      setLoading(false);
    }
  }

  return <section style={sectionStyle}>
    <p style={eyebrowStyle}>TASK-10-04</p>
    <h2 style={titleStyle}>Operational dashboard</h2>
    <p>Aggregate operational data only. It never displays request, conversation, source, or provider-secret content.</p>
    <label htmlFor="dashboard-token">Bearer token</label>
    <textarea id="dashboard-token" rows={3} value={token} onChange={(event) => setToken(event.target.value)} placeholder="Temporary authorized token; held in memory only." style={inputStyle} />
    <label htmlFor="dashboard-window">Observation window</label>
    <select id="dashboard-window" value={windowMinutes} onChange={(event) => setWindowMinutes(Number(event.target.value))} style={inputStyle}>
      {WINDOWS.map((value) => <option key={value} value={value}>{value >= 60 ? `${value / 60} hour(s)` : `${value} minutes`}</option>)}
    </select>
    <button type="button" onClick={() => void refresh()} disabled={loading || !token.trim()} style={buttonStyle}>{loading ? "Loading…" : "Refresh dashboard"}</button>
    {notice ? <p role="alert">Telemetry unavailable: {notice}</p> : null}
    {summary ? <><p aria-live="polite">Updated {generatedAt ?? "just now"}; requested window: {windowMinutes} minutes.</p><div style={gridStyle}>
      <Metric label="Registered users" value={summary.registered_user_count} />
      <Metric label="Review queue" value={summary.queue_depth} />
      <Metric label="Open feedback" value={summary.feedback_open_count} />
      <Metric label="Open incidents" value={summary.incident_open_count} />
      <Metric label="Provider health checks" value={summary.provider_health_ok_count} />
      <Metric label="Local RAG hits" value={summary.local_rag_hit_count} />
      <Metric label="External fallbacks" value={summary.external_fallback_count} />
      <Metric label="Citation failures" value={summary.citation_failure_count} />
      <Metric label="Errors" value={summary.error_count} />
      <Metric label="Cost limit (USD/day)" value={summary.provider_cost_limit_daily_usd.toFixed(2)} />
    </div></> : null}
  </section>;
}

function Metric(props: { readonly label: string; readonly value: string | number }): ReactElement { return <article style={cardStyle}><span>{props.label}</span><strong>{props.value}</strong></article>; }
const sectionStyle: CSSProperties = { display: "grid", gap: 14, maxWidth: 1000 };
const eyebrowStyle: CSSProperties = { margin: 0, color: "#375545", fontWeight: 700 };
const titleStyle: CSSProperties = { margin: 0 };
const inputStyle: CSSProperties = { maxWidth: 520, padding: 10, borderRadius: 8, border: "1px solid #8ba093" };
const buttonStyle: CSSProperties = { width: "fit-content", padding: "10px 16px", borderRadius: 8, border: 0, background: "#183629", color: "#fff", fontWeight: 700 };
const gridStyle: CSSProperties = { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 };
const cardStyle: CSSProperties = { display: "grid", gap: 6, padding: 16, background: "#fff", borderRadius: 10, border: "1px solid #d4ddd5" };
