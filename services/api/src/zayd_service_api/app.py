import asyncio
import base64
import hashlib
import re
import socket
import threading
from collections.abc import Awaitable, Callable
from datetime import UTC, date, datetime
from typing import Annotated, Any, cast
from urllib.parse import urlparse
from uuid import UUID

from fastapi import Depends, FastAPI, Header, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from zayd_common.answer_invalidation import (
    AffectedAnswerPage,
    AnswerInvalidationError,
    AnswerInvalidationResult,
    AnswerInvalidationService,
)
from zayd_common.audit import AuditLogQuery, AuditOutcome, AuditService, serialize_audit_log
from zayd_common.auth import AccessTokenClaims, AuthError, AuthResult, AuthService
from zayd_common.conversations import (
    ConversationDetailPublic,
    ConversationHistoryError,
    ConversationHistoryService,
    ConversationListResult,
    ConversationSummaryPublic,
)
from zayd_common.database import get_sessionmaker
from zayd_common.document_lifecycle import (
    AffectedAnswerPublic,
    DocumentLifecycleError,
    DocumentLifecycleResult,
    DocumentLifecycleService,
)
from zayd_common.document_publishing import (
    DocumentPublishingError,
    DocumentPublishingService,
    DocumentPublishResult,
)
from zayd_common.document_review import (
    DocumentReviewError,
    DocumentReviewService,
    ReviewCommentPublic,
    ReviewDecisionPublic,
    ReviewDraft,
    ReviewEditResult,
    ReviewRevisionPublic,
)
from zayd_common.documents import (
    DocumentMalwareScanResult,
    DocumentProcessingError,
    DocumentUploadDuplicate,
    DocumentUploadError,
    DocumentUploadRequest,
    DocumentUploadResult,
    DocumentUploadService,
)
from zayd_common.feedback import FeedbackError, FeedbackPublic, FeedbackService, FeedbackSubmit
from zayd_common.feedback_review import (
    FeedbackAssignRequest,
    FeedbackClassifyRequest,
    FeedbackQueueItem,
    FeedbackQueueQuery,
    FeedbackQueueResult,
    FeedbackResolveRequest,
    FeedbackReviewDetail,
    FeedbackReviewError,
    FeedbackReviewService,
)
from zayd_common.guest import GuestError, GuestService
from zayd_common.health import HealthStatus
from zayd_common.incident_management import (
    IncidentCreate,
    IncidentManagementError,
    IncidentManagementService,
    IncidentPublic,
)
from zayd_common.licenses import (
    LicenseCreate,
    LicenseError,
    LicensePolicyDecisionPublic,
    LicensePublic,
    LicenseService,
    PermissionDocumentAccess,
    PublicationAuthorization,
)
from zayd_common.logging import (
    bind_request_context,
    configure_logging,
    get_logger,
    new_trace_context,
    normalize_request_id,
)
from zayd_common.malware_scanning import MalwareScannerUnavailable
from zayd_common.mfa import (
    MfaEnrollment,
    MfaError,
    MfaResetChannel,
    MfaService,
)
from zayd_common.parsing import (
    ParserError,
    ParserRegistry,
)
from zayd_common.prompt_registry import (
    DEFAULT_ANSWER_PROMPT_NAME,
    PromptComparison,
    PromptCreate,
    PromptDefinition,
    PromptRegistryError,
    PromptRegistryService,
    PromptStatusChange,
    PromptTestCase,
    bootstrap_registry_defaults,
)
from zayd_common.provider_admin import (
    ModelConfigurationCreate,
    ModelConfigurationPublic,
    ModelConfigurationUpdate,
    ProviderAdminError,
    ProviderAdminService,
    ProviderConnectionTestResult,
    ProviderCreate,
    ProviderDisableImpact,
    ProviderPublic,
    ProviderUpdate,
)
from zayd_common.rbac import Permission, RbacError, RbacService, UserPrincipal
from zayd_common.review_queue import (
    ReviewerDashboardResult,
    ReviewerDashboardSummary,
    ReviewerFeedbackWorkItem,
    ReviewQueueError,
    ReviewQueueQuery,
    ReviewQueueService,
    ReviewTaskDetail,
    ReviewTaskSummary,
)
from zayd_common.saved_answers import (
    SavedAnswerError,
    SavedAnswerListResult,
    SavedAnswerPublic,
    SavedAnswerService,
)
from zayd_common.scholar_approval import (
    ApprovalListResult,
    ApprovalPublic,
    ApprovalRequirement,
    ScholarApprovalError,
    ScholarApprovalService,
)
from zayd_common.security import SecurityError, detect_prompt_injection, sanitize_xss
from zayd_common.settings import ServiceSettings
from zayd_common.sources import (
    SourceError,
    SourcePublic,
    SourceSearchQuery,
    SourceService,
)
from zayd_common.storage import S3ObjectStorage, S3StorageSettings, SignedUrl, StorageError
from zayd_common.telemetry import telemetry_registry
from zayd_common.user_admin import AdminUserPublic, UserAdminError, UserAdminService
from zayd_common.user_preferences import (
    UserPreferencesError,
    UserPreferencesPublic,
    UserPreferencesService,
    UserPreferencesUpdate,
)
from zayd_service_evaluation import (
    BenchmarkComparisonError,
    BenchmarkComparisonService,
    EvaluationCaseContract,
    IncidentRegressionError,
    IncidentRegressionResult,
    IncidentRegressionService,
    RunComparisonReport,
    RunInfo,
)
from zayd_service_orchestrator import (
    ChatRequest,
    ChatStreamingError,
    ChatStreamingService,
    CitationDetailPublic,
    CitationRegistryError,
    CitationRegistryService,
    LLMProvider,
    MockLLMProvider,
    StaticAnswerRetriever,
    build_managed_answer_orchestrator,
    citation_id_from_token,
    sse_encode,
)
from zayd_service_orchestrator import (
    PromptRegistryService as OrchestratorPromptRegistryService,
)

logger = get_logger("zayd.api")


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=12, max_length=256)
    display_name: str = Field(min_length=1, max_length=200)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=1, max_length=256)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20)


class PasswordResetRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class PasswordResetConfirmRequest(BaseModel):
    reset_token: str = Field(min_length=20)
    new_password: str = Field(min_length=12, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str


class AuthResponse(BaseModel):
    user: UserResponse
    tokens: TokenResponse


class PasswordResetResponse(BaseModel):
    status: str
    reset_token: str | None = None


class GuestSessionResponse(BaseModel):
    guest_token: str
    expires_at: str
    message_quota: int
    messages_used: int


class GuestConversionRequest(BaseModel):
    guest_token: str = Field(min_length=20)
    email: str = Field(min_length=3, max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=12, max_length=256)
    display_name: str = Field(min_length=1, max_length=200)


class PrincipalResponse(BaseModel):
    id: str
    email: str
    roles: list[str]
    permissions: list[str]


class UserPreferencesResponse(BaseModel):
    madhhab: str
    default_madhhab: str
    answer_length: str
    show_arabic: bool
    history_mode: str
    preferred_language: str
    synced: bool = True


class UserPreferencesPatchRequest(BaseModel):
    madhhab: str | None = Field(default=None, pattern=r"^(shafii|hanafi|maliki|hanbali)$")
    answer_length: str | None = Field(default=None, pattern=r"^(short|normal|detailed)$")
    show_arabic: bool | None = None
    history_mode: str | None = Field(default=None, pattern=r"^(enabled|disabled)$")


class ConversationSummaryResponse(BaseModel):
    id: UUID
    title: str | None
    language: str
    madhhab: str
    message_count: int
    preview: str | None
    created_at: str
    updated_at: str


class ConversationListResponse(BaseModel):
    conversations: list[ConversationSummaryResponse]
    total_count: int
    limit: int
    offset: int
    next_offset: int | None = None


class ConversationAnswerResponse(BaseModel):
    id: str
    summary: str
    answer_th: str
    madhhab: str
    risk_level: str
    confidence: str
    evidence_sufficient: bool
    citations: list[dict[str, str]]
    limitations: list[str]
    warning: str | None = None
    status: str | None = None


class ConversationMessageResponse(BaseModel):
    id: UUID
    sender_type: str
    body: str
    created_at: str
    answer: ConversationAnswerResponse | None = None


class ConversationDetailResponse(BaseModel):
    conversation: ConversationSummaryResponse
    messages: list[ConversationMessageResponse]


class ConversationDeleteAllResponse(BaseModel):
    deleted_count: int


class SavedAnswerCitationResponse(BaseModel):
    citation_id: str
    display: str
    source_type: str
    verification_status: str


class SavedAnswerResponse(BaseModel):
    id: UUID
    answer_id: UUID
    saved_at: str
    summary: str
    answer_th: str
    madhhab: str
    warnings: list[str]
    citations: list[SavedAnswerCitationResponse]


class SavedAnswerListResponse(BaseModel):
    saved_answers: list[SavedAnswerResponse]
    total_count: int


class SavedAnswerCreateRequest(BaseModel):
    answer_id: UUID


class FeedbackSubmitRequest(BaseModel):
    answer_id: UUID
    category: str = Field(min_length=1, max_length=64)
    notes: str | None = Field(default=None, max_length=2000)
    citation_id: UUID | None = None


class FeedbackResponse(BaseModel):
    id: UUID
    category: str
    status: str
    answer_id: UUID | None
    citation_id: UUID | None
    created_at: str
    receipt_message: str


class FeedbackReviewItemResponse(BaseModel):
    id: UUID
    category: str
    status: str
    priority: str
    severity: str
    answer_id: UUID | None
    citation_id: UUID | None
    reviewer_id: UUID | None
    root_cause: str | None
    created_at: str
    updated_at: str


class FeedbackReviewDetailResponse(BaseModel):
    id: UUID
    category: str
    status: str
    priority: str
    severity: str
    answer_id: UUID | None
    citation_id: UUID | None
    reviewer_id: UUID | None
    reviewer_notes: str
    root_cause: str | None
    resolution: str | None
    resolved_at: str | None
    trace_context: "FeedbackTraceContextResponse | None"
    created_at: str
    updated_at: str


class FeedbackTraceContextResponse(BaseModel):
    retrieval_run_id: UUID
    model_configuration_id: UUID
    prompt_version_id: UUID
    policy_version_id: UUID


class FeedbackQueueListResponse(BaseModel):
    items: list[FeedbackReviewItemResponse]
    total_count: int
    limit: int
    offset: int
    next_offset: int | None


class EvaluationRunInfoResponse(BaseModel):
    run_id: UUID
    dataset_name: str
    dataset_version: str
    provider_name: str
    model_name: str
    retriever_version: str
    embedding_version: str | None
    reranker_version: str | None
    git_commit: str
    random_seed: int
    started_at: str
    finished_at: str | None
    metrics: dict[str, Any]


class EvaluationRunListResponse(BaseModel):
    runs: list[EvaluationRunInfoResponse]


class CaseComparisonResponse(BaseModel):
    case_key: str
    case_type: str
    risk_level: str
    visibility: str
    base_passed: bool
    target_passed: bool
    regression: bool
    improvement: bool
    base_scores: dict[str, float]
    target_scores: dict[str, float]
    topic: str
    language: str
    madhhab: str


class RunComparisonReportResponse(BaseModel):
    base_run: EvaluationRunInfoResponse
    target_run: EvaluationRunInfoResponse
    regression_count: int
    improvement_count: int
    overall_base_pass_rate: float
    overall_target_pass_rate: float
    comparisons: list[CaseComparisonResponse]
    version: str


class FeedbackAssignRequestPayload(BaseModel):
    reviewer_id: UUID | None = None


class FeedbackClassifyRequestPayload(BaseModel):
    root_cause: str | None = Field(default=None, min_length=1, max_length=64)
    priority: str | None = Field(default=None, min_length=1, max_length=16)
    severity: str | None = Field(default=None, min_length=1, max_length=16)
    reviewer_notes: str | None = Field(default=None, max_length=4000)


class FeedbackResolveRequestPayload(BaseModel):
    resolution: str = Field(min_length=1, max_length=4000)
    dismissed: bool = False


class IncidentCreateRequest(BaseModel):
    idempotency_key: str = Field(min_length=1, max_length=200)
    severity: str = Field(min_length=2, max_length=2)
    summary: str = Field(min_length=1, max_length=1000)
    feedback_id: UUID | None = None
    affected_answer_id: UUID | None = None
    affected_document_id: UUID | None = None
    affected_citation_id: UUID | None = None
    owner_id: UUID | None = None


class IncidentTransitionRequest(BaseModel):
    target_status: str = Field(min_length=1, max_length=20)
    reason: str = Field(min_length=1, max_length=1000)
    base_row_version: int = Field(ge=1)


class IncidentAssignRequest(BaseModel):
    owner_id: UUID


class IncidentResponse(BaseModel):
    id: UUID
    severity: str
    status: str
    summary: str
    owner_id: UUID | None
    feedback_id: UUID | None
    affected_answer_id: UUID | None
    affected_document_id: UUID | None
    affected_citation_id: UUID | None
    alert_status: str
    row_version: int
    created_at: str
    updated_at: str
    idempotent: bool = False


class IncidentTimelineResponse(BaseModel):
    events: list[dict[str, object]]


class IncidentRegressionCreateRequest(BaseModel):
    dataset_id: UUID
    case: EvaluationCaseContract


class IncidentRegressionCreateResponse(BaseModel):
    evaluation_case_id: UUID
    incident_id: UUID
    redaction_count: int
    schema_version: str
    policy_version: str


class AnswerInvalidateRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)
    idempotency_key: str = Field(min_length=1, max_length=200)
    incident_id: UUID | None = None
    citation_id: UUID | None = None
    source_id: UUID | None = None


class AnswerInvalidationResponse(BaseModel):
    answer_id: UUID
    invalidated_at: str
    warning: str
    notification_status: str
    idempotent: bool


class AffectedAnswerPageResponse(BaseModel):
    answer_ids: list[UUID]
    total_count: int
    limit: int
    offset: int
    next_offset: int | None


class RoleAssignmentRequest(BaseModel):
    user_id: UUID
    role_name: str = Field(min_length=1, max_length=64)


class RoleAssignmentResponse(BaseModel):
    status: str
    changed: bool


class ProviderDisableImpactReadinessResponse(BaseModel):
    model_type: str
    active_model_count: int
    alternative_model_count: int
    fallback_ready: bool


class ProviderDisableImpactResponse(BaseModel):
    provider_id: str
    provider_name: str
    active_model_count: int
    impacted_model_types: list[str]
    fallback_readiness: list[ProviderDisableImpactReadinessResponse]
    safe_to_disable: bool


class ProviderCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    provider_type: str = Field(min_length=1, max_length=40)
    status: str = Field(default="disabled", min_length=1, max_length=40)
    base_url: str | None = Field(default=None, max_length=1000)
    secret_ref: str | None = Field(default=None, max_length=1000)
    terms_url: str | None = Field(default=None, max_length=1000)
    data_policy_json: dict[str, Any] = Field(default_factory=dict)


class ProviderUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    status: str | None = Field(default=None, min_length=1, max_length=40)
    base_url: str | None = Field(default=None, max_length=1000)
    secret_ref: str | None = Field(default=None, max_length=1000)
    terms_url: str | None = Field(default=None, max_length=1000)
    data_policy_json: dict[str, Any] | None = None


class ProviderResponse(BaseModel):
    id: str
    name: str
    provider_type: str
    status: str
    base_url: str | None
    terms_url: str | None
    data_policy_json: dict[str, Any]
    secret_configured: bool
    secret_mask: str
    created_by: str
    updated_by: str | None
    created_at: str
    updated_at: str
    row_version: int
    model_count: int
    active_model_count: int
    disable_impact: ProviderDisableImpactResponse


class ProviderListResponse(BaseModel):
    providers: list[ProviderResponse]


class ProviderConnectionTestResponse(BaseModel):
    provider_id: str
    provider_name: str
    status: str
    checked_at: str
    latency_ms: int
    message: str


class ModelConfigurationCreateRequest(BaseModel):
    provider_id: UUID
    model_name: str = Field(min_length=1, max_length=200)
    model_type: str = Field(min_length=1, max_length=40)
    configuration: dict[str, Any] = Field(default_factory=dict)
    allow_listed: bool = True
    fallback_model_id: UUID | None = None
    cost_limit_daily_usd: float | None = Field(default=None, ge=0)
    is_default: bool = False
    status: str = Field(default="disabled", min_length=1, max_length=40)


class ModelConfigurationUpdateRequest(BaseModel):
    model_name: str | None = Field(default=None, min_length=1, max_length=200)
    configuration: dict[str, Any] | None = None
    allow_listed: bool | None = None
    fallback_model_id: UUID | None = None
    cost_limit_daily_usd: float | None = Field(default=None, ge=0)
    is_default: bool | None = None
    status: str | None = Field(default=None, min_length=1, max_length=40)


class ModelConfigurationResponse(BaseModel):
    id: str
    provider_id: str
    provider_name: str
    provider_status: str
    model_name: str
    model_type: str
    configuration: dict[str, Any]
    allow_listed: bool
    fallback_model_id: str | None
    fallback_model_name: str | None
    cost_limit_daily_usd: float | None
    is_default: bool
    status: str
    created_by: str
    created_at: str
    updated_at: str
    row_version: int


class ModelConfigurationListResponse(BaseModel):
    models: list[ModelConfigurationResponse]


class AdminUserResponse(BaseModel):
    id: str
    email: str
    display_name: str
    status: str
    roles: list[str]
    active_session_count: int
    last_login_at: str | None
    created_at: str
    updated_at: str
    row_version: int
    last_admin_guarded: bool


class AdminUserListResponse(BaseModel):
    users: list[AdminUserResponse]


class AdminUserStatusRequest(BaseModel):
    status: str = Field(min_length=1, max_length=40)


class AdminUserStatusResponse(BaseModel):
    user: AdminUserResponse


class AdminUserSessionRevokeResponse(BaseModel):
    revoked_sessions: int


class PromptTestCaseRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    input_payload: dict[str, Any]
    expected_assertions: list[str] = Field(default_factory=list)


class PromptCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    version: str = Field(min_length=1, max_length=100)
    prompt_body: str = Field(min_length=1)
    purpose: str = Field(min_length=1, max_length=500)
    owner: str = Field(min_length=1, max_length=200)
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    changelog: list[str] = Field(default_factory=list)
    test_cases: list[PromptTestCaseRequest] = Field(default_factory=list)
    status: str = Field(default="draft", min_length=1, max_length=32)


class PromptResponse(BaseModel):
    id: str
    name: str
    version: str
    prompt_body: str
    status: str
    owner: str
    purpose: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    changelog: list[str]
    test_cases: list[PromptTestCaseRequest]
    prompt_hash: str
    created_by: str
    approved_by: str | None
    created_at: str
    updated_at: str
    active: bool
    registry_version: str


class PromptListResponse(BaseModel):
    prompts: list[PromptResponse]


class PromptStatusChangeResponse(BaseModel):
    prompt: PromptResponse
    active_prompt: PromptResponse | None
    changed: bool
    trace: dict[str, Any]


class PromptComparisonResponse(BaseModel):
    prompt_name: str
    from_version: str
    to_version: str
    from_status: str
    to_status: str
    from_hash: str
    to_hash: str
    body_changed: bool
    purpose_changed: bool
    owner_changed: bool
    input_schema_changed: bool
    output_schema_changed: bool
    changelog_added: list[str]
    test_case_names_added: list[str]
    trace: dict[str, Any]


class PromptRollbackRequest(BaseModel):
    prompt_name: str = Field(min_length=1, max_length=200)
    target_version: str = Field(min_length=1, max_length=100)


class ChatStreamRequest(BaseModel):
    question: str = Field(min_length=1)
    conversation_id: UUID | None = None
    requested_madhhab: str | None = Field(default=None, max_length=50)
    answer_length: str = Field(default="normal", pattern=r"^(short|normal|detailed)$")
    no_history: bool = False
    guest_token: str | None = Field(default=None, min_length=20, max_length=256)


class CitationRecordResponse(BaseModel):
    id: str
    token: str
    canonical_reference: str
    document_version_id: str
    chunk_id: str
    citation_type: str
    display_title: str
    arabic_text: str | None
    thai_translation: str | None
    hadith_grade: str | None
    volume: str | None
    page: str | None
    verified: bool
    active: bool
    invalidated_at: str | None
    registry_version: str


class CitationSourceSummaryResponse(BaseModel):
    id: str
    name: str
    source_type: str
    language: str
    is_active: bool
    reliability_level: int


class CitationDocumentSummaryResponse(BaseModel):
    id: str
    title: str
    author: str | None
    translator: str | None
    publisher: str | None
    edition: str | None
    language: str
    document_type: str
    version_status: str


class CitationDetailResponse(BaseModel):
    citation: CitationRecordResponse
    source_text: str | None
    source: CitationSourceSummaryResponse | None
    document: CitationDocumentSummaryResponse | None
    warnings: list[str]
    registry_version: str


class DocumentApprovalAuthorizationRequest(BaseModel):
    document_created_by: UUID


class AuthorizationCheckResponse(BaseModel):
    status: str


class AuditLogResponse(BaseModel):
    id: str
    actor_user_id: str | None
    action: str
    resource_type: str
    resource_id: str | None
    outcome: str
    reason: str | None
    request_id: str | None
    trace_id: str | None
    before_summary: dict[str, object] | None
    after_summary: dict[str, object] | None
    source_context: dict[str, object]
    created_at: str
    hash_algorithm: str
    previous_hash: str | None
    content_hash: str


class AuditLogListResponse(BaseModel):
    records: list[AuditLogResponse]


class MfaEnrollmentResponse(BaseModel):
    provisioning_uri: str
    secret: str
    recovery_codes: list[str]


class MfaConfirmRequest(BaseModel):
    code: str = Field(min_length=6, max_length=12)


class MfaChallengeStartResponse(BaseModel):
    challenge_id: UUID
    expires_at: str


class MfaChallengeVerifyRequest(BaseModel):
    challenge_id: UUID
    code: str = Field(min_length=6, max_length=12)


class MfaRecoveryCodeRequest(BaseModel):
    challenge_id: UUID
    recovery_code: str = Field(min_length=8, max_length=64)


class MfaResetRequest(BaseModel):
    channel: MfaResetChannel
    proof: str = Field(min_length=8, max_length=128)


class MfaRecoveryRotateResponse(BaseModel):
    recovery_codes: list[str]


class MfaStatusResponse(BaseModel):
    enrolled: bool
    privileged_role_required: bool


class SourceCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    source_type: str = Field(min_length=1, max_length=100)
    owner: str | None = Field(default=None, max_length=500)
    website: str | None = Field(default=None, max_length=1000)
    language: str = Field(min_length=2, max_length=10)
    country: str | None = Field(default=None, max_length=100)
    reliability_level: int = Field(ge=1, le=5)
    is_active: bool = True


class SourceUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=500)
    source_type: str | None = Field(default=None, min_length=1, max_length=100)
    owner: str | None = None
    website: str | None = None
    language: str | None = Field(default=None, min_length=2, max_length=10)
    country: str | None = None
    reliability_level: int | None = Field(default=None, ge=1, le=5)


class SourceResponse(BaseModel):
    id: str
    name: str
    source_type: str
    owner: str | None
    website: str | None
    language: str
    country: str | None
    reliability_level: int
    is_active: bool
    created_by: str
    updated_by: str | None
    created_at: str
    updated_at: str


class SourceListResponse(BaseModel):
    sources: list[SourceResponse]


class PublicSourceDetailResponse(BaseModel):
    source: SourceResponse
    warnings: list[str]


class LicenseCreateRequest(BaseModel):
    license_name: str = Field(min_length=1, max_length=500)
    license_version: str | None = Field(default=None, max_length=100)
    status: str = Field(min_length=1, max_length=100)
    storage_permission: str = Field(min_length=1, max_length=100)
    embedding_permission: str = Field(min_length=1, max_length=100)
    commercial_use: str = Field(min_length=1, max_length=100)
    redistribution: str = Field(min_length=1, max_length=100)
    attribution_required: bool = True
    attribution_template: str | None = None
    permission_document_key: str | None = Field(default=None, max_length=1000)
    valid_from: date | None = None
    valid_until: date | None = None
    notes: str | None = None


class LicenseResponse(BaseModel):
    id: str
    source_id: str
    license_name: str
    license_version: str | None
    status: str
    storage_permission: str
    embedding_permission: str
    commercial_use: str
    redistribution: str
    attribution_required: bool
    attribution_template: str | None
    permission_document_key: str | None
    valid_from: str | None
    valid_until: str | None
    notes: str | None
    created_by: str
    updated_by: str | None
    created_at: str
    updated_at: str
    row_version: int


class LicenseListResponse(BaseModel):
    licenses: list[LicenseResponse]


class PermissionDocumentResponse(BaseModel):
    license_id: str
    permission_document_key: str
    access: str
    audited: bool


class PublicationAuthorizationResponse(BaseModel):
    license_id: str
    authorized: bool
    policy_version: str
    reason: str


class LicensePolicyActionResponse(BaseModel):
    action: str
    allowed: bool
    reason_codes: list[str]
    source_license_version: str | None
    max_cache_ttl_seconds: int | None = None
    attribution_required: bool | None = None
    attribution_template: str | None = None


class LicensePolicyDecisionResponse(BaseModel):
    license_id: str
    source_id: str
    workflow: str
    policy_version: str
    evaluated_on: str
    source_license_version: str | None
    workflow_allowed: bool
    llm_override_allowed: bool
    reason_codes: list[str]
    actions: list[LicensePolicyActionResponse]


class DocumentUploadRequestModel(BaseModel):
    source_id: UUID
    source_license_id: UUID
    canonical_id: str = Field(min_length=1, max_length=255)
    document_type: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=500)
    language: str = Field(min_length=1, max_length=32)
    filename: str = Field(min_length=1, max_length=500)
    content_type: str = Field(min_length=1, max_length=255)
    file_base64: str = Field(min_length=1)
    author: str | None = Field(default=None, max_length=255)
    translator: str | None = Field(default=None, max_length=255)
    publisher: str | None = Field(default=None, max_length=255)
    edition: str | None = Field(default=None, max_length=255)
    madhhab: str = Field(default="unknown", min_length=1, max_length=100)


class DocumentUploadDuplicateResponse(BaseModel):
    document_id: str
    document_version_id: str
    canonical_id: str
    title: str
    content_hash: str


class SignedUrlResponse(BaseModel):
    method: str
    url: str
    expires_at: int
    expires_in_seconds: int


class DocumentUploadResponse(BaseModel):
    document_id: str
    document_version_id: str
    content_hash: str
    filename: str
    content_type: str
    byte_size: int
    duplicate: DocumentUploadDuplicateResponse | None
    upload_status: str
    original_file_key: str
    download_url: SignedUrlResponse
    policy_version: str


class DocumentMalwareScanResponse(BaseModel):
    document_id: str
    document_version_id: str
    status: str
    engine: str
    engine_version: str
    signature_name: str | None
    scanned_bytes: int
    policy_version: str
    incident_id: str | None


class ParserEligibilityResponse(BaseModel):
    document_version_id: str
    parser_eligible: bool


class ParseWarningResponse(BaseModel):
    category: str
    message: str
    location: str | None


class ParsedSectionResponse(BaseModel):
    content: str
    heading: str | None
    page: int | None
    section_index: int
    content_type: str
    metadata: dict[str, object] | None


class DocumentParseResponse(BaseModel):
    document_version_id: str
    parser_name: str
    parser_version: str
    framework_version: str
    content_type: str
    sections: list[ParsedSectionResponse]
    warnings: list[ParseWarningResponse]
    page_count: int | None
    metadata: dict[str, object]


# ---------------------------------------------------------------------------
# Review Queue response models
# ---------------------------------------------------------------------------


class ReviewTaskSummaryResponse(BaseModel):
    id: str
    document_version_id: str
    document_id: str
    review_level: str
    status: str
    priority: str
    category: str | None = None
    language: str | None = None
    madhhab: str | None = None
    assigned_to: str | None = None
    due_at: str | None = None
    created_at: str
    updated_at: str
    document_title: str | None = None
    document_type: str | None = None


class ReviewTaskDetailResponse(ReviewTaskSummaryResponse):
    created_by: str
    original_file_key: str | None = None
    extracted_text_preview: str | None = None
    filename: str | None = None
    content_type: str | None = None


class ReviewQueueListResponse(BaseModel):
    tasks: list[ReviewTaskSummaryResponse]
    total_count: int
    limit: int
    offset: int
    next_offset: int | None = None


class ReviewerDashboardSummaryResponse(BaseModel):
    total_visible_count: int
    pending_count: int
    assigned_count: int
    overdue_count: int
    changes_requested_count: int
    feedback_open_count: int


class ReviewerFeedbackWorkItemResponse(BaseModel):
    id: str
    category: str
    status: str
    answer_id: str | None = None
    citation_id: str | None = None
    created_at: str


class ReviewerDashboardResponse(BaseModel):
    summary: ReviewerDashboardSummaryResponse
    queue: ReviewQueueListResponse
    feedback_items: list[ReviewerFeedbackWorkItemResponse]


class MetricsSummaryResponse(BaseModel):
    registered_user_count: int
    queue_depth: int
    feedback_open_count: int
    incident_open_count: int
    provider_count: int
    enabled_provider_count: int
    model_count: int
    default_model_count: int
    provider_cost_limit_daily_usd: float
    provider_health_ok_count: int
    spans_recorded: int
    api_latency_ms_avg: float = 0.0
    error_count: int = 0
    external_fallback_count: int = 0
    local_rag_hit_count: int = 0
    citation_failure_count: int = 0
    queue_age_seconds_avg: float = 0.0


class MetricsSnapshotResponse(BaseModel):
    generated_at: str
    window_minutes: int
    summary: MetricsSummaryResponse


class DependencyHealthResponse(BaseModel):
    status: str


class SystemHealthResponse(BaseModel):
    service: str
    status: str
    dependencies: dict[str, DependencyHealthResponse]


class ReviewTaskAssignRequest(BaseModel):
    assignee_user_id: UUID


class ReviewTaskActionResponse(BaseModel):
    status: str
    task: ReviewTaskSummaryResponse


class ReviewCommentResponse(BaseModel):
    id: str
    review_task_id: str
    author_id: str
    body: str
    anchor: dict[str, object]
    created_at: str


class ReviewDraftResponse(BaseModel):
    review_task_id: str
    document_version_id: str
    document_id: str
    source_id: str | None
    source_license_id: str | None
    canonical_id: str | None
    document_title: str | None
    document_type: str | None
    language: str | None
    madhhab: str | None
    task_status: str
    task_row_version: int
    document_review_status: str
    original_file_key: str | None
    editable_text: str | None
    editable_metadata: dict[str, object]
    latest_revision_number: int
    revisions: list["ReviewRevisionResponse"]
    comments: list[ReviewCommentResponse]


class ReviewEditRequest(BaseModel):
    base_task_row_version: int = Field(ge=1)
    text: str | None = None
    metadata_updates: dict[str, object] | None = None


class ReviewRevisionResponse(BaseModel):
    id: str
    review_task_id: str
    document_version_id: str
    actor_user_id: str
    revision_number: int
    base_task_row_version: int
    text_changed: bool
    metadata_changed_fields: list[str]
    diff_text: str
    created_at: str


class ReviewEditResponse(BaseModel):
    status: str
    task_row_version: int
    revision: ReviewRevisionResponse
    editable_text: str | None
    editable_metadata: dict[str, object]


class ReviewCommentRequest(BaseModel):
    body: str = Field(min_length=1, max_length=10000)
    anchor: dict[str, object] | None = None


class ReviewDecisionRequest(BaseModel):
    decision: str = Field(pattern="^(approve|request_changes|reject)$")
    reason: str = Field(min_length=1, max_length=10000)
    base_task_row_version: int = Field(ge=1)


class ReviewDecisionResponse(BaseModel):
    id: str
    review_task_id: str
    document_version_id: str
    actor_user_id: str
    decision: str
    reason: str
    resulting_task_status: str
    resulting_document_status: str
    created_at: str


class ReviewDecisionActionResponse(BaseModel):
    status: str
    task_row_version: int
    decision: ReviewDecisionResponse


class ScholarApprovalRequest(BaseModel):
    content_risk: str = Field(pattern="^(routine|sensitive|restricted)$")
    approval_level: str = Field(pattern="^(initial|scholar|board)$")
    reason: str = Field(min_length=1, max_length=10000)
    valid_until: datetime | None = None


class ScholarApprovalRevokeRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=10000)


class ApprovalResponse(BaseModel):
    id: str
    document_version_id: str
    review_task_id: str
    approver_id: str
    approval_level: str
    content_risk: str
    status: str
    reason: str
    valid_until: str | None
    revoked_at: str | None
    revoked_by: str | None
    revoke_reason: str | None
    created_at: str


class ApprovalRequirementResponse(BaseModel):
    document_version_id: str
    content_risk: str
    required_levels: list[str]
    satisfied_levels: list[str]
    missing_levels: list[str]
    ready_for_publish: bool


class ApprovalListResponse(BaseModel):
    document_version_id: str
    approvals: list[ApprovalResponse]


class ScholarApprovalActionResponse(BaseModel):
    status: str
    approval: ApprovalResponse


class DocumentPublishRequest(BaseModel):
    content_risk: str = Field(pattern="^(routine|sensitive|restricted)$")
    reason: str = Field(min_length=1, max_length=10000)


class PublishedChunkResponse(BaseModel):
    id: str
    chunk_index: int
    content_hash: str
    reference: str | None
    is_published: bool


class DocumentPublishResponse(BaseModel):
    document_id: str
    document_version_id: str
    published_version_id: str
    document_status: str
    version_status: str
    chunk_count: int
    chunks: list[PublishedChunkResponse]
    policy_version: str
    license_policy_version: str
    scholar_approval_policy_version: str
    chunking_strategy_version: str
    embedding_pipeline_version: str
    citation_pipeline_version: str
    published_at: str
    idempotent: bool


class DocumentLifecycleRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=10000)
    base_row_version: int | None = Field(default=None, ge=1)


class DocumentRollbackRequest(DocumentLifecycleRequest):
    target_document_version_id: UUID


class AffectedAnswerResponse(BaseModel):
    id: str
    invalidated_at: str
    warning: str


class DocumentLifecycleResponse(BaseModel):
    document_id: str
    previous_published_version_id: str | None
    current_published_version_id: str | None
    document_status: str
    affected_chunk_count: int
    affected_citation_count: int
    affected_answer_count: int
    affected_answers: list[AffectedAnswerResponse]
    policy_version: str
    changed_at: str


def _auth_response(result: AuthResult) -> AuthResponse:
    user = result.user
    tokens = result.tokens
    return AuthResponse(
        user=UserResponse(id=str(user.id), email=user.email, display_name=user.display_name),
        tokens=TokenResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            token_type=tokens.token_type,
            expires_in=tokens.expires_in,
        ),
    )


def _principal_response(principal: UserPrincipal) -> PrincipalResponse:
    return PrincipalResponse(
        id=str(principal.id),
        email=principal.email,
        roles=sorted(principal.roles),
        permissions=sorted(principal.permissions),
    )


def _provider_disable_impact_response(
    impact: ProviderDisableImpact,
) -> ProviderDisableImpactResponse:
    return ProviderDisableImpactResponse(
        provider_id=str(impact.provider_id),
        provider_name=impact.provider_name,
        active_model_count=impact.active_model_count,
        impacted_model_types=list(impact.impacted_model_types),
        fallback_readiness=[
            ProviderDisableImpactReadinessResponse(
                model_type=item.model_type,
                active_model_count=item.active_model_count,
                alternative_model_count=item.alternative_model_count,
                fallback_ready=item.fallback_ready,
            )
            for item in impact.fallback_readiness
        ],
        safe_to_disable=impact.safe_to_disable,
    )


def _provider_response(provider: ProviderPublic) -> ProviderResponse:
    return ProviderResponse(
        id=str(provider.id),
        name=provider.name,
        provider_type=provider.provider_type,
        status=provider.status,
        base_url=provider.base_url,
        terms_url=provider.terms_url,
        data_policy_json=provider.data_policy_json,
        secret_configured=provider.secret_configured,
        secret_mask=provider.secret_mask,
        created_by=str(provider.created_by),
        updated_by=str(provider.updated_by) if provider.updated_by else None,
        created_at=provider.created_at.isoformat(),
        updated_at=provider.updated_at.isoformat(),
        row_version=provider.row_version,
        model_count=provider.model_count,
        active_model_count=provider.active_model_count,
        disable_impact=_provider_disable_impact_response(provider.disable_impact),
    )


def _provider_connection_test_response(
    result: ProviderConnectionTestResult,
) -> ProviderConnectionTestResponse:
    return ProviderConnectionTestResponse(
        provider_id=str(result.provider_id),
        provider_name=result.provider_name,
        status=result.status,
        checked_at=result.checked_at.isoformat(),
        latency_ms=result.latency_ms,
        message=result.message,
    )


def _model_configuration_response(
    model: ModelConfigurationPublic,
) -> ModelConfigurationResponse:
    return ModelConfigurationResponse(
        id=str(model.id),
        provider_id=str(model.provider_id),
        provider_name=model.provider_name,
        provider_status=model.provider_status,
        model_name=model.model_name,
        model_type=model.model_type,
        configuration=model.configuration,
        allow_listed=model.allow_listed,
        fallback_model_id=str(model.fallback_model_id) if model.fallback_model_id else None,
        fallback_model_name=model.fallback_model_name,
        cost_limit_daily_usd=model.cost_limit_daily_usd,
        is_default=model.is_default,
        status=model.status,
        created_by=str(model.created_by),
        created_at=model.created_at.isoformat(),
        updated_at=model.updated_at.isoformat(),
        row_version=model.row_version,
    )


def _admin_user_response(user: AdminUserPublic) -> AdminUserResponse:
    return AdminUserResponse(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        status=user.status,
        roles=list(user.roles),
        active_session_count=user.active_session_count,
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat(),
        row_version=user.row_version,
        last_admin_guarded=user.last_admin_guarded,
    )


def _enrollment_response(enrollment: MfaEnrollment) -> MfaEnrollmentResponse:
    secret_text = base64.b32encode(enrollment.secret).decode("ascii").rstrip("=")
    return MfaEnrollmentResponse(
        provisioning_uri=enrollment.provisioning_uri,
        secret=secret_text,
        recovery_codes=list(enrollment.recovery_codes),
    )


def _audit_log_response(record: Any) -> AuditLogResponse:
    return AuditLogResponse(**serialize_audit_log(record))


def _audit_outcome(value: str | None) -> AuditOutcome | None:
    if value == "success":
        return "success"
    if value == "failure":
        return "failure"
    if value == "denied":
        return "denied"
    if value == "error":
        return "error"
    return None


def _prompt_test_case_request(case: PromptTestCase) -> PromptTestCaseRequest:
    return PromptTestCaseRequest(
        name=case.name,
        input_payload=case.input_payload,
        expected_assertions=list(case.expected_assertions),
    )


def _prompt_response(prompt: PromptDefinition) -> PromptResponse:
    return PromptResponse(
        id=str(prompt.id),
        name=prompt.name,
        version=prompt.version,
        prompt_body=prompt.prompt_body,
        status=prompt.status,
        owner=prompt.owner,
        purpose=prompt.purpose,
        input_schema=prompt.input_schema,
        output_schema=prompt.output_schema,
        changelog=list(prompt.changelog),
        test_cases=[_prompt_test_case_request(case) for case in prompt.test_cases],
        prompt_hash=prompt.prompt_hash,
        created_by=str(prompt.created_by),
        approved_by=str(prompt.approved_by) if prompt.approved_by else None,
        created_at=prompt.created_at.isoformat(),
        updated_at=prompt.updated_at.isoformat(),
        active=prompt.active,
        registry_version=prompt.registry_version,
    )


def _prompt_status_change_response(result: PromptStatusChange) -> PromptStatusChangeResponse:
    return PromptStatusChangeResponse(
        prompt=_prompt_response(result.prompt),
        active_prompt=_prompt_response(result.active_prompt) if result.active_prompt else None,
        changed=result.changed,
        trace=result.trace,
    )


def _prompt_comparison_response(result: PromptComparison) -> PromptComparisonResponse:
    return PromptComparisonResponse(
        prompt_name=result.prompt_name,
        from_version=result.from_version,
        to_version=result.to_version,
        from_status=result.from_status,
        to_status=result.to_status,
        from_hash=result.from_hash,
        to_hash=result.to_hash,
        body_changed=result.body_changed,
        purpose_changed=result.purpose_changed,
        owner_changed=result.owner_changed,
        input_schema_changed=result.input_schema_changed,
        output_schema_changed=result.output_schema_changed,
        changelog_added=list(result.changelog_added),
        test_case_names_added=list(result.test_case_names_added),
        trace=result.trace,
    )


def build_chat_streaming_service(
    *,
    session_factory: Any,
    prompt_registry_service: PromptRegistryService,
) -> ChatStreamingService:
    from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

    registry = prompt_registry_service
    try:
        prompt, policy_version_id, model_configuration_id = registry.resolve_answer_dependencies(
            prompt_name=DEFAULT_ANSWER_PROMPT_NAME,
            policy_name="answer-safety",
        )
    except PromptRegistryError:
        bootstrap_registry_defaults(registry)
        prompt, policy_version_id, model_configuration_id = registry.resolve_answer_dependencies(
            prompt_name=DEFAULT_ANSWER_PROMPT_NAME,
            policy_name="answer-safety",
        )
    orchestrator = build_managed_answer_orchestrator(
        prompt_registry=OrchestratorPromptRegistryService(SQLAlchemyUnitOfWork(session_factory)),
        retriever=StaticAnswerRetriever(candidates=()),
        llm_provider=cast(LLMProvider, MockLLMProvider()),
    )
    orchestrator.prompt_version_id = prompt.id
    orchestrator.policy_version_id = policy_version_id
    orchestrator.model_configuration_id = model_configuration_id
    return ChatStreamingService(
        uow_factory=lambda: SQLAlchemyUnitOfWork(session_factory),
        orchestrator=orchestrator,
        prompt_registry_factory=lambda: PromptRegistryService(
            SQLAlchemyUnitOfWork(session_factory)
        ),
    )


def _build_chat_request(
    *,
    payload: ChatStreamRequest,
    request: Request,
    authorization: str | None,
    auth_service: AuthService,
    rbac_service: RbacService,
    guest_service: GuestService,
) -> ChatRequest:
    trace_id = request.headers.get("x-request-id")
    if payload.guest_token:
        snapshot = guest_service.consume_quota(token=payload.guest_token, trace_id=trace_id)
        return ChatRequest(
            question=payload.question,
            guest_session_id=snapshot["id"],
            conversation_id=payload.conversation_id,
            requested_madhhab=payload.requested_madhhab,
            answer_length=payload.answer_length,
            no_history=payload.no_history,
            trace_id=trace_id,
        )
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        claims = auth_service.verify_access_token(token)
        rbac_service.require_permission(
            user_id=claims.user_id,
            permission=Permission.CONVERSATIONS_MANAGE_OWN,
            trace_id=trace_id,
        )
        return ChatRequest(
            question=payload.question,
            actor_user_id=claims.user_id,
            conversation_id=payload.conversation_id,
            requested_madhhab=payload.requested_madhhab,
            answer_length=payload.answer_length,
            no_history=payload.no_history,
            trace_id=trace_id,
        )
    raise ChatStreamingError(
        "CHAT_AUTH_REQUIRED",
        "Authentication or guest token is required.",
        status_code=401,
    )


def _assert_chat_stream_access(
    *,
    authorization: str | None,
    auth_service: AuthService,
    rbac_service: RbacService,
    guest_service: GuestService,
) -> None:
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        claims = auth_service.verify_access_token(token)
        rbac_service.require_permission(
            user_id=claims.user_id,
            permission=Permission.CONVERSATIONS_MANAGE_OWN,
        )
        return
    raise ChatStreamingError(
        "CHAT_AUTH_REQUIRED",
        "Authentication is required.",
        status_code=401,
    )


def _prompt_create_from_request(payload: PromptCreateRequest) -> PromptCreate:
    return PromptCreate(
        name=payload.name,
        version=payload.version,
        prompt_body=payload.prompt_body,
        purpose=payload.purpose,
        owner=payload.owner,
        input_schema=payload.input_schema,
        output_schema=payload.output_schema,
        changelog=tuple(payload.changelog),
        test_cases=tuple(
            PromptTestCase(
                name=case.name,
                input_payload=case.input_payload,
                expected_assertions=tuple(case.expected_assertions),
            )
            for case in payload.test_cases
        ),
    )


_ISO_DATETIME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?([+-]\d{2}:\d{2}|Z)?$"
)

_DEPENDENCY_DEFAULT_PORTS = {
    "http": 80,
    "https": 443,
    "postgresql": 5432,
    "redis": 6379,
}


def _tcp_dependency_status(url: str, *, timeout_seconds: float = 0.5) -> str:
    parsed = urlparse(url)
    host = parsed.hostname
    port = parsed.port or _DEPENDENCY_DEFAULT_PORTS.get(parsed.scheme)
    if not host or not port:
        return "unavailable"
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            return "ok"
    except OSError:
        return "unavailable"


def _parse_iso_datetime(value: str | None) -> datetime | None:
    """Parse an ISO-8601 string to datetime, or return None."""
    if value is None:
        return None
    if not _ISO_DATETIME_RE.match(value):
        return None
    return datetime.fromisoformat(value)


def _source_response(source: SourcePublic) -> SourceResponse:
    return SourceResponse(
        id=str(source.id),
        name=source.name,
        source_type=source.source_type,
        owner=source.owner,
        website=source.website,
        language=source.language,
        country=source.country,
        reliability_level=source.reliability_level,
        is_active=source.is_active,
        created_by=str(source.created_by),
        updated_by=str(source.updated_by) if source.updated_by else None,
        created_at=source.created_at.isoformat(),
        updated_at=source.updated_at.isoformat(),
    )


def _parse_citation_ref(value: str) -> UUID:
    normalized = value.strip()
    if normalized.startswith("CIT-"):
        return citation_id_from_token(normalized)
    return UUID(normalized)


def _metrics_summary(session_factory: Any) -> MetricsSummaryResponse:
    from sqlalchemy import select
    from zayd_common.database.models import (
        Feedback,
        Incident,
        ModelConfiguration,
        Provider,
        ReviewTask,
        User,
    )

    with session_factory() as session:
        queue_depth = len(
            session.execute(
                select(ReviewTask).where(ReviewTask.status.in_(("open", "in_progress")))
            )
            .scalars()
            .all()
        )
        feedback_open_count = len(
            session.execute(
                select(Feedback)
                .where(Feedback.deleted_at.is_(None))
                .where(Feedback.status == "open")
            )
            .scalars()
            .all()
        )
        registered_user_count = len(
            session.execute(select(User).where(User.deleted_at.is_(None))).scalars().all()
        )
        incident_open_count = len(
            session.execute(select(Incident).where(Incident.status != "closed")).scalars().all()
        )
        providers = (
            session.execute(select(Provider).where(Provider.deleted_at.is_(None))).scalars().all()
        )
        models = (
            session.execute(
                select(ModelConfiguration).where(ModelConfiguration.deleted_at.is_(None))
            )
            .scalars()
            .all()
        )

    counters = telemetry_registry.counters()
    histograms = telemetry_registry.histograms()
    queue_age_samples = [
        span.duration_ms for span in telemetry_registry.spans() if span.name == "worker.lifecycle"
    ]
    provider_health_ok_count = sum(
        int(snapshot.value)
        for snapshot in counters
        if snapshot.name == "provider_health_total" and snapshot.labels.get("status") == "ok"
    )
    fallback_count = sum(
        int(snapshot.value)
        for snapshot in counters
        if snapshot.name == "external_fallback_total"
        and snapshot.labels.get("status") in {"attempted", "improved", "no_improvement"}
    )
    rag_hit_count = sum(
        int(snapshot.value)
        for snapshot in counters
        if snapshot.name == "local_rag_hit_total" and snapshot.labels.get("status") == "hit"
    )
    citation_failure_count = sum(
        int(snapshot.value)
        for snapshot in counters
        if snapshot.name == "citation_verification_total"
        and snapshot.labels.get("status") != "verified"
    )
    error_count = sum(
        int(snapshot.value)
        for snapshot in counters
        if snapshot.name in {"provider_generate_total", "orchestrator_answer_total"}
        and snapshot.labels.get("status") not in {"ok", "completed"}
    )
    api_latency_sum = sum(
        snapshot.sum_value
        for snapshot in histograms
        if snapshot.name == "provider_generate_latency_ms"
    )
    api_latency_count = sum(
        snapshot.count for snapshot in histograms if snapshot.name == "provider_generate_latency_ms"
    )

    return MetricsSummaryResponse(
        registered_user_count=registered_user_count,
        queue_depth=queue_depth,
        feedback_open_count=feedback_open_count,
        incident_open_count=incident_open_count,
        provider_count=len(providers),
        enabled_provider_count=sum(1 for provider in providers if provider.status == "enabled"),
        model_count=len(models),
        default_model_count=sum(1 for model in models if model.is_default),
        provider_cost_limit_daily_usd=sum(
            float(model.configuration_json.get("cost_limit_daily_usd") or 0.0) for model in models
        ),
        provider_health_ok_count=provider_health_ok_count,
        spans_recorded=len(telemetry_registry.spans()),
        api_latency_ms_avg=(api_latency_sum / api_latency_count) if api_latency_count else 0.0,
        error_count=error_count,
        external_fallback_count=fallback_count,
        local_rag_hit_count=rag_hit_count,
        citation_failure_count=citation_failure_count,
        queue_age_seconds_avg=(sum(queue_age_samples) / len(queue_age_samples) / 1000)
        if queue_age_samples
        else 0.0,
    )


def _citation_record_response(citation: CitationDetailPublic) -> CitationRecordResponse:
    record = citation.citation
    return CitationRecordResponse(
        id=str(record.id),
        token=record.token,
        canonical_reference=record.canonical_reference,
        document_version_id=str(record.document_version_id),
        chunk_id=str(record.chunk_id),
        citation_type=record.citation_type.value,
        display_title=record.display_title,
        arabic_text=record.arabic_text,
        thai_translation=record.thai_translation,
        hadith_grade=record.hadith_grade,
        volume=record.volume,
        page=record.page,
        verified=record.verified,
        active=record.active,
        invalidated_at=record.invalidated_at.isoformat() if record.invalidated_at else None,
        registry_version=record.registry_version,
    )


def _citation_detail_response(detail: CitationDetailPublic) -> CitationDetailResponse:
    return CitationDetailResponse(
        citation=_citation_record_response(detail),
        source_text=detail.source_text,
        source=(
            CitationSourceSummaryResponse(
                id=str(detail.source.id),
                name=detail.source.name,
                source_type=detail.source.source_type,
                language=detail.source.language,
                is_active=detail.source.is_active,
                reliability_level=detail.source.reliability_level,
            )
            if detail.source is not None
            else None
        ),
        document=(
            CitationDocumentSummaryResponse(
                id=str(detail.document.id),
                title=detail.document.title,
                author=detail.document.author,
                translator=detail.document.translator,
                publisher=detail.document.publisher,
                edition=detail.document.edition,
                language=detail.document.language,
                document_type=detail.document.document_type,
                version_status=detail.document.version_status,
            )
            if detail.document is not None
            else None
        ),
        warnings=list(detail.warnings),
        registry_version=detail.registry_version,
    )


def _preferences_response(preferences: UserPreferencesPublic) -> UserPreferencesResponse:
    return UserPreferencesResponse(
        madhhab=preferences.madhhab,
        default_madhhab=preferences.default_madhhab,
        answer_length=preferences.answer_length,
        show_arabic=preferences.show_arabic,
        history_mode=preferences.history_mode,
        preferred_language=preferences.preferred_language,
        synced=preferences.synced,
    )


def _conversation_summary_response(
    summary: ConversationSummaryPublic,
) -> ConversationSummaryResponse:
    return ConversationSummaryResponse(
        id=summary.id,
        title=summary.title,
        language=summary.language,
        madhhab=summary.madhhab,
        message_count=summary.message_count,
        preview=summary.preview,
        created_at=summary.created_at.isoformat(),
        updated_at=summary.updated_at.isoformat(),
    )


def _conversation_detail_response(detail: ConversationDetailPublic) -> ConversationDetailResponse:
    return ConversationDetailResponse(
        conversation=_conversation_summary_response(detail.conversation),
        messages=[
            ConversationMessageResponse(
                id=message.id,
                sender_type=message.sender_type,
                body=message.body,
                created_at=message.created_at.isoformat(),
                answer=(
                    ConversationAnswerResponse(
                        id=message.answer["id"],
                        summary=message.answer.get("summary", ""),
                        answer_th=message.answer.get("answer_th", ""),
                        madhhab=message.answer.get("madhhab", "shafii"),
                        risk_level=message.answer.get("risk_level", "low"),
                        confidence=message.answer.get("confidence", "medium"),
                        evidence_sufficient=bool(message.answer.get("evidence_sufficient")),
                        citations=list(message.answer.get("citations", [])),
                        limitations=list(message.answer.get("limitations", [])),
                        warning=message.answer.get("warning"),
                        status=message.answer.get("status"),
                    )
                    if message.answer is not None
                    else None
                ),
            )
            for message in detail.messages
        ],
    )


def _conversation_list_response(result: ConversationListResult) -> ConversationListResponse:
    return ConversationListResponse(
        conversations=[_conversation_summary_response(item) for item in result.conversations],
        total_count=result.total_count,
        limit=result.limit,
        offset=result.offset,
        next_offset=result.next_offset,
    )


def _saved_answer_response(saved: SavedAnswerPublic) -> SavedAnswerResponse:
    return SavedAnswerResponse(
        id=saved.id,
        answer_id=saved.answer_id,
        saved_at=saved.saved_at.isoformat(),
        summary=saved.summary,
        answer_th=saved.answer_th,
        madhhab=saved.madhhab,
        warnings=list(saved.warnings),
        citations=[
            SavedAnswerCitationResponse(
                citation_id=item["citation_id"],
                display=item["display"],
                source_type=item["source_type"],
                verification_status=item["verification_status"],
            )
            for item in saved.citations
        ],
    )


def _saved_answer_list_response(result: SavedAnswerListResult) -> SavedAnswerListResponse:
    return SavedAnswerListResponse(
        saved_answers=[_saved_answer_response(item) for item in result.saved_answers],
        total_count=result.total_count,
    )


def _feedback_response(feedback: FeedbackPublic) -> FeedbackResponse:
    return FeedbackResponse(
        id=feedback.id,
        category=feedback.category,
        status=feedback.status,
        answer_id=feedback.answer_id,
        citation_id=feedback.citation_id,
        created_at=feedback.created_at.isoformat(),
        receipt_message=feedback.receipt_message,
    )


def _feedback_review_item_response(item: FeedbackQueueItem) -> FeedbackReviewItemResponse:
    return FeedbackReviewItemResponse(
        id=item.id,
        category=item.category,
        status=item.status,
        priority=item.priority,
        severity=item.severity,
        answer_id=item.answer_id,
        citation_id=item.citation_id,
        reviewer_id=item.reviewer_id,
        root_cause=item.root_cause,
        created_at=item.created_at.isoformat(),
        updated_at=item.updated_at.isoformat(),
    )


def _feedback_review_detail_response(detail: FeedbackReviewDetail) -> FeedbackReviewDetailResponse:
    return FeedbackReviewDetailResponse(
        id=detail.id,
        category=detail.category,
        status=detail.status,
        priority=detail.priority,
        severity=detail.severity,
        answer_id=detail.answer_id,
        citation_id=detail.citation_id,
        reviewer_id=detail.reviewer_id,
        reviewer_notes=detail.reviewer_notes,
        root_cause=detail.root_cause,
        resolution=detail.resolution,
        resolved_at=detail.resolved_at.isoformat() if detail.resolved_at else None,
        trace_context=(
            FeedbackTraceContextResponse(
                retrieval_run_id=detail.trace_context.retrieval_run_id,
                model_configuration_id=detail.trace_context.model_configuration_id,
                prompt_version_id=detail.trace_context.prompt_version_id,
                policy_version_id=detail.trace_context.policy_version_id,
            )
            if detail.trace_context is not None
            else None
        ),
        created_at=detail.created_at.isoformat(),
        updated_at=detail.updated_at.isoformat(),
    )


def _feedback_queue_list_response(result: FeedbackQueueResult) -> FeedbackQueueListResponse:
    return FeedbackQueueListResponse(
        items=[_feedback_review_item_response(item) for item in result.items],
        total_count=result.total_count,
        limit=result.limit,
        offset=result.offset,
        next_offset=result.next_offset,
    )


def _evaluation_run_info_response(run: RunInfo) -> EvaluationRunInfoResponse:
    return EvaluationRunInfoResponse(
        run_id=run.run_id,
        dataset_name=run.dataset_name,
        dataset_version=run.dataset_version,
        provider_name=run.provider_name,
        model_name=run.model_name,
        retriever_version=run.retriever_version,
        embedding_version=run.embedding_version,
        reranker_version=run.reranker_version,
        git_commit=run.git_commit,
        random_seed=run.random_seed,
        started_at=run.started_at,
        finished_at=run.finished_at,
        metrics=dict(run.metrics or {}),
    )


def _run_comparison_report_response(report: RunComparisonReport) -> RunComparisonReportResponse:
    return RunComparisonReportResponse(
        base_run=_evaluation_run_info_response(report.base_run),
        target_run=_evaluation_run_info_response(report.target_run),
        regression_count=report.regression_count,
        improvement_count=report.improvement_count,
        overall_base_pass_rate=report.overall_base_pass_rate,
        overall_target_pass_rate=report.overall_target_pass_rate,
        comparisons=[
            CaseComparisonResponse(
                case_key=c.case_key,
                case_type=c.case_type,
                risk_level=c.risk_level,
                visibility=c.visibility,
                base_passed=c.base_passed,
                target_passed=c.target_passed,
                regression=c.regression,
                improvement=c.improvement,
                base_scores=dict(c.base_scores or {}),
                target_scores=dict(c.target_scores or {}),
                topic=c.topic,
                language=c.language,
                madhhab=c.madhhab,
            )
            for c in report.comparisons
        ],
        version=report.version,
    )


def _incident_response(item: IncidentPublic, *, idempotent: bool = False) -> IncidentResponse:
    return IncidentResponse(
        id=item.id,
        severity=item.severity,
        status=item.status,
        summary=item.summary,
        owner_id=item.owner_id,
        feedback_id=item.feedback_id,
        affected_answer_id=item.affected_answer_id,
        affected_document_id=item.affected_document_id,
        affected_citation_id=item.affected_citation_id,
        alert_status=item.alert_status,
        row_version=item.row_version,
        created_at=item.created_at.isoformat(),
        updated_at=item.updated_at.isoformat(),
        idempotent=idempotent,
    )


def _incident_regression_response(
    result: IncidentRegressionResult,
) -> IncidentRegressionCreateResponse:
    return IncidentRegressionCreateResponse(
        evaluation_case_id=result.evaluation_case_id,
        incident_id=result.incident_id,
        redaction_count=result.redaction_count,
        schema_version=result.schema_version,
        policy_version=result.policy_version,
    )


def _answer_invalidation_response(item: AnswerInvalidationResult) -> AnswerInvalidationResponse:
    return AnswerInvalidationResponse(
        answer_id=item.answer_id,
        invalidated_at=item.invalidated_at.isoformat(),
        warning=item.warning,
        notification_status=item.notification_status,
        idempotent=item.idempotent,
    )


def _affected_answer_page_response(item: AffectedAnswerPage) -> AffectedAnswerPageResponse:
    return AffectedAnswerPageResponse(
        answer_ids=list(item.answer_ids),
        total_count=item.total_count,
        limit=item.limit,
        offset=item.offset,
        next_offset=item.next_offset,
    )


def _public_source_warnings(source: SourcePublic) -> list[str]:
    warnings: list[str] = []
    if not source.is_active:
        warnings.append("source_suspended")
    return warnings


def _license_create(payload: LicenseCreateRequest) -> LicenseCreate:
    return LicenseCreate(
        license_name=payload.license_name,
        license_version=payload.license_version,
        status=payload.status,
        storage_permission=payload.storage_permission,
        embedding_permission=payload.embedding_permission,
        commercial_use=payload.commercial_use,
        redistribution=payload.redistribution,
        attribution_required=payload.attribution_required,
        attribution_template=payload.attribution_template,
        permission_document_key=payload.permission_document_key,
        valid_from=payload.valid_from,
        valid_until=payload.valid_until,
        notes=payload.notes,
    )


def _license_response(license_record: LicensePublic) -> LicenseResponse:
    return LicenseResponse(
        id=str(license_record.id),
        source_id=str(license_record.source_id),
        license_name=license_record.license_name,
        license_version=license_record.license_version,
        status=license_record.status,
        storage_permission=license_record.storage_permission,
        embedding_permission=license_record.embedding_permission,
        commercial_use=license_record.commercial_use,
        redistribution=license_record.redistribution,
        attribution_required=license_record.attribution_required,
        attribution_template=license_record.attribution_template,
        permission_document_key=license_record.permission_document_key,
        valid_from=license_record.valid_from.isoformat()
        if license_record.valid_from is not None
        else None,
        valid_until=license_record.valid_until.isoformat()
        if license_record.valid_until is not None
        else None,
        notes=license_record.notes,
        created_by=str(license_record.created_by),
        updated_by=str(license_record.updated_by) if license_record.updated_by else None,
        created_at=license_record.created_at.isoformat(),
        updated_at=license_record.updated_at.isoformat(),
        row_version=license_record.row_version,
    )


def _permission_document_response(access: PermissionDocumentAccess) -> PermissionDocumentResponse:
    return PermissionDocumentResponse(
        license_id=str(access.license_id),
        permission_document_key=access.permission_document_key,
        access=access.access,
        audited=access.audited,
    )


def _publication_authorization_response(
    authorization: PublicationAuthorization,
) -> PublicationAuthorizationResponse:
    return PublicationAuthorizationResponse(
        license_id=str(authorization.license_id),
        authorized=authorization.authorized,
        policy_version=authorization.policy_version,
        reason=authorization.reason,
    )


def _license_policy_decision_response(
    decision: LicensePolicyDecisionPublic,
) -> LicensePolicyDecisionResponse:
    return LicensePolicyDecisionResponse(
        license_id=str(decision.license_id),
        source_id=str(decision.source_id),
        workflow=decision.workflow,
        policy_version=decision.policy_version,
        evaluated_on=decision.evaluated_on.isoformat(),
        source_license_version=decision.source_license_version,
        workflow_allowed=decision.workflow_allowed,
        llm_override_allowed=decision.llm_override_allowed,
        reason_codes=list(decision.reason_codes),
        actions=[
            LicensePolicyActionResponse(
                action=action.action,
                allowed=action.allowed,
                reason_codes=list(action.reason_codes),
                source_license_version=action.source_license_version,
                max_cache_ttl_seconds=action.max_cache_ttl_seconds,
                attribution_required=action.attribution_required,
                attribution_template=action.attribution_template,
            )
            for action in decision.actions
        ],
    )


def _document_upload_request(payload: DocumentUploadRequestModel) -> DocumentUploadRequest:
    try:
        file_bytes = base64.b64decode(payload.file_base64, validate=True)
    except ValueError as exc:
        raise DocumentUploadError(
            "DOCUMENT_INVALID_FILE_PAYLOAD",
            "File payload is not valid base64.",
            status_code=400,
        ) from exc
    return DocumentUploadRequest(
        source_id=payload.source_id,
        source_license_id=payload.source_license_id,
        canonical_id=payload.canonical_id,
        document_type=payload.document_type,
        title=payload.title,
        language=payload.language,
        filename=payload.filename,
        content_type=payload.content_type,
        file_bytes=file_bytes,
        author=payload.author,
        translator=payload.translator,
        publisher=payload.publisher,
        edition=payload.edition,
        madhhab=payload.madhhab,
    )


def _document_upload_duplicate_response(
    duplicate: DocumentUploadDuplicate,
) -> DocumentUploadDuplicateResponse:
    return DocumentUploadDuplicateResponse(
        document_id=str(duplicate.document_id),
        document_version_id=str(duplicate.document_version_id),
        canonical_id=duplicate.canonical_id,
        title=duplicate.title,
        content_hash=duplicate.content_hash,
    )


def _document_upload_response(result: DocumentUploadResult) -> DocumentUploadResponse:
    return DocumentUploadResponse(
        document_id=str(result.document_id),
        document_version_id=str(result.document_version_id),
        content_hash=result.content_hash,
        filename=result.filename,
        content_type=result.content_type,
        byte_size=result.byte_size,
        duplicate=_document_upload_duplicate_response(result.duplicate)
        if result.duplicate
        else None,
        upload_status=result.upload_status,
        original_file_key=result.original_file_key,
        download_url=_signed_url_response(result.download_url),
        policy_version=result.policy_version,
    )


def _document_malware_scan_response(
    result: DocumentMalwareScanResult,
) -> DocumentMalwareScanResponse:
    return DocumentMalwareScanResponse(
        document_id=str(result.document_id),
        document_version_id=str(result.document_version_id),
        status=result.status,
        engine=result.engine,
        engine_version=result.engine_version,
        signature_name=result.signature_name,
        scanned_bytes=result.scanned_bytes,
        policy_version=result.policy_version,
        incident_id=str(result.incident_id) if result.incident_id else None,
    )


def _signed_url_response(signed_url: SignedUrl) -> SignedUrlResponse:
    return SignedUrlResponse(
        method=signed_url.method,
        url=signed_url.url,
        expires_at=signed_url.expires_at,
        expires_in_seconds=signed_url.expires_in_seconds,
    )


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requests: dict[str, list[float]] = {}

    def is_allowed(self, identifier: str, limit: int, window_seconds: float) -> bool:
        now = datetime.now(UTC).timestamp()
        cutoff = now - window_seconds
        with self._lock:
            history = self._requests.get(identifier, [])
            history = [t for t in history if t > cutoff]
            if len(history) >= limit:
                return False
            history.append(now)
            self._requests[identifier] = history
            # Memory safeguard: limit dictionary to avoid storage attacks
            if len(self._requests) > 10000:
                self._requests = {k: v for k, v in self._requests.items() if len(v) > 0}
            return True


rate_limiter = InMemoryRateLimiter()


def create_app() -> FastAPI:
    settings = ServiceSettings.from_runtime_env(app_name="api")
    configure_logging(level=settings.log_level)
    app = FastAPI(title=f"Zayd {settings.app_name} service")
    session_factory = get_sessionmaker(settings.database_url)

    # 1. Register CORS Middleware
    origins = [origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Register Global Security Headers Middleware
    @app.middleware("http")
    async def add_security_headers(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'wasm-unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "object-src 'none'; "
            "base-uri 'self';"
        )
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains; preload"
        )
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response

    # 3. Register IP & Token Rate Limiting Middleware
    @app.middleware("http")
    async def rate_limiting_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.url.path in {"/health", "/metrics"}:
            return await call_next(request)

        auth_header = request.headers.get("authorization")
        identifier = request.client.host if request.client else "unknown-ip"
        if auth_header and auth_header.startswith("Bearer "):
            token_val = auth_header.split(" ", 1)[1]
            identifier = hashlib.sha256(token_val.encode("utf-8")).hexdigest()

        is_strict = any(
            request.url.path.startswith(p)
            for p in {"/auth/login", "/auth/register", "/feedback", "/admin/providers"}
        )
        limit = 10 if is_strict else 100
        window = 60.0

        if not rate_limiter.is_allowed(identifier, limit, window):
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests. Please try again later.",
                    }
                },
            )

        return await call_next(request)

    @app.middleware("http")
    async def request_context_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        inbound_request_id = normalize_request_id(request.headers.get("x-request-id"))
        inbound_trace_id = normalize_request_id(request.headers.get("x-trace-id"))
        context = new_trace_context(
            request_id=inbound_request_id,
            trace_id=inbound_trace_id or inbound_request_id,
            source="header" if inbound_request_id or inbound_trace_id else "generated",
            service=settings.app_name,
        )
        headers = [
            (key, value)
            for key, value in request.scope["headers"]
            if key not in {b"x-request-id", b"x-trace-id"}
        ]
        headers.append((b"x-request-id", context.request_id.encode("utf-8")))
        headers.append((b"x-trace-id", context.trace_id.encode("utf-8")))
        request.scope["headers"] = headers
        request.state.request_context = context
        request.state.request_id = context.request_id
        request.state.trace_id = context.trace_id
        with bind_request_context(context):
            started_at = datetime.now(UTC)
            try:
                response = await call_next(request)
            except Exception:
                telemetry_registry.record_counter(
                    "api_request_total",
                    method=request.method,
                    path=request.url.path,
                    status="error",
                )
                logger.exception(
                    "request_failed method=%s path=%s",
                    request.method,
                    request.url.path,
                )
                raise
            duration_ms = (datetime.now(UTC) - started_at).total_seconds() * 1000
            telemetry_registry.record_counter(
                "api_request_total",
                method=request.method,
                path=request.url.path,
                status=str(response.status_code),
            )
            telemetry_registry.record_histogram(
                "api_request_latency_ms",
                duration_ms,
                method=request.method,
                path=request.url.path,
            )
            response.headers["x-request-id"] = context.request_id
            response.headers["x-trace-id"] = context.trace_id
            logger.info(
                "request_completed method=%s path=%s status_code=%s",
                request.method,
                request.url.path,
                response.status_code,
            )
            return response

    def auth_service() -> AuthService:
        from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

        return AuthService(
            SQLAlchemyUnitOfWork(session_factory),
            signing_secret=settings.auth_jwt_secret.get_secret_value(),
        )

    def rbac_service() -> RbacService:
        from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

        return RbacService(SQLAlchemyUnitOfWork(session_factory))

    def mfa_service() -> MfaService:
        from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

        return MfaService(SQLAlchemyUnitOfWork(session_factory))

    def audit_service() -> AuditService:
        from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

        return AuditService(SQLAlchemyUnitOfWork(session_factory))

    def source_service() -> SourceService:
        from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

        return SourceService(SQLAlchemyUnitOfWork(session_factory))

    def license_service() -> LicenseService:
        from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

        return LicenseService(SQLAlchemyUnitOfWork(session_factory))

    def prompt_registry_service() -> PromptRegistryService:
        from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

        return PromptRegistryService(SQLAlchemyUnitOfWork(session_factory))

    def provider_admin_service() -> ProviderAdminService:
        from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

        return ProviderAdminService(SQLAlchemyUnitOfWork(session_factory))

    def citation_registry_service() -> CitationRegistryService:
        from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

        return CitationRegistryService(SQLAlchemyUnitOfWork(session_factory))

    def user_preferences_service() -> UserPreferencesService:
        from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

        return UserPreferencesService(SQLAlchemyUnitOfWork(session_factory))

    def user_admin_service() -> UserAdminService:
        from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

        return UserAdminService(SQLAlchemyUnitOfWork(session_factory))

    def conversation_history_service() -> ConversationHistoryService:
        from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

        return ConversationHistoryService(SQLAlchemyUnitOfWork(session_factory))

    def saved_answer_service() -> SavedAnswerService:
        from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

        return SavedAnswerService(SQLAlchemyUnitOfWork(session_factory))

    def feedback_service() -> FeedbackService:
        from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

        return FeedbackService(SQLAlchemyUnitOfWork(session_factory))

    def feedback_review_service() -> FeedbackReviewService:
        from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

        return FeedbackReviewService(SQLAlchemyUnitOfWork(session_factory))

    def benchmark_comparison_service() -> BenchmarkComparisonService:
        from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

        return BenchmarkComparisonService(SQLAlchemyUnitOfWork(session_factory))

    def incident_management_service() -> IncidentManagementService:
        from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

        return IncidentManagementService(SQLAlchemyUnitOfWork(session_factory))

    def incident_regression_service() -> IncidentRegressionService:
        from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

        return IncidentRegressionService(SQLAlchemyUnitOfWork(session_factory))

    def answer_invalidation_service() -> AnswerInvalidationService:
        from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

        return AnswerInvalidationService(SQLAlchemyUnitOfWork(session_factory))

    def document_upload_service() -> DocumentUploadService:
        from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

        return DocumentUploadService(
            SQLAlchemyUnitOfWork(session_factory),
            S3ObjectStorage(
                S3StorageSettings(
                    endpoint=settings.s3_endpoint,
                    region=settings.s3_region,
                    access_key=settings.s3_access_key.get_secret_value(),
                    secret_key=settings.s3_secret_key.get_secret_value(),
                    bucket=settings.s3_bucket,
                    addressing_style=settings.s3_addressing_style,
                    max_attempts=settings.s3_max_attempts,
                    signed_url_ttl_seconds=settings.s3_signed_url_ttl_seconds,
                )
            ),
        )

    def chat_streaming_service() -> ChatStreamingService:
        return build_chat_streaming_service(
            session_factory=session_factory,
            prompt_registry_service=prompt_registry_service(),
        )

    def get_current_claims(
        service: Annotated[AuthService, Depends(auth_service)],
        authorization: Annotated[str | None, Header()] = None,
    ) -> AccessTokenClaims:
        if not authorization or not authorization.startswith("Bearer "):
            raise AuthError("AUTH_UNAUTHENTICATED", "Authentication required.", status_code=401)
        token = authorization.removeprefix("Bearer ").strip()
        return service.verify_access_token(token)

    def get_current_user_id(
        claims: Annotated[AccessTokenClaims, Depends(get_current_claims)],
    ) -> str:
        return str(claims.user_id)

    def require_permission(permission: Permission) -> Callable[..., UserPrincipal]:
        def dependency(
            request: Request,
            claims: Annotated[AccessTokenClaims, Depends(get_current_claims)],
            service: Annotated[RbacService, Depends(rbac_service)],
            mfa: Annotated[MfaService, Depends(mfa_service)],
        ) -> UserPrincipal:
            principal = service.require_permission(
                user_id=claims.user_id,
                permission=permission,
                trace_id=request.headers.get("x-request-id"),
            )
            mfa.assert_privileged_access(
                user_id=claims.user_id,
                trace_id=request.headers.get("x-request-id"),
            )
            return principal

        return dependency

    def require_self_or_privileged() -> Callable[..., UserPrincipal]:
        def dependency(
            request: Request,
            claims: Annotated[AccessTokenClaims, Depends(get_current_claims)],
            service: Annotated[RbacService, Depends(rbac_service)],
            mfa: Annotated[MfaService, Depends(mfa_service)],
        ) -> UserPrincipal:
            principal = service.require_permission(
                user_id=claims.user_id,
                permission=Permission.USERS_READ_SELF,
                trace_id=request.headers.get("x-request-id"),
            )
            mfa.assert_privileged_access(
                user_id=claims.user_id,
                trace_id=request.headers.get("x-request-id"),
            )
            return principal

        return dependency

    @app.exception_handler(AuthError)
    async def auth_error_handler(request: Request, exc: AuthError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(RbacError)
    async def rbac_error_handler(request: Request, exc: RbacError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(MfaError)
    async def mfa_error_handler(request: Request, exc: MfaError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(SourceError)
    async def source_error_handler(request: Request, exc: SourceError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(LicenseError)
    async def license_error_handler(request: Request, exc: LicenseError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(DocumentUploadError)
    async def document_upload_error_handler(
        request: Request, exc: DocumentUploadError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(DocumentProcessingError)
    async def document_processing_error_handler(
        request: Request, exc: DocumentProcessingError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(MalwareScannerUnavailable)
    async def malware_scanner_unavailable_handler(
        request: Request, exc: MalwareScannerUnavailable
    ) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(StorageError)
    async def storage_error_handler(request: Request, exc: StorageError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(ParserError)
    async def parser_error_handler(request: Request, exc: ParserError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(SecurityError)
    async def security_error_handler(request: Request, exc: SecurityError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(PromptRegistryError)
    async def prompt_registry_error_handler(
        request: Request, exc: PromptRegistryError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(ProviderAdminError)
    async def provider_admin_error_handler(
        request: Request, exc: ProviderAdminError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(UserAdminError)
    async def user_admin_error_handler(request: Request, exc: UserAdminError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(ChatStreamingError)
    async def chat_streaming_error_handler(
        request: Request, exc: ChatStreamingError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(CitationRegistryError)
    async def citation_registry_error_handler(
        request: Request, exc: CitationRegistryError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(UserPreferencesError)
    async def user_preferences_error_handler(
        request: Request, exc: UserPreferencesError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(ConversationHistoryError)
    async def conversation_history_error_handler(
        request: Request, exc: ConversationHistoryError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(SavedAnswerError)
    async def saved_answer_error_handler(request: Request, exc: SavedAnswerError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(FeedbackError)
    async def feedback_error_handler(request: Request, exc: FeedbackError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(FeedbackReviewError)
    async def feedback_review_error_handler(
        request: Request, exc: FeedbackReviewError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(IncidentManagementError)
    async def incident_management_error_handler(
        request: Request, exc: IncidentManagementError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(IncidentRegressionError)
    async def incident_regression_error_handler(
        request: Request, exc: IncidentRegressionError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(AnswerInvalidationError)
    async def answer_invalidation_error_handler(
        request: Request, exc: AnswerInvalidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(BenchmarkComparisonError)
    async def benchmark_comparison_error_handler(
        request: Request, exc: BenchmarkComparisonError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.get("/health", response_model=HealthStatus)
    async def health() -> HealthStatus:
        logger.info("health_check")
        return HealthStatus(service=settings.app_name)

    @app.get("/health/dependencies", response_model=SystemHealthResponse)
    async def dependency_health() -> SystemHealthResponse:
        dependency_urls = {
            "database": settings.database_url,
            "redis": settings.redis_url,
            "object_storage": settings.s3_endpoint,
            "llm_provider": settings.llm_base_url,
        }
        statuses = await asyncio.gather(
            *(asyncio.to_thread(_tcp_dependency_status, url) for url in dependency_urls.values())
        )
        dependencies = {
            name: DependencyHealthResponse(status=status)
            for name, status in zip(dependency_urls, statuses, strict=True)
        }
        overall = "ok" if all(item.status == "ok" for item in dependencies.values()) else "degraded"
        return SystemHealthResponse(
            service=settings.app_name,
            status=overall,
            dependencies=dependencies,
        )

    @app.get("/admin/dashboard", response_model=MetricsSnapshotResponse)
    async def admin_dashboard(
        _: Annotated[UserPrincipal, Depends(require_permission(Permission.AUDIT_READ))],
        window_minutes: int = Query(default=60, ge=1, le=1440),
    ) -> MetricsSnapshotResponse:
        return MetricsSnapshotResponse(
            generated_at=datetime.now().isoformat(),
            window_minutes=window_minutes,
            summary=_metrics_summary(session_factory),
        )

    @app.post("/auth/register", response_model=AuthResponse, status_code=201)
    async def register(
        payload: RegisterRequest,
        request: Request,
        service: Annotated[AuthService, Depends(auth_service)],
    ) -> AuthResponse:
        result = service.register(
            email=str(payload.email),
            password=payload.password,
            display_name=payload.display_name,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            trace_id=request.headers.get("x-request-id"),
        )
        return _auth_response(result)

    @app.post("/auth/login", response_model=AuthResponse)
    async def login(
        payload: LoginRequest,
        request: Request,
        service: Annotated[AuthService, Depends(auth_service)],
    ) -> AuthResponse:
        result = service.login(
            email=str(payload.email),
            password=payload.password,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            trace_id=request.headers.get("x-request-id"),
        )
        return _auth_response(result)

    @app.post("/auth/refresh", response_model=TokenResponse)
    async def refresh(
        payload: RefreshRequest,
        request: Request,
        service: Annotated[AuthService, Depends(auth_service)],
    ) -> TokenResponse:
        tokens = service.refresh(
            refresh_token=payload.refresh_token,
            trace_id=request.headers.get("x-request-id"),
        )
        return TokenResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            token_type=tokens.token_type,
            expires_in=tokens.expires_in,
        )

    @app.post("/auth/logout")
    async def logout(
        payload: RefreshRequest,
        request: Request,
        service: Annotated[AuthService, Depends(auth_service)],
    ) -> dict[str, str]:
        service.logout(
            refresh_token=payload.refresh_token,
            trace_id=request.headers.get("x-request-id"),
        )
        return {"status": "ok"}

    @app.post("/auth/password-reset/request", response_model=PasswordResetResponse)
    async def request_password_reset(
        payload: PasswordResetRequest,
        request: Request,
        service: Annotated[AuthService, Depends(auth_service)],
    ) -> PasswordResetResponse:
        reset_token = service.request_password_reset(
            email=str(payload.email),
            ip_address=request.client.host if request.client else None,
            trace_id=request.headers.get("x-request-id"),
        )
        return PasswordResetResponse(status="ok", reset_token=reset_token)

    @app.post("/auth/password-reset/confirm")
    async def confirm_password_reset(
        payload: PasswordResetConfirmRequest,
        request: Request,
        service: Annotated[AuthService, Depends(auth_service)],
    ) -> dict[str, str]:
        service.reset_password(
            reset_token=payload.reset_token,
            new_password=payload.new_password,
            trace_id=request.headers.get("x-request-id"),
        )
        return {"status": "ok"}

    @app.post("/auth/sessions/revoke-all")
    async def revoke_all_sessions(
        request: Request,
        current_user_id: Annotated[str, Depends(get_current_user_id)],
        _: Annotated[UserPrincipal, Depends(require_permission(Permission.SESSIONS_REVOKE_OWN))],
        service: Annotated[AuthService, Depends(auth_service)],
    ) -> dict[str, int]:
        revoked = service.revoke_all_sessions(
            user_id=UUID(current_user_id),
            trace_id=request.headers.get("x-request-id"),
        )
        return {"revoked_sessions": revoked}

    @app.get("/auth/me", response_model=PrincipalResponse)
    async def me(
        claims: Annotated[AccessTokenClaims, Depends(get_current_claims)],
        service: Annotated[RbacService, Depends(rbac_service)],
    ) -> PrincipalResponse:
        return _principal_response(service.get_principal(claims.user_id))

    @app.get("/auth/me/preferences", response_model=UserPreferencesResponse)
    async def get_my_preferences(
        claims: Annotated[AccessTokenClaims, Depends(get_current_claims)],
        service: Annotated[UserPreferencesService, Depends(user_preferences_service)],
    ) -> UserPreferencesResponse:
        return _preferences_response(service.get_preferences(user_id=claims.user_id))

    @app.patch("/auth/me/preferences", response_model=UserPreferencesResponse)
    async def update_my_preferences(
        payload: UserPreferencesPatchRequest,
        request: Request,
        claims: Annotated[AccessTokenClaims, Depends(get_current_claims)],
        service: Annotated[UserPreferencesService, Depends(user_preferences_service)],
    ) -> UserPreferencesResponse:
        updated = service.update_preferences(
            user_id=claims.user_id,
            update=UserPreferencesUpdate(
                madhhab=payload.madhhab,
                answer_length=payload.answer_length,
                show_arabic=payload.show_arabic,
                history_mode=payload.history_mode,
            ),
            trace_id=request.headers.get("x-request-id"),
        )
        return _preferences_response(updated)

    @app.post("/admin/rbac/bootstrap")
    async def bootstrap_rbac(
        _: Annotated[UserPrincipal, Depends(require_permission(Permission.USERS_ROLES_MANAGE))],
        service: Annotated[RbacService, Depends(rbac_service)],
    ) -> dict[str, str]:
        service.bootstrap_system_roles()
        return {"status": "ok"}

    @app.post("/admin/users/roles/grant", response_model=RoleAssignmentResponse)
    async def grant_user_role(
        payload: RoleAssignmentRequest,
        request: Request,
        claims: Annotated[AccessTokenClaims, Depends(get_current_claims)],
        _: Annotated[UserPrincipal, Depends(require_permission(Permission.USERS_ROLES_MANAGE))],
        service: Annotated[RbacService, Depends(rbac_service)],
    ) -> RoleAssignmentResponse:
        changed = service.grant_role(
            actor_user_id=claims.user_id,
            target_user_id=payload.user_id,
            role_name=payload.role_name,
            trace_id=request.headers.get("x-request-id"),
        )
        return RoleAssignmentResponse(status="ok", changed=changed)

    @app.post("/admin/users/roles/revoke", response_model=RoleAssignmentResponse)
    async def revoke_user_role(
        payload: RoleAssignmentRequest,
        request: Request,
        claims: Annotated[AccessTokenClaims, Depends(get_current_claims)],
        _: Annotated[UserPrincipal, Depends(require_permission(Permission.USERS_ROLES_MANAGE))],
        service: Annotated[RbacService, Depends(rbac_service)],
    ) -> RoleAssignmentResponse:
        changed = service.revoke_role(
            actor_user_id=claims.user_id,
            target_user_id=payload.user_id,
            role_name=payload.role_name,
            trace_id=request.headers.get("x-request-id"),
        )
        return RoleAssignmentResponse(status="ok", changed=changed)

    @app.get("/admin/users", response_model=AdminUserListResponse)
    async def list_admin_users(
        _: Annotated[UserPrincipal, Depends(require_permission(Permission.USERS_READ))],
        service: Annotated[UserAdminService, Depends(user_admin_service)],
        query: str | None = None,
        status: str | None = None,
        role: str | None = None,
    ) -> AdminUserListResponse:
        users = service.list_users(query=query, status=status, role=role)
        return AdminUserListResponse(users=[_admin_user_response(user) for user in users])

    @app.patch("/admin/users/{user_id}/status", response_model=AdminUserStatusResponse)
    async def update_admin_user_status(
        user_id: UUID,
        payload: AdminUserStatusRequest,
        request: Request,
        claims: Annotated[AccessTokenClaims, Depends(get_current_claims)],
        _: Annotated[UserPrincipal, Depends(require_permission(Permission.USERS_MANAGE))],
        service: Annotated[UserAdminService, Depends(user_admin_service)],
    ) -> AdminUserStatusResponse:
        user = service.set_status(
            user_id=user_id,
            status=payload.status,
            actor_user_id=claims.user_id,
            trace_id=request.headers.get("x-request-id"),
        )
        return AdminUserStatusResponse(user=_admin_user_response(user))

    @app.post(
        "/admin/users/{user_id}/sessions/revoke",
        response_model=AdminUserSessionRevokeResponse,
    )
    async def revoke_admin_user_sessions(
        user_id: UUID,
        request: Request,
        claims: Annotated[AccessTokenClaims, Depends(get_current_claims)],
        _: Annotated[UserPrincipal, Depends(require_permission(Permission.USERS_MANAGE))],
        service: Annotated[UserAdminService, Depends(user_admin_service)],
    ) -> AdminUserSessionRevokeResponse:
        revoked = service.revoke_sessions(
            user_id=user_id,
            actor_user_id=claims.user_id,
            trace_id=request.headers.get("x-request-id"),
        )
        return AdminUserSessionRevokeResponse(revoked_sessions=revoked)

    @app.get("/admin/providers", response_model=ProviderListResponse)
    async def list_admin_providers(
        _: Annotated[UserPrincipal, Depends(require_permission(Permission.PROVIDERS_READ))],
        service: Annotated[ProviderAdminService, Depends(provider_admin_service)],
    ) -> ProviderListResponse:
        providers = service.list_providers()
        return ProviderListResponse(
            providers=[_provider_response(provider) for provider in providers]
        )

    @app.post("/admin/providers", response_model=ProviderResponse, status_code=201)
    async def create_admin_provider(
        payload: ProviderCreateRequest,
        request: Request,
        claims: Annotated[AccessTokenClaims, Depends(get_current_claims)],
        _: Annotated[UserPrincipal, Depends(require_permission(Permission.PROVIDERS_MANAGE))],
        service: Annotated[ProviderAdminService, Depends(provider_admin_service)],
    ) -> ProviderResponse:
        provider = service.create_provider(
            data=ProviderCreate(
                name=payload.name,
                provider_type=payload.provider_type,
                status=payload.status,
                base_url=payload.base_url,
                secret_ref=payload.secret_ref,
                terms_url=payload.terms_url,
                data_policy_json=payload.data_policy_json,
            ),
            actor_user_id=claims.user_id,
            trace_id=request.headers.get("x-request-id"),
        )
        return _provider_response(provider)

    @app.patch("/admin/providers/{provider_id}", response_model=ProviderResponse)
    async def update_admin_provider(
        provider_id: UUID,
        payload: ProviderUpdateRequest,
        request: Request,
        claims: Annotated[AccessTokenClaims, Depends(get_current_claims)],
        _: Annotated[UserPrincipal, Depends(require_permission(Permission.PROVIDERS_MANAGE))],
        service: Annotated[ProviderAdminService, Depends(provider_admin_service)],
    ) -> ProviderResponse:
        provider = service.update_provider(
            provider_id=provider_id,
            data=ProviderUpdate(
                name=payload.name,
                status=payload.status,
                base_url=payload.base_url,
                secret_ref=payload.secret_ref,
                terms_url=payload.terms_url,
                data_policy_json=payload.data_policy_json,
            ),
            actor_user_id=claims.user_id,
            trace_id=request.headers.get("x-request-id"),
        )
        return _provider_response(provider)

    @app.post(
        "/admin/providers/{provider_id}/test-connection",
        response_model=ProviderConnectionTestResponse,
    )
    async def test_admin_provider_connection(
        provider_id: UUID,
        request: Request,
        claims: Annotated[AccessTokenClaims, Depends(get_current_claims)],
        _: Annotated[UserPrincipal, Depends(require_permission(Permission.PROVIDERS_MANAGE))],
        service: Annotated[ProviderAdminService, Depends(provider_admin_service)],
    ) -> ProviderConnectionTestResponse:
        result = service.test_connection(
            provider_id=provider_id,
            actor_user_id=claims.user_id,
            trace_id=request.headers.get("x-request-id"),
        )
        return _provider_connection_test_response(result)

    @app.get("/admin/models", response_model=ModelConfigurationListResponse)
    async def list_admin_models(
        _: Annotated[UserPrincipal, Depends(require_permission(Permission.PROVIDERS_READ))],
        service: Annotated[ProviderAdminService, Depends(provider_admin_service)],
    ) -> ModelConfigurationListResponse:
        models = service.list_models()
        return ModelConfigurationListResponse(
            models=[_model_configuration_response(model) for model in models]
        )

    @app.post("/admin/models", response_model=ModelConfigurationResponse, status_code=201)
    async def create_admin_model(
        payload: ModelConfigurationCreateRequest,
        request: Request,
        claims: Annotated[AccessTokenClaims, Depends(get_current_claims)],
        _: Annotated[UserPrincipal, Depends(require_permission(Permission.MODELS_MANAGE))],
        service: Annotated[ProviderAdminService, Depends(provider_admin_service)],
    ) -> ModelConfigurationResponse:
        model = service.create_model(
            data=ModelConfigurationCreate(
                provider_id=payload.provider_id,
                model_name=payload.model_name,
                model_type=payload.model_type,
                configuration=payload.configuration,
                allow_listed=payload.allow_listed,
                fallback_model_id=payload.fallback_model_id,
                cost_limit_daily_usd=payload.cost_limit_daily_usd,
                is_default=payload.is_default,
                status=payload.status,
            ),
            actor_user_id=claims.user_id,
            trace_id=request.headers.get("x-request-id"),
        )
        return _model_configuration_response(model)

    @app.patch("/admin/models/{model_id}", response_model=ModelConfigurationResponse)
    async def update_admin_model(
        model_id: UUID,
        payload: ModelConfigurationUpdateRequest,
        request: Request,
        claims: Annotated[AccessTokenClaims, Depends(get_current_claims)],
        _: Annotated[UserPrincipal, Depends(require_permission(Permission.MODELS_MANAGE))],
        service: Annotated[ProviderAdminService, Depends(provider_admin_service)],
    ) -> ModelConfigurationResponse:
        model = service.update_model(
            model_id=model_id,
            data=ModelConfigurationUpdate(
                model_name=payload.model_name,
                configuration=payload.configuration,
                allow_listed=payload.allow_listed,
                fallback_model_id=payload.fallback_model_id,
                cost_limit_daily_usd=payload.cost_limit_daily_usd,
                is_default=payload.is_default,
                status=payload.status,
            ),
            actor_user_id=claims.user_id,
            trace_id=request.headers.get("x-request-id"),
        )
        return _model_configuration_response(model)

    @app.post("/authorization/documents/approve", response_model=AuthorizationCheckResponse)
    async def authorize_document_approval(
        payload: DocumentApprovalAuthorizationRequest,
        request: Request,
        claims: Annotated[AccessTokenClaims, Depends(get_current_claims)],
        service: Annotated[RbacService, Depends(rbac_service)],
    ) -> AuthorizationCheckResponse:
        service.assert_can_approve_document(
            actor_user_id=claims.user_id,
            document_created_by=payload.document_created_by,
            trace_id=request.headers.get("x-request-id"),
        )
        return AuthorizationCheckResponse(status="ok")

    @app.get("/admin/audit-logs", response_model=AuditLogListResponse)
    async def list_audit_logs(
        _: Annotated[UserPrincipal, Depends(require_permission(Permission.AUDIT_READ))],
        service: Annotated[AuditService, Depends(audit_service)],
        actor_user_id: UUID | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        resource_id: UUID | None = None,
        outcome: str | None = None,
        request_id: str | None = None,
        trace_id: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        limit: int = 100,
    ) -> AuditLogListResponse:
        query = AuditLogQuery(
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome=_audit_outcome(outcome),
            request_id=request_id,
            trace_id=trace_id,
            created_from=created_from,
            created_to=created_to,
            limit=limit,
        )
        return AuditLogListResponse(
            records=[_audit_log_response(record) for record in service.list_records(query)]
        )

    @app.get("/admin/audit-logs/export")
    async def export_audit_logs(
        _: Annotated[UserPrincipal, Depends(require_permission(Permission.AUDIT_EXPORT))],
        service: Annotated[AuditService, Depends(audit_service)],
        actor_user_id: UUID | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        resource_id: UUID | None = None,
        outcome: str | None = None,
        request_id: str | None = None,
        trace_id: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        limit: int = 1000,
    ) -> Response:
        query = AuditLogQuery(
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome=_audit_outcome(outcome),
            request_id=request_id,
            trace_id=trace_id,
            created_from=created_from,
            created_to=created_to,
            limit=limit,
        )
        return Response(
            content=service.export_jsonl(query),
            media_type="application/x-ndjson",
            headers={"content-disposition": "attachment; filename=audit-logs.ndjson"},
        )

    @app.post("/admin/prompts", response_model=PromptResponse, status_code=201)
    async def create_prompt(
        payload: PromptCreateRequest,
        request: Request,
        principal: Annotated[UserPrincipal, Depends(require_permission(Permission.PROMPTS_MANAGE))],
        service: Annotated[PromptRegistryService, Depends(prompt_registry_service)],
    ) -> PromptResponse:
        prompt = service.create_prompt(
            data=_prompt_create_from_request(payload),
            actor_user_id=principal.id,
            trace_id=request.headers.get("x-request-id"),
        )
        return _prompt_response(prompt)

    @app.get("/admin/prompts", response_model=PromptListResponse)
    async def list_prompts(
        _: Annotated[UserPrincipal, Depends(require_permission(Permission.PROMPTS_MANAGE))],
        service: Annotated[PromptRegistryService, Depends(prompt_registry_service)],
        name: str | None = None,
    ) -> PromptListResponse:
        return PromptListResponse(
            prompts=[_prompt_response(prompt) for prompt in service.list_prompts(name=name)]
        )

    @app.get("/admin/prompts/compare", response_model=PromptComparisonResponse)
    async def compare_prompt_versions(
        _: Annotated[UserPrincipal, Depends(require_permission(Permission.PROMPTS_MANAGE))],
        service: Annotated[PromptRegistryService, Depends(prompt_registry_service)],
        prompt_name: str,
        from_version: str,
        to_version: str,
    ) -> PromptComparisonResponse:
        result = service.compare_versions(
            prompt_name=prompt_name,
            from_version=from_version,
            to_version=to_version,
        )
        return _prompt_comparison_response(result)

    @app.post("/admin/prompts/rollback", response_model=PromptStatusChangeResponse)
    async def rollback_prompt(
        payload: PromptRollbackRequest,
        request: Request,
        principal: Annotated[UserPrincipal, Depends(require_permission(Permission.PROMPTS_MANAGE))],
        service: Annotated[PromptRegistryService, Depends(prompt_registry_service)],
    ) -> PromptStatusChangeResponse:
        result = service.rollback_prompt(
            prompt_name=payload.prompt_name,
            target_version=payload.target_version,
            actor_user_id=principal.id,
            trace_id=request.headers.get("x-request-id"),
        )
        return _prompt_status_change_response(result)

    @app.post("/admin/prompts/bootstrap")
    async def bootstrap_prompt_registry(
        request: Request,
        principal: Annotated[UserPrincipal, Depends(require_permission(Permission.PROMPTS_MANAGE))],
        service: Annotated[PromptRegistryService, Depends(prompt_registry_service)],
    ) -> dict[str, str]:
        bootstrap_registry_defaults(service, actor_user_id=principal.id)
        return {"status": "ok"}

    @app.get("/admin/prompts/{prompt_id}", response_model=PromptResponse)
    async def get_prompt(
        prompt_id: UUID,
        _: Annotated[UserPrincipal, Depends(require_permission(Permission.PROMPTS_MANAGE))],
        service: Annotated[PromptRegistryService, Depends(prompt_registry_service)],
    ) -> PromptResponse:
        return _prompt_response(service.get_prompt(prompt_id=prompt_id))

    @app.post("/admin/prompts/{prompt_id}/approve", response_model=PromptStatusChangeResponse)
    async def approve_prompt(
        prompt_id: UUID,
        request: Request,
        principal: Annotated[UserPrincipal, Depends(require_permission(Permission.PROMPTS_MANAGE))],
        service: Annotated[PromptRegistryService, Depends(prompt_registry_service)],
    ) -> PromptStatusChangeResponse:
        result = service.approve_prompt(
            prompt_id=prompt_id,
            actor_user_id=principal.id,
            trace_id=request.headers.get("x-request-id"),
        )
        return _prompt_status_change_response(result)

    def guest_service() -> GuestService:
        from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

        return GuestService(
            SQLAlchemyUnitOfWork(session_factory),
            auth_service=AuthService(
                SQLAlchemyUnitOfWork(session_factory),
                signing_secret=settings.auth_jwt_secret.get_secret_value(),
            ),
            ttl_minutes=settings.guest_session_ttl_minutes,
            message_quota=settings.guest_message_quota,
            enabled=settings.enable_guest_mode,
        )

    @app.exception_handler(GuestError)
    async def guest_error_handler(request: Request, exc: GuestError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.post("/auth/guest/start", response_model=GuestSessionResponse)
    async def start_guest_session(
        request: Request,
        service: Annotated[GuestService, Depends(guest_service)],
    ) -> GuestSessionResponse:
        info = service.start_session(
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            trace_id=request.headers.get("x-request-id"),
        )
        return GuestSessionResponse(
            guest_token=info.token,
            expires_at=info.expires_at.isoformat(),
            message_quota=info.message_quota,
            messages_used=info.messages_used,
        )

    @app.post("/auth/guest/convert", response_model=AuthResponse, status_code=201)
    async def convert_guest_to_user(
        payload: GuestConversionRequest,
        request: Request,
        service: Annotated[GuestService, Depends(guest_service)],
    ) -> AuthResponse:
        result = service.convert_to_user(
            token=payload.guest_token,
            email=str(payload.email),
            password=payload.password,
            display_name=payload.display_name,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            trace_id=request.headers.get("x-request-id"),
        )
        return _auth_response(result)

    @app.post("/chat/stream")
    async def stream_chat(
        payload: ChatStreamRequest,
        request: Request,
        chat_service: Annotated[ChatStreamingService, Depends(chat_streaming_service)],
        guest_service: Annotated[GuestService, Depends(guest_service)],
        auth_service: Annotated[AuthService, Depends(auth_service)],
        rbac_service: Annotated[RbacService, Depends(rbac_service)],
        authorization: Annotated[str | None, Header()] = None,
    ) -> StreamingResponse:
        detect_prompt_injection(payload.question)
        payload.question = sanitize_xss(payload.question)
        chat_request = _build_chat_request(
            payload=payload,
            request=request,
            authorization=authorization,
            auth_service=auth_service,
            rbac_service=rbac_service,
            guest_service=guest_service,
        )
        handle = chat_service.start_stream(chat_request)

        async def event_stream() -> Any:
            try:
                async for event in handle.events:
                    yield sse_encode(event)
            except asyncio.CancelledError:
                handle.cancel()
                raise
            finally:
                if not handle.task.done():
                    handle.cancel()

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "X-Stream-Id": handle.stream_id,
            },
        )

    @app.get("/chat/streams/{stream_id}")
    async def reconnect_chat_stream(
        stream_id: str,
        chat_service: Annotated[ChatStreamingService, Depends(chat_streaming_service)],
        auth_service: Annotated[AuthService, Depends(auth_service)],
        rbac_service: Annotated[RbacService, Depends(rbac_service)],
        guest_service: Annotated[GuestService, Depends(guest_service)],
        authorization: Annotated[str | None, Header()] = None,
        last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
    ) -> StreamingResponse:
        _assert_chat_stream_access(
            authorization=authorization,
            auth_service=auth_service,
            rbac_service=rbac_service,
            guest_service=guest_service,
        )
        snapshot = chat_service.get_snapshot(
            stream_id=stream_id,
            last_event_id=last_event_id,
        )
        if not snapshot.events and not snapshot.completed:
            raise ChatStreamingError(
                "CHAT_STREAM_NOT_FOUND",
                "Chat stream not found.",
                status_code=404,
            )

        async def replay_stream() -> Any:
            for event in snapshot.events:
                yield sse_encode(event)

        return StreamingResponse(
            replay_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "X-Stream-Id": stream_id,
            },
        )

    @app.delete("/chat/streams/{stream_id}")
    async def cancel_chat_stream(
        stream_id: str,
        chat_service: Annotated[ChatStreamingService, Depends(chat_streaming_service)],
        auth_service: Annotated[AuthService, Depends(auth_service)],
        rbac_service: Annotated[RbacService, Depends(rbac_service)],
        guest_service: Annotated[GuestService, Depends(guest_service)],
        authorization: Annotated[str | None, Header()] = None,
    ) -> dict[str, str]:
        _assert_chat_stream_access(
            authorization=authorization,
            auth_service=auth_service,
            rbac_service=rbac_service,
            guest_service=guest_service,
        )
        if not chat_service.cancel_stream(stream_id=stream_id):
            raise ChatStreamingError(
                "CHAT_STREAM_NOT_FOUND",
                "Active chat stream not found.",
                status_code=404,
            )
        return {"status": "ok"}

    @app.get("/chat/conversations", response_model=ConversationListResponse)
    async def list_chat_conversations(
        request: Request,
        principal: Annotated[
            UserPrincipal, Depends(require_permission(Permission.CONVERSATIONS_MANAGE_OWN))
        ],
        service: Annotated[ConversationHistoryService, Depends(conversation_history_service)],
        q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ConversationListResponse:
        result = service.list_conversations(
            user_id=principal.id,
            query=q,
            limit=limit,
            offset=offset,
        )
        return _conversation_list_response(result)

    @app.get("/chat/conversations/{conversation_id}", response_model=ConversationDetailResponse)
    async def get_chat_conversation(
        conversation_id: UUID,
        principal: Annotated[
            UserPrincipal, Depends(require_permission(Permission.CONVERSATIONS_MANAGE_OWN))
        ],
        service: Annotated[ConversationHistoryService, Depends(conversation_history_service)],
    ) -> ConversationDetailResponse:
        detail = service.get_conversation(user_id=principal.id, conversation_id=conversation_id)
        return _conversation_detail_response(detail)

    @app.delete("/chat/conversations/{conversation_id}")
    async def delete_chat_conversation(
        conversation_id: UUID,
        request: Request,
        principal: Annotated[
            UserPrincipal, Depends(require_permission(Permission.CONVERSATIONS_MANAGE_OWN))
        ],
        service: Annotated[ConversationHistoryService, Depends(conversation_history_service)],
    ) -> dict[str, str]:
        service.delete_conversation(
            user_id=principal.id,
            conversation_id=conversation_id,
            trace_id=request.headers.get("x-request-id"),
        )
        return {"status": "ok"}

    @app.post("/chat/conversations/delete-all", response_model=ConversationDeleteAllResponse)
    async def delete_all_chat_conversations(
        request: Request,
        principal: Annotated[
            UserPrincipal, Depends(require_permission(Permission.CONVERSATIONS_MANAGE_OWN))
        ],
        service: Annotated[ConversationHistoryService, Depends(conversation_history_service)],
    ) -> ConversationDeleteAllResponse:
        result = service.delete_all_conversations(
            user_id=principal.id,
            trace_id=request.headers.get("x-request-id"),
        )
        return ConversationDeleteAllResponse(deleted_count=result.deleted_count)

    @app.get("/saved-answers", response_model=SavedAnswerListResponse)
    async def list_saved_answers(
        principal: Annotated[
            UserPrincipal, Depends(require_permission(Permission.CONVERSATIONS_MANAGE_OWN))
        ],
        service: Annotated[SavedAnswerService, Depends(saved_answer_service)],
        limit: int = 50,
        offset: int = 0,
    ) -> SavedAnswerListResponse:
        result = service.list_saved_answers(user_id=principal.id, limit=limit, offset=offset)
        return _saved_answer_list_response(result)

    @app.post("/saved-answers", response_model=SavedAnswerResponse, status_code=201)
    async def save_answer(
        payload: SavedAnswerCreateRequest,
        request: Request,
        principal: Annotated[
            UserPrincipal, Depends(require_permission(Permission.CONVERSATIONS_MANAGE_OWN))
        ],
        service: Annotated[SavedAnswerService, Depends(saved_answer_service)],
    ) -> SavedAnswerResponse:
        saved = service.save_answer(
            user_id=principal.id,
            answer_id=payload.answer_id,
            trace_id=request.headers.get("x-request-id"),
        )
        return _saved_answer_response(saved)

    @app.delete("/saved-answers/{saved_answer_id}")
    async def unsave_answer(
        saved_answer_id: UUID,
        request: Request,
        principal: Annotated[
            UserPrincipal, Depends(require_permission(Permission.CONVERSATIONS_MANAGE_OWN))
        ],
        service: Annotated[SavedAnswerService, Depends(saved_answer_service)],
    ) -> dict[str, str]:
        service.unsave_answer(
            user_id=principal.id,
            saved_answer_id=saved_answer_id,
            trace_id=request.headers.get("x-request-id"),
        )
        return {"status": "ok"}

    @app.post("/feedback", response_model=FeedbackResponse, status_code=201)
    async def submit_feedback(
        payload: FeedbackSubmitRequest,
        request: Request,
        principal: Annotated[
            UserPrincipal, Depends(require_permission(Permission.FEEDBACK_CREATE))
        ],
        service: Annotated[FeedbackService, Depends(feedback_service)],
    ) -> FeedbackResponse:
        submitted = service.submit_feedback(
            user_id=principal.id,
            submission=FeedbackSubmit(
                answer_id=payload.answer_id,
                category=payload.category,
                notes=payload.notes,
                citation_id=payload.citation_id,
            ),
            trace_id=request.headers.get("x-request-id"),
        )
        return _feedback_response(submitted)

    @app.get("/feedback/{feedback_id}", response_model=FeedbackResponse)
    async def get_feedback(
        feedback_id: UUID,
        principal: Annotated[
            UserPrincipal, Depends(require_permission(Permission.FEEDBACK_CREATE))
        ],
        service: Annotated[FeedbackService, Depends(feedback_service)],
    ) -> FeedbackResponse:
        feedback = service.get_feedback(user_id=principal.id, feedback_id=feedback_id)
        return _feedback_response(feedback)

    # -- Admin Feedback Review Queue ----------------------------------------

    @app.get("/admin/feedback", response_model=FeedbackQueueListResponse)
    async def list_feedback_queue(
        request: Request,
        principal: Annotated[UserPrincipal, Depends(require_permission(Permission.FEEDBACK_READ))],
        service: Annotated[FeedbackReviewService, Depends(feedback_review_service)],
        status: str | None = Query(default=None),
        category: str | None = Query(default=None),
        priority: str | None = Query(default=None),
        severity: str | None = Query(default=None),
        reviewer_id: str | None = Query(default=None),
        unassigned_only: bool = Query(default=False),
        limit: int = Query(default=20, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> FeedbackQueueListResponse:
        result = service.list_queue(
            FeedbackQueueQuery(
                status=status,
                category=category,
                priority=priority,
                severity=severity,
                reviewer_id=reviewer_id,
                unassigned_only=unassigned_only,
                limit=limit,
                offset=offset,
            ),
            actor_user_id=principal.id,
            actor_permissions=principal.permissions,
        )
        return _feedback_queue_list_response(result)

    @app.get("/admin/feedback/{feedback_id}/review", response_model=FeedbackReviewDetailResponse)
    async def get_feedback_review_detail(
        feedback_id: UUID,
        principal: Annotated[UserPrincipal, Depends(require_permission(Permission.FEEDBACK_READ))],
        service: Annotated[FeedbackReviewService, Depends(feedback_review_service)],
    ) -> FeedbackReviewDetailResponse:
        detail = service.get_detail(
            feedback_id,
            actor_permissions=principal.permissions,
        )
        return _feedback_review_detail_response(detail)

    @app.put(
        "/admin/feedback/{feedback_id}/assign",
        response_model=FeedbackReviewDetailResponse,
    )
    async def assign_feedback_reviewer(
        feedback_id: UUID,
        payload: FeedbackAssignRequestPayload,
        request: Request,
        principal: Annotated[
            UserPrincipal, Depends(require_permission(Permission.FEEDBACK_MANAGE))
        ],
        service: Annotated[FeedbackReviewService, Depends(feedback_review_service)],
    ) -> FeedbackReviewDetailResponse:
        detail = service.assign(
            feedback_id,
            FeedbackAssignRequest(reviewer_id=payload.reviewer_id),
            actor_user_id=principal.id,
            actor_permissions=principal.permissions,
            trace_id=request.headers.get("x-request-id"),
        )
        return _feedback_review_detail_response(detail)

    @app.patch(
        "/admin/feedback/{feedback_id}/classify",
        response_model=FeedbackReviewDetailResponse,
    )
    async def classify_feedback(
        feedback_id: UUID,
        payload: FeedbackClassifyRequestPayload,
        request: Request,
        principal: Annotated[
            UserPrincipal, Depends(require_permission(Permission.FEEDBACK_MANAGE))
        ],
        service: Annotated[FeedbackReviewService, Depends(feedback_review_service)],
    ) -> FeedbackReviewDetailResponse:
        detail = service.classify(
            feedback_id,
            FeedbackClassifyRequest(
                root_cause=payload.root_cause,
                priority=payload.priority,
                severity=payload.severity,
                reviewer_notes=payload.reviewer_notes,
            ),
            actor_user_id=principal.id,
            actor_permissions=principal.permissions,
            trace_id=request.headers.get("x-request-id"),
        )
        return _feedback_review_detail_response(detail)

    @app.post(
        "/admin/feedback/{feedback_id}/resolve",
        response_model=FeedbackReviewDetailResponse,
    )
    async def resolve_feedback(
        feedback_id: UUID,
        payload: FeedbackResolveRequestPayload,
        request: Request,
        principal: Annotated[
            UserPrincipal, Depends(require_permission(Permission.FEEDBACK_MANAGE))
        ],
        service: Annotated[FeedbackReviewService, Depends(feedback_review_service)],
    ) -> FeedbackReviewDetailResponse:
        detail = service.resolve(
            feedback_id,
            FeedbackResolveRequest(
                resolution=payload.resolution,
                dismissed=payload.dismissed,
            ),
            actor_user_id=principal.id,
            actor_permissions=principal.permissions,
            trace_id=request.headers.get("x-request-id"),
        )
        return _feedback_review_detail_response(detail)

    # -- Evaluation Dashboard and Run Comparison ----------------------------

    @app.get("/admin/evaluation/runs", response_model=EvaluationRunListResponse)
    async def list_evaluation_runs(
        principal: Annotated[
            UserPrincipal, Depends(require_permission(Permission.EVALUATIONS_READ))
        ],
        service: Annotated[BenchmarkComparisonService, Depends(benchmark_comparison_service)],
        dataset_id: UUID | None = Query(default=None),  # noqa: B008
    ) -> EvaluationRunListResponse:
        runs = service.list_runs(permissions=principal.permissions, dataset_id=dataset_id)
        return EvaluationRunListResponse(runs=[_evaluation_run_info_response(r) for r in runs])

    @app.get("/admin/evaluation/runs/{run_id}", response_model=EvaluationRunInfoResponse)
    async def get_evaluation_run(
        run_id: UUID,
        principal: Annotated[
            UserPrincipal, Depends(require_permission(Permission.EVALUATIONS_READ))
        ],
        service: Annotated[BenchmarkComparisonService, Depends(benchmark_comparison_service)],
    ) -> EvaluationRunInfoResponse:
        run = service.get_run(run_id, permissions=principal.permissions)
        return _evaluation_run_info_response(run)

    @app.get("/admin/evaluation/compare", response_model=RunComparisonReportResponse)
    async def compare_evaluation_runs(
        principal: Annotated[
            UserPrincipal, Depends(require_permission(Permission.EVALUATIONS_READ))
        ],
        service: Annotated[BenchmarkComparisonService, Depends(benchmark_comparison_service)],
        base_run_id: UUID = Query(...),  # noqa: B008
        target_run_id: UUID = Query(...),  # noqa: B008
    ) -> RunComparisonReportResponse:
        report = service.compare_runs(
            base_run_id=base_run_id,
            target_run_id=target_run_id,
            permissions=principal.permissions,
        )
        return _run_comparison_report_response(report)

    @app.post("/admin/incidents", response_model=IncidentResponse, status_code=201)
    async def create_incident(
        payload: IncidentCreateRequest,
        request: Request,
        principal: Annotated[
            UserPrincipal, Depends(require_permission(Permission.FEEDBACK_MANAGE))
        ],
        service: Annotated[IncidentManagementService, Depends(incident_management_service)],
    ) -> IncidentResponse:
        incident, idempotent = service.create(
            IncidentCreate(**payload.model_dump()),
            actor_user_id=principal.id,
            permissions=principal.permissions,
            trace_id=request.headers.get("x-request-id"),
        )
        return _incident_response(incident, idempotent=idempotent)

    @app.post("/admin/incidents/{incident_id}/transition", response_model=IncidentResponse)
    async def transition_incident(
        incident_id: UUID,
        payload: IncidentTransitionRequest,
        request: Request,
        principal: Annotated[
            UserPrincipal, Depends(require_permission(Permission.FEEDBACK_MANAGE))
        ],
        service: Annotated[IncidentManagementService, Depends(incident_management_service)],
    ) -> IncidentResponse:
        return _incident_response(
            service.transition(
                incident_id,
                target_status=payload.target_status,
                reason=payload.reason,
                actor_user_id=principal.id,
                permissions=principal.permissions,
                base_row_version=payload.base_row_version,
                trace_id=request.headers.get("x-request-id"),
            )
        )

    @app.put("/admin/incidents/{incident_id}/owner", response_model=IncidentResponse)
    async def assign_incident_owner(
        incident_id: UUID,
        payload: IncidentAssignRequest,
        request: Request,
        principal: Annotated[
            UserPrincipal, Depends(require_permission(Permission.FEEDBACK_MANAGE))
        ],
        service: Annotated[IncidentManagementService, Depends(incident_management_service)],
    ) -> IncidentResponse:
        return _incident_response(
            service.assign(
                incident_id,
                owner_id=payload.owner_id,
                actor_user_id=principal.id,
                permissions=principal.permissions,
                trace_id=request.headers.get("x-request-id"),
            )
        )

    @app.get("/admin/incidents/{incident_id}/timeline", response_model=IncidentTimelineResponse)
    async def incident_timeline(
        incident_id: UUID,
        principal: Annotated[UserPrincipal, Depends(require_permission(Permission.FEEDBACK_READ))],
        service: Annotated[IncidentManagementService, Depends(incident_management_service)],
    ) -> IncidentTimelineResponse:
        events = service.timeline(incident_id, permissions=principal.permissions)
        return IncidentTimelineResponse(
            events=[
                {
                    "event_type": item.event_type,
                    "status_from": item.status_from,
                    "status_to": item.status_to,
                    "actor_user_id": str(item.actor_user_id) if item.actor_user_id else None,
                    "details": item.details,
                    "created_at": item.created_at.isoformat(),
                }
                for item in events
            ]
        )

    @app.post(
        "/admin/incidents/{incident_id}/regression-cases",
        response_model=IncidentRegressionCreateResponse,
        status_code=201,
    )
    async def create_incident_regression_case(
        incident_id: UUID,
        payload: IncidentRegressionCreateRequest,
        request: Request,
        principal: Annotated[
            UserPrincipal, Depends(require_permission(Permission.FEEDBACK_MANAGE))
        ],
        service: Annotated[IncidentRegressionService, Depends(incident_regression_service)],
    ) -> IncidentRegressionCreateResponse:
        result = service.create(
            incident_id,
            payload.dataset_id,
            payload.case,
            actor_user_id=principal.id,
            permissions=principal.permissions,
            trace_id=request.headers.get("x-request-id"),
        )
        return _incident_regression_response(result)

    @app.post("/admin/answers/{answer_id}/invalidate", response_model=AnswerInvalidationResponse)
    async def invalidate_answer(
        answer_id: UUID,
        payload: AnswerInvalidateRequest,
        request: Request,
        principal: Annotated[
            UserPrincipal, Depends(require_permission(Permission.ANSWERS_INVALIDATE))
        ],
        service: Annotated[AnswerInvalidationService, Depends(answer_invalidation_service)],
    ) -> AnswerInvalidationResponse:
        return _answer_invalidation_response(
            service.invalidate(
                answer_id=answer_id,
                reason=payload.reason,
                idempotency_key=payload.idempotency_key,
                incident_id=payload.incident_id,
                citation_id=payload.citation_id,
                source_id=payload.source_id,
                actor_user_id=principal.id,
                permissions=principal.permissions,
                trace_id=request.headers.get("x-request-id"),
            )
        )

    @app.get("/admin/answers/affected", response_model=AffectedAnswerPageResponse)
    async def discover_affected_answers(
        request: Request,
        principal: Annotated[UserPrincipal, Depends(require_permission(Permission.ANSWERS_REVIEW))],
        service: Annotated[AnswerInvalidationService, Depends(answer_invalidation_service)],
        citation_id: UUID | None = None,
        source_id: UUID | None = None,
        limit: int = Query(default=100, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> AffectedAnswerPageResponse:
        return _affected_answer_page_response(
            service.discover(
                permissions=principal.permissions,
                citation_id=citation_id,
                source_id=source_id,
                limit=limit,
                offset=offset,
                actor_user_id=principal.id,
                trace_id=request.headers.get("x-request-id"),
            )
        )

    @app.get("/citations/{citation_id}", response_model=CitationDetailResponse)
    async def get_citation_detail(
        citation_id: str,
        service: Annotated[CitationRegistryService, Depends(citation_registry_service)],
    ) -> CitationDetailResponse:
        detail = service.get_citation_detail(_parse_citation_ref(citation_id))
        return _citation_detail_response(detail)

    @app.get("/sources/{source_id}", response_model=PublicSourceDetailResponse)
    async def get_public_source_detail(
        source_id: UUID,
        service: Annotated[SourceService, Depends(source_service)],
    ) -> PublicSourceDetailResponse:
        source = service.get_by_id(source_id=source_id)
        return PublicSourceDetailResponse(
            source=_source_response(source),
            warnings=_public_source_warnings(source),
        )

    @app.get("/auth/mfa/status", response_model=MfaStatusResponse)
    async def mfa_status(
        claims: Annotated[AccessTokenClaims, Depends(get_current_claims)],
        service: Annotated[MfaService, Depends(mfa_service)],
    ) -> MfaStatusResponse:
        return MfaStatusResponse(
            enrolled=service.is_enrolled(user_id=claims.user_id),
            privileged_role_required=service.has_privileged_role(user_id=claims.user_id),
        )

    @app.post("/auth/mfa/enroll", response_model=MfaEnrollmentResponse)
    async def mfa_enroll(
        request: Request,
        claims: Annotated[AccessTokenClaims, Depends(get_current_claims)],
        service: Annotated[MfaService, Depends(mfa_service)],
    ) -> MfaEnrollmentResponse:
        enrollment = service.start_enrollment(
            user_id=claims.user_id,
            trace_id=request.headers.get("x-request-id"),
        )
        return _enrollment_response(enrollment)

    @app.post("/auth/mfa/confirm")
    async def mfa_confirm(
        payload: MfaConfirmRequest,
        request: Request,
        claims: Annotated[AccessTokenClaims, Depends(get_current_claims)],
        service: Annotated[MfaService, Depends(mfa_service)],
    ) -> dict[str, str]:
        service.confirm_enrollment(
            user_id=claims.user_id,
            code=payload.code,
            trace_id=request.headers.get("x-request-id"),
        )
        return {"status": "ok"}

    @app.post("/auth/mfa/challenge/start", response_model=MfaChallengeStartResponse)
    async def mfa_challenge_start(
        request: Request,
        claims: Annotated[AccessTokenClaims, Depends(get_current_claims)],
        service: Annotated[MfaService, Depends(mfa_service)],
    ) -> MfaChallengeStartResponse:
        challenge = service.start_challenge(
            user_id=claims.user_id,
            trace_id=request.headers.get("x-request-id"),
        )
        return MfaChallengeStartResponse(
            challenge_id=challenge.challenge_id,
            expires_at=challenge.expires_at.isoformat(),
        )

    @app.post("/auth/mfa/challenge/verify")
    async def mfa_challenge_verify(
        payload: MfaChallengeVerifyRequest,
        request: Request,
        claims: Annotated[AccessTokenClaims, Depends(get_current_claims)],
        service: Annotated[MfaService, Depends(mfa_service)],
    ) -> dict[str, str]:
        service.verify_challenge(
            user_id=claims.user_id,
            challenge_id=payload.challenge_id,
            code=payload.code,
            trace_id=request.headers.get("x-request-id"),
        )
        return {"status": "ok"}

    @app.post("/auth/mfa/challenge/recovery")
    async def mfa_challenge_recovery(
        payload: MfaRecoveryCodeRequest,
        request: Request,
        claims: Annotated[AccessTokenClaims, Depends(get_current_claims)],
        service: Annotated[MfaService, Depends(mfa_service)],
    ) -> dict[str, str]:
        service.consume_recovery_code(
            user_id=claims.user_id,
            challenge_id=payload.challenge_id,
            recovery_code=payload.recovery_code,
            trace_id=request.headers.get("x-request-id"),
        )
        return {"status": "ok"}

    @app.post("/auth/mfa/reset", response_model=MfaEnrollmentResponse)
    async def mfa_reset(
        payload: MfaResetRequest,
        request: Request,
        claims: Annotated[AccessTokenClaims, Depends(get_current_claims)],
        service: Annotated[MfaService, Depends(mfa_service)],
    ) -> MfaEnrollmentResponse:
        enrollment = service.reset_mfa(
            user_id=claims.user_id,
            channel=payload.channel,
            channel_proof=payload.proof,
            trace_id=request.headers.get("x-request-id"),
        )
        return _enrollment_response(enrollment)

    @app.post("/auth/mfa/recovery/rotate", response_model=MfaRecoveryRotateResponse)
    async def mfa_recovery_rotate(
        request: Request,
        claims: Annotated[AccessTokenClaims, Depends(get_current_claims)],
        service: Annotated[MfaService, Depends(mfa_service)],
    ) -> MfaRecoveryRotateResponse:
        codes = service.rotate_recovery_codes(
            user_id=claims.user_id,
            trace_id=request.headers.get("x-request-id"),
        )
        return MfaRecoveryRotateResponse(recovery_codes=list(codes))

    @app.post("/documents", response_model=DocumentUploadResponse, status_code=201)
    async def register_document_upload(
        payload: DocumentUploadRequestModel,
        request: Request,
        claims: Annotated[AccessTokenClaims, Depends(get_current_claims)],
        _: Annotated[UserPrincipal, Depends(require_permission(Permission.DOCUMENTS_UPLOAD))],
        service: Annotated[DocumentUploadService, Depends(document_upload_service)],
    ) -> DocumentUploadResponse:
        result = service.register_upload(
            data=_document_upload_request(payload),
            actor_user_id=claims.user_id,
            trace_id=request.headers.get("x-request-id"),
        )
        return _document_upload_response(result)

    @app.post(
        "/documents/{document_version_id}/scan",
        response_model=DocumentMalwareScanResponse,
    )
    async def scan_document_version(
        document_version_id: UUID,
        request: Request,
        claims: Annotated[AccessTokenClaims, Depends(get_current_claims)],
        _: Annotated[UserPrincipal, Depends(require_permission(Permission.DOCUMENTS_UPLOAD))],
        service: Annotated[DocumentUploadService, Depends(document_upload_service)],
    ) -> DocumentMalwareScanResponse:
        result = service.scan_document_version(
            document_version_id=document_version_id,
            actor_user_id=claims.user_id,
            trace_id=request.headers.get("x-request-id"),
        )
        return _document_malware_scan_response(result)

    @app.get(
        "/documents/{document_version_id}/parser-eligibility",
        response_model=ParserEligibilityResponse,
    )
    async def check_parser_eligibility(
        document_version_id: UUID,
        _: Annotated[UserPrincipal, Depends(require_permission(Permission.DOCUMENTS_UPLOAD))],
        service: Annotated[DocumentUploadService, Depends(document_upload_service)],
    ) -> ParserEligibilityResponse:
        service.assert_parser_allowed(document_version_id=document_version_id)
        return ParserEligibilityResponse(
            document_version_id=str(document_version_id),
            parser_eligible=True,
        )

    @app.post(
        "/documents/{document_version_id}/parse",
        response_model=DocumentParseResponse,
    )
    async def parse_document_version(
        document_version_id: UUID,
        request: Request,
        claims: Annotated[AccessTokenClaims, Depends(get_current_claims)],
        _: Annotated[UserPrincipal, Depends(require_permission(Permission.DOCUMENTS_UPLOAD))],
        upload_service: Annotated[DocumentUploadService, Depends(document_upload_service)],
    ) -> DocumentParseResponse:
        upload_service.assert_parser_allowed(document_version_id=document_version_id)
        registry = ParserRegistry()
        with upload_service.uow:
            version = upload_service.uow.documents.get_version_by_id(document_version_id)
            if version is None:
                raise DocumentProcessingError(
                    "DOCUMENT_VERSION_NOT_FOUND",
                    "Document version not found.",
                    status_code=404,
                )
            metadata = version.metadata_json or {}
            content_type = str(metadata.get("content_type", "application/octet-stream"))
            filename = str(metadata.get("filename", "uploaded-file"))
            content = upload_service.storage.get_private_bytes(key=version.original_file_key or "")
        result = registry.parse(
            content=content,
            filename=filename,
            content_type=content_type,
        )
        return DocumentParseResponse(
            document_version_id=str(document_version_id),
            parser_name=result.parser_name,
            parser_version=result.parser_version,
            framework_version=result.framework_version,
            content_type=result.content_type,
            sections=[
                ParsedSectionResponse(
                    content=s.content,
                    heading=s.heading,
                    page=s.page,
                    section_index=s.section_index,
                    content_type=s.content_type,
                    metadata=s.metadata,
                )
                for s in result.sections
            ],
            warnings=[
                ParseWarningResponse(
                    category=w.category,
                    message=w.message,
                    location=w.location,
                )
                for w in result.warnings
            ],
            page_count=result.page_count,
            metadata=result.metadata,
        )

    @app.post("/admin/sources", response_model=SourceResponse, status_code=201)
    async def create_source(
        payload: SourceCreateRequest,
        request: Request,
        claims: Annotated[AccessTokenClaims, Depends(get_current_claims)],
        _: Annotated[UserPrincipal, Depends(require_permission(Permission.LICENSES_MANAGE))],
        service: Annotated[SourceService, Depends(source_service)],
    ) -> SourceResponse:
        source = service.create(
            name=payload.name,
            source_type=payload.source_type,
            language=payload.language,
            reliability_level=payload.reliability_level,
            owner=payload.owner,
            website=payload.website,
            country=payload.country,
            is_active=payload.is_active,
            created_by=claims.user_id,
            trace_id=request.headers.get("x-request-id"),
        )
        return _source_response(source)

    @app.get("/admin/sources/{source_id}", response_model=SourceResponse)
    async def get_source(
        source_id: UUID,
        _: Annotated[UserPrincipal, Depends(require_permission(Permission.LICENSES_READ))],
        service: Annotated[SourceService, Depends(source_service)],
    ) -> SourceResponse:
        source = service.get_by_id(source_id=source_id)
        return _source_response(source)

    @app.patch("/admin/sources/{source_id}", response_model=SourceResponse)
    async def update_source(
        source_id: UUID,
        payload: SourceUpdateRequest,
        request: Request,
        claims: Annotated[AccessTokenClaims, Depends(get_current_claims)],
        _: Annotated[UserPrincipal, Depends(require_permission(Permission.LICENSES_MANAGE))],
        service: Annotated[SourceService, Depends(source_service)],
    ) -> SourceResponse:
        source = service.update(
            source_id=source_id,
            name=payload.name,
            source_type=payload.source_type,
            owner=payload.owner,
            website=payload.website,
            language=payload.language,
            country=payload.country,
            reliability_level=payload.reliability_level,
            updated_by=claims.user_id,
            trace_id=request.headers.get("x-request-id"),
        )
        return _source_response(source)

    @app.post("/admin/sources/{source_id}/suspend", response_model=SourceResponse)
    async def suspend_source(
        source_id: UUID,
        request: Request,
        claims: Annotated[AccessTokenClaims, Depends(get_current_claims)],
        _: Annotated[UserPrincipal, Depends(require_permission(Permission.LICENSES_MANAGE))],
        service: Annotated[SourceService, Depends(source_service)],
    ) -> SourceResponse:
        source = service.suspend(
            source_id=source_id,
            actor_user_id=claims.user_id,
            trace_id=request.headers.get("x-request-id"),
        )
        return _source_response(source)

    @app.get("/admin/sources", response_model=SourceListResponse)
    async def search_sources(
        _: Annotated[UserPrincipal, Depends(require_permission(Permission.LICENSES_READ))],
        service: Annotated[SourceService, Depends(source_service)],
        name: str | None = None,
        source_type: str | None = None,
        language: str | None = None,
        country: str | None = None,
        is_active: bool | None = None,
        reliability_level_min: int | None = None,
        reliability_level_max: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> SourceListResponse:
        query = SourceSearchQuery(
            name=name,
            source_type=source_type,
            language=language,
            country=country,
            is_active=is_active,
            reliability_level_min=reliability_level_min,
            reliability_level_max=reliability_level_max,
            limit=limit,
            offset=offset,
        )
        sources = service.search(query)
        return SourceListResponse(sources=[_source_response(source) for source in sources])

    @app.post(
        "/admin/sources/{source_id}/licenses",
        response_model=LicenseResponse,
        status_code=201,
    )
    async def create_license(
        source_id: UUID,
        payload: LicenseCreateRequest,
        request: Request,
        claims: Annotated[AccessTokenClaims, Depends(get_current_claims)],
        _: Annotated[UserPrincipal, Depends(require_permission(Permission.LICENSES_MANAGE))],
        service: Annotated[LicenseService, Depends(license_service)],
    ) -> LicenseResponse:
        license_record = service.create(
            source_id=source_id,
            data=_license_create(payload),
            created_by=claims.user_id,
            trace_id=request.headers.get("x-request-id"),
        )
        return _license_response(license_record)

    @app.get("/admin/sources/{source_id}/licenses", response_model=LicenseListResponse)
    async def list_source_licenses(
        source_id: UUID,
        _: Annotated[UserPrincipal, Depends(require_permission(Permission.LICENSES_READ))],
        service: Annotated[LicenseService, Depends(license_service)],
    ) -> LicenseListResponse:
        licenses = service.list_by_source(source_id=source_id)
        return LicenseListResponse(licenses=[_license_response(record) for record in licenses])

    @app.get("/admin/licenses/{license_id}", response_model=LicenseResponse)
    async def get_license(
        license_id: UUID,
        _: Annotated[UserPrincipal, Depends(require_permission(Permission.LICENSES_READ))],
        service: Annotated[LicenseService, Depends(license_service)],
    ) -> LicenseResponse:
        license_record = service.get_by_id(license_id=license_id)
        return _license_response(license_record)

    @app.post(
        "/admin/licenses/{license_id}/replace",
        response_model=LicenseResponse,
        status_code=201,
    )
    async def replace_license(
        license_id: UUID,
        payload: LicenseCreateRequest,
        request: Request,
        claims: Annotated[AccessTokenClaims, Depends(get_current_claims)],
        _: Annotated[UserPrincipal, Depends(require_permission(Permission.LICENSES_MANAGE))],
        service: Annotated[LicenseService, Depends(license_service)],
    ) -> LicenseResponse:
        replacement = service.replace(
            license_id=license_id,
            data=_license_create(payload),
            actor_user_id=claims.user_id,
            trace_id=request.headers.get("x-request-id"),
        )
        return _license_response(replacement)

    @app.get(
        "/admin/licenses/{license_id}/permission-document",
        response_model=PermissionDocumentResponse,
    )
    async def get_license_permission_document(
        license_id: UUID,
        request: Request,
        claims: Annotated[AccessTokenClaims, Depends(get_current_claims)],
        _: Annotated[UserPrincipal, Depends(require_permission(Permission.LICENSES_READ))],
        service: Annotated[LicenseService, Depends(license_service)],
    ) -> PermissionDocumentResponse:
        access = service.get_permission_document(
            license_id=license_id,
            actor_user_id=claims.user_id,
            trace_id=request.headers.get("x-request-id"),
        )
        return _permission_document_response(access)

    @app.post(
        "/admin/licenses/{license_id}/publication-authorization",
        response_model=PublicationAuthorizationResponse,
    )
    async def check_license_publication_authorization(
        license_id: UUID,
        request: Request,
        claims: Annotated[AccessTokenClaims, Depends(get_current_claims)],
        _: Annotated[UserPrincipal, Depends(require_permission(Permission.LICENSES_READ))],
        service: Annotated[LicenseService, Depends(license_service)],
    ) -> PublicationAuthorizationResponse:
        authorization = service.check_publication_authorization(
            license_id=license_id,
            actor_user_id=claims.user_id,
            trace_id=request.headers.get("x-request-id"),
        )
        return _publication_authorization_response(authorization)

    @app.get(
        "/admin/licenses/{license_id}/policy-decision",
        response_model=LicensePolicyDecisionResponse,
    )
    async def get_license_policy_decision(
        license_id: UUID,
        request: Request,
        claims: Annotated[AccessTokenClaims, Depends(get_current_claims)],
        _: Annotated[UserPrincipal, Depends(require_permission(Permission.LICENSES_READ))],
        service: Annotated[LicenseService, Depends(license_service)],
        workflow: str = "retrieval",
    ) -> LicensePolicyDecisionResponse:
        decision = service.decide_policy(
            license_id=license_id,
            workflow=workflow,
            actor_user_id=claims.user_id,
            trace_id=request.headers.get("x-request-id"),
        )
        return _license_policy_decision_response(decision)

    # ------------------------------------------------------------------
    # Review queue routes
    # ------------------------------------------------------------------

    def review_queue_service() -> ReviewQueueService:
        from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

        return ReviewQueueService(SQLAlchemyUnitOfWork(session_factory))

    def document_review_service() -> DocumentReviewService:
        from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

        return DocumentReviewService(SQLAlchemyUnitOfWork(session_factory))

    def scholar_approval_service() -> ScholarApprovalService:
        from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

        return ScholarApprovalService(SQLAlchemyUnitOfWork(session_factory))

    def document_publishing_service() -> DocumentPublishingService:
        from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

        return DocumentPublishingService(SQLAlchemyUnitOfWork(session_factory))

    def document_lifecycle_service() -> DocumentLifecycleService:
        from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

        return DocumentLifecycleService(SQLAlchemyUnitOfWork(session_factory))

    @app.exception_handler(ReviewQueueError)
    async def review_queue_error_handler(request: Request, exc: ReviewQueueError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(DocumentReviewError)
    async def document_review_error_handler(
        request: Request, exc: DocumentReviewError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(ScholarApprovalError)
    async def scholar_approval_error_handler(
        request: Request, exc: ScholarApprovalError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(DocumentPublishingError)
    async def document_publishing_error_handler(
        request: Request, exc: DocumentPublishingError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(DocumentLifecycleError)
    async def document_lifecycle_error_handler(
        request: Request, exc: DocumentLifecycleError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    def _review_task_summary_response(summary: ReviewTaskSummary) -> ReviewTaskSummaryResponse:
        return ReviewTaskSummaryResponse(
            id=str(summary.id),
            document_version_id=str(summary.document_version_id),
            document_id=str(summary.document_id),
            review_level=summary.review_level,
            status=summary.status,
            priority=summary.priority,
            category=summary.category,
            language=summary.language,
            madhhab=summary.madhhab,
            assigned_to=str(summary.assigned_to) if summary.assigned_to else None,
            due_at=summary.due_at.isoformat() if summary.due_at else None,
            created_at=summary.created_at.isoformat(),
            updated_at=summary.updated_at.isoformat(),
            document_title=summary.document_title,
            document_type=summary.document_type,
        )

    def _review_task_detail_response(detail: ReviewTaskDetail) -> ReviewTaskDetailResponse:
        return ReviewTaskDetailResponse(
            id=str(detail.id),
            document_version_id=str(detail.document_version_id),
            document_id=str(detail.document_id),
            review_level=detail.review_level,
            status=detail.status,
            priority=detail.priority,
            category=detail.category,
            language=detail.language,
            madhhab=detail.madhhab,
            assigned_to=str(detail.assigned_to) if detail.assigned_to else None,
            due_at=detail.due_at.isoformat() if detail.due_at else None,
            created_at=detail.created_at.isoformat(),
            updated_at=detail.updated_at.isoformat(),
            document_title=detail.document_title,
            document_type=detail.document_type,
            created_by=str(detail.created_by),
            original_file_key=detail.original_file_key,
            extracted_text_preview=detail.extracted_text_preview,
            filename=detail.filename,
            content_type=detail.content_type,
        )

    def _reviewer_dashboard_summary_response(
        summary: ReviewerDashboardSummary,
    ) -> ReviewerDashboardSummaryResponse:
        return ReviewerDashboardSummaryResponse(
            total_visible_count=summary.total_visible_count,
            pending_count=summary.pending_count,
            assigned_count=summary.assigned_count,
            overdue_count=summary.overdue_count,
            changes_requested_count=summary.changes_requested_count,
            feedback_open_count=summary.feedback_open_count,
        )

    def _reviewer_feedback_item_response(
        item: ReviewerFeedbackWorkItem,
    ) -> ReviewerFeedbackWorkItemResponse:
        return ReviewerFeedbackWorkItemResponse(
            id=str(item.id),
            category=item.category,
            status=item.status,
            answer_id=str(item.answer_id) if item.answer_id else None,
            citation_id=str(item.citation_id) if item.citation_id else None,
            created_at=item.created_at.isoformat(),
        )

    def _reviewer_dashboard_response(
        dashboard: ReviewerDashboardResult,
    ) -> ReviewerDashboardResponse:
        return ReviewerDashboardResponse(
            summary=_reviewer_dashboard_summary_response(dashboard.summary),
            queue=ReviewQueueListResponse(
                tasks=[_review_task_summary_response(task) for task in dashboard.queue.tasks],
                total_count=dashboard.queue.total_count,
                limit=dashboard.queue.limit,
                offset=dashboard.queue.offset,
                next_offset=dashboard.queue.next_offset,
            ),
            feedback_items=[
                _reviewer_feedback_item_response(item) for item in dashboard.feedback_items
            ],
        )

    def _review_comment_response(comment: ReviewCommentPublic) -> ReviewCommentResponse:
        return ReviewCommentResponse(
            id=str(comment.id),
            review_task_id=str(comment.review_task_id),
            author_id=str(comment.author_id),
            body=comment.body,
            anchor=dict(comment.anchor),
            created_at=comment.created_at.isoformat(),
        )

    def _review_draft_response(draft: ReviewDraft) -> ReviewDraftResponse:
        return ReviewDraftResponse(
            review_task_id=str(draft.review_task_id),
            document_version_id=str(draft.document_version_id),
            document_id=str(draft.document_id),
            source_id=str(draft.source_id) if draft.source_id else None,
            source_license_id=str(draft.source_license_id) if draft.source_license_id else None,
            canonical_id=draft.canonical_id,
            document_title=draft.document_title,
            document_type=draft.document_type,
            language=draft.language,
            madhhab=draft.madhhab,
            task_status=draft.task_status,
            task_row_version=draft.task_row_version,
            document_review_status=draft.document_review_status,
            original_file_key=draft.original_file_key,
            editable_text=draft.editable_text,
            editable_metadata=dict(draft.editable_metadata),
            latest_revision_number=draft.latest_revision_number,
            revisions=[_review_revision_response(revision) for revision in draft.revisions],
            comments=[_review_comment_response(comment) for comment in draft.comments],
        )

    def _review_revision_response(revision: ReviewRevisionPublic) -> ReviewRevisionResponse:
        return ReviewRevisionResponse(
            id=str(revision.id),
            review_task_id=str(revision.review_task_id),
            document_version_id=str(revision.document_version_id),
            actor_user_id=str(revision.actor_user_id),
            revision_number=revision.revision_number,
            base_task_row_version=revision.base_task_row_version,
            text_changed=revision.text_changed,
            metadata_changed_fields=list(revision.metadata_changed_fields),
            diff_text=revision.diff_text,
            created_at=revision.created_at.isoformat(),
        )

    def _review_edit_response(result: ReviewEditResult) -> ReviewEditResponse:
        return ReviewEditResponse(
            status="ok",
            task_row_version=result.task_row_version,
            revision=_review_revision_response(result.revision),
            editable_text=result.editable_text,
            editable_metadata=dict(result.editable_metadata),
        )

    def _review_decision_response(decision: ReviewDecisionPublic) -> ReviewDecisionResponse:
        return ReviewDecisionResponse(
            id=str(decision.id),
            review_task_id=str(decision.review_task_id),
            document_version_id=str(decision.document_version_id),
            actor_user_id=str(decision.actor_user_id),
            decision=decision.decision,
            reason=decision.reason,
            resulting_task_status=decision.resulting_task_status,
            resulting_document_status=decision.resulting_document_status,
            created_at=decision.created_at.isoformat(),
        )

    def _approval_response(approval: ApprovalPublic) -> ApprovalResponse:
        return ApprovalResponse(
            id=str(approval.id),
            document_version_id=str(approval.document_version_id),
            review_task_id=str(approval.review_task_id),
            approver_id=str(approval.approver_id),
            approval_level=approval.approval_level,
            content_risk=approval.content_risk,
            status=approval.status,
            reason=approval.reason,
            valid_until=approval.valid_until.isoformat() if approval.valid_until else None,
            revoked_at=approval.revoked_at.isoformat() if approval.revoked_at else None,
            revoked_by=str(approval.revoked_by) if approval.revoked_by else None,
            revoke_reason=approval.revoke_reason,
            created_at=approval.created_at.isoformat(),
        )

    def _approval_requirement_response(
        requirement: ApprovalRequirement,
    ) -> ApprovalRequirementResponse:
        return ApprovalRequirementResponse(
            document_version_id=str(requirement.document_version_id),
            content_risk=requirement.content_risk,
            required_levels=list(requirement.required_levels),
            satisfied_levels=list(requirement.satisfied_levels),
            missing_levels=list(requirement.missing_levels),
            ready_for_publish=requirement.ready_for_publish,
        )

    def _approval_list_response(result: ApprovalListResult) -> ApprovalListResponse:
        return ApprovalListResponse(
            document_version_id=str(result.document_version_id),
            approvals=[_approval_response(approval) for approval in result.approvals],
        )

    def _document_publish_response(result: DocumentPublishResult) -> DocumentPublishResponse:
        return DocumentPublishResponse(
            document_id=str(result.document_id),
            document_version_id=str(result.document_version_id),
            published_version_id=str(result.published_version_id),
            document_status=result.document_status,
            version_status=result.version_status,
            chunk_count=result.chunk_count,
            chunks=[
                PublishedChunkResponse(
                    id=str(chunk.id),
                    chunk_index=chunk.chunk_index,
                    content_hash=chunk.content_hash,
                    reference=chunk.reference,
                    is_published=chunk.is_published,
                )
                for chunk in result.chunks
            ],
            policy_version=result.policy_version,
            license_policy_version=result.license_policy_version,
            scholar_approval_policy_version=result.scholar_approval_policy_version,
            chunking_strategy_version=result.chunking_strategy_version,
            embedding_pipeline_version=result.embedding_pipeline_version,
            citation_pipeline_version=result.citation_pipeline_version,
            published_at=result.published_at.isoformat(),
            idempotent=result.idempotent,
        )

    def _affected_answer_response(answer: AffectedAnswerPublic) -> AffectedAnswerResponse:
        return AffectedAnswerResponse(
            id=str(answer.id),
            invalidated_at=answer.invalidated_at.isoformat(),
            warning=answer.warning,
        )

    def _document_lifecycle_response(
        result: DocumentLifecycleResult,
    ) -> DocumentLifecycleResponse:
        return DocumentLifecycleResponse(
            document_id=str(result.document_id),
            previous_published_version_id=str(result.previous_published_version_id)
            if result.previous_published_version_id
            else None,
            current_published_version_id=str(result.current_published_version_id)
            if result.current_published_version_id
            else None,
            document_status=result.document_status,
            affected_chunk_count=result.affected_chunk_count,
            affected_citation_count=result.affected_citation_count,
            affected_answer_count=result.affected_answer_count,
            affected_answers=[
                _affected_answer_response(answer) for answer in result.affected_answers
            ],
            policy_version=result.policy_version,
            changed_at=result.changed_at.isoformat(),
        )

    @app.get("/reviews/queue", response_model=ReviewQueueListResponse)
    async def list_review_queue(
        request: Request,
        principal: Annotated[
            UserPrincipal, Depends(require_permission(Permission.DOCUMENTS_REVIEW))
        ],
        service: Annotated[ReviewQueueService, Depends(review_queue_service)],
        language: str | None = None,
        madhhab: str | None = None,
        content_type: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        assigned_to: UUID | None = None,
        review_level: str | None = None,
        due_before: str | None = None,
        due_after: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ReviewQueueListResponse:
        query = ReviewQueueQuery(
            language=language,
            madhhab=madhhab,
            content_type=content_type,
            status=status,
            priority=priority,
            assigned_to=assigned_to,
            review_level=review_level,
            due_before=_parse_iso_datetime(due_before),
            due_after=_parse_iso_datetime(due_after),
            limit=limit,
            offset=offset,
        )
        result = service.list_queue(
            query,
            actor_user_id=principal.id,
            principal_roles=principal.roles,
        )
        return ReviewQueueListResponse(
            tasks=[_review_task_summary_response(t) for t in result.tasks],
            total_count=result.total_count,
            limit=result.limit,
            offset=result.offset,
            next_offset=result.next_offset,
        )

    @app.get("/reviews/dashboard", response_model=ReviewerDashboardResponse)
    async def get_reviewer_dashboard(
        principal: Annotated[
            UserPrincipal, Depends(require_permission(Permission.DOCUMENTS_REVIEW))
        ],
        service: Annotated[ReviewQueueService, Depends(review_queue_service)],
        language: str | None = None,
        madhhab: str | None = None,
        content_type: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        assigned_to: UUID | None = None,
        review_level: str | None = None,
        due_before: str | None = None,
        due_after: str | None = None,
        limit: int = 10,
        offset: int = 0,
        feedback_limit: int = 5,
    ) -> ReviewerDashboardResponse:
        query = ReviewQueueQuery(
            language=language,
            madhhab=madhhab,
            content_type=content_type,
            status=status,
            priority=priority,
            assigned_to=assigned_to,
            review_level=review_level,
            due_before=_parse_iso_datetime(due_before),
            due_after=_parse_iso_datetime(due_after),
            limit=limit,
            offset=offset,
        )
        dashboard = service.get_dashboard(
            query,
            actor_user_id=principal.id,
            principal_roles=principal.roles,
            feedback_limit=feedback_limit,
        )
        return _reviewer_dashboard_response(dashboard)

    @app.get("/reviews/{review_task_id}", response_model=ReviewTaskDetailResponse)
    async def get_review_task_detail(
        review_task_id: UUID,
        principal: Annotated[
            UserPrincipal, Depends(require_permission(Permission.DOCUMENTS_REVIEW))
        ],
        service: Annotated[ReviewQueueService, Depends(review_queue_service)],
    ) -> ReviewTaskDetailResponse:
        detail = service.get_task_detail(
            review_task_id,
            actor_user_id=principal.id,
            principal_roles=principal.roles,
        )
        return _review_task_detail_response(detail)

    @app.get("/reviews/{review_task_id}/draft", response_model=ReviewDraftResponse)
    async def get_review_draft(
        review_task_id: UUID,
        principal: Annotated[
            UserPrincipal, Depends(require_permission(Permission.DOCUMENTS_REVIEW))
        ],
        service: Annotated[DocumentReviewService, Depends(document_review_service)],
    ) -> ReviewDraftResponse:
        draft = service.get_draft(
            review_task_id,
            actor_user_id=principal.id,
            principal_roles=principal.roles,
        )
        return _review_draft_response(draft)

    @app.patch("/reviews/{review_task_id}/draft", response_model=ReviewEditResponse)
    async def update_review_draft(
        review_task_id: UUID,
        payload: ReviewEditRequest,
        request: Request,
        principal: Annotated[
            UserPrincipal, Depends(require_permission(Permission.DOCUMENTS_REVIEW))
        ],
        service: Annotated[DocumentReviewService, Depends(document_review_service)],
    ) -> ReviewEditResponse:
        result = service.apply_edit(
            review_task_id,
            actor_user_id=principal.id,
            principal_roles=principal.roles,
            base_task_row_version=payload.base_task_row_version,
            text=payload.text,
            metadata_updates=payload.metadata_updates,
            trace_id=request.headers.get("x-request-id"),
        )
        return _review_edit_response(result)

    @app.post("/reviews/{review_task_id}/comments", response_model=ReviewCommentResponse)
    async def add_review_comment(
        review_task_id: UUID,
        payload: ReviewCommentRequest,
        request: Request,
        principal: Annotated[
            UserPrincipal, Depends(require_permission(Permission.DOCUMENTS_REVIEW))
        ],
        service: Annotated[DocumentReviewService, Depends(document_review_service)],
    ) -> ReviewCommentResponse:
        comment = service.add_comment(
            review_task_id,
            actor_user_id=principal.id,
            principal_roles=principal.roles,
            body=payload.body,
            anchor=payload.anchor,
            trace_id=request.headers.get("x-request-id"),
        )
        return _review_comment_response(comment)

    @app.post(
        "/reviews/{review_task_id}/decision",
        response_model=ReviewDecisionActionResponse,
    )
    async def decide_review_task(
        review_task_id: UUID,
        payload: ReviewDecisionRequest,
        request: Request,
        principal: Annotated[
            UserPrincipal, Depends(require_permission(Permission.DOCUMENTS_REVIEW))
        ],
        service: Annotated[DocumentReviewService, Depends(document_review_service)],
    ) -> ReviewDecisionActionResponse:
        result = service.decide(
            review_task_id,
            actor_user_id=principal.id,
            principal_roles=principal.roles,
            decision=payload.decision,
            reason=payload.reason,
            base_task_row_version=payload.base_task_row_version,
            trace_id=request.headers.get("x-request-id"),
        )
        return ReviewDecisionActionResponse(
            status="ok",
            task_row_version=result.task_row_version,
            decision=_review_decision_response(result.decision),
        )

    @app.post(
        "/reviews/{review_task_id}/approvals",
        response_model=ScholarApprovalActionResponse,
    )
    async def create_scholar_approval(
        review_task_id: UUID,
        payload: ScholarApprovalRequest,
        request: Request,
        principal: Annotated[
            UserPrincipal, Depends(require_permission(Permission.DOCUMENTS_REVIEW))
        ],
        service: Annotated[ScholarApprovalService, Depends(scholar_approval_service)],
    ) -> ScholarApprovalActionResponse:
        approval = service.approve(
            review_task_id=review_task_id,
            actor_user_id=principal.id,
            principal_roles=principal.roles,
            content_risk=payload.content_risk,
            approval_level=payload.approval_level,
            reason=payload.reason,
            valid_until=payload.valid_until,
            trace_id=request.headers.get("x-request-id"),
        )
        return ScholarApprovalActionResponse(
            status="ok",
            approval=_approval_response(approval),
        )

    @app.get(
        "/documents/{document_version_id}/approval-requirements",
        response_model=ApprovalRequirementResponse,
    )
    async def get_approval_requirements(
        document_version_id: UUID,
        content_risk: str,
        _: Annotated[UserPrincipal, Depends(require_permission(Permission.DOCUMENTS_REVIEW))],
        service: Annotated[ScholarApprovalService, Depends(scholar_approval_service)],
    ) -> ApprovalRequirementResponse:
        requirement = service.get_requirements(
            document_version_id=document_version_id,
            content_risk=content_risk,
        )
        return _approval_requirement_response(requirement)

    @app.get(
        "/documents/{document_version_id}/approvals",
        response_model=ApprovalListResponse,
    )
    async def list_document_approvals(
        document_version_id: UUID,
        _: Annotated[UserPrincipal, Depends(require_permission(Permission.DOCUMENTS_REVIEW))],
        service: Annotated[ScholarApprovalService, Depends(scholar_approval_service)],
    ) -> ApprovalListResponse:
        result = service.list_approvals(document_version_id=document_version_id)
        return _approval_list_response(result)

    @app.post(
        "/documents/{document_version_id}/publish",
        response_model=DocumentPublishResponse,
    )
    async def publish_document_version(
        document_version_id: UUID,
        payload: DocumentPublishRequest,
        request: Request,
        principal: Annotated[
            UserPrincipal, Depends(require_permission(Permission.DOCUMENTS_PUBLISH))
        ],
        service: Annotated[DocumentPublishingService, Depends(document_publishing_service)],
    ) -> DocumentPublishResponse:
        result = service.publish_document_version(
            document_version_id=document_version_id,
            actor_user_id=principal.id,
            principal_roles=principal.roles,
            content_risk=payload.content_risk,
            reason=payload.reason,
            trace_id=request.headers.get("x-request-id"),
        )
        return _document_publish_response(result)

    @app.post(
        "/documents/{document_id}/suspend",
        response_model=DocumentLifecycleResponse,
    )
    async def suspend_published_document(
        document_id: UUID,
        payload: DocumentLifecycleRequest,
        request: Request,
        principal: Annotated[
            UserPrincipal, Depends(require_permission(Permission.DOCUMENTS_ARCHIVE))
        ],
        service: Annotated[DocumentLifecycleService, Depends(document_lifecycle_service)],
    ) -> DocumentLifecycleResponse:
        result = service.suspend_document(
            document_id=document_id,
            actor_user_id=principal.id,
            principal_roles=principal.roles,
            reason=payload.reason,
            base_row_version=payload.base_row_version,
            trace_id=request.headers.get("x-request-id"),
        )
        return _document_lifecycle_response(result)

    @app.post(
        "/documents/{document_id}/archive",
        response_model=DocumentLifecycleResponse,
    )
    async def archive_published_document(
        document_id: UUID,
        payload: DocumentLifecycleRequest,
        request: Request,
        principal: Annotated[
            UserPrincipal, Depends(require_permission(Permission.DOCUMENTS_ARCHIVE))
        ],
        service: Annotated[DocumentLifecycleService, Depends(document_lifecycle_service)],
    ) -> DocumentLifecycleResponse:
        result = service.archive_document(
            document_id=document_id,
            actor_user_id=principal.id,
            principal_roles=principal.roles,
            reason=payload.reason,
            base_row_version=payload.base_row_version,
            trace_id=request.headers.get("x-request-id"),
        )
        return _document_lifecycle_response(result)

    @app.post(
        "/documents/{document_id}/rollback",
        response_model=DocumentLifecycleResponse,
    )
    async def rollback_published_document(
        document_id: UUID,
        payload: DocumentRollbackRequest,
        request: Request,
        principal: Annotated[
            UserPrincipal, Depends(require_permission(Permission.DOCUMENTS_ARCHIVE))
        ],
        service: Annotated[DocumentLifecycleService, Depends(document_lifecycle_service)],
    ) -> DocumentLifecycleResponse:
        result = service.rollback_document(
            document_id=document_id,
            target_document_version_id=payload.target_document_version_id,
            actor_user_id=principal.id,
            principal_roles=principal.roles,
            reason=payload.reason,
            base_row_version=payload.base_row_version,
            trace_id=request.headers.get("x-request-id"),
        )
        return _document_lifecycle_response(result)

    @app.post(
        "/review-approvals/{approval_id}/revoke",
        response_model=ScholarApprovalActionResponse,
    )
    async def revoke_scholar_approval(
        approval_id: UUID,
        payload: ScholarApprovalRevokeRequest,
        request: Request,
        principal: Annotated[
            UserPrincipal, Depends(require_permission(Permission.DOCUMENTS_REVIEW))
        ],
        service: Annotated[ScholarApprovalService, Depends(scholar_approval_service)],
    ) -> ScholarApprovalActionResponse:
        approval = service.revoke(
            approval_id=approval_id,
            actor_user_id=principal.id,
            principal_roles=principal.roles,
            reason=payload.reason,
            trace_id=request.headers.get("x-request-id"),
        )
        return ScholarApprovalActionResponse(
            status="ok",
            approval=_approval_response(approval),
        )

    @app.post(
        "/reviews/{review_task_id}/claim",
        response_model=ReviewTaskActionResponse,
    )
    async def claim_review_task(
        review_task_id: UUID,
        request: Request,
        principal: Annotated[
            UserPrincipal, Depends(require_permission(Permission.DOCUMENTS_REVIEW))
        ],
        service: Annotated[ReviewQueueService, Depends(review_queue_service)],
    ) -> ReviewTaskActionResponse:
        summary = service.claim_task(
            review_task_id,
            actor_user_id=principal.id,
            trace_id=request.headers.get("x-request-id"),
        )
        return ReviewTaskActionResponse(status="ok", task=_review_task_summary_response(summary))

    @app.post(
        "/reviews/{review_task_id}/release",
        response_model=ReviewTaskActionResponse,
    )
    async def release_review_task(
        review_task_id: UUID,
        request: Request,
        principal: Annotated[
            UserPrincipal, Depends(require_permission(Permission.DOCUMENTS_REVIEW))
        ],
        service: Annotated[ReviewQueueService, Depends(review_queue_service)],
    ) -> ReviewTaskActionResponse:
        summary = service.release_task(
            review_task_id,
            actor_user_id=principal.id,
            principal_roles=principal.roles,
            trace_id=request.headers.get("x-request-id"),
        )
        return ReviewTaskActionResponse(status="ok", task=_review_task_summary_response(summary))

    @app.post(
        "/reviews/{review_task_id}/assign",
        response_model=ReviewTaskActionResponse,
    )
    async def assign_review_task(
        review_task_id: UUID,
        payload: ReviewTaskAssignRequest,
        request: Request,
        principal: Annotated[
            UserPrincipal, Depends(require_permission(Permission.DOCUMENTS_REVIEW))
        ],
        service: Annotated[ReviewQueueService, Depends(review_queue_service)],
    ) -> ReviewTaskActionResponse:
        summary = service.assign_task(
            review_task_id,
            assignee_user_id=payload.assignee_user_id,
            actor_user_id=principal.id,
            principal_roles=principal.roles,
            trace_id=request.headers.get("x-request-id"),
        )
        return ReviewTaskActionResponse(status="ok", task=_review_task_summary_response(summary))

    @app.post(
        "/reviews/{review_task_id}/escalate",
        response_model=ReviewTaskActionResponse,
    )
    async def escalate_review_task(
        review_task_id: UUID,
        request: Request,
        principal: Annotated[
            UserPrincipal, Depends(require_permission(Permission.DOCUMENTS_REVIEW))
        ],
        service: Annotated[ReviewQueueService, Depends(review_queue_service)],
    ) -> ReviewTaskActionResponse:
        summary = service.escalate_task(
            review_task_id,
            actor_user_id=principal.id,
            principal_roles=principal.roles,
            trace_id=request.headers.get("x-request-id"),
        )
        return ReviewTaskActionResponse(status="ok", task=_review_task_summary_response(summary))

    return app
