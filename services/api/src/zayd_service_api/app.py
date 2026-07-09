import base64
import asyncio
import json
import re
from collections.abc import Callable
from datetime import date, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, FastAPI, Header, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from zayd_common.audit import AuditLogQuery, AuditOutcome, AuditService, serialize_audit_log
from zayd_common.auth import AccessTokenClaims, AuthError, AuthResult, AuthService
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
from zayd_common.guest import GuestError, GuestService
from zayd_common.health import HealthStatus
from zayd_common.licenses import (
    LicenseCreate,
    LicenseError,
    LicensePolicyDecisionPublic,
    LicensePublic,
    LicenseService,
    PermissionDocumentAccess,
    PublicationAuthorization,
)
from zayd_common.logging import get_logger
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
from zayd_common.rbac import Permission, RbacError, RbacService, UserPrincipal
from zayd_common.review_queue import (
    ReviewQueueError,
    ReviewQueueQuery,
    ReviewQueueService,
    ReviewTaskDetail,
    ReviewTaskSummary,
)
from zayd_common.scholar_approval import (
    ApprovalPublic,
    ApprovalRequirement,
    ScholarApprovalError,
    ScholarApprovalService,
)
from zayd_common.settings import ServiceSettings
from zayd_common.sources import (
    SourceError,
    SourcePublic,
    SourceSearchQuery,
    SourceService,
)
from zayd_common.storage import S3ObjectStorage, S3StorageSettings, SignedUrl, StorageError
from zayd_common.prompt_registry import (
    DEFAULT_ANSWER_PROMPT_NAME,
    DEFAULT_ANSWER_PROMPT_VERSION,
    DEFAULT_POLICY_VERSION,
    PromptComparison,
    PromptCreate,
    PromptRegistryError,
    PromptRegistryService,
    PromptStatusChange,
    PromptTestCase,
    bootstrap_registry_defaults,
    default_answer_generation_prompt,
)
from zayd_service_orchestrator import (
    ChatRequest,
    ChatStreamingError,
    ChatStreamingService,
    MockLLMProvider,
    PromptRegistryService as OrchestratorPromptRegistryService,
    StaticAnswerRetriever,
    build_managed_answer_orchestrator,
    sse_encode,
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


class RoleAssignmentRequest(BaseModel):
    user_id: UUID
    role_name: str = Field(min_length=1, max_length=64)


class RoleAssignmentResponse(BaseModel):
    status: str
    changed: bool


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
    task_status: str
    task_row_version: int
    document_review_status: str
    original_file_key: str | None
    editable_text: str | None
    editable_metadata: dict[str, object]
    latest_revision_number: int
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


def _prompt_test_case_request(case) -> PromptTestCaseRequest:
    return PromptTestCaseRequest(
        name=case.name,
        input_payload=case.input_payload,
        expected_assertions=list(case.expected_assertions),
    )


def _prompt_response(prompt) -> PromptResponse:
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
        llm_provider=MockLLMProvider(),
    )
    orchestrator.prompt_version_id = prompt.id
    orchestrator.policy_version_id = policy_version_id
    orchestrator.model_configuration_id = model_configuration_id
    return ChatStreamingService(
        uow_factory=lambda: SQLAlchemyUnitOfWork(session_factory),
        orchestrator=orchestrator,
        prompt_registry_factory=lambda: PromptRegistryService(SQLAlchemyUnitOfWork(session_factory)),
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


def create_app() -> FastAPI:
    settings = ServiceSettings.from_runtime_env(app_name="api")
    app = FastAPI(title=f"Zayd {settings.app_name} service")
    session_factory = get_sessionmaker(settings.database_url)

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

    @app.exception_handler(PromptRegistryError)
    async def prompt_registry_error_handler(
        request: Request, exc: PromptRegistryError
    ) -> JSONResponse:
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

    @app.get("/health", response_model=HealthStatus)
    async def health() -> HealthStatus:
        logger.info("health_check")
        return HealthStatus(service=settings.app_name)

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
        return PromptListResponse(prompts=[_prompt_response(prompt) for prompt in service.list_prompts(name=name)])

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
            content = upload_service.storage.get_private_bytes(
                key=version.original_file_key or ""
            )
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
    async def review_queue_error_handler(
        request: Request, exc: ReviewQueueError
    ) -> JSONResponse:
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
            task_status=draft.task_status,
            task_row_version=draft.task_row_version,
            document_review_status=draft.document_review_status,
            original_file_key=draft.original_file_key,
            editable_text=draft.editable_text,
            editable_metadata=dict(draft.editable_metadata),
            latest_revision_number=draft.latest_revision_number,
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
        _: Annotated[
            UserPrincipal, Depends(require_permission(Permission.DOCUMENTS_REVIEW))
        ],
        service: Annotated[ScholarApprovalService, Depends(scholar_approval_service)],
    ) -> ApprovalRequirementResponse:
        requirement = service.get_requirements(
            document_version_id=document_version_id,
            content_risk=content_risk,
        )
        return _approval_requirement_response(requirement)

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
        return ReviewTaskActionResponse(
            status="ok", task=_review_task_summary_response(summary)
        )

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
        return ReviewTaskActionResponse(
            status="ok", task=_review_task_summary_response(summary)
        )

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
        return ReviewTaskActionResponse(
            status="ok", task=_review_task_summary_response(summary)
        )

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
        return ReviewTaskActionResponse(
            status="ok", task=_review_task_summary_response(summary)
        )

    return app
