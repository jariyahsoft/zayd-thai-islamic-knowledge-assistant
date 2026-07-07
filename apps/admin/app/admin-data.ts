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
