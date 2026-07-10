"use client";

export type ReviewerDashboardSummary = {
  readonly total_visible_count: number;
  readonly pending_count: number;
  readonly assigned_count: number;
  readonly overdue_count: number;
  readonly changes_requested_count: number;
  readonly feedback_open_count: number;
};

export type ReviewTaskSummary = {
  readonly id: string;
  readonly document_version_id: string;
  readonly document_id: string;
  readonly review_level: string;
  readonly status: string;
  readonly priority: string;
  readonly category: string | null;
  readonly language: string | null;
  readonly madhhab: string | null;
  readonly assigned_to: string | null;
  readonly due_at: string | null;
  readonly created_at: string;
  readonly updated_at: string;
  readonly document_title: string | null;
  readonly document_type: string | null;
};

export type ReviewerFeedbackWorkItem = {
  readonly id: string;
  readonly category: string;
  readonly status: string;
  readonly answer_id: string | null;
  readonly citation_id: string | null;
  readonly created_at: string;
};

export type ReviewerDashboardData = {
  readonly summary: ReviewerDashboardSummary;
  readonly queue: {
    readonly tasks: readonly ReviewTaskSummary[];
    readonly total_count: number;
    readonly limit: number;
    readonly offset: number;
    readonly next_offset: number | null;
  };
  readonly feedback_items: readonly ReviewerFeedbackWorkItem[];
};

export type FeedbackReviewItem = {
  readonly id: string;
  readonly category: string;
  readonly status: string;
  readonly priority: string;
  readonly severity: string;
  readonly reviewer_id: string | null;
  readonly root_cause: string | null;
  readonly created_at: string;
};

export type FeedbackReviewQueue = {
  readonly items: readonly FeedbackReviewItem[];
  readonly total_count: number;
};

export type FeedbackReviewDetail = FeedbackReviewItem & {
  readonly reviewer_notes: string;
  readonly resolution: string | null;
  readonly trace_context: {
    readonly retrieval_run_id: string;
    readonly model_configuration_id: string;
    readonly prompt_version_id: string;
    readonly policy_version_id: string;
  } | null;
};

export type PrincipalResponse = {
  readonly id: string;
  readonly email: string;
  readonly roles: readonly string[];
  readonly permissions: readonly string[];
};

export type ReviewComment = {
  readonly id: string;
  readonly review_task_id: string;
  readonly author_id: string;
  readonly body: string;
  readonly anchor: Record<string, unknown>;
  readonly created_at: string;
};

export type ReviewDraft = {
  readonly review_task_id: string;
  readonly document_version_id: string;
  readonly document_id: string;
  readonly source_id: string | null;
  readonly source_license_id: string | null;
  readonly canonical_id: string | null;
  readonly document_title: string | null;
  readonly document_type: string | null;
  readonly language: string | null;
  readonly madhhab: string | null;
  readonly task_status: string;
  readonly task_row_version: number;
  readonly document_review_status: string;
  readonly original_file_key: string | null;
  readonly editable_text: string | null;
  readonly editable_metadata: Record<string, unknown>;
  readonly latest_revision_number: number;
  readonly revisions: readonly ReviewRevision[];
  readonly comments: readonly ReviewComment[];
};

export type ReviewRevision = {
  readonly id: string;
  readonly review_task_id: string;
  readonly document_version_id: string;
  readonly actor_user_id: string;
  readonly revision_number: number;
  readonly base_task_row_version: number;
  readonly text_changed: boolean;
  readonly metadata_changed_fields: readonly string[];
  readonly diff_text: string;
  readonly created_at: string;
};

export type ReviewEditResult = {
  readonly status: string;
  readonly task_row_version: number;
  readonly revision: ReviewRevision;
  readonly editable_text: string | null;
  readonly editable_metadata: Record<string, unknown>;
};

export type ReviewDecisionResult = {
  readonly status: string;
  readonly task_row_version: number;
  readonly decision: {
    readonly id: string;
    readonly review_task_id: string;
    readonly document_version_id: string;
    readonly actor_user_id: string;
    readonly decision: string;
    readonly reason: string;
    readonly resulting_task_status: string;
    readonly resulting_document_status: string;
    readonly created_at: string;
  };
};

export type SourceDetail = {
  readonly source: {
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
  readonly warnings: readonly string[];
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
  readonly actions: readonly {
    readonly action: string;
    readonly allowed: boolean;
    readonly reason_codes: readonly string[];
    readonly source_license_version: string | null;
    readonly max_cache_ttl_seconds: number | null;
    readonly attribution_required: boolean | null;
    readonly attribution_template: string | null;
  }[];
};

export type LicenseDetail = {
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

export type ApprovalRequirement = {
  readonly document_version_id: string;
  readonly content_risk: "routine" | "sensitive" | "restricted";
  readonly required_levels: readonly string[];
  readonly satisfied_levels: readonly string[];
  readonly missing_levels: readonly string[];
  readonly ready_for_publish: boolean;
};

export type ApprovalRecord = {
  readonly id: string;
  readonly document_version_id: string;
  readonly review_task_id: string;
  readonly approver_id: string;
  readonly approval_level: "initial" | "scholar" | "board";
  readonly content_risk: "routine" | "sensitive" | "restricted";
  readonly status: string;
  readonly reason: string;
  readonly valid_until: string | null;
  readonly revoked_at: string | null;
  readonly revoked_by: string | null;
  readonly revoke_reason: string | null;
  readonly created_at: string;
};

export type ApprovalActionResult = {
  readonly status: string;
  readonly approval: ApprovalRecord;
};

export type ApprovalListResult = {
  readonly document_version_id: string;
  readonly approvals: readonly ApprovalRecord[];
};

type ErrorResponse = {
  readonly error?: {
    readonly code?: string;
    readonly message?: string;
  };
};

export class ReviewerClientError extends Error {
  readonly statusCode: number;
  readonly code: string;

  constructor(code: string, message: string, statusCode: number) {
    super(message);
    this.name = "ReviewerClientError";
    this.code = code;
    this.statusCode = statusCode;
  }
}

function buildUrl(baseUrl: string, path: string, params?: URLSearchParams): URL {
  const url = new URL(path, baseUrl);
  if (params) {
    url.search = params.toString();
  }
  return url;
}

async function parseError(response: Response): Promise<ReviewerClientError> {
  const fallback = new ReviewerClientError(
    "REVIEWER_REQUEST_FAILED",
    "ไม่สามารถติดต่อเซิร์ฟเวอร์รีวิวได้",
    response.status,
  );
  try {
    const payload = (await response.json()) as ErrorResponse;
    const code = payload.error?.code ?? fallback.code;
    const message = payload.error?.message ?? fallback.message;
    return new ReviewerClientError(code, message, response.status);
  } catch {
    return fallback;
  }
}

async function request<T>(
  baseUrl: string,
  accessToken: string,
  path: string,
  options?: {
    readonly method?: string;
    readonly params?: URLSearchParams;
    readonly body?: unknown;
  },
): Promise<T> {
  const response = await fetch(buildUrl(baseUrl, path, options?.params), {
    method: options?.method ?? "GET",
    headers: {
      authorization: `Bearer ${accessToken}`,
      ...(options?.body === undefined ? {} : { "content-type": "application/json" }),
    },
    body: options?.body === undefined ? undefined : JSON.stringify(options.body),
    cache: "no-store",
  });
  if (!response.ok) {
    throw await parseError(response);
  }
  return (await response.json()) as T;
}

export async function fetchPrincipal(
  apiBaseUrl: string,
  accessToken: string,
): Promise<PrincipalResponse> {
  return request<PrincipalResponse>(apiBaseUrl, accessToken, "/auth/me");
}

export async function fetchReviewerDashboard(
  apiBaseUrl: string,
  accessToken: string,
  options?: {
    readonly status?: string;
    readonly assignedToUserId?: string;
    readonly dueOnly?: "all" | "overdue";
    readonly limit?: number;
    readonly offset?: number;
    readonly feedbackLimit?: number;
  },
): Promise<ReviewerDashboardData> {
  const params = new URLSearchParams();
  if (options?.status) {
    params.set("status", options.status);
  }
  if (options?.assignedToUserId) {
    params.set("assigned_to", options.assignedToUserId);
  }
  if (options?.dueOnly === "overdue") {
    params.set("due_before", new Date().toISOString());
  }
  params.set("limit", String(options?.limit ?? 12));
  params.set("offset", String(options?.offset ?? 0));
  params.set("feedback_limit", String(options?.feedbackLimit ?? 5));
  return request<ReviewerDashboardData>(
    apiBaseUrl,
    accessToken,
    "/reviews/dashboard",
    { params },
  );
}

export async function fetchFeedbackReviewQueue(
  apiBaseUrl: string,
  accessToken: string,
  status?: string,
): Promise<FeedbackReviewQueue> {
  const params = new URLSearchParams({ limit: "50" });
  if (status) params.set("status", status);
  return request<FeedbackReviewQueue>(apiBaseUrl, accessToken, "/admin/feedback", { params });
}

export async function fetchFeedbackReviewDetail(apiBaseUrl: string, accessToken: string, id: string): Promise<FeedbackReviewDetail> {
  return request<FeedbackReviewDetail>(apiBaseUrl, accessToken, `/admin/feedback/${id}/review`);
}

export async function fetchReviewDraft(
  apiBaseUrl: string,
  accessToken: string,
  reviewTaskId: string,
): Promise<ReviewDraft> {
  return request<ReviewDraft>(apiBaseUrl, accessToken, `/reviews/${reviewTaskId}/draft`);
}

export async function updateReviewDraft(
  apiBaseUrl: string,
  accessToken: string,
  reviewTaskId: string,
  payload: {
    readonly base_task_row_version: number;
    readonly text?: string;
    readonly metadata_updates?: Record<string, unknown>;
  },
): Promise<ReviewEditResult> {
  return request<ReviewEditResult>(apiBaseUrl, accessToken, `/reviews/${reviewTaskId}/draft`, {
    method: "PATCH",
    body: payload,
  });
}

export async function addReviewComment(
  apiBaseUrl: string,
  accessToken: string,
  reviewTaskId: string,
  payload: {
    readonly body: string;
    readonly anchor?: Record<string, unknown>;
  },
): Promise<ReviewComment> {
  return request<ReviewComment>(apiBaseUrl, accessToken, `/reviews/${reviewTaskId}/comments`, {
    method: "POST",
    body: payload,
  });
}

export async function submitReviewDecision(
  apiBaseUrl: string,
  accessToken: string,
  reviewTaskId: string,
  payload: {
    readonly decision: "approve" | "request_changes" | "reject";
    readonly reason: string;
    readonly base_task_row_version: number;
  },
): Promise<ReviewDecisionResult> {
  return request<ReviewDecisionResult>(
    apiBaseUrl,
    accessToken,
    `/reviews/${reviewTaskId}/decision`,
    {
      method: "POST",
      body: payload,
    },
  );
}

export async function fetchApprovalRequirements(
  apiBaseUrl: string,
  accessToken: string,
  documentVersionId: string,
  contentRisk: ApprovalRequirement["content_risk"],
): Promise<ApprovalRequirement> {
  const params = new URLSearchParams({ content_risk: contentRisk });
  return request<ApprovalRequirement>(
    apiBaseUrl,
    accessToken,
    `/documents/${documentVersionId}/approval-requirements`,
    { params },
  );
}

export async function createScholarApproval(
  apiBaseUrl: string,
  accessToken: string,
  reviewTaskId: string,
  payload: {
    readonly content_risk: ApprovalRequirement["content_risk"];
    readonly approval_level: ApprovalRecord["approval_level"];
    readonly reason: string;
    readonly valid_until?: string | null;
  },
): Promise<ApprovalActionResult> {
  return request<ApprovalActionResult>(apiBaseUrl, accessToken, `/reviews/${reviewTaskId}/approvals`, {
    method: "POST",
    body: payload,
  });
}

export async function revokeScholarApproval(
  apiBaseUrl: string,
  accessToken: string,
  approvalId: string,
  payload: {
    readonly reason: string;
  },
): Promise<ApprovalActionResult> {
  return request<ApprovalActionResult>(
    apiBaseUrl,
    accessToken,
    `/review-approvals/${approvalId}/revoke`,
    {
      method: "POST",
      body: payload,
    },
  );
}

export async function fetchSourceDetail(
  apiBaseUrl: string,
  accessToken: string,
  sourceId: string,
): Promise<SourceDetail> {
  return request<SourceDetail>(apiBaseUrl, accessToken, `/sources/${sourceId}`);
}

export async function fetchLicensePolicyDecision(
  apiBaseUrl: string,
  accessToken: string,
  licenseId: string,
  workflow = "retrieval",
): Promise<LicensePolicyDecision> {
  const params = new URLSearchParams({ workflow });
  return request<LicensePolicyDecision>(
    apiBaseUrl,
    accessToken,
    `/admin/licenses/${licenseId}/policy-decision`,
    { params },
  );
}

export async function fetchLicenseDetail(
  apiBaseUrl: string,
  accessToken: string,
  licenseId: string,
): Promise<LicenseDetail> {
  return request<LicenseDetail>(apiBaseUrl, accessToken, `/admin/licenses/${licenseId}`);
}

export async function fetchApprovalHistory(
  apiBaseUrl: string,
  accessToken: string,
  documentVersionId: string,
): Promise<ApprovalListResult> {
  return request<ApprovalListResult>(
    apiBaseUrl,
    accessToken,
    `/documents/${documentVersionId}/approvals`,
  );
}
