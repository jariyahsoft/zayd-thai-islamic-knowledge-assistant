import base64
from collections.abc import Callable
from datetime import date, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, FastAPI, Header, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from zayd_common.audit import AuditLogQuery, AuditOutcome, AuditService, serialize_audit_log
from zayd_common.auth import AccessTokenClaims, AuthError, AuthResult, AuthService
from zayd_common.database import get_sessionmaker
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
from zayd_common.settings import ServiceSettings
from zayd_common.sources import (
    SourceError,
    SourcePublic,
    SourceSearchQuery,
    SourceService,
)
from zayd_common.storage import S3ObjectStorage, S3StorageSettings, SignedUrl, StorageError

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

    return app
