from typing import Annotated

from fastapi import Depends, FastAPI, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from zayd_common.auth import AuthError, AuthResult, AuthService
from zayd_common.database import get_sessionmaker
from zayd_common.health import HealthStatus
from zayd_common.logging import get_logger
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

    def get_current_user_id(
        service: Annotated[AuthService, Depends(auth_service)],
        authorization: Annotated[str | None, Header()] = None,
    ) -> str:
        if not authorization or not authorization.startswith("Bearer "):
            raise AuthError("AUTH_UNAUTHENTICATED", "Authentication required.", status_code=401)
        token = authorization.removeprefix("Bearer ").strip()
        return str(service.verify_access_token(token).user_id)

    @app.exception_handler(AuthError)
    async def auth_error_handler(request: Request, exc: AuthError) -> JSONResponse:
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
        service: Annotated[AuthService, Depends(auth_service)],
    ) -> dict[str, int]:
        from uuid import UUID

        revoked = service.revoke_all_sessions(
            user_id=UUID(current_user_id),
            trace_id=request.headers.get("x-request-id"),
        )
        return {"revoked_sessions": revoked}

    return app
