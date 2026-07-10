"use client";

import type { CSSProperties, ReactElement } from "react";
import { useState } from "react";
import type {
  CaseComparison,
  EvaluationRunInfo,
  RunComparisonReport,
} from "./admin-data.js";
import {
  compareEvaluationRuns,
  listEvaluationRuns,
} from "./admin-data.js";

type Notice = {
  readonly tone: "success" | "error" | "info";
  readonly message: string;
};

export function EvaluationConsole(props: { readonly apiBaseUrl: string }): ReactElement {
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [runs, setRuns] = useState<readonly EvaluationRunInfo[]>([]);
  const [baseRunId, setBaseRunId] = useState("");
  const [targetRunId, setTargetRunId] = useState("");
  const [report, setReport] = useState<RunComparisonReport | null>(null);

  // Filters
  const [filterType, setFilterType] = useState<"all" | "regression" | "improvement">("all");
  const [searchKey, setSearchKey] = useState("");
  const [caseTypeFilter, setCaseTypeFilter] = useState("all");

  async function loadRuns(): Promise<void> {
    if (!token.trim()) {
      setNotice({ tone: "error", message: "Bearer token is required to load runs." });
      return;
    }
    setBusy("Loading evaluation runs...");
    setNotice(null);
    try {
      const fetchedRuns = await listEvaluationRuns(props.apiBaseUrl, token.trim());
      setRuns(fetchedRuns);
      if (fetchedRuns.length > 0) {
        setBaseRunId(fetchedRuns[0].run_id);
        if (fetchedRuns.length > 1) {
          setTargetRunId(fetchedRuns[1].run_id);
        } else {
          setTargetRunId(fetchedRuns[0].run_id);
        }
      }
      setNotice({ tone: "success", message: `Successfully loaded ${fetchedRuns.length} runs.` });
    } catch (error) {
      setRuns([]);
      setNotice({
        tone: "error",
        message: error instanceof Error ? error.message : "Failed to load runs. Permission restricted.",
      });
    } finally {
      setBusy(null);
    }
  }

  async function performComparison(): Promise<void> {
    if (!baseRunId || !targetRunId) {
      setNotice({ tone: "error", message: "Both base and target runs must be selected." });
      return;
    }
    setBusy("Generating comparison report...");
    setNotice(null);
    try {
      const cmpReport = await compareEvaluationRuns(
        props.apiBaseUrl,
        token.trim(),
        baseRunId,
        targetRunId,
      );
      setReport(cmpReport);
      setNotice({ tone: "success", message: "Comparison report generated successfully." });
    } catch (error) {
      setReport(null);
      setNotice({
        tone: "error",
        message: error instanceof Error ? error.message : "Failed to compare runs.",
      });
    } finally {
      setBusy(null);
    }
  }

  function downloadReport(): void {
    if (!report) {
      return;
    }
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `zayd-eval-comparison-${report.base_run.run_id.slice(0, 8)}-vs-${report.target_run.run_id.slice(0, 8)}.json`;
    link.click();
    URL.revokeObjectURL(url);
  }

  // Filter logic
  const filteredComparisons = (report?.comparisons ?? []).filter((item) => {
    if (filterType === "regression" && !item.regression) {
      return false;
    }
    if (filterType === "improvement" && !item.improvement) {
      return false;
    }
    if (caseTypeFilter !== "all" && item.case_type !== caseTypeFilter) {
      return false;
    }
    if (searchKey.trim() !== "") {
      const normQuery = searchKey.toLowerCase();
      const matchKey = item.case_key.toLowerCase().includes(normQuery);
      const matchTopic = item.topic.toLowerCase().includes(normQuery);
      if (!matchKey && !matchTopic) {
        return false;
      }
    }
    return true;
  });

  return (
    <section style={sectionStyle}>
      <h2 style={titleStyle}>Evaluation Runs & Comparison Dashboard</h2>
      <p style={descriptionStyle}>
        Compare benchmark runs, trace regressions, review safety and retrieval configurations, and verify policy compliance across runs.
      </p>

      {/* Auth Panel */}
      <div style={panelCardStyle}>
        <h3 style={panelTitleStyle}>Telemetry Verification Access</h3>
        <div style={authFormStyle}>
          <div style={formGroupStyle}>
            <label htmlFor="eval-token" style={labelStyle}>Bearer Auth Token</label>
            <textarea
              id="eval-token"
              rows={2}
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="Authorized admin or scholar token."
              style={textareaStyle}
            />
          </div>
          <button
            type="button"
            onClick={() => void loadRuns()}
            disabled={!!busy || !token.trim()}
            style={primaryButtonStyle}
          >
            Load Runs
          </button>
        </div>
      </div>

      {busy ? <div style={busyNotificationStyle}>{busy}</div> : null}
      {notice ? (
        <div
          role="alert"
          style={{
            ...noticeStyle,
            backgroundColor:
              notice.tone === "success"
                ? "#eef7f2"
                : notice.tone === "error"
                ? "#fdf2f2"
                : "#f2f7fd",
            borderColor:
              notice.tone === "success"
                ? "#375545"
                : notice.tone === "error"
                ? "#e05252"
                : "#528be0",
          }}
        >
          {notice.message}
        </div>
      ) : null}

      {/* Select Runs to Compare */}
      {runs.length > 0 ? (
        <div style={panelCardStyle}>
          <h3 style={panelTitleStyle}>Choose Runs to Compare</h3>
          <div style={selectGridStyle}>
            <div style={formGroupStyle}>
              <label htmlFor="base-run-select" style={labelStyle}>Base Run (older/benchmark/parent)</label>
              <select
                id="base-run-select"
                value={baseRunId}
                onChange={(e) => setBaseRunId(e.target.value)}
                style={selectStyle}
              >
                {runs.map((r) => (
                  <option key={`base-${r.run_id}`} value={r.run_id}>
                    {r.model_name} on {r.provider_name} ({r.started_at.slice(0, 16)})
                  </option>
                ))}
              </select>
            </div>
            <div style={formGroupStyle}>
              <label htmlFor="target-run-select" style={labelStyle}>Target Run (newer/experimental/feature)</label>
              <select
                id="target-run-select"
                value={targetRunId}
                onChange={(e) => setTargetRunId(e.target.value)}
                style={selectStyle}
              >
                {runs.map((r) => (
                  <option key={`target-${r.run_id}`} value={r.run_id}>
                    {r.model_name} on {r.provider_name} ({r.started_at.slice(0, 16)})
                  </option>
                ))}
              </select>
            </div>
          </div>
          <button
            type="button"
            onClick={() => void performComparison()}
            disabled={!!busy || !baseRunId || !targetRunId}
            style={compareButtonStyle}
          >
            Compare Selected Runs
          </button>
        </div>
      ) : null}

      {/* Comparison results */}
      {report ? (
        <div style={resultsContainerStyle}>
          {/* Side-by-side run config info */}
          <div style={runConfigGridStyle}>
            <RunConfigCard title="Base Run" run={report.base_run} />
            <RunConfigCard title="Target Run" run={report.target_run} />
          </div>

          {/* Aggregate Metrics comparison */}
          <div style={statsGridStyle}>
            <div style={metricCardStyle}>
              <span style={metricLabelStyle}>Regressions</span>
              <strong style={{ ...metricValueStyle, color: report.regression_count > 0 ? "#e05252" : "#375545" }}>
                {report.regression_count}
              </strong>
              <span style={metricSubtextStyle}>cases degraded</span>
            </div>
            <div style={metricCardStyle}>
              <span style={metricLabelStyle}>Improvements</span>
              <strong style={{ ...metricValueStyle, color: "#375545" }}>
                {report.improvement_count}
              </strong>
              <span style={metricSubtextStyle}>cases repaired</span>
            </div>
            <div style={metricCardStyle}>
              <span style={metricLabelStyle}>Base Pass Rate</span>
              <strong style={metricValueStyle}>
                {(report.overall_base_pass_rate * 100).toFixed(1)}%
              </strong>
              <span style={metricSubtextStyle}>overall accuracy</span>
            </div>
            <div style={metricCardStyle}>
              <span style={metricLabelStyle}>Target Pass Rate</span>
              <strong style={{ ...metricValueStyle, color: report.overall_target_pass_rate >= report.overall_base_pass_rate ? "#183629" : "#e05252" }}>
                {(report.overall_target_pass_rate * 100).toFixed(1)}%
              </strong>
              <span style={metricSubtextStyle}>
                Diff: {((report.overall_target_pass_rate - report.overall_base_pass_rate) * 100).toFixed(1)}%
              </span>
            </div>
          </div>

          {/* Action Header */}
          <div style={actionsRowStyle}>
            <h3 style={sectionTitleStyle}>Case-Level Comparison</h3>
            <button type="button" onClick={downloadReport} style={exportButtonStyle}>
              Export JSON Report
            </button>
          </div>

          {/* Toolbar filters */}
          <div style={toolbarStyle}>
            <div style={filterGroupStyle}>
              <button
                type="button"
                onClick={() => setFilterType("all")}
                style={filterTabStyle(filterType === "all")}
              >
                All Cases ({report.comparisons.length})
              </button>
              <button
                type="button"
                onClick={() => setFilterType("regression")}
                style={filterTabStyle(filterType === "regression")}
              >
                Regressions ({report.regression_count})
              </button>
              <button
                type="button"
                onClick={() => setFilterType("improvement")}
                style={filterTabStyle(filterType === "improvement")}
              >
                Improvements ({report.improvement_count})
              </button>
            </div>

            <div style={searchFormStyle}>
              <select
                value={caseTypeFilter}
                onChange={(e) => setCaseTypeFilter(e.target.value)}
                style={inlineSelectStyle}
                aria-label="Filter by case type"
              >
                <option value="all">All Types</option>
                <option value="multiple_choice">Multiple Choice</option>
                <option value="open_ended">Open Ended</option>
                <option value="retrieval_only">Retrieval Only</option>
                <option value="citation">Citation</option>
                <option value="abstention">Abstention</option>
                <option value="risk_routing">Risk Routing</option>
              </select>

              <input
                type="text"
                value={searchKey}
                onChange={(e) => setSearchKey(e.target.value)}
                placeholder="Search key or topic..."
                style={searchInputStyle}
                aria-label="Search cases"
              />
            </div>
          </div>

          {/* Table list */}
          <div style={tableWrapperStyle}>
            {filteredComparisons.length > 0 ? (
              <table style={tableStyle}>
                <thead>
                  <tr style={thRowStyle}>
                    <th style={thStyle}>Case Key</th>
                    <th style={thStyle}>Type</th>
                    <th style={thStyle}>Risk</th>
                    <th style={thStyle}>Topic</th>
                    <th style={thStyle}>Base Outcome</th>
                    <th style={thStyle}>Target Outcome</th>
                    <th style={thStyle}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredComparisons.map((c) => {
                    let statusLabel = "No Change";
                    let bg = "transparent";
                    let fg = "#333";
                    if (c.regression) {
                      statusLabel = "Regression";
                      bg = "#fdf2f2";
                      fg = "#e05252";
                    } else if (c.improvement) {
                      statusLabel = "Improvement";
                      bg = "#eef7f2";
                      fg = "#375545";
                    }

                    return (
                      <tr key={c.case_key} style={trStyle}>
                        <td style={tdStyle}>
                          <span style={caseKeyStyle}>{c.case_key}</span>
                          {c.visibility === "private" ? (
                            <span style={privateBadgeStyle}>restricted</span>
                          ) : null}
                        </td>
                        <td style={tdStyle}>{c.case_type}</td>
                        <td style={tdStyle}>{c.risk_level}</td>
                        <td style={tdStyle}>{c.topic}</td>
                        <td style={tdStyle}>
                          <span
                            style={outcomeBadgeStyle(c.base_passed)}
                          >
                            {c.base_passed ? "PASS" : "FAIL"}
                          </span>
                        </td>
                        <td style={tdStyle}>
                          <span
                            style={outcomeBadgeStyle(c.target_passed)}
                          >
                            {c.target_passed ? "PASS" : "FAIL"}
                          </span>
                        </td>
                        <td style={{ ...tdStyle, backgroundColor: bg, color: fg, fontWeight: 700 }}>
                          {statusLabel}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            ) : (
              <div style={emptyStateStyle}>No case comparisons matched the active filters.</div>
            )}
          </div>
        </div>
      ) : null}
    </section>
  );
}

function RunConfigCard(props: {
  readonly title: string;
  readonly run: EvaluationRunInfo;
}): ReactElement {
  const { run } = props;
  return (
    <div style={configCardStyle}>
      <h4 style={configCardTitleStyle}>{props.title}</h4>
      <div style={configMetadataStyle}>
        <div style={metadataRowStyle}>
          <strong>Model:</strong> <span>{run.model_name} ({run.provider_name})</span>
        </div>
        <div style={metadataRowStyle}>
          <strong>Dataset:</strong> <span>{run.dataset_name} (v{run.dataset_version})</span>
        </div>
        <div style={metadataRowStyle}>
          <strong>Git commit:</strong> <code style={codeStyle}>{run.git_commit.slice(0, 8)}</code>
        </div>
        <div style={metadataRowStyle}>
          <strong>Random seed:</strong> <span>{run.random_seed}</span>
        </div>
        {run.retriever_version ? (
          <div style={metadataRowStyle}>
            <strong>Retriever:</strong> <span>{run.retriever_version}</span>
          </div>
        ) : null}
        <div style={metadataRowStyle}>
          <strong>Run ID:</strong> <span style={uuidStyle}>{run.run_id}</span>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Stylesheet
// ---------------------------------------------------------------------------

const sectionStyle: CSSProperties = {
  display: "grid",
  gap: 16,
  maxWidth: 1200,
};

const titleStyle: CSSProperties = {
  margin: 0,
};

const descriptionStyle: CSSProperties = {
  margin: 0,
  color: "#4a5a50",
  fontSize: 15,
};

const panelCardStyle: CSSProperties = {
  padding: 20,
  backgroundColor: "#fff",
  borderRadius: 12,
  border: "1px solid #d4ddd5",
  display: "grid",
  gap: 12,
};

const panelTitleStyle: CSSProperties = {
  margin: 0,
  fontSize: 16,
  fontWeight: 700,
  color: "#183629",
};

const authFormStyle: CSSProperties = {
  display: "grid",
  gap: 14,
};

const formGroupStyle: CSSProperties = {
  display: "grid",
  gap: 6,
};

const labelStyle: CSSProperties = {
  fontSize: 13,
  fontWeight: 700,
  color: "#375545",
};

const textareaStyle: CSSProperties = {
  padding: 10,
  borderRadius: 8,
  border: "1px solid #8ba093",
  fontSize: 14,
  fontFamily: "monospace",
};

const selectStyle: CSSProperties = {
  padding: 10,
  borderRadius: 8,
  border: "1px solid #8ba093",
  fontSize: 14,
  backgroundColor: "#fff",
};

const primaryButtonStyle: CSSProperties = {
  width: "fit-content",
  padding: "10px 20px",
  borderRadius: 8,
  border: 0,
  background: "#183629",
  color: "#fff",
  fontWeight: 700,
  cursor: "pointer",
};

const compareButtonStyle: CSSProperties = {
  padding: "12px 24px",
  borderRadius: 8,
  border: 0,
  background: "#375545",
  color: "#fff",
  fontWeight: 700,
  cursor: "pointer",
  marginTop: 10,
  width: "fit-content",
};

const noticeStyle: CSSProperties = {
  padding: 12,
  borderRadius: 8,
  border: "1px solid",
  fontSize: 14,
};

const busyNotificationStyle: CSSProperties = {
  padding: 14,
  backgroundColor: "#f2f7fd",
  borderColor: "#528be0",
  borderRadius: 8,
  border: "1px solid",
  fontWeight: 700,
  color: "#1c3d5a",
};

const selectGridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
  gap: 16,
};

const resultsContainerStyle: CSSProperties = {
  display: "grid",
  gap: 20,
};

const runConfigGridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
  gap: 16,
};

const configCardStyle: CSSProperties = {
  padding: 16,
  backgroundColor: "#fff",
  borderRadius: 10,
  border: "1px solid #d4ddd5",
  display: "grid",
  gap: 8,
};

const configCardTitleStyle: CSSProperties = {
  margin: 0,
  fontSize: 15,
  fontWeight: 700,
  borderBottom: "1px solid #ede4d8",
  paddingBottom: 8,
};

const configMetadataStyle: CSSProperties = {
  display: "grid",
  gap: 6,
  fontSize: 13,
};

const metadataRowStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: 10,
};

const codeStyle: CSSProperties = {
  fontFamily: "monospace",
  backgroundColor: "#f8f3eb",
  padding: "2px 6px",
  borderRadius: 4,
};

const uuidStyle: CSSProperties = {
  fontFamily: "monospace",
  fontSize: 11,
};

const statsGridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
  gap: 12,
};

const metricCardStyle: CSSProperties = {
  display: "grid",
  gap: 4,
  padding: 16,
  backgroundColor: "#fff",
  borderRadius: 10,
  border: "1px solid #d4ddd5",
  textAlign: "center",
};

const metricLabelStyle: CSSProperties = {
  fontSize: 12,
  fontWeight: 700,
  color: "#375545",
  textTransform: "uppercase",
};

const metricValueStyle: CSSProperties = {
  fontSize: 28,
  fontWeight: 700,
};

const metricSubtextStyle: CSSProperties = {
  fontSize: 12,
  color: "#6c7a72",
};

const actionsRowStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  borderBottom: "2px solid #ede4d8",
  paddingBottom: 8,
  marginTop: 10,
};

const sectionTitleStyle: CSSProperties = {
  margin: 0,
};

const exportButtonStyle: CSSProperties = {
  padding: "8px 16px",
  borderRadius: 8,
  border: "1px solid #183629",
  background: "transparent",
  color: "#183629",
  fontWeight: 700,
  cursor: "pointer",
};

const toolbarStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  flexWrap: "wrap",
  gap: 12,
};

const filterGroupStyle: CSSProperties = {
  display: "flex",
  gap: 6,
};

const filterTabStyle = (active: boolean): CSSProperties => ({
  padding: "8px 14px",
  borderRadius: 6,
  border: active ? "1px solid #375545" : "1px solid rgba(55,85,69,0.15)",
  background: active ? "#375545" : "#fff",
  color: active ? "#fff" : "#375545",
  fontWeight: 600,
  cursor: "pointer",
  fontSize: 13,
});

const searchFormStyle: CSSProperties = {
  display: "flex",
  gap: 8,
};

const searchInputStyle: CSSProperties = {
  padding: "8px 12px",
  borderRadius: 6,
  border: "1px solid #8ba093",
  fontSize: 13,
  width: 200,
};

const inlineSelectStyle: CSSProperties = {
  padding: "8px 12px",
  borderRadius: 6,
  border: "1px solid #8ba093",
  fontSize: 13,
  backgroundColor: "#fff",
};

const tableWrapperStyle: CSSProperties = {
  backgroundColor: "#fff",
  borderRadius: 10,
  border: "1px solid #d4ddd5",
  overflow: "hidden",
};

const tableStyle: CSSProperties = {
  width: "100%",
  borderCollapse: "collapse",
  fontSize: 13,
};

const thRowStyle: CSSProperties = {
  backgroundColor: "#f8f3eb",
  borderBottom: "1px solid #d4ddd5",
  textAlign: "left",
};

const thStyle: CSSProperties = {
  padding: "12px 14px",
  fontWeight: 700,
  color: "#375545",
};

const trStyle: CSSProperties = {
  borderBottom: "1px solid #ede4d8",
};

const tdStyle: CSSProperties = {
  padding: "12px 14px",
  verticalAlign: "middle",
};

const caseKeyStyle: CSSProperties = {
  fontWeight: 600,
  color: "#1c2e24",
};

const privateBadgeStyle: CSSProperties = {
  fontSize: 10,
  fontWeight: 700,
  backgroundColor: "#fff8eb",
  color: "#b7791f",
  border: "1px solid #fbd38d",
  borderRadius: 4,
  padding: "2px 6px",
  marginLeft: 8,
};

const outcomeBadgeStyle = (passed: boolean): CSSProperties => ({
  display: "inline-block",
  padding: "2px 8px",
  borderRadius: 4,
  fontSize: 11,
  fontWeight: 700,
  backgroundColor: passed ? "#eef7f2" : "#fdf2f2",
  color: passed ? "#375545" : "#e05252",
  border: passed ? "1px solid #a3e2bc" : "1px solid #f8b4b4",
});

const emptyStateStyle: CSSProperties = {
  padding: 40,
  textAlign: "center",
  color: "#83928a",
  fontWeight: 600,
};
