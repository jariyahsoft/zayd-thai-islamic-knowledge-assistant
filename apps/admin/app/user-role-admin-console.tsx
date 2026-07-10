"use client";

import type { CSSProperties, ReactElement } from "react";
import { startTransition, useState } from "react";
import type { AdminUserRecord } from "./admin-data.js";
import {
  grantRole,
  listAdminUsers,
  revokeAdminUserSessions,
  revokeRole,
  updateAdminUserStatus,
} from "./admin-data.js";
import { sortRoles, summarizeUserRisk } from "./user-admin-ui.js";

type Notice = {
  readonly tone: "success" | "error" | "info";
  readonly message: string;
};

export function UserRoleAdminConsole(props: {
  readonly apiBaseUrl: string;
}): ReactElement {
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [users, setUsers] = useState<readonly AdminUserRecord[]>([]);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [role, setRole] = useState("");
  const [roleDrafts, setRoleDrafts] = useState<Record<string, string>>({});

  async function refresh(): Promise<void> {
    setBusy("Loading user records...");
    try {
      const nextUsers = await listAdminUsers(props.apiBaseUrl, token.trim(), {
        query: query.trim() || undefined,
        status: status.trim() || undefined,
        role: role.trim() || undefined,
      });
      setUsers(nextUsers);
      setRoleDrafts((current) => {
        const next: Record<string, string> = {};
        for (const user of nextUsers) {
          next[user.id] = current[user.id] ?? "";
        }
        return next;
      });
      setNotice(null);
    } catch (error) {
      setNotice({ tone: "error", message: errorMessage(error) });
      setUsers([]);
    } finally {
      setBusy(null);
    }
  }

  async function submitStatus(user: AdminUserRecord, nextStatus: string): Promise<void> {
    setBusy(`${nextStatus === "disabled" ? "Disabling" : "Enabling"} account...`);
    try {
      const updated = await updateAdminUserStatus(
        props.apiBaseUrl,
        token.trim(),
        user.id,
        { status: nextStatus },
      );
      setUsers((current) => current.map((entry) => (entry.id === user.id ? updated : entry)));
      setNotice({
        tone: "success",
        message:
          nextStatus === "disabled"
            ? `${user.email} disabled and active sessions revoked.`
            : `${user.email} re-enabled.`,
      });
    } catch (error) {
      setNotice({ tone: "error", message: errorMessage(error) });
    } finally {
      setBusy(null);
    }
  }

  async function submitRevokeSessions(user: AdminUserRecord): Promise<void> {
    setBusy("Revoking user sessions...");
    try {
      const revoked = await revokeAdminUserSessions(
        props.apiBaseUrl,
        token.trim(),
        user.id,
      );
      setUsers((current) =>
        current.map((entry) =>
          entry.id === user.id ? { ...entry, active_session_count: 0 } : entry,
        ),
      );
      setNotice({
        tone: "success",
        message: `${revoked} session(s) revoked for ${user.email}.`,
      });
    } catch (error) {
      setNotice({ tone: "error", message: errorMessage(error) });
    } finally {
      setBusy(null);
    }
  }

  async function submitGrantRole(user: AdminUserRecord): Promise<void> {
    const roleName = roleDrafts[user.id]?.trim();
    if (!roleName) {
      setNotice({ tone: "error", message: "Enter a role name before granting." });
      return;
    }
    setBusy("Granting role...");
    try {
      await grantRole(props.apiBaseUrl, token.trim(), {
        user_id: user.id,
        role_name: roleName,
      });
      setNotice({ tone: "success", message: `Granted ${roleName} to ${user.email}.` });
      await refresh();
    } catch (error) {
      setNotice({ tone: "error", message: errorMessage(error) });
    } finally {
      setBusy(null);
    }
  }

  async function submitRevokeRole(user: AdminUserRecord, roleName: string): Promise<void> {
    setBusy("Revoking role...");
    try {
      await revokeRole(props.apiBaseUrl, token.trim(), {
        user_id: user.id,
        role_name: roleName,
      });
      setNotice({ tone: "success", message: `Revoked ${roleName} from ${user.email}.` });
      await refresh();
    } catch (error) {
      setNotice({ tone: "error", message: errorMessage(error) });
    } finally {
      setBusy(null);
    }
  }

  return (
    <section style={sectionStyle}>
      <div style={heroStyle}>
        <div>
          <p style={eyebrowStyle}>TASK-10-06</p>
          <h2 style={titleStyle}>User and role management</h2>
          <p style={copyStyle}>
            Search accounts, grant or revoke roles, disable users with active
            session revocation, and surface the final-admin guard before
            high-risk changes.
          </p>
        </div>
        <div style={tokenCardStyle}>
          <label htmlFor="user-admin-token" style={labelStyle}>
            Bearer token
          </label>
          <textarea
            id="user-admin-token"
            rows={4}
            value={token}
            onChange={(event) => {
              const next = event.target.value;
              startTransition(() => {
                setToken(next);
                if (!next.trim()) {
                  setUsers([]);
                  setNotice(null);
                }
              });
            }}
            placeholder="Paste a temporary admin token. It stays in memory only."
            style={textAreaStyle}
          />
          <div style={filterGridStyle}>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search by email or name"
              style={inputDarkStyle}
            />
            <input
              value={status}
              onChange={(event) => setStatus(event.target.value)}
              placeholder="Status filter"
              style={inputDarkStyle}
            />
            <input
              value={role}
              onChange={(event) => setRole(event.target.value)}
              placeholder="Role filter"
              style={inputDarkStyle}
            />
          </div>
          <button type="button" onClick={() => void refresh()} style={primaryButtonStyle}>
            Load user records
          </button>
        </div>
      </div>

      {notice ? <div style={bannerStyle(notice.tone)}>{notice.message}</div> : null}
      {busy ? <div style={bannerStyle("info")}>{busy}</div> : null}

      <div style={stackStyle}>
        {users.map((user) => (
          <article key={user.id} style={cardStyle}>
            <div style={headerRowStyle}>
              <div>
                <h3 style={sectionTitleStyle}>{user.display_name}</h3>
                <p style={mutedStyle}>
                  {user.email} · {user.status} · {user.active_session_count} active
                  session(s)
                </p>
              </div>
              <span style={statusPillStyle(user.status)}>
                {user.last_admin_guarded ? "Final active admin" : user.status}
              </span>
            </div>

            <p style={mutedStyle}>{summarizeUserRisk(user)}</p>

            <div style={roleWrapStyle}>
              {sortRoles(user.roles).map((assignedRole) => (
                <button
                  key={`${user.id}-${assignedRole}`}
                  type="button"
                  onClick={() => void submitRevokeRole(user, assignedRole)}
                  style={roleChipStyle(assignedRole === "admin")}
                >
                  {assignedRole}
                </button>
              ))}
            </div>

            <div style={actionGridStyle}>
              <input
                value={roleDrafts[user.id] ?? ""}
                onChange={(event) =>
                  setRoleDrafts((current) => ({
                    ...current,
                    [user.id]: event.target.value,
                  }))
                }
                placeholder="Role to grant"
                style={inputStyle}
              />
              <button type="button" onClick={() => void submitGrantRole(user)} style={secondaryButtonStyle}>
                Grant role
              </button>
              <button
                type="button"
                onClick={() => void submitRevokeSessions(user)}
                style={secondaryButtonStyle}
              >
                Revoke sessions
              </button>
              <button
                type="button"
                onClick={() =>
                  void submitStatus(
                    user,
                    user.status === "disabled" ? "active" : "disabled",
                  )
                }
                style={user.status === "disabled" ? primaryButtonStyle : dangerButtonStyle}
              >
                {user.status === "disabled" ? "Enable account" : "Disable account"}
              </button>
            </div>
          </article>
        ))}
        {users.length === 0 ? (
          <div style={cardStyle}>
            Load protected admin users to manage roles, status, and sessions.
          </div>
        ) : null}
      </div>
    </section>
  );
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Request failed.";
}

const sectionStyle: CSSProperties = {
  display: "grid",
  gap: 20,
};

const heroStyle: CSSProperties = {
  display: "grid",
  gap: 18,
  gridTemplateColumns: "1.3fr 1fr",
  alignItems: "start",
};

const eyebrowStyle: CSSProperties = {
  margin: 0,
  textTransform: "uppercase",
  letterSpacing: "0.14em",
  fontSize: 12,
  color: "#456050",
};

const titleStyle: CSSProperties = {
  margin: "8px 0 0",
  fontSize: "clamp(1.9rem, 4vw, 3rem)",
};

const copyStyle: CSSProperties = {
  margin: "12px 0 0",
  color: "#486054",
};

const tokenCardStyle: CSSProperties = {
  borderRadius: 28,
  padding: 20,
  background: "#173127",
  color: "#eff6ef",
  display: "grid",
  gap: 12,
};

const labelStyle: CSSProperties = {
  fontSize: 12,
  textTransform: "uppercase",
  letterSpacing: "0.12em",
};

const textAreaStyle: CSSProperties = {
  width: "100%",
  borderRadius: 18,
  border: "1px solid rgba(255,255,255,0.14)",
  padding: "12px 14px",
  background: "#10231b",
  color: "#eff6ef",
  resize: "vertical",
};

const filterGridStyle: CSSProperties = {
  display: "grid",
  gap: 10,
  gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
};

const inputDarkStyle: CSSProperties = {
  borderRadius: 14,
  border: "1px solid rgba(255,255,255,0.14)",
  padding: "10px 12px",
  background: "#10231b",
  color: "#eff6ef",
};

const stackStyle: CSSProperties = {
  display: "grid",
  gap: 18,
};

const cardStyle: CSSProperties = {
  borderRadius: 28,
  padding: 22,
  background: "rgba(255,252,248,0.92)",
  border: "1px solid rgba(24,54,41,0.08)",
  boxShadow: "0 20px 42px rgba(41,54,46,0.08)",
  display: "grid",
  gap: 14,
};

const headerRowStyle: CSSProperties = {
  display: "flex",
  gap: 12,
  justifyContent: "space-between",
  alignItems: "start",
  flexWrap: "wrap",
};

const sectionTitleStyle: CSSProperties = {
  margin: 0,
  fontSize: 24,
};

const mutedStyle: CSSProperties = {
  margin: "6px 0 0",
  color: "#596d63",
};

const roleWrapStyle: CSSProperties = {
  display: "flex",
  gap: 10,
  flexWrap: "wrap",
};

const roleChipStyle = (isAdmin: boolean): CSSProperties => ({
  borderRadius: 999,
  border: isAdmin ? "1px solid #7f3628" : "1px solid rgba(24,54,41,0.14)",
  background: isAdmin ? "#f7ddd6" : "#eef4ee",
  color: isAdmin ? "#7f3628" : "#183629",
  padding: "8px 12px",
  fontWeight: 700,
});

const actionGridStyle: CSSProperties = {
  display: "grid",
  gap: 10,
  gridTemplateColumns: "minmax(180px, 1fr) repeat(3, auto)",
};

const inputStyle: CSSProperties = {
  width: "100%",
  borderRadius: 14,
  border: "1px solid rgba(24,54,41,0.12)",
  padding: "12px 14px",
  background: "#fffaf4",
  color: "#18211c",
};

const primaryButtonStyle: CSSProperties = {
  borderRadius: 16,
  border: "1px solid #183629",
  background: "#183629",
  color: "#f5efe6",
  padding: "12px 16px",
  fontWeight: 700,
};

const secondaryButtonStyle: CSSProperties = {
  borderRadius: 16,
  border: "1px solid rgba(24,54,41,0.18)",
  background: "#f8f3eb",
  color: "#183629",
  padding: "12px 16px",
  fontWeight: 700,
};

const dangerButtonStyle: CSSProperties = {
  borderRadius: 16,
  border: "1px solid #8c4d41",
  background: "#8c4d41",
  color: "#fff4ee",
  padding: "12px 16px",
  fontWeight: 700,
};

const bannerStyle = (tone: "success" | "error" | "info"): CSSProperties => ({
  borderRadius: 18,
  padding: "14px 18px",
  background:
    tone === "success" ? "#e7f4e9" : tone === "error" ? "#f8e2dd" : "#eef3f5",
  border:
    tone === "success"
      ? "1px solid #8eb698"
      : tone === "error"
        ? "1px solid #d18c7f"
        : "1px solid #9eb3bc",
});

const statusPillStyle = (status: string): CSSProperties => ({
  borderRadius: 999,
  background: status === "disabled" ? "#f7ddd6" : "#dce8de",
  color: status === "disabled" ? "#8a4031" : "#1b3a2d",
  padding: "8px 12px",
  fontWeight: 700,
  fontSize: 13,
});
