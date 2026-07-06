from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Literal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from zayd_common.database.models import (
    AuditLog,
    AuthMfaChallenge,
    AuthMfaRecoveryCode,
    AuthMfaSecret,
    Role,
    User,
    UserRole,
)
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

TOTP_PERIOD_SECONDS = 30
TOTP_DIGITS = 6
TOTP_WINDOW = 1
RECOVERY_CODE_COUNT = 10
RECOVERY_CODE_BYTES = 10
RECOVERY_TTL = timedelta(hours=1)
MFA_CHALLENGE_TTL = timedelta(minutes=5)
MFA_RECOVERY_GRACE_PERIOD = 0

MfaErrorCode = Literal[
    "MFA_REQUIRED",
    "MFA_NOT_ENROLLED",
    "MFA_ALREADY_ENROLLED",
    "MFA_INVALID_CHALLENGE",
    "MFA_INVALID_CODE",
    "MFA_INVALID_RECOVERY_CODE",
    "MFA_CHALLENGE_EXPIRED",
    "MFA_PRIVILEGED_ACCESS_BLOCKED",
    "MFA_RESET_REQUIRES_RECOVERY",
    "MFA_UNKNOWN_USER",
]


class MfaError(Exception):
    def __init__(self, code: MfaErrorCode, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class MfaResetChannel(StrEnum):
    RECOVERY_CODE = "recovery_code"
    PASSWORD_RESET = "password_reset"


@dataclass(frozen=True)
class MfaEnrollment:
    secret: bytes
    provisioning_uri: str
    recovery_codes: tuple[str, ...]


@dataclass(frozen=True)
class MfaChallenge:
    challenge_id: UUID
    expires_at: datetime


PRIVILEGED_ROLE_NAMES: tuple[str, ...] = (
    "reviewer",
    "senior_scholar",
    "admin",
)


class MfaService:
    def __init__(self, uow: SQLAlchemyUnitOfWork) -> None:
        self.uow = uow

    def start_enrollment(
        self,
        *,
        user_id: UUID,
        trace_id: str | None = None,
    ) -> MfaEnrollment:
        with self.uow:
            session = self._session()
            user = self._require_active_user_in_session(session, user_id)
            existing_secret = session.execute(
                select(AuthMfaSecret).where(AuthMfaSecret.user_id == user.id)
            ).scalar_one_or_none()
            if existing_secret is not None and existing_secret.confirmed_at is not None:
                raise MfaError("MFA_ALREADY_ENROLLED", "MFA is already enrolled.", status_code=409)
            pending_secret = (
                existing_secret.secret
                if existing_secret is not None and existing_secret.confirmed_at is None
                else _generate_secret()
            )
            if existing_secret is None:
                session.add(
                    AuthMfaSecret(
                        id=uuid4(),
                        user_id=user.id,
                        secret=pending_secret,
                        confirmed_at=None,
                        recovery_codes_rotated_at=None,
                    )
                )
            elif existing_secret.secret != pending_secret:
                existing_secret.secret = pending_secret
                existing_secret.confirmed_at = None
                existing_secret.recovery_codes_rotated_at = None
                _purge_recovery_codes_in_session(session, user_id=user.id)
            recovery_codes = _generate_recovery_codes()
            _persist_recovery_codes(session, user_id=user.id, codes=recovery_codes)
            self._audit(
                action="mfa.enrollment.start",
                outcome="success",
                actor_user_id=user.id,
                resource_id=user.id,
                trace_id=trace_id,
            )
            self.uow.commit()
            return MfaEnrollment(
                secret=pending_secret,
                provisioning_uri=_build_provisioning_uri(
                    user_email=user.email, secret=pending_secret
                ),
                recovery_codes=recovery_codes,
            )

    def confirm_enrollment(
        self,
        *,
        user_id: UUID,
        code: str,
        trace_id: str | None = None,
    ) -> None:
        normalized_code = _normalize_totp_code(code)
        with self.uow:
            session = self._session()
            self._require_active_user_in_session(session, user_id)
            secret = self._load_unconfirmed_secret_in_session(session, user_id)
            if not verify_totp(secret.secret, code=normalized_code):
                self._audit(
                    action="mfa.enrollment.confirm",
                    outcome="failure",
                    actor_user_id=user_id,
                    reason="invalid_code",
                    trace_id=trace_id,
                )
                self.uow.commit()
                raise MfaError("MFA_INVALID_CODE", "MFA code is invalid.", status_code=400)
            now = datetime.now(UTC)
            secret.confirmed_at = now
            secret.recovery_codes_rotated_at = now
            self._audit(
                action="mfa.enrollment.confirm",
                outcome="success",
                actor_user_id=user_id,
                resource_id=user_id,
                trace_id=trace_id,
            )
            self.uow.commit()

    def is_enrolled(self, *, user_id: UUID) -> bool:
        with self.uow:
            session = self._session()
            secret = session.execute(
                select(AuthMfaSecret).where(AuthMfaSecret.user_id == user_id)
            ).scalar_one_or_none()
            self.uow.commit()
            return secret is not None and secret.confirmed_at is not None

    def has_privileged_role(self, *, user_id: UUID) -> bool:
        with self.uow:
            session = self._session()
            privileged_names = set(PRIVILEGED_ROLE_NAMES)
            role_names = set(
                session.execute(
                    select(Role.name)
                    .join(UserRole, UserRole.role_id == Role.id)
                    .where(UserRole.user_id == user_id)
                    .where(Role.deleted_at.is_(None))
                )
                .scalars()
                .all()
            )
            self.uow.commit()
            return bool(privileged_names & role_names)

    def start_challenge(
        self,
        *,
        user_id: UUID,
        trace_id: str | None = None,
    ) -> MfaChallenge:
        with self.uow:
            session = self._session()
            self._require_enrolled_active_user_in_session(session, user_id)
            now = datetime.now(UTC)
            challenge = AuthMfaChallenge(
                id=uuid4(),
                user_id=user_id,
                challenge_code=secrets.token_urlsafe(32),
                issued_at=now,
                expires_at=now + MFA_CHALLENGE_TTL,
                consumed_at=None,
            )
            session.add(challenge)
            self._audit(
                action="mfa.challenge.start",
                outcome="success",
                actor_user_id=user_id,
                resource_id=user_id,
                trace_id=trace_id,
            )
            self.uow.commit()
            return MfaChallenge(challenge_id=challenge.id, expires_at=challenge.expires_at)

    def verify_challenge(
        self,
        *,
        user_id: UUID,
        challenge_id: UUID,
        code: str,
        trace_id: str | None = None,
    ) -> None:
        normalized_code = _normalize_totp_code(code)
        with self.uow:
            session = self._session()
            self._require_enrolled_active_user_in_session(session, user_id)
            challenge = self._load_pending_challenge_in_session(
                session, user_id=user_id, challenge_id=challenge_id
            )
            secret = self._load_confirmed_secret_in_session(session, user_id)
            if not verify_totp(secret.secret, code=normalized_code):
                self._audit(
                    action="mfa.challenge.verify",
                    outcome="failure",
                    actor_user_id=user_id,
                    resource_id=challenge_id,
                    reason="invalid_code",
                    trace_id=trace_id,
                )
                self.uow.commit()
                raise MfaError("MFA_INVALID_CODE", "MFA code is invalid.", status_code=400)
            now = datetime.now(UTC)
            challenge.consumed_at = now
            self._audit(
                action="mfa.challenge.verify",
                outcome="success",
                actor_user_id=user_id,
                resource_id=challenge_id,
                trace_id=trace_id,
            )
            self.uow.commit()

    def consume_recovery_code(
        self,
        *,
        user_id: UUID,
        challenge_id: UUID,
        recovery_code: str,
        trace_id: str | None = None,
    ) -> None:
        normalized = _normalize_recovery_code(recovery_code)
        with self.uow:
            session = self._session()
            self._require_enrolled_active_user_in_session(session, user_id)
            self._load_pending_challenge_in_session(
                session, user_id=user_id, challenge_id=challenge_id
            )
            recovery_hash = _hash_recovery_code(normalized)
            record = (
                session.execute(
                    select(AuthMfaRecoveryCode).where(AuthMfaRecoveryCode.user_id == user_id)
                )
                .scalars()
                .all()
            )
            matching = next(
                (item for item in record if hmac.compare_digest(item.code_hash, recovery_hash)),
                None,
            )
            if matching is None:
                self._audit(
                    action="mfa.recovery.use",
                    outcome="failure",
                    actor_user_id=user_id,
                    resource_id=challenge_id,
                    reason="invalid_recovery_code",
                    trace_id=trace_id,
                )
                self.uow.commit()
                raise MfaError(
                    "MFA_INVALID_RECOVERY_CODE",
                    "MFA recovery code is invalid.",
                    status_code=400,
                )
            now = datetime.now(UTC)
            if matching.used_at is not None or _as_utc(matching.expires_at) <= now:
                self._audit(
                    action="mfa.recovery.use",
                    outcome="failure",
                    actor_user_id=user_id,
                    resource_id=challenge_id,
                    reason="expired_or_used",
                    trace_id=trace_id,
                )
                self.uow.commit()
                raise MfaError(
                    "MFA_INVALID_RECOVERY_CODE",
                    "MFA recovery code is invalid.",
                    status_code=400,
                )
            matching.used_at = now
            challenge = session.get(AuthMfaChallenge, challenge_id)
            if challenge is not None:
                challenge.consumed_at = now
            self._audit(
                action="mfa.recovery.use",
                outcome="success",
                actor_user_id=user_id,
                resource_id=challenge_id,
                trace_id=trace_id,
            )
            self.uow.commit()

    def assert_privileged_access(
        self,
        *,
        user_id: UUID,
        trace_id: str | None = None,
    ) -> None:
        with self.uow:
            session = self._session()
            self._require_active_user_in_session(session, user_id)
            self.uow.commit()
        if not self.has_privileged_role(user_id=user_id):
            return
        if not self.is_enrolled(user_id=user_id):
            self._audit_privileged_block(user_id=user_id, trace_id=trace_id, reason="not_enrolled")
            raise MfaError(
                "MFA_PRIVILEGED_ACCESS_BLOCKED",
                "Privileged access requires MFA enrollment.",
                status_code=403,
            )

    def reset_mfa(
        self,
        *,
        user_id: UUID,
        channel: MfaResetChannel,
        channel_proof: str,
        trace_id: str | None = None,
    ) -> MfaEnrollment:
        with self.uow:
            session = self._session()
            self._require_active_user_in_session(session, user_id)
            secret = session.execute(
                select(AuthMfaSecret).where(AuthMfaSecret.user_id == user_id)
            ).scalar_one_or_none()
            if secret is None:
                raise MfaError("MFA_NOT_ENROLLED", "MFA is not enrolled.", status_code=404)
            if channel == MfaResetChannel.RECOVERY_CODE:
                _consume_reset_recovery_code_in_session(
                    session,
                    user_id=user_id,
                    recovery_code=channel_proof,
                )
            else:
                _verify_password_reset_proof_in_session(
                    session,
                    user_id=user_id,
                    reset_token=channel_proof,
                )
            new_secret = _generate_secret()
            secret.secret = new_secret
            secret.confirmed_at = None
            secret.recovery_codes_rotated_at = datetime.now(UTC)
            _purge_recovery_codes_in_session(session, user_id=user_id)
            recovery_codes = _generate_recovery_codes()
            _persist_recovery_codes(session, user_id=user_id, codes=recovery_codes)
            self._audit(
                action=f"mfa.reset.{channel.value}",
                outcome="success",
                actor_user_id=user_id,
                resource_id=user_id,
                trace_id=trace_id,
            )
            self.uow.commit()
            user_email = session.get(User, user_id)
            return MfaEnrollment(
                secret=new_secret,
                provisioning_uri=_build_provisioning_uri(
                    user_email=user_email.email if user_email else "user",
                    secret=new_secret,
                ),
                recovery_codes=recovery_codes,
            )

    def rotate_recovery_codes(
        self,
        *,
        user_id: UUID,
        trace_id: str | None = None,
    ) -> tuple[str, ...]:
        with self.uow:
            session = self._session()
            self._require_enrolled_active_user_in_session(session, user_id)
            codes = _generate_recovery_codes()
            _purge_recovery_codes_in_session(session, user_id=user_id)
            _persist_recovery_codes(session, user_id=user_id, codes=codes)
            secret = self._load_confirmed_secret_in_session(session, user_id)
            secret.recovery_codes_rotated_at = datetime.now(UTC)
            self._audit(
                action="mfa.recovery.rotate",
                outcome="success",
                actor_user_id=user_id,
                resource_id=user_id,
                trace_id=trace_id,
            )
            self.uow.commit()
            return codes

    def _audit_privileged_block(
        self,
        *,
        user_id: UUID,
        trace_id: str | None,
        reason: str,
    ) -> None:
        with self.uow:
            self._audit(
                action="mfa.privileged_access.block",
                outcome="denied",
                actor_user_id=user_id,
                resource_id=user_id,
                reason=reason,
                trace_id=trace_id,
            )
            self.uow.commit()

    def _require_active_user_in_session(self, session: Session, user_id: UUID) -> User:
        user = session.get(User, user_id)
        if user is None or user.deleted_at is not None or user.status != "active":
            raise MfaError("MFA_UNKNOWN_USER", "User was not found.", status_code=404)
        return user

    def _require_enrolled_active_user_in_session(self, session: Session, user_id: UUID) -> User:
        user = self._require_active_user_in_session(session, user_id)
        secret = session.execute(
            select(AuthMfaSecret).where(AuthMfaSecret.user_id == user.id)
        ).scalar_one_or_none()
        if secret is None or secret.confirmed_at is None:
            raise MfaError("MFA_NOT_ENROLLED", "MFA is not enrolled.", status_code=404)
        return user

    def _load_unconfirmed_secret_in_session(self, session: Session, user_id: UUID) -> AuthMfaSecret:
        secret = session.execute(
            select(AuthMfaSecret).where(AuthMfaSecret.user_id == user_id)
        ).scalar_one_or_none()
        if secret is None:
            raise MfaError("MFA_NOT_ENROLLED", "MFA enrollment is missing.", status_code=404)
        if secret.confirmed_at is not None:
            raise MfaError("MFA_ALREADY_ENROLLED", "MFA is already enrolled.", status_code=409)
        return secret

    def _load_confirmed_secret_in_session(self, session: Session, user_id: UUID) -> AuthMfaSecret:
        secret = session.execute(
            select(AuthMfaSecret).where(AuthMfaSecret.user_id == user_id)
        ).scalar_one_or_none()
        if secret is None or secret.confirmed_at is None:
            raise MfaError("MFA_NOT_ENROLLED", "MFA is not enrolled.", status_code=404)
        return secret

    def _load_pending_challenge_in_session(
        self, session: Session, *, user_id: UUID, challenge_id: UUID
    ) -> AuthMfaChallenge:
        challenge = session.execute(
            select(AuthMfaChallenge).where(AuthMfaChallenge.id == challenge_id)
        ).scalar_one_or_none()
        if challenge is None or challenge.user_id != user_id or challenge.consumed_at is not None:
            raise MfaError("MFA_INVALID_CHALLENGE", "MFA challenge is invalid.", status_code=404)
        if _as_utc(challenge.expires_at) <= datetime.now(UTC):
            raise MfaError(
                "MFA_CHALLENGE_EXPIRED",
                "MFA challenge has expired.",
                status_code=400,
            )
        return challenge

    def _audit(
        self,
        *,
        action: str,
        outcome: str,
        actor_user_id: UUID | None = None,
        resource_id: UUID | None = None,
        reason: str | None = None,
        before_summary: dict[str, object] | None = None,
        after_summary: dict[str, object] | None = None,
        trace_id: str | None = None,
    ) -> None:
        self._session().add(
            AuditLog(
                id=uuid4(),
                actor_user_id=actor_user_id,
                action=action,
                resource_type="mfa",
                resource_id=resource_id,
                outcome=outcome,
                reason=reason,
                trace_id=trace_id,
                before_summary=before_summary,
                after_summary=after_summary,
                source_context={},
            )
        )

    def _session(self) -> Session:
        if self.uow.session is None:
            raise RuntimeError("Database session not initialized in UoW.")
        return self.uow.session


def verify_totp(secret: bytes, *, code: str) -> bool:
    normalized = _normalize_totp_code(code)
    for offset in range(-TOTP_WINDOW, TOTP_WINDOW + 1):
        candidate = generate_totp(secret, timestamp=int(time.time()) + offset * TOTP_PERIOD_SECONDS)
        if hmac.compare_digest(candidate, normalized):
            return True
    return False


def generate_totp(secret: bytes, *, timestamp: int) -> str:
    counter = timestamp // TOTP_PERIOD_SECONDS
    counter_bytes = struct.pack(">Q", counter)
    digest = hmac.new(secret, counter_bytes, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code_int = (
        ((digest[offset] & 0x7F) << 24)
        | ((digest[offset + 1] & 0xFF) << 16)
        | ((digest[offset + 2] & 0xFF) << 8)
        | (digest[offset + 3] & 0xFF)
    )
    code = code_int % (10**TOTP_DIGITS)
    return str(code).rjust(TOTP_DIGITS, "0")


def _generate_secret() -> bytes:
    return secrets.token_bytes(20)


def _generate_recovery_codes() -> tuple[str, ...]:
    return tuple(secrets.token_urlsafe(RECOVERY_CODE_BYTES) for _ in range(RECOVERY_CODE_COUNT))


def _persist_recovery_codes(session: Session, *, user_id: UUID, codes: tuple[str, ...]) -> None:
    now = datetime.now(UTC)
    expires_at = now + RECOVERY_TTL
    for code in codes:
        session.add(
            AuthMfaRecoveryCode(
                id=uuid4(),
                user_id=user_id,
                code_hash=_hash_recovery_code(code),
                issued_at=now,
                expires_at=expires_at,
                used_at=None,
            )
        )


def _purge_recovery_codes_in_session(session: Session, *, user_id: UUID) -> None:
    codes = (
        session.execute(select(AuthMfaRecoveryCode).where(AuthMfaRecoveryCode.user_id == user_id))
        .scalars()
        .all()
    )
    for record in codes:
        session.delete(record)


def _consume_reset_recovery_code_in_session(
    session: Session, *, user_id: UUID, recovery_code: str
) -> None:
    normalized = _normalize_recovery_code(recovery_code)
    records = (
        session.execute(select(AuthMfaRecoveryCode).where(AuthMfaRecoveryCode.user_id == user_id))
        .scalars()
        .all()
    )
    target = next(
        (
            record
            for record in records
            if hmac.compare_digest(record.code_hash, _hash_recovery_code(normalized))
        ),
        None,
    )
    if target is None or target.used_at is not None:
        raise MfaError(
            "MFA_INVALID_RECOVERY_CODE",
            "MFA recovery code is invalid.",
            status_code=400,
        )
    if _as_utc(target.expires_at) <= datetime.now(UTC):
        raise MfaError(
            "MFA_INVALID_RECOVERY_CODE",
            "MFA recovery code is invalid.",
            status_code=400,
        )
    target.used_at = datetime.now(UTC)


def _verify_password_reset_proof_in_session(
    session: Session, *, user_id: UUID, reset_token: str
) -> None:
    from zayd_common.database.models import PasswordResetToken

    token_hash = hashlib.sha256(reset_token.encode("utf-8")).hexdigest()
    record = session.execute(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    ).scalar_one_or_none()
    if (
        record is None
        or record.user_id != user_id
        or record.used_at is not None
        or _as_utc(record.expires_at) <= datetime.now(UTC)
    ):
        raise MfaError(
            "MFA_RESET_REQUIRES_RECOVERY",
            "MFA reset requires a valid recovery code or password reset token.",
            status_code=400,
        )


def _build_provisioning_uri(*, user_email: str, secret: bytes) -> str:
    issuer = "Zayd"
    account = user_email or "user"
    encoded_secret = base64.b32encode(secret).decode("ascii").rstrip("=")
    label = f"{issuer}:{account}"
    return (
        f"otpauth://totp/{_quote(label)}?secret={encoded_secret}"
        f"&issuer={_quote(issuer)}&algorithm=SHA1&digits={TOTP_DIGITS}&period={TOTP_PERIOD_SECONDS}"
    )


def _quote(value: str) -> str:
    return value.replace(":", "%3A").replace(" ", "%20")


def _normalize_totp_code(code: str) -> str:
    cleaned = "".join(ch for ch in code if ch.isdigit())
    if len(cleaned) != TOTP_DIGITS:
        raise MfaError("MFA_INVALID_CODE", "MFA code is invalid.", status_code=400)
    return cleaned


def _normalize_recovery_code(code: str) -> str:
    cleaned = "".join(ch for ch in code.strip() if ch.isalnum() or ch in "-_")
    if not cleaned:
        raise MfaError(
            "MFA_INVALID_RECOVERY_CODE",
            "MFA recovery code is invalid.",
            status_code=400,
        )
    return cleaned


def _hash_recovery_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
