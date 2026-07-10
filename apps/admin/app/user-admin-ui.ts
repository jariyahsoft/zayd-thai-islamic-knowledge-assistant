import type { AdminUserRecord } from "./admin-data.js";

export type UserFilters = {
  readonly query: string;
  readonly status: string;
  readonly role: string;
};

export function summarizeUserRisk(user: AdminUserRecord): string {
  if (user.last_admin_guarded) {
    return "This is the final active admin. Disable or admin-role removal is guarded.";
  }
  if (user.status === "disabled") {
    return "Account is disabled and active sessions should already be revoked.";
  }
  if (user.active_session_count > 0) {
    return `${user.active_session_count} active session(s) will be revoked if you disable this account.`;
  }
  return "No active sessions are currently tracked for this account.";
}

export function sortRoles(roles: readonly string[]): readonly string[] {
  return [...roles].sort((left, right) => left.localeCompare(right));
}
