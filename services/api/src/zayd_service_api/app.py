import base64
from collections.abc import Callable
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, FastAPI, Header, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from zayd_common.audit import AuditLogQuery, AuditOutcome, AuditService, serialize_audit_log
from zayd_common.auth import AccessTokenClaims, AuthError, AuthResult, AuthService
from zayd_common.database import get_sessionmaker
from zayd_common.guest import GuestError, GuestService
from zayd_common.health import HealthStatus
from zayd_common.logging import get_logger
from zayd_common.mfa import (
    MfaEnrollment,
    MfaError,
    MfaResetChannel,
    MfaService,
)
from zayd_common.rbac import Permission, RbacError, RbacService, UserPrincipal
from zayd_common.settings import ServiceSettings

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

    return app
