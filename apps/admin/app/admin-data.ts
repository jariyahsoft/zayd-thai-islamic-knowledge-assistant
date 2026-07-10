export type SourceRecord = {
  readonly id: string;
  readonly name: string;
  readonly source_type: string;
  readonly owner: string | null;
  readonly website: string | null;
  readonly language: string;
  readonly country: string | null;
  readonly reliability_level: number;
  readonly is_active: boolean;
  readonly created_by: string;
  readonly updated_by: string | null;
  readonly created_at: string;
  readonly updated_at: string;
};

export type AdminDashboardSummary = {
  readonly registered_user_count: number;
  readonly queue_depth: number;
  readonly feedback_open_count: number;
  readonly incident_open_count: number;
  readonly provider_cost_limit_daily_usd: number;
  readonly provider_health_ok_count: number;
  readonly error_count: number;
  readonly external_fallback_count: number;
  readonly local_rag_hit_count: number;
  readonly citation_failure_count: number;
};

export type AdminDashboardResponse = { readonly generated_at: string; readonly window_minutes: number; readonly summary: AdminDashboardSummary };

export type SourceListResponse = {
  readonly sources: readonly SourceRecord[];
};

export type SourceCreatePayload = {
  readonly name: string;
  readonly source_type: string;
  readonly owner: string | null;
  readonly website: string | null;
  readonly language: string;
  readonly country: string | null;
  readonly reliability_level: number;
  readonly is_active: boolean;
};

export type LicenseRecord = {
  readonly id: string;
  readonly source_id: string;
  readonly license_name: string;
  readonly license_version: string | null;
  readonly status: string;
  readonly storage_permission: string;
  readonly embedding_permission: string;
  readonly commercial_use: string;
  readonly redistribution: string;
  readonly attribution_required: boolean;
  readonly attribution_template: string | null;
  readonly permission_document_key: string | null;
  readonly valid_from: string | null;
  readonly valid_until: string | null;
  readonly notes: string | null;
  readonly created_by: string;
  readonly updated_by: string | null;
  readonly created_at: string;
  readonly updated_at: string;
  readonly row_version: number;
};

export type LicenseListResponse = {
  readonly licenses: readonly LicenseRecord[];
};

export type LicenseCreatePayload = {
  readonly license_name: string;
  readonly license_version: string | null;
  readonly status: string;
  readonly storage_permission: string;
  readonly embedding_permission: string;
  readonly commercial_use: string;
  readonly redistribution: string;
  readonly attribution_required: boolean;
  readonly attribution_template: string | null;
  readonly permission_document_key: string | null;
  readonly valid_from: string | null;
  readonly valid_until: string | null;
  readonly notes: string | null;
};

export type PermissionDocumentResponse = {
  readonly license_id: string;
  readonly permission_document_key: string;
  readonly access: string;
  readonly audited: boolean;
};

export type LicensePolicyAction = {
  readonly action: string;
  readonly allowed: boolean;
  readonly reason_codes: readonly string[];
  readonly source_license_version: string | null;
  readonly max_cache_ttl_seconds: number | null;
  readonly attribution_required: boolean | null;
  readonly attribution_template: string | null;
};

export type LicensePolicyDecision = {
  readonly license_id: string;
  readonly source_id: string;
  readonly workflow: string;
  readonly policy_version: string;
  readonly evaluated_on: string;
  readonly source_license_version: string | null;
  readonly workflow_allowed: boolean;
  readonly llm_override_allowed: boolean;
  readonly reason_codes: readonly string[];
  readonly actions: readonly LicensePolicyAction[];
};

export type ProviderDisableImpactReadiness = {
  readonly model_type: string;
  readonly active_model_count: number;
  readonly alternative_model_count: number;
  readonly fallback_ready: boolean;
};

export type ProviderDisableImpact = {
  readonly provider_id: string;
  readonly provider_name: string;
  readonly active_model_count: number;
  readonly impacted_model_types: readonly string[];
  readonly fallback_readiness: readonly ProviderDisableImpactReadiness[];
  readonly safe_to_disable: boolean;
};

export type ProviderRecord = {
  readonly id: string;
  readonly name: string;
  readonly provider_type: string;
  readonly status: string;
  readonly base_url: string | null;
  readonly terms_url: string | null;
  readonly data_policy_json: Record<string, unknown>;
  readonly secret_configured: boolean;
  readonly secret_mask: string;
  readonly created_by: string;
  readonly updated_by: string | null;
  readonly created_at: string;
  readonly updated_at: string;
  readonly row_version: number;
  readonly model_count: number;
  readonly active_model_count: number;
  readonly disable_impact: ProviderDisableImpact;
};

export type ProviderListResponse = {
  readonly providers: readonly ProviderRecord[];
};

export type ProviderCreatePayload = {
  readonly name: string;
  readonly provider_type: string;
  readonly status: string;
  readonly base_url: string | null;
  readonly secret_ref: string | null;
  readonly terms_url: string | null;
  readonly data_policy_json: Record<string, unknown>;
};

export type ProviderUpdatePayload = Partial<ProviderCreatePayload>;

export type ProviderConnectionTestResult = {
  readonly provider_id: string;
  readonly provider_name: string;
  readonly status: string;
  readonly checked_at: string;
  readonly latency_ms: number;
  readonly message: string;
};

export type ModelRecord = {
  readonly id: string;
  readonly provider_id: string;
  readonly provider_name: string;
  readonly provider_status: string;
  readonly model_name: string;
  readonly model_type: string;
  readonly configuration: Record<string, unknown>;
  readonly allow_listed: boolean;
  readonly fallback_model_id: string | null;
  readonly fallback_model_name: string | null;
  readonly cost_limit_daily_usd: number | null;
  readonly is_default: boolean;
  readonly status: string;
  readonly created_by: string;
  readonly created_at: string;
  readonly updated_at: string;
  readonly row_version: number;
};

export type ModelListResponse = {
  readonly models: readonly ModelRecord[];
};

export type ModelCreatePayload = {
  readonly provider_id: string;
  readonly model_name: string;
  readonly model_type: string;
  readonly configuration: Record<string, unknown>;
  readonly allow_listed: boolean;
  readonly fallback_model_id: string | null;
  readonly cost_limit_daily_usd: number | null;
  readonly is_default: boolean;
  readonly status: string;
};

export type ModelUpdatePayload = Partial<ModelCreatePayload>;

export type AdminUserRecord = {
  readonly id: string;
  readonly email: string;
  readonly display_name: string;
  readonly status: string;
  readonly roles: readonly string[];
  readonly active_session_count: number;
  readonly last_login_at: string | null;
  readonly created_at: string;
  readonly updated_at: string;
  readonly row_version: number;
  readonly last_admin_guarded: boolean;
};

export type AdminUserListResponse = {
  readonly users: readonly AdminUserRecord[];
};

export type AdminUserStatusResponse = {
  readonly user: AdminUserRecord;
};

export type AdminUserStatusPayload = {
  readonly status: string;
};

export type AdminUserSessionRevokeResponse = {
  readonly revoked_sessions: number;
};

export type RoleAssignmentPayload = {
  readonly user_id: string;
  readonly role_name: string;
};

export type RoleAssignmentResult = {
  readonly status: string;
  readonly changed: boolean;
};

type ErrorResponse = {
  readonly error?: {
    readonly code?: string;
    readonly message?: string;
  };
};

async function parseJson<T>(response: Response): Promise<T> {
  return (await response.json()) as T;
}

function isErrorResponse(value: unknown): value is ErrorResponse {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  if (!("error" in candidate)) {
    return false;
  }
  const error = candidate.error;
  return !error || typeof error === "object";
}

async function request<T>(
  input: string,
  authToken: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(input, {
    ...init,
    headers: {
      "content-type": "application/json",
      authorization: `Bearer ${authToken}`,
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const payload = await parseJson<unknown>(response).catch(() => null);
    const message =
      isErrorResponse(payload) && payload.error?.code && payload.error?.message
        ? `${payload.error.code}: ${payload.error.message}`
        : `HTTP ${response.status}`;
    throw new Error(message);
  }

  return parseJson<T>(response);
}

function url(baseUrl: string, path: string, search?: URLSearchParams): string {
  const normalized = new URL(path, baseUrl);
  if (search) {
    normalized.search = search.toString();
  }
  return normalized.toString();
}

export async function getAdminDashboard(baseUrl: string, authToken: string, windowMinutes: number): Promise<AdminDashboardResponse> {
  return request<AdminDashboardResponse>(url(baseUrl, "/admin/dashboard", new URLSearchParams({ window_minutes: String(windowMinutes) })), authToken);
}

export async function listSources(
  baseUrl: string,
  authToken: string,
  query?: string,
): Promise<readonly SourceRecord[]> {
  const search = new URLSearchParams();
  if (query) {
    search.set("name", query);
  }
  const payload = await request<SourceListResponse>(
    url(baseUrl, "/admin/sources", search),
    authToken,
  );
  return payload.sources;
}

export async function createSource(
  baseUrl: string,
  authToken: string,
  payload: SourceCreatePayload,
): Promise<SourceRecord> {
  return request<SourceRecord>(url(baseUrl, "/admin/sources"), authToken, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateSource(
  baseUrl: string,
  authToken: string,
  sourceId: string,
  payload: Partial<SourceCreatePayload>,
): Promise<SourceRecord> {
  return request<SourceRecord>(
    url(baseUrl, `/admin/sources/${sourceId}`),
    authToken,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    },
  );
}

export async function suspendSource(
  baseUrl: string,
  authToken: string,
  sourceId: string,
): Promise<SourceRecord> {
  return request<SourceRecord>(
    url(baseUrl, `/admin/sources/${sourceId}/suspend`),
    authToken,
    {
      method: "POST",
      body: JSON.stringify({}),
    },
  );
}

export async function listLicenses(
  baseUrl: string,
  authToken: string,
  sourceId: string,
): Promise<readonly LicenseRecord[]> {
  const payload = await request<LicenseListResponse>(
    url(baseUrl, `/admin/sources/${sourceId}/licenses`),
    authToken,
  );
  return payload.licenses;
}

export async function createLicense(
  baseUrl: string,
  authToken: string,
  sourceId: string,
  payload: LicenseCreatePayload,
): Promise<LicenseRecord> {
  return request<LicenseRecord>(
    url(baseUrl, `/admin/sources/${sourceId}/licenses`),
    authToken,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export async function replaceLicense(
  baseUrl: string,
  authToken: string,
  licenseId: string,
  payload: LicenseCreatePayload,
): Promise<LicenseRecord> {
  return request<LicenseRecord>(
    url(baseUrl, `/admin/licenses/${licenseId}/replace`),
    authToken,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export async function getPermissionDocumentMetadata(
  baseUrl: string,
  authToken: string,
  licenseId: string,
): Promise<PermissionDocumentResponse> {
  return request<PermissionDocumentResponse>(
    url(baseUrl, `/admin/licenses/${licenseId}/permission-document`),
    authToken,
  );
}

export async function getPolicyDecision(
  baseUrl: string,
  authToken: string,
  licenseId: string,
  workflow: string,
): Promise<LicensePolicyDecision> {
  const search = new URLSearchParams({ workflow });
  return request<LicensePolicyDecision>(
    url(baseUrl, `/admin/licenses/${licenseId}/policy-decision`, search),
    authToken,
  );
}

export async function listProviders(
  baseUrl: string,
  authToken: string,
): Promise<readonly ProviderRecord[]> {
  const payload = await request<ProviderListResponse>(
    url(baseUrl, "/admin/providers"),
    authToken,
  );
  return payload.providers;
}

export async function createProvider(
  baseUrl: string,
  authToken: string,
  payload: ProviderCreatePayload,
): Promise<ProviderRecord> {
  return request<ProviderRecord>(url(baseUrl, "/admin/providers"), authToken, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateProvider(
  baseUrl: string,
  authToken: string,
  providerId: string,
  payload: ProviderUpdatePayload,
): Promise<ProviderRecord> {
  return request<ProviderRecord>(
    url(baseUrl, `/admin/providers/${providerId}`),
    authToken,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    },
  );
}

export async function testProviderConnection(
  baseUrl: string,
  authToken: string,
  providerId: string,
): Promise<ProviderConnectionTestResult> {
  return request<ProviderConnectionTestResult>(
    url(baseUrl, `/admin/providers/${providerId}/test-connection`),
    authToken,
    {
      method: "POST",
      body: JSON.stringify({}),
    },
  );
}

export async function listModels(
  baseUrl: string,
  authToken: string,
): Promise<readonly ModelRecord[]> {
  const payload = await request<ModelListResponse>(
    url(baseUrl, "/admin/models"),
    authToken,
  );
  return payload.models;
}

export async function createModel(
  baseUrl: string,
  authToken: string,
  payload: ModelCreatePayload,
): Promise<ModelRecord> {
  return request<ModelRecord>(url(baseUrl, "/admin/models"), authToken, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateModel(
  baseUrl: string,
  authToken: string,
  modelId: string,
  payload: ModelUpdatePayload,
): Promise<ModelRecord> {
  return request<ModelRecord>(url(baseUrl, `/admin/models/${modelId}`), authToken, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function listAdminUsers(
  baseUrl: string,
  authToken: string,
  filters?: {
    readonly query?: string;
    readonly status?: string;
    readonly role?: string;
  },
): Promise<readonly AdminUserRecord[]> {
  const search = new URLSearchParams();
  if (filters?.query) {
    search.set("query", filters.query);
  }
  if (filters?.status) {
    search.set("status", filters.status);
  }
  if (filters?.role) {
    search.set("role", filters.role);
  }
  const payload = await request<AdminUserListResponse>(
    url(baseUrl, "/admin/users", search),
    authToken,
  );
  return payload.users;
}

export async function updateAdminUserStatus(
  baseUrl: string,
  authToken: string,
  userId: string,
  payload: AdminUserStatusPayload,
): Promise<AdminUserRecord> {
  const result = await request<AdminUserStatusResponse>(
    url(baseUrl, `/admin/users/${userId}/status`),
    authToken,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    },
  );
  return result.user;
}

export async function revokeAdminUserSessions(
  baseUrl: string,
  authToken: string,
  userId: string,
): Promise<number> {
  const payload = await request<AdminUserSessionRevokeResponse>(
    url(baseUrl, `/admin/users/${userId}/sessions/revoke`),
    authToken,
    {
      method: "POST",
      body: JSON.stringify({}),
    },
  );
  return payload.revoked_sessions;
}

export async function grantRole(
  baseUrl: string,
  authToken: string,
  payload: RoleAssignmentPayload,
): Promise<RoleAssignmentResult> {
  return request<RoleAssignmentResult>(
    url(baseUrl, "/admin/users/roles/grant"),
    authToken,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export async function revokeRole(
  baseUrl: string,
  authToken: string,
  payload: RoleAssignmentPayload,
): Promise<RoleAssignmentResult> {
  return request<RoleAssignmentResult>(
    url(baseUrl, "/admin/users/roles/revoke"),
    authToken,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}
