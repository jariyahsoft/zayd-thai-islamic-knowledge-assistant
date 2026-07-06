from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID, uuid4

from sqlalchemy import select

from zayd_common.database.models import (
    AuditLog,
    AuthRateLimit,
    AuthRefreshToken,
    AuthSession,
    PasswordResetToken,
    User,
)
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

PBKDF2_ALGORITHM = "pbkdf2_sha256"
PBKDF2_ITERATIONS = 310_000
ACCESS_TOKEN_TTL = timedelta(minutes=15)
REFRESH_TOKEN_TTL = timedelta(days=30)
PASSWORD_RESET_TTL = timedelta(hours=1)
RATE_LIMIT_WINDOW = timedelta(minutes=15)
LOGIN_RATE_LIMIT = 5
RESET_RATE_LIMIT = 3

AuthErrorCode = Literal[
    "AUTH_INVALID_CREDENTIALS",
    "AUTH_RATE_LIMITED",
    "AUTH_REFRESH_REUSE_DETECTED",
    "AUTH_INVALID_REFRESH_TOKEN",
    "AUTH_INVALID_RESET_TOKEN",
    "AUTH_USER_EXISTS",
    "AUTH_UNAUTHENTICATED",
]


@dataclass(frozen=True)
class AccessTokenClaims:
    user_id: UUID
    email: str
    expires_at: datetime


class AuthError(Exception):
    def __init__(self, code: AuthErrorCode, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class AuthTokens:
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


@dataclass(frozen=True)
class UserPublic:
    id: UUID
    email: str
    display_name: str


@dataclass(frozen=True)
class AuthResult:
    user: UserPublic
    tokens: AuthTokens


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return "$".join(
        [
            PBKDF2_ALGORITHM,
            str(PBKDF2_ITERATIONS),
            _b64url_encode(salt),
            _b64url_encode(derived),
        ]
    )


def verify_password(password: str, encoded_hash: str | None) -> bool:
    if not encoded_hash:
        return False
    try:
        algorithm, iterations_raw, salt_raw, hash_raw = encoded_hash.split("$", 3)
        if algorithm != PBKDF2_ALGORITHM:
            return False
        salt = _b64url_decode(salt_raw)
        expected = _b64url_decode(hash_raw)
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            int(iterations_raw),
        )
        return hmac.compare_digest(actual, expected)
    except (TypeError, ValueError):
        return False


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class AuthService:
    def __init__(self, uow: SQLAlchemyUnitOfWork, *, signing_secret: str) -> None:
        self.uow = uow
        self.signing_secret = signing_secret

    def register(
        self,
        *,
        email: str,
        password: str,
        display_name: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
        trace_id: str | None = None,
    ) -> AuthResult:
        normalized_email = email.strip().lower()
        now = datetime.now(UTC)
        with self.uow:
            session = self._session()
            if self.uow.users.get_by_email(normalized_email) is not None:
                self._audit(
                    action="auth.register",
                    outcome="failure",
                    reason="duplicate_email",
                    trace_id=trace_id,
                )
                raise AuthError(
                    "AUTH_USER_EXISTS",
                    "Registration could not be completed.",
                    status_code=409,
                )

            user = User(
                id=uuid4(),
                email=normalized_email,
                display_name=display_name.strip(),
                password_hash=hash_password(password),
                status="active",
            )
            self.uow.users.create(user)
            session.flush()
            tokens = self._create_session_tokens(
                user=user,
                now=now,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            self._audit(
                action="auth.register",
                outcome="success",
                actor_user_id=user.id,
                resource_id=user.id,
                trace_id=trace_id,
            )
            self.uow.commit()
            return AuthResult(user=_public_user(user), tokens=tokens)

    def login(
        self,
        *,
        email: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
        trace_id: str | None = None,
    ) -> AuthResult:
        normalized_email = email.strip().lower()
        now = datetime.now(UTC)
        with self.uow:
            self._check_rate_limit(
                action="login",
                identifier=f"{normalized_email}:{ip_address or 'unknown'}",
                limit=LOGIN_RATE_LIMIT,
                now=now,
                trace_id=trace_id,
            )
            user = self.uow.users.get_by_email(normalized_email)
            if (
                user is None
                or user.status != "active"
                or not verify_password(password, user.password_hash)
            ):
                self._audit(
                    action="auth.login",
                    outcome="failure",
                    reason="invalid_credentials",
                    trace_id=trace_id,
                )
                self.uow.commit()
                raise AuthError(
                    "AUTH_INVALID_CREDENTIALS",
                    "Invalid email or password.",
                    status_code=401,
                )

            user.last_login_at = now
            tokens = self._create_session_tokens(
                user=user,
                now=now,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            self._audit(
                action="auth.login",
                outcome="success",
                actor_user_id=user.id,
                resource_id=user.id,
                trace_id=trace_id,
            )
            self.uow.commit()
            return AuthResult(user=_public_user(user), tokens=tokens)

    def refresh(self, *, refresh_token: str, trace_id: str | None = None) -> AuthTokens:
        now = datetime.now(UTC)
        token_hash = hash_token(refresh_token)
        with self.uow:
            session = self._session()
            token = session.execute(
                select(AuthRefreshToken).where(AuthRefreshToken.token_hash == token_hash)
            ).scalar_one_or_none()
            if token is None or token.revoked_at is not None or _as_utc(token.expires_at) <= now:
                self._audit(
                    action="auth.refresh",
                    outcome="failure",
                    reason="invalid_refresh_token",
                    trace_id=trace_id,
                )
                self.uow.commit()
                raise AuthError(
                    "AUTH_INVALID_REFRESH_TOKEN",
                    "Refresh token is invalid.",
                    status_code=401,
                )

            user = self.uow.users.get_by_id(token.user_id)
            auth_session = session.get(AuthSession, token.session_id)
            if user is None or auth_session is None or auth_session.revoked_at is not None:
                self.uow.commit()
                raise AuthError(
                    "AUTH_INVALID_REFRESH_TOKEN",
                    "Refresh token is invalid.",
                    status_code=401,
                )

            if token.used_at is not None:
                token.reuse_detected_at = now
                auth_session.revoked_at = now
                self._revoke_session_refresh_tokens(token.session_id, now=now)
                self._audit(
                    action="auth.refresh_reuse",
                    outcome="denied",
                    actor_user_id=token.user_id,
                    resource_id=token.session_id,
                    reason="reuse_detected",
                    trace_id=trace_id,
                )
                self.uow.commit()
                raise AuthError(
                    "AUTH_REFRESH_REUSE_DETECTED",
                    "Refresh token reuse detected.",
                    status_code=401,
                )

            token.used_at = now
            new_refresh_token = secrets.token_urlsafe(48)
            new_token = AuthRefreshToken(
                id=uuid4(),
                session_id=token.session_id,
                user_id=token.user_id,
                token_hash=hash_token(new_refresh_token),
                parent_token_hash=token.token_hash,
                expires_at=now + REFRESH_TOKEN_TTL,
            )
            session.add(new_token)
            self._audit(
                action="auth.refresh",
                outcome="success",
                actor_user_id=user.id,
                resource_id=token.session_id,
                trace_id=trace_id,
            )
            self.uow.commit()
            return AuthTokens(
                access_token=self._create_access_token(user, now=now),
                refresh_token=new_refresh_token,
                token_type="bearer",
                expires_in=int(ACCESS_TOKEN_TTL.total_seconds()),
            )

    def logout(self, *, refresh_token: str, trace_id: str | None = None) -> None:
        now = datetime.now(UTC)
        token_hash = hash_token(refresh_token)
        with self.uow:
            session = self._session()
            token = session.execute(
                select(AuthRefreshToken).where(AuthRefreshToken.token_hash == token_hash)
            ).scalar_one_or_none()
            if token is not None:
                auth_session = session.get(AuthSession, token.session_id)
                if auth_session is not None:
                    auth_session.revoked_at = now
                    self._revoke_session_refresh_tokens(token.session_id, now=now)
                    self._audit(
                        action="auth.logout",
                        outcome="success",
                        actor_user_id=token.user_id,
                        resource_id=token.session_id,
                        trace_id=trace_id,
                    )
            self.uow.commit()

    def revoke_all_sessions(self, *, user_id: UUID, trace_id: str | None = None) -> int:
        now = datetime.now(UTC)
        with self.uow:
            session = self._session()
            sessions = (
                session.execute(
                    select(AuthSession)
                    .where(AuthSession.user_id == user_id)
                    .where(AuthSession.revoked_at.is_(None))
                )
                .scalars()
                .all()
            )
            for auth_session in sessions:
                auth_session.revoked_at = now
                self._revoke_session_refresh_tokens(auth_session.id, now=now)
            self._audit(
                action="auth.sessions.revoke_all",
                outcome="success",
                actor_user_id=user_id,
                resource_id=user_id,
                after_summary={"revoked_session_count": len(sessions)},
                trace_id=trace_id,
            )
            self.uow.commit()
            return len(sessions)

    def request_password_reset(
        self,
        *,
        email: str,
        ip_address: str | None = None,
        trace_id: str | None = None,
    ) -> str | None:
        normalized_email = email.strip().lower()
        now = datetime.now(UTC)
        with self.uow:
            self._check_rate_limit(
                action="password_reset",
                identifier=f"{normalized_email}:{ip_address or 'unknown'}",
                limit=RESET_RATE_LIMIT,
                now=now,
                trace_id=trace_id,
            )
            user = self.uow.users.get_by_email(normalized_email)
            if user is None:
                self._audit(
                    action="auth.password_reset.request",
                    outcome="success",
                    reason="non_enumerating_unknown_email",
                    trace_id=trace_id,
                )
                self.uow.commit()
                return None

            reset_token = secrets.token_urlsafe(48)
            self._session().add(
                PasswordResetToken(
                    id=uuid4(),
                    user_id=user.id,
                    token_hash=hash_token(reset_token),
                    expires_at=now + PASSWORD_RESET_TTL,
                )
            )
            self._audit(
                action="auth.password_reset.request",
                outcome="success",
                actor_user_id=user.id,
                resource_id=user.id,
                trace_id=trace_id,
            )
            self.uow.commit()
            return reset_token

    def reset_password(
        self,
        *,
        reset_token: str,
        new_password: str,
        trace_id: str | None = None,
    ) -> None:
        now = datetime.now(UTC)
        token_hash = hash_token(reset_token)
        with self.uow:
            session = self._session()
            token = session.execute(
                select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
            ).scalar_one_or_none()
            if token is None or token.used_at is not None or _as_utc(token.expires_at) <= now:
                self._audit(
                    action="auth.password_reset.confirm",
                    outcome="failure",
                    reason="invalid_reset_token",
                    trace_id=trace_id,
                )
                self.uow.commit()
                raise AuthError(
                    "AUTH_INVALID_RESET_TOKEN",
                    "Password reset token is invalid.",
                    status_code=400,
                )
            user = self.uow.users.get_by_id(token.user_id)
            if user is None:
                self.uow.commit()
                raise AuthError(
                    "AUTH_INVALID_RESET_TOKEN",
                    "Password reset token is invalid.",
                    status_code=400,
                )

            user.password_hash = hash_password(new_password)
            token.used_at = now
            sessions = (
                session.execute(
                    select(AuthSession)
                    .where(AuthSession.user_id == user.id)
                    .where(AuthSession.revoked_at.is_(None))
                )
                .scalars()
                .all()
            )
            for auth_session in sessions:
                auth_session.revoked_at = now
                self._revoke_session_refresh_tokens(auth_session.id, now=now)
            self._audit(
                action="auth.password_reset.confirm",
                outcome="success",
                actor_user_id=user.id,
                resource_id=user.id,
                after_summary={"revoked_session_count": len(sessions)},
                trace_id=trace_id,
            )
            self.uow.commit()

    def _create_session_tokens(
        self,
        *,
        user: User,
        now: datetime,
        ip_address: str | None,
        user_agent: str | None,
    ) -> AuthTokens:
        session = self._session()
        refresh_token = secrets.token_urlsafe(48)
        session_hash_seed = secrets.token_urlsafe(32)
        auth_session = AuthSession(
            id=uuid4(),
            user_id=user.id,
            session_hash=hash_token(session_hash_seed),
            ip_hash=_hash_optional(ip_address),
            user_agent_hash=_hash_optional(user_agent),
            expires_at=now + REFRESH_TOKEN_TTL,
        )
        session.add(auth_session)
        session.add(
            AuthRefreshToken(
                id=uuid4(),
                session_id=auth_session.id,
                user_id=user.id,
                token_hash=hash_token(refresh_token),
                expires_at=now + REFRESH_TOKEN_TTL,
            )
        )
        return AuthTokens(
            access_token=self._create_access_token(user, now=now),
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=int(ACCESS_TOKEN_TTL.total_seconds()),
        )

    def _create_access_token(self, user: User, *, now: datetime) -> str:
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "iat": int(now.timestamp()),
            "exp": int((now + ACCESS_TOKEN_TTL).timestamp()),
        }
        signing_input = ".".join(
            [
                _b64url_json(header),
                _b64url_json(payload),
            ]
        )
        signature = hmac.new(
            self.signing_secret.encode("utf-8"),
            signing_input.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        return f"{signing_input}.{_b64url_encode(signature)}"

    def verify_access_token(self, token: str) -> AccessTokenClaims:
        parts = token.split(".")
        if len(parts) != 3:
            raise AuthError("AUTH_UNAUTHENTICATED", "Authentication required.", status_code=401)

        signing_input = ".".join(parts[:2])
        expected_signature = hmac.new(
            self.signing_secret.encode("utf-8"),
            signing_input.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        try:
            actual_signature = _b64url_decode(parts[2])
            if not hmac.compare_digest(actual_signature, expected_signature):
                raise ValueError
            payload = json.loads(_b64url_decode(parts[1]))
            expires_at = datetime.fromtimestamp(int(payload["exp"]), tz=UTC)
            if expires_at <= datetime.now(UTC):
                raise ValueError
            return AccessTokenClaims(
                user_id=UUID(str(payload["sub"])),
                email=str(payload["email"]),
                expires_at=expires_at,
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise AuthError(
                "AUTH_UNAUTHENTICATED",
                "Authentication required.",
                status_code=401,
            ) from exc

    def _check_rate_limit(
        self,
        *,
        action: str,
        identifier: str,
        limit: int,
        now: datetime,
        trace_id: str | None,
    ) -> None:
        session = self._session()
        bucket = hash_token(f"{action}:{identifier}")
        record = session.execute(
            select(AuthRateLimit).where(AuthRateLimit.bucket == bucket)
        ).scalar_one_or_none()
        if record is None:
            session.add(
                AuthRateLimit(
                    id=uuid4(),
                    bucket=bucket,
                    action=action,
                    attempts=1,
                    window_start=now,
                )
            )
            return

        if record.blocked_until is not None and _as_utc(record.blocked_until) > now:
            self._audit(
                action=f"auth.{action}.rate_limit",
                outcome="denied",
                reason="rate_limited",
                trace_id=trace_id,
            )
            self.uow.commit()
            raise AuthError("AUTH_RATE_LIMITED", "Too many attempts.", status_code=429)

        if _as_utc(record.window_start) + RATE_LIMIT_WINDOW <= now:
            record.attempts = 1
            record.window_start = now
            record.blocked_until = None
            return

        record.attempts += 1
        if record.attempts > limit:
            record.blocked_until = now + RATE_LIMIT_WINDOW
            self._audit(
                action=f"auth.{action}.rate_limit",
                outcome="denied",
                reason="rate_limited",
                trace_id=trace_id,
            )
            self.uow.commit()
            raise AuthError("AUTH_RATE_LIMITED", "Too many attempts.", status_code=429)

    def _revoke_session_refresh_tokens(self, session_id: UUID, *, now: datetime) -> None:
        tokens = (
            self._session()
            .execute(
                select(AuthRefreshToken)
                .where(AuthRefreshToken.session_id == session_id)
                .where(AuthRefreshToken.revoked_at.is_(None))
            )
            .scalars()
            .all()
        )
        for token in tokens:
            token.revoked_at = now

    def _audit(
        self,
        *,
        action: str,
        outcome: str,
        actor_user_id: UUID | None = None,
        resource_id: UUID | None = None,
        reason: str | None = None,
        before_summary: dict[str, Any] | None = None,
        after_summary: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> None:
        self._session().add(
            AuditLog(
                id=uuid4(),
                actor_user_id=actor_user_id,
                action=action,
                resource_type="auth",
                resource_id=resource_id,
                outcome=outcome,
                reason=reason,
                trace_id=trace_id,
                before_summary=before_summary,
                after_summary=after_summary,
                source_context={},
            )
        )

    def _session(self) -> Any:
        if self.uow.session is None:
            raise RuntimeError("Database session not initialized in UoW.")
        return self.uow.session


def _public_user(user: User) -> UserPublic:
    return UserPublic(id=user.id, email=user.email, display_name=user.display_name)


def _hash_optional(value: str | None) -> str | None:
    return hash_token(value) if value else None


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _b64url_json(value: dict[str, Any]) -> str:
    return _b64url_encode(json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8"))


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
