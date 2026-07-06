from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, String, Text
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


class User(Base):
    __tablename__ = "auth_users"

    id: Mapped[UUID] = mapped_column(BaseUUID, primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    preferred_language: Mapped[str] = mapped_column(String, default="th", nullable=False)
    preferred_madhhab: Mapped[str] = mapped_column(String, default="shafii", nullable=False)
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
    trace_id: Mapped[str | None] = mapped_column(String, nullable=True)
    before_summary: Mapped[dict[str, Any] | None] = mapped_column(BaseJSONB, nullable=True)
    after_summary: Mapped[dict[str, Any] | None] = mapped_column(BaseJSONB, nullable=True)
    source_context: Mapped[dict[str, Any]] = mapped_column(BaseJSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


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


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

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
