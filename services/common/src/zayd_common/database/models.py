import hashlib
import json
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


class Base(DeclarativeBase):
    pass


class BaseUUID(TypeDecorator[UUID]):
    """UUID class that supports both PostgreSQL native UUID and SQLite String validation."""

    impl = PG_UUID
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "sqlite":
            return dialect.type_descriptor(String(36))
        return dialect.type_descriptor(PG_UUID(as_uuid=True))

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return value
        if dialect.name == "sqlite":
            return str(value)
        return value

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return value
        if dialect.name == "sqlite":
            return UUID(value)
        return value


class BaseJSONB(TypeDecorator[dict[str, Any]]):
    """JSONB class that defaults to JSON in SQLite and JSONB in PostgreSQL."""

    impl = JSONB
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "sqlite":
            return dialect.type_descriptor(JSON())
        return dialect.type_descriptor(JSONB())


class BaseVector(TypeDecorator[list[float]]):
    """pgvector-compatible storage with JSON fallback for SQLite tests."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(String())
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return value
        vector = [float(item) for item in value]
        if dialect.name == "postgresql":
            return "[" + ",".join(str(item) for item in vector) + "]"
        return vector


class User(Base):
    __tablename__ = "auth_users"

    id: Mapped[UUID] = mapped_column(BaseUUID, primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    preferred_language: Mapped[str] = mapped_column(String, default="th", nullable=False)
    preferred_madhhab: Mapped[str] = mapped_column(String, default="shafii", nullable=False)
    answer_length: Mapped[str] = mapped_column(String, default="normal", nullable=False)
    show_arabic: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    history_mode: Mapped[str] = mapped_column(String, default="enabled", nullable=False)
    status: Mapped[str] = mapped_column(String, default="active", nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    row_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class Role(Base):
    __tablename__ = "auth_roles"

    id: Mapped[UUID] = mapped_column(BaseUUID, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    row_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class AuthPermission(Base):
    __tablename__ = "auth_permissions"
    __table_args__ = (UniqueConstraint("resource", "action"),)

    id: Mapped[UUID] = mapped_column(BaseUUID, primary_key=True, default=uuid4)
    resource: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class UserRole(Base):
    __tablename__ = "auth_user_roles"

    user_id: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("auth_users.id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("auth_roles.id", ondelete="RESTRICT"), primary_key=True
    )
    granted_by: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("auth_users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class RolePermission(Base):
    __tablename__ = "auth_role_permissions"

    role_id: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("auth_roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("auth_permissions.id", ondelete="RESTRICT"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[UUID] = mapped_column(BaseUUID, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False
    )
    session_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    ip_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    user_agent_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class AuthRefreshToken(Base):
    __tablename__ = "auth_refresh_tokens"

    id: Mapped[UUID] = mapped_column(BaseUUID, primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("auth_sessions.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    parent_token_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reuse_detected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class PasswordResetToken(Base):
    __tablename__ = "auth_password_reset_tokens"

    id: Mapped[UUID] = mapped_column(BaseUUID, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class AuthRateLimit(Base):
    __tablename__ = "auth_rate_limits"

    id: Mapped[UUID] = mapped_column(BaseUUID, primary_key=True, default=uuid4)
    bucket: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    action: Mapped[str] = mapped_column(String, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    blocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class AuthMfaSecret(Base):
    __tablename__ = "auth_mfa_secrets"

    id: Mapped[UUID] = mapped_column(BaseUUID, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    secret: Mapped[bytes] = mapped_column(String, nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recovery_codes_rotated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_used_counter: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class AuthMfaRecoveryCode(Base):
    __tablename__ = "auth_mfa_recovery_codes"

    id: Mapped[UUID] = mapped_column(BaseUUID, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False
    )
    code_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class AuthMfaChallenge(Base):
    __tablename__ = "auth_mfa_challenges"

    id: Mapped[UUID] = mapped_column(BaseUUID, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False
    )
    challenge_code: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class GuestSession(Base):
    __tablename__ = "guest_sessions"

    id: Mapped[UUID] = mapped_column(BaseUUID, primary_key=True, default=uuid4)
    session_token_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    ip_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    user_agent_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    converted_user_id: Mapped[UUID | None] = mapped_column(
        BaseUUID, ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True
    )
    message_quota: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    messages_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[UUID] = mapped_column(BaseUUID, primary_key=True, default=uuid4)
    actor_user_id: Mapped[UUID | None] = mapped_column(
        BaseUUID, ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String, nullable=False)
    resource_type: Mapped[str] = mapped_column(String, nullable=False)
    resource_id: Mapped[UUID | None] = mapped_column(BaseUUID, nullable=True)
    outcome: Mapped[str] = mapped_column(String, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String, nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String, nullable=True)
    before_summary: Mapped[dict[str, Any] | None] = mapped_column(BaseJSONB, nullable=True)
    after_summary: Mapped[dict[str, Any] | None] = mapped_column(BaseJSONB, nullable=True)
    source_context: Mapped[dict[str, Any]] = mapped_column(BaseJSONB, default=dict, nullable=False)
    hash_algorithm: Mapped[str] = mapped_column(String, default="sha256", nullable=False)
    previous_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    content_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


SENSITIVE_AUDIT_KEYS = {
    "authorization",
    "access_token",
    "refresh_token",
    "token",
    "password",
    "password_hash",
    "secret",
    "mfa_secret",
    "recovery_code",
    "api_key",
    "credential",
}
AUDIT_REDACTION = "[REDACTED]"


def _redact_audit_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): AUDIT_REDACTION
            if any(marker in str(key).lower() for marker in SENSITIVE_AUDIT_KEYS)
            else _redact_audit_value(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_audit_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_audit_value(item) for item in value)
    return value


def _audit_hash_payload(record: AuditLog) -> dict[str, Any]:
    return {
        "id": record.id,
        "actor_user_id": record.actor_user_id,
        "action": record.action,
        "resource_type": record.resource_type,
        "resource_id": record.resource_id,
        "outcome": record.outcome,
        "reason": record.reason,
        "request_id": record.request_id,
        "trace_id": record.trace_id,
        "before_summary": record.before_summary,
        "after_summary": record.after_summary,
        "source_context": record.source_context or {},
        "created_at": record.created_at,
        "previous_hash": record.previous_hash,
    }


def _audit_json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    raise TypeError(f"Value of type {type(value).__name__} is not JSON serializable")


@event.listens_for(AuditLog, "before_insert")
def _set_audit_hash(_mapper: Any, connection: Any, target: AuditLog) -> None:
    now = datetime.now(UTC)
    if target.id is None:
        target.id = uuid4()
    if target.created_at is None:
        target.created_at = now
    if target.updated_at is None:
        target.updated_at = target.created_at
    target.before_summary = _redact_audit_value(target.before_summary)
    target.after_summary = _redact_audit_value(target.after_summary)
    target.source_context = _redact_audit_value(target.source_context or {})
    if target.hash_algorithm is None:
        target.hash_algorithm = "sha256"
    if target.previous_hash is None:
        target.previous_hash = connection.execute(
            select(AuditLog.content_hash)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .limit(1)
        ).scalar_one_or_none()
    canonical = json.dumps(
        _audit_hash_payload(target),
        default=_audit_json_default,
        sort_keys=True,
        separators=(",", ":"),
    )
    target.content_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@event.listens_for(AuditLog, "before_update")
def _deny_audit_update(_mapper: Any, _connection: Any, _target: AuditLog) -> None:
    raise ValueError("audit_logs are append-only and cannot be updated")


@event.listens_for(AuditLog, "before_delete")
def _deny_audit_delete(_mapper: Any, _connection: Any, _target: AuditLog) -> None:
    raise ValueError("audit_logs are append-only and cannot be deleted")


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[UUID] = mapped_column(BaseUUID, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    source_type: Mapped[str] = mapped_column(String, nullable=False)
    owner: Mapped[str | None] = mapped_column(String, nullable=True)
    website: Mapped[str | None] = mapped_column(String, nullable=True)
    language: Mapped[str] = mapped_column(String, nullable=False)
    country: Mapped[str | None] = mapped_column(String, nullable=True)
    reliability_level: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("auth_users.id", ondelete="RESTRICT"), nullable=False
    )
    updated_by: Mapped[UUID | None] = mapped_column(
        BaseUUID, ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    row_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class SourceLicense(Base):
    __tablename__ = "source_licenses"

    id: Mapped[UUID] = mapped_column(BaseUUID, primary_key=True, default=uuid4)
    source_id: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False
    )
    license_name: Mapped[str] = mapped_column(String, nullable=False)
    license_version: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="unknown", nullable=False)
    storage_permission: Mapped[str] = mapped_column(String, default="unknown", nullable=False)
    embedding_permission: Mapped[str] = mapped_column(String, default="unknown", nullable=False)
    commercial_use: Mapped[str] = mapped_column(String, default="unknown", nullable=False)
    redistribution: Mapped[str] = mapped_column(String, default="unknown", nullable=False)
    attribution_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    attribution_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    permission_document_key: Mapped[str | None] = mapped_column(String, nullable=True)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("auth_users.id", ondelete="RESTRICT"), nullable=False
    )
    updated_by: Mapped[UUID | None] = mapped_column(
        BaseUUID, ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    row_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class Provider(Base):
    __tablename__ = "providers"

    id: Mapped[UUID] = mapped_column(BaseUUID, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    provider_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="disabled", nullable=False)
    base_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    secret_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    terms_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_policy_json: Mapped[dict[str, Any]] = mapped_column(
        BaseJSONB, default=dict, nullable=False
    )
    created_by: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("auth_users.id", ondelete="RESTRICT"), nullable=False
    )
    updated_by: Mapped[UUID | None] = mapped_column(
        BaseUUID, ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    row_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class ModelConfiguration(Base):
    __tablename__ = "model_configurations"

    id: Mapped[UUID] = mapped_column(BaseUUID, primary_key=True, default=uuid4)
    provider_id: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("providers.id", ondelete="RESTRICT"), nullable=False
    )
    model_name: Mapped[str] = mapped_column(String, nullable=False)
    model_type: Mapped[str] = mapped_column(String, nullable=False)
    configuration_json: Mapped[dict[str, Any]] = mapped_column(
        BaseJSONB, default=dict, nullable=False
    )
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String, default="disabled", nullable=False)
    created_by: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("auth_users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    row_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class PromptVersion(Base):
    __tablename__ = "prompt_versions"
    __table_args__ = (UniqueConstraint("name", "version"),)

    id: Mapped[UUID] = mapped_column(BaseUUID, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[str] = mapped_column(String, nullable=False)
    prompt_hash: Mapped[str] = mapped_column(String, nullable=False)
    prompt_body: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(BaseJSONB, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String, default="draft", nullable=False)
    created_by: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("auth_users.id", ondelete="RESTRICT"), nullable=False
    )
    approved_by: Mapped[UUID | None] = mapped_column(
        BaseUUID, ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class PolicyVersion(Base):
    __tablename__ = "policy_versions"
    __table_args__ = (UniqueConstraint("policy_name", "version"),)

    id: Mapped[UUID] = mapped_column(BaseUUID, primary_key=True, default=uuid4)
    policy_name: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[str] = mapped_column(String, nullable=False)
    policy_hash: Mapped[str] = mapped_column(String, nullable=False)
    policy_json: Mapped[dict[str, Any]] = mapped_column(BaseJSONB, nullable=False)
    status: Mapped[str] = mapped_column(String, default="draft", nullable=False)
    created_by: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("auth_users.id", ondelete="RESTRICT"), nullable=False
    )
    approved_by: Mapped[UUID | None] = mapped_column(
        BaseUUID, ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[UUID] = mapped_column(BaseUUID, primary_key=True, default=uuid4)
    source_id: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False
    )
    source_license_id: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("source_licenses.id", ondelete="RESTRICT"), nullable=False
    )
    canonical_id: Mapped[str] = mapped_column(String, nullable=False)
    document_type: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    author: Mapped[str | None] = mapped_column(String, nullable=True)
    translator: Mapped[str | None] = mapped_column(String, nullable=True)
    publisher: Mapped[str | None] = mapped_column(String, nullable=True)
    edition: Mapped[str | None] = mapped_column(String, nullable=True)
    language: Mapped[str] = mapped_column(String, nullable=False)
    madhhab: Mapped[str] = mapped_column(String, default="unknown", nullable=False)
    review_status: Mapped[str] = mapped_column(String, default="draft", nullable=False)
    published_version_id: Mapped[UUID | None] = mapped_column(BaseUUID, nullable=True)
    created_by: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("auth_users.id", ondelete="RESTRICT"), nullable=False
    )
    updated_by: Mapped[UUID | None] = mapped_column(
        BaseUUID, ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    row_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id: Mapped[UUID] = mapped_column(BaseUUID, primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("documents.id", ondelete="RESTRICT"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, default="uploaded", nullable=False)
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    original_file_key: Mapped[str | None] = mapped_column(String, nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(BaseJSONB, default=dict, nullable=False)
    created_by: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("auth_users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReviewTask(Base):
    __tablename__ = "review_tasks"
    __table_args__ = (
        UniqueConstraint(
            "document_version_id", "review_level",
            name="uq_review_tasks_open_level",
        ),
    )

    id: Mapped[UUID] = mapped_column(BaseUUID, primary_key=True, default=uuid4)
    document_version_id: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[UUID] = mapped_column(BaseUUID, nullable=False)
    assigned_to: Mapped[UUID | None] = mapped_column(
        BaseUUID, ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True
    )
    review_level: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="open", nullable=False)
    priority: Mapped[str] = mapped_column(String, default="normal", nullable=False)
    category: Mapped[str | None] = mapped_column(String, nullable=True)
    language: Mapped[str | None] = mapped_column(String, nullable=True)
    madhhab: Mapped[str | None] = mapped_column(String, nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    row_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_by: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("auth_users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class ReviewRevision(Base):
    __tablename__ = "review_revisions"

    id: Mapped[UUID] = mapped_column(BaseUUID, primary_key=True, default=uuid4)
    review_task_id: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("review_tasks.id", ondelete="CASCADE"), nullable=False
    )
    document_version_id: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False
    )
    actor_user_id: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("auth_users.id", ondelete="RESTRICT"), nullable=False
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    base_task_row_version: Mapped[int] = mapped_column(Integer, nullable=False)
    text_before: Mapped[str | None] = mapped_column(Text, nullable=True)
    text_after: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_before: Mapped[dict[str, Any]] = mapped_column(BaseJSONB, default=dict, nullable=False)
    metadata_after: Mapped[dict[str, Any]] = mapped_column(BaseJSONB, default=dict, nullable=False)
    diff_summary: Mapped[dict[str, Any]] = mapped_column(BaseJSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class ReviewDecisionRecord(Base):
    __tablename__ = "review_decisions"

    id: Mapped[UUID] = mapped_column(BaseUUID, primary_key=True, default=uuid4)
    review_task_id: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("review_tasks.id", ondelete="CASCADE"), nullable=False
    )
    document_version_id: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False
    )
    actor_user_id: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("auth_users.id", ondelete="RESTRICT"), nullable=False
    )
    decision: Mapped[str] = mapped_column(String, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    base_task_row_version: Mapped[int] = mapped_column(Integer, nullable=False)
    resulting_task_status: Mapped[str] = mapped_column(String, nullable=False)
    resulting_document_status: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class ReviewApproval(Base):
    __tablename__ = "review_approvals"

    id: Mapped[UUID] = mapped_column(BaseUUID, primary_key=True, default=uuid4)
    document_version_id: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False
    )
    review_task_id: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("review_tasks.id", ondelete="CASCADE"), nullable=False
    )
    approver_id: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("auth_users.id", ondelete="RESTRICT"), nullable=False
    )
    approval_level: Mapped[str] = mapped_column(String, nullable=False)
    content_risk: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="active", nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by: Mapped[UUID | None] = mapped_column(
        BaseUUID, ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True
    )
    revoke_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class ReviewComment(Base):
    __tablename__ = "review_comments"

    id: Mapped[UUID] = mapped_column(BaseUUID, primary_key=True, default=uuid4)
    review_task_id: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("review_tasks.id", ondelete="CASCADE"), nullable=False
    )
    author_id: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("auth_users.id", ondelete="RESTRICT"), nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    anchor_json: Mapped[dict[str, Any]] = mapped_column(BaseJSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint(
            "document_version_id",
            "chunk_index",
            name="uq_document_chunks_version_index",
        ),
        UniqueConstraint(
            "document_version_id",
            "content_hash",
            name="uq_document_chunks_version_hash",
        ),
    )

    id: Mapped[UUID] = mapped_column(BaseUUID, primary_key=True, default=uuid4)
    document_version_id: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_normalized: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section: Mapped[str | None] = mapped_column(String, nullable=True)
    reference: Mapped[str | None] = mapped_column(String, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(BaseJSONB, default=dict, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    chunking_strategy_version: Mapped[str] = mapped_column(String, nullable=False)
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class EmbeddingRecord(Base):
    __tablename__ = "embedding_records"
    __table_args__ = (
        UniqueConstraint(
            "chunk_id",
            "model_configuration_id",
            name="uq_embedding_records_chunk_model",
        ),
    )

    id: Mapped[UUID] = mapped_column(BaseUUID, primary_key=True, default=uuid4)
    document_version_id: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False
    )
    chunk_id: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=False
    )
    model_configuration_id: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("model_configurations.id", ondelete="RESTRICT"), nullable=False
    )
    provider_id: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("providers.id", ondelete="RESTRICT"), nullable=False
    )
    embedding: Mapped[list[float]] = mapped_column(BaseVector, nullable=False)
    embedding_hash: Mapped[str] = mapped_column(String, nullable=False)
    dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, default="staged", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class Citation(Base):
    __tablename__ = "citations"
    __table_args__ = (
        UniqueConstraint(
            "canonical_reference",
            "document_version_id",
            name="uq_citations_canonical_version",
        ),
    )

    id: Mapped[UUID] = mapped_column(BaseUUID, primary_key=True, default=uuid4)
    canonical_reference: Mapped[str] = mapped_column(Text, nullable=False)
    document_version_id: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("document_versions.id", ondelete="RESTRICT"), nullable=False
    )
    chunk_id: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("document_chunks.id", ondelete="RESTRICT"), nullable=False
    )
    citation_type: Mapped[str] = mapped_column(String, nullable=False)
    display_title: Mapped[str] = mapped_column(Text, nullable=False)
    arabic_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    thai_translation: Mapped[str | None] = mapped_column(Text, nullable=True)
    hadith_grade: Mapped[str | None] = mapped_column(String, nullable=True)
    volume: Mapped[str | None] = mapped_column(String, nullable=True)
    page: Mapped[str | None] = mapped_column(String, nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class RetrievalRun(Base):
    __tablename__ = "retrieval_runs"

    id: Mapped[UUID] = mapped_column(BaseUUID, primary_key=True, default=uuid4)
    request_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    trace_id: Mapped[str | None] = mapped_column(String, nullable=True)
    query_original: Mapped[str] = mapped_column(Text, nullable=False)
    query_normalized: Mapped[str] = mapped_column(Text, nullable=False)
    query_expansions: Mapped[dict[str, Any]] = mapped_column(
        BaseJSONB, default=dict, nullable=False
    )
    filters: Mapped[dict[str, Any]] = mapped_column(BaseJSONB, default=dict, nullable=False)
    retriever_version: Mapped[str] = mapped_column(String, nullable=False)
    evidence_sufficient: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class RetrievalResult(Base):
    __tablename__ = "retrieval_results"

    id: Mapped[UUID] = mapped_column(BaseUUID, primary_key=True, default=uuid4)
    retrieval_run_id: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("retrieval_runs.id", ondelete="CASCADE"), nullable=False
    )
    document_version_id: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("document_versions.id", ondelete="RESTRICT"), nullable=False
    )
    chunk_id: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("document_chunks.id", ondelete="RESTRICT"), nullable=False
    )
    citation_id: Mapped[UUID | None] = mapped_column(BaseUUID, nullable=True)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    score_exact: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_full_text: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_vector: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_reranker: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_final: Mapped[float] = mapped_column(Float, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(BaseJSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[UUID] = mapped_column(BaseUUID, primary_key=True, default=uuid4)
    user_id: Mapped[UUID | None] = mapped_column(
        BaseUUID, ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True
    )
    guest_session_id: Mapped[str | None] = mapped_column(String, nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String, default="th", nullable=False)
    madhhab: Mapped[str] = mapped_column(String, default="shafii", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[UUID] = mapped_column(BaseUUID, primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    sender_type: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    body_hash: Mapped[str] = mapped_column(String, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(BaseJSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[UUID] = mapped_column(BaseUUID, primary_key=True, default=uuid4)
    message_id: Mapped[UUID] = mapped_column(BaseUUID, nullable=False, unique=True)
    retrieval_run_id: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("retrieval_runs.id", ondelete="RESTRICT"), nullable=False
    )
    model_configuration_id: Mapped[UUID] = mapped_column(BaseUUID, nullable=False)
    prompt_version_id: Mapped[UUID] = mapped_column(BaseUUID, nullable=False)
    policy_version_id: Mapped[UUID] = mapped_column(BaseUUID, nullable=False)
    risk_level: Mapped[str] = mapped_column(String, nullable=False)
    madhhab: Mapped[str] = mapped_column(String, nullable=False)
    answer_json: Mapped[dict[str, Any]] = mapped_column(BaseJSONB, default=dict, nullable=False)
    confidence_level: Mapped[str] = mapped_column(String, nullable=False)
    evidence_sufficient: Mapped[bool] = mapped_column(Boolean, nullable=False)
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class SavedAnswer(Base):
    __tablename__ = "saved_answers"

    id: Mapped[UUID] = mapped_column(BaseUUID, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False
    )
    answer_id: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("answers.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[UUID] = mapped_column(BaseUUID, primary_key=True, default=uuid4)
    user_id: Mapped[UUID | None] = mapped_column(
        BaseUUID, ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True
    )
    answer_id: Mapped[UUID | None] = mapped_column(BaseUUID, nullable=True)
    citation_id: Mapped[UUID | None] = mapped_column(BaseUUID, nullable=True)
    category: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, default="open", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[UUID] = mapped_column(BaseUUID, primary_key=True, default=uuid4)
    feedback_id: Mapped[UUID | None] = mapped_column(
        BaseUUID, ForeignKey("feedback.id", ondelete="SET NULL"), nullable=True
    )
    severity: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="open", nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    affected_answer_id: Mapped[UUID | None] = mapped_column(BaseUUID, nullable=True)
    affected_document_id: Mapped[UUID | None] = mapped_column(
        BaseUUID, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    affected_citation_id: Mapped[UUID | None] = mapped_column(BaseUUID, nullable=True)
    opened_by: Mapped[UUID] = mapped_column(
        BaseUUID, ForeignKey("auth_users.id", ondelete="RESTRICT"), nullable=False
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
