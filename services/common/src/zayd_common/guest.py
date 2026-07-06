from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID, uuid4

from sqlalchemy import select

from zayd_common.auth import AuthError, AuthResult, AuthService, hash_token
from zayd_common.database.models import AuditLog, GuestSession
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

GUEST_TOKEN_BYTES = 32
GUEST_DEFAULT_TTL_MINUTES = 120
GUEST_DEFAULT_MESSAGE_QUOTA = 10

GuestErrorCode = Literal[
    "GUEST_DISABLED",
    "GUEST_INVALID_SESSION",
    "GUEST_EXPIRED",
    "GUEST_QUOTA_EXCEEDED",
    "GUEST_REVOKED",
    "GUEST_ALREADY_CONVERTED",
]


class GuestError(Exception):
    def __init__(self, code: GuestErrorCode, message: str, *, status_code: int = 401) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class GuestSessionInfo:
    id: UUID
    token: str
    expires_at: datetime
    message_quota: int
    messages_used: int
    converted_user_id: UUID | None


def hash_guest_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class GuestService:
    def __init__(
        self,
        uow: SQLAlchemyUnitOfWork,
        *,
        auth_service: AuthService,
        ttl_minutes: int = GUEST_DEFAULT_TTL_MINUTES,
        message_quota: int = GUEST_DEFAULT_MESSAGE_QUOTA,
        enabled: bool = True,
    ) -> None:
        self.uow = uow
        self.auth_service = auth_service
        self.ttl_minutes = ttl_minutes
        self.message_quota = message_quota
        self.enabled = enabled

    def _ensure_enabled(self) -> None:
        if not self.enabled:
            raise GuestError(
                "GUEST_DISABLED",
                "Guest sessions are not enabled.",
                status_code=403,
            )

    def _session(self) -> Any:
        if self.uow.session is None:
            raise RuntimeError("Database session not initialized in UoW.")
        return self.uow.session

    def start_session(
        self,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
        trace_id: str | None = None,
    ) -> GuestSessionInfo:
        self._ensure_enabled()
        token = secrets.token_urlsafe(GUEST_TOKEN_BYTES)
        token_hash = hash_guest_token(token)
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=self.ttl_minutes)
        with self.uow:
            session = self._session()
            session.add(
                GuestSession(
                    id=uuid4(),
                    session_token_hash=token_hash,
                    ip_hash=hash_token(ip_address) if ip_address else None,
                    user_agent_hash=hash_token(user_agent) if user_agent else None,
                    message_quota=self.message_quota,
                    messages_used=0,
                    expires_at=expires_at,
                    last_seen_at=now,
                )
            )
            self._audit(
                action="guest.session.start",
                outcome="success",
                trace_id=trace_id,
                after_summary={"ttl_minutes": self.ttl_minutes},
            )
            self.uow.commit()
            return GuestSessionInfo(
                id=session.execute(
                    select(GuestSession).where(GuestSession.session_token_hash == token_hash)
                )
                .scalar_one()
                .id,
                token=token,
                expires_at=expires_at,
                message_quota=self.message_quota,
                messages_used=0,
                converted_user_id=None,
            )

    def validate_session(
        self,
        *,
        token: str,
        touch: bool = False,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        self._ensure_enabled()
        now = datetime.now(UTC)
        result: dict[str, Any]
        with self.uow:
            session = self._session()
            guest = session.execute(
                select(GuestSession).where(
                    GuestSession.session_token_hash == hash_guest_token(token)
                )
            ).scalar_one_or_none()
            if guest is None:
                self._audit(
                    action="guest.session.validate",
                    outcome="failure",
                    reason="invalid_token",
                    trace_id=trace_id,
                )
                self.uow.commit()
                raise GuestError(
                    "GUEST_INVALID_SESSION",
                    "Guest session is invalid.",
                    status_code=401,
                )

            if guest.revoked_at is not None:
                self._audit(
                    action="guest.session.validate",
                    outcome="denied",
                    reason="revoked",
                    resource_id=guest.id,
                    trace_id=trace_id,
                )
                self.uow.commit()
                raise GuestError(
                    "GUEST_REVOKED",
                    "Guest session is no longer valid.",
                    status_code=401,
                )

            if _as_utc(guest.expires_at) <= now:
                self._audit(
                    action="guest.session.validate",
                    outcome="denied",
                    reason="expired",
                    resource_id=guest.id,
                    trace_id=trace_id,
                )
                self.uow.commit()
                raise GuestError(
                    "GUEST_EXPIRED",
                    "Guest session has expired.",
                    status_code=401,
                )

            if touch:
                guest.last_seen_at = now

            result = {
                "id": guest.id,
                "messages_used": guest.messages_used,
                "message_quota": guest.message_quota,
                "converted_user_id": guest.converted_user_id,
                "expires_at": guest.expires_at,
                "revoked_at": guest.revoked_at,
            }
            self.uow.commit()
        return result

    def consume_quota(
        self,
        *,
        token: str,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        snapshot = self.validate_session(token=token, trace_id=trace_id)
        if snapshot["messages_used"] >= snapshot["message_quota"]:
            with self.uow:
                self._audit(
                    action="guest.quota.exceeded",
                    outcome="denied",
                    reason="quota_exceeded",
                    resource_id=snapshot["id"],
                    trace_id=trace_id,
                )
                self.uow.commit()
            raise GuestError(
                "GUEST_QUOTA_EXCEEDED",
                "Guest message quota exceeded.",
                status_code=429,
            )
        with self.uow:
            session = self._session()
            guest = session.get(GuestSession, snapshot["id"])
            assert guest is not None
            guest.messages_used += 1
            guest.last_seen_at = datetime.now(UTC)
            snapshot["messages_used"] = guest.messages_used
            self._audit(
                action="guest.quota.consume",
                outcome="success",
                resource_id=guest.id,
                after_summary={
                    "messages_used": guest.messages_used,
                    "message_quota": guest.message_quota,
                },
                trace_id=trace_id,
            )
            self.uow.commit()
        return snapshot

    def revoke_session(
        self,
        *,
        token: str,
        reason: str = "user_requested",
        trace_id: str | None = None,
    ) -> bool:
        with self.uow:
            session = self._session()
            guest = session.execute(
                select(GuestSession).where(
                    GuestSession.session_token_hash == hash_guest_token(token)
                )
            ).scalar_one_or_none()
            if guest is None or guest.revoked_at is not None:
                self.uow.commit()
                return False
            guest.revoked_at = datetime.now(UTC)
            self._audit(
                action="guest.session.revoke",
                outcome="success",
                reason=reason,
                resource_id=guest.id,
                trace_id=trace_id,
            )
            self.uow.commit()
        return True

    def convert_to_user(
        self,
        *,
        token: str,
        email: str,
        password: str,
        display_name: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
        trace_id: str | None = None,
    ) -> AuthResult:
        self._ensure_enabled()
        snapshot = self.validate_session(token=token, trace_id=trace_id)
        if snapshot["converted_user_id"] is not None:
            self._audit(
                action="guest.convert",
                outcome="denied",
                reason="already_converted",
                resource_id=snapshot["id"],
                trace_id=trace_id,
            )
            with self.uow:
                self.uow.commit()
            raise GuestError(
                "GUEST_ALREADY_CONVERTED",
                "Guest session has already been converted.",
                status_code=409,
            )

        guest_id = snapshot["id"]

        try:
            auth_result = self.auth_service.register(
                email=email,
                password=password,
                display_name=display_name,
                ip_address=ip_address,
                user_agent=user_agent,
                trace_id=trace_id,
            )
        except AuthError as exc:
            self._audit(
                action="guest.convert",
                outcome="failure",
                reason="duplicate_email" if exc.code == "AUTH_USER_EXISTS" else exc.code.lower(),
                resource_id=guest_id,
                trace_id=trace_id,
            )
            with self.uow:
                self.uow.commit()
            raise

        with self.uow:
            session = self._session()
            guest = session.get(GuestSession, guest_id)
            assert guest is not None
            guest.converted_user_id = auth_result.user.id
            guest.revoked_at = datetime.now(UTC)
            self._audit(
                action="guest.convert",
                outcome="success",
                actor_user_id=auth_result.user.id,
                resource_id=guest_id,
                after_summary={"converted_user_id": str(auth_result.user.id)},
                trace_id=trace_id,
            )
            self.uow.commit()

        return auth_result

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
                resource_type="guest_session",
                resource_id=resource_id,
                outcome=outcome,
                reason=reason,
                request_id=trace_id,
                trace_id=trace_id,
                before_summary=before_summary,
                after_summary=after_summary,
                source_context={},
            )
        )
