"use client";

import type { CSSProperties, ReactElement } from "react";
import { useState } from "react";
import { ProviderModelConsole } from "./provider-model-console.js";
import { SourceLicenseAdminConsole } from "./source-license-admin-console.js";
import { UserRoleAdminConsole } from "./user-role-admin-console.js";
import { AdminDashboard } from "./admin-dashboard.js";
import { EvaluationConsole } from "./evaluation-console.js";

type ViewKey = "dashboard" | "sources" | "providers" | "users" | "evaluation";

export function AdminWorkspace(props: {
  readonly apiBaseUrl: string;
}): ReactElement {
  const [view, setView] = useState<ViewKey>("dashboard");

  return (
    <main style={shellStyle}>
      <div style={frameStyle}>
        <header style={headerStyle}>
          <div>
            <p style={eyebrowStyle}>Zayd Admin Workspace</p>
            <h1 style={titleStyle}>Governed operations console</h1>
          </div>
          <nav style={navStyle} aria-label="Admin sections">
            <TabButton active={view === "dashboard"} label="Dashboard" onClick={() => setView("dashboard")} />
            <TabButton
              active={view === "providers"}
              label="Providers & Models"
              onClick={() => setView("providers")}
            />
            <TabButton
              active={view === "users"}
              label="Users & Roles"
              onClick={() => setView("users")}
            />
            <TabButton
              active={view === "sources"}
              label="Sources & Licenses"
              onClick={() => setView("sources")}
            />
            <TabButton
              active={view === "evaluation"}
              label="Evaluation Dashboard"
              onClick={() => setView("evaluation")}
            />
          </nav>
        </header>

        {view === "dashboard" ? <AdminDashboard apiBaseUrl={props.apiBaseUrl} /> : null}
        {view === "providers" ? (
          <ProviderModelConsole apiBaseUrl={props.apiBaseUrl} />
        ) : null}
        {view === "users" ? (
          <UserRoleAdminConsole apiBaseUrl={props.apiBaseUrl} />
        ) : null}
        {view === "sources" ? (
          <SourceLicenseAdminConsole apiBaseUrl={props.apiBaseUrl} />
        ) : null}
        {view === "evaluation" ? (
          <EvaluationConsole apiBaseUrl={props.apiBaseUrl} />
        ) : null}
      </div>
    </main>
  );
}

function TabButton(props: {
  readonly active: boolean;
  readonly label: string;
  readonly onClick: () => void;
}): ReactElement {
  return (
    <button
      type="button"
      onClick={props.onClick}
      style={{
        borderRadius: 999,
        border: props.active ? "1px solid #183629" : "1px solid rgba(24,54,41,0.16)",
        background: props.active ? "#183629" : "#f6efe5",
        color: props.active ? "#f5efe6" : "#183629",
        padding: "10px 16px",
        fontWeight: 700,
      }}
    >
      {props.label}
    </button>
  );
}

const shellStyle: CSSProperties = {
  minHeight: "100vh",
  background:
    "radial-gradient(circle at top left, rgba(198,214,203,0.8), transparent 38%), linear-gradient(180deg, #ede4d8 0%, #f8f3eb 100%)",
  color: "#132019",
};

const frameStyle: CSSProperties = {
  width: "min(1320px, calc(100vw - 32px))",
  margin: "0 auto",
  padding: "28px 0 40px",
};

const headerStyle: CSSProperties = {
  display: "grid",
  gap: 18,
  marginBottom: 24,
};

const eyebrowStyle: CSSProperties = {
  margin: 0,
  textTransform: "uppercase",
  letterSpacing: "0.14em",
  fontSize: 12,
  color: "#375545",
};

const titleStyle: CSSProperties = {
  margin: "8px 0 0",
  fontSize: "clamp(2rem, 5vw, 3.3rem)",
};

const navStyle: CSSProperties = {
  display: "flex",
  gap: 10,
  flexWrap: "wrap",
};
