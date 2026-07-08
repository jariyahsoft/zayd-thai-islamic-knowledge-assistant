"""Document publishing service.

Freezes an approved document version, creates deterministic retrieval chunks,
records pipeline versions, and exposes the version atomically for retrieval.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from sqlalchemy import delete, select

from zayd_common.chunking import (
    CHUNKING_FRAMEWORK_VERSION,
    ChunkingError,
    chunk_text_for_retrieval,
    chunking_strategy_versions,
)
from zayd_common.database.models import (
    AuditLog,
    Document,
    DocumentChunk,
    DocumentVersion,
    ReviewApproval,
    SourceLicense,
)
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.enums import DocumentStatus
from zayd_common.license_policy import (
    LICENSE_POLICY_ENGINE_VERSION,
    LicensePolicyInput,
    evaluate_license_policy,
)
from zayd_common.scholar_approval import SCHOLAR_APPROVAL_POLICY_VERSION
from zayd_common.state_machines import DocumentStateMachine, TransitionMetadata

DOCUMENT_PUBLISH_POLICY_VERSION = "document-publish-v1"
CHUNKING_STRATEGY_VERSION = CHUNKING_FRAMEWORK_VERSION
EMBEDDING_PIPELINE_VERSION = "embedding-record-v1"
CITATION_PIPELINE_VERSION = "canonical-citation-v1"
PUBLISHING_METADATA_KEY = "publishing"

PublishErrorCode = Literal[
    "DOCUMENT_PUBLISH_VERSION_NOT_FOUND",
    "DOCUMENT_PUBLISH_DOCUMENT_NOT_FOUND",
    "DOCUMENT_PUBLISH_LICENSE_NOT_FOUND",
    "DOCUMENT_PUBLISH_ACCESS_DENIED",
    "DOCUMENT_PUBLISH_INVALID_STATUS",
    "DOCUMENT_PUBLISH_APPROVAL_REQUIRED",
    "DOCUMENT_PUBLISH_LICENSE_BLOCKED",
    "DOCUMENT_PUBLISH_EMPTY_CONTENT",
    "DOCUMENT_PUBLISH_PIPELINE_FAILED",
]

_PUBLISH_ROLES = frozenset({"admin", "senior_scholar"})
_REQUIRED_BY_RISK: dict[str, tuple[str, ...]] = {
    "routine": ("initial",),
    "sensitive": ("initial", "scholar"),
    "restricted": ("initial", "scholar", "board"),
}
_MAX_CHUNK_WORDS = 180


class DocumentPublishingError(Exception):
    """Raised when a document version cannot be published."""

    def __init__(
        self,
        code: PublishErrorCode,
        message: str,
        *,
        status_code: int = 409,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class PublishedChunkPublic:
    id: UUID
    chunk_index: int
    content_hash: str
    reference: str | None
    is_published: bool


@dataclass(frozen=True)
class DocumentPublishResult:
    document_id: UUID
    document_version_id: UUID
    published_version_id: UUID
    document_status: str
    version_status: str
    chunk_count: int
    chunks: tuple[PublishedChunkPublic, ...]
    policy_version: str
    license_policy_version: str
    scholar_approval_policy_version: str
    chunking_strategy_version: str
    embedding_pipeline_version: str
    citation_pipeline_version: str
    published_at: datetime
    idempotent: bool


class DocumentPublishingService:
    """Publishes approved document versions for retrieval."""

    def __init__(
        self,
        uow: SQLAlchemyUnitOfWork,
        *,
        before_visibility_flip: Callable[[], None] | None = None,
    ) -> None:
        self.uow = uow
        self.before_visibility_flip = before_visibility_flip

    def publish_document_version(
        self,
        *,
        document_version_id: UUID,
        actor_user_id: UUID,
        principal_roles: frozenset[str],
        content_risk: str,
        reason: str,
        trace_id: str | None = None,
        today: date | None = None,
    ) -> DocumentPublishResult:
        """Publish one reviewed document version."""
        normalized_reason = reason.strip()
        if not normalized_reason:
            raise DocumentPublishingError(
                "DOCUMENT_PUBLISH_INVALID_STATUS",
                "Publish reason is required.",
                status_code=400,
            )
        normalized_risk = _normalize_risk(content_risk)
        if not principal_roles & _PUBLISH_ROLES:
            raise DocumentPublishingError(
                "DOCUMENT_PUBLISH_ACCESS_DENIED",
                "Only senior scholars or admins can publish documents.",
                status_code=403,
            )

        with self.uow:
            session = self._session()
            version = session.get(DocumentVersion, document_version_id)
            if version is None:
                raise DocumentPublishingError(
                    "DOCUMENT_PUBLISH_VERSION_NOT_FOUND",
                    "Document version not found.",
                    status_code=404,
                )
            document = session.get(Document, version.document_id)
            if document is None:
                raise DocumentPublishingError(
                    "DOCUMENT_PUBLISH_DOCUMENT_NOT_FOUND",
                    "Document not found for this version.",
                    status_code=404,
                )
            license_record = session.get(SourceLicense, document.source_license_id)
            if license_record is None:
                raise DocumentPublishingError(
                    "DOCUMENT_PUBLISH_LICENSE_NOT_FOUND",
                    "Source license not found for this document.",
                    status_code=404,
                )

            existing_chunks = self._chunks_for_version(session, version.id)
            if self._is_already_published(document, version):
                result = self._published_result(
                    document=document,
                    version=version,
                    chunks=existing_chunks,
                    published_at=version.frozen_at or datetime.now(UTC),
                    idempotent=True,
                )
                self.uow.commit()
                return result

            self._assert_status_allows_publish(document, version, actor_user_id, normalized_reason)
            self._assert_approvals_ready(session, version.id, normalized_risk)
            license_decision = evaluate_license_policy(
                _policy_input(license_record),
                workflow="retrieval",
                today=today or datetime.now(UTC).date(),
            )
            if not license_decision.workflow_allowed:
                self._audit(
                    session,
                    action="documents.publish",
                    outcome="denied",
                    actor_user_id=actor_user_id,
                    resource_id=document.id,
                    reason=",".join(license_decision.reason_codes),
                    after_summary={
                        "document_version_id": str(version.id),
                        "source_license_id": str(license_record.id),
                        "license_policy_version": license_decision.policy_version,
                        "reason_codes": list(license_decision.reason_codes),
                    },
                    trace_id=trace_id,
                )
                self.uow.commit()
                raise DocumentPublishingError(
                    "DOCUMENT_PUBLISH_LICENSE_BLOCKED",
                    "License policy blocks retrieval publishing.",
                    status_code=409,
                )

            text = (version.extracted_text or "").strip()
            if not text:
                raise DocumentPublishingError(
                    "DOCUMENT_PUBLISH_EMPTY_CONTENT",
                    "Document version has no extracted text to publish.",
                    status_code=409,
                )

            if existing_chunks:
                session.execute(
                    delete(DocumentChunk).where(DocumentChunk.document_version_id == version.id)
                )
                session.flush()

            now = datetime.now(UTC)
            generated_chunks = _build_chunks(
                document=document,
                version=version,
                text=text,
                license_record=license_record,
                published_at=now,
            )
            for chunk in generated_chunks:
                session.add(chunk)
            session.flush()

            metadata = dict(version.metadata_json or {})
            metadata[PUBLISHING_METADATA_KEY] = _publishing_metadata(
                document=document,
                version=version,
                license_record=license_record,
                license_reason_codes=license_decision.reason_codes,
                content_risk=normalized_risk,
                actor_user_id=actor_user_id,
                published_at=now,
            )
            version.metadata_json = metadata
            version.status = DocumentStatus.PUBLISHED.value
            version.frozen_at = now

            if self.before_visibility_flip is not None:
                try:
                    self.before_visibility_flip()
                except Exception as exc:  # pragma: no cover - exercised by tests
                    raise DocumentPublishingError(
                        "DOCUMENT_PUBLISH_PIPELINE_FAILED",
                        "Publish pipeline failed before visibility changed.",
                        status_code=503,
                    ) from exc

            for chunk in generated_chunks:
                chunk.is_published = True
            document.review_status = DocumentStatus.PUBLISHED.value
            document.published_version_id = version.id
            document.updated_by = actor_user_id
            document.updated_at = now
            document.row_version += 1

            self._audit(
                session,
                action="documents.publish",
                outcome="success",
                actor_user_id=actor_user_id,
                resource_id=document.id,
                after_summary={
                    "document_version_id": str(version.id),
                    "published_version_id": str(version.id),
                    "chunk_count": len(generated_chunks),
                    "content_risk": normalized_risk,
                    "policy_version": DOCUMENT_PUBLISH_POLICY_VERSION,
                    "license_policy_version": license_decision.policy_version,
                    "scholar_approval_policy_version": SCHOLAR_APPROVAL_POLICY_VERSION,
                    "chunking_strategy_version": CHUNKING_STRATEGY_VERSION,
                    "chunking_strategy_versions": list(chunking_strategy_versions()),
                    "embedding_pipeline_version": EMBEDDING_PIPELINE_VERSION,
                    "citation_pipeline_version": CITATION_PIPELINE_VERSION,
                },
                trace_id=trace_id,
            )
            result = self._published_result(
                document=document,
                version=version,
                chunks=generated_chunks,
                published_at=now,
                idempotent=False,
            )
            self.uow.commit()
            return result

    def _assert_status_allows_publish(
        self,
        document: Document,
        version: DocumentVersion,
        actor_user_id: UUID,
        reason: str,
    ) -> None:
        if (
            document.published_version_id is not None
            and document.published_version_id != version.id
        ):
            raise DocumentPublishingError(
                "DOCUMENT_PUBLISH_INVALID_STATUS",
                "A different document version is already published.",
                status_code=409,
            )
        document_status = _document_status(document.review_status)
        if (
            document_status == DocumentStatus.PUBLISHED
            and document.published_version_id == version.id
        ):
            return
        if document_status != DocumentStatus.SCHOLAR_APPROVED:
            raise DocumentPublishingError(
                "DOCUMENT_PUBLISH_INVALID_STATUS",
                "Document must be scholar approved before publishing.",
                status_code=409,
            )
        DocumentStateMachine.validate_transition(
            document_status,
            DocumentStatus.PUBLISHED,
            TransitionMetadata(actor_id=str(actor_user_id), reason=reason),
        )
        if version.status not in {
            DocumentStatus.SCHOLAR_APPROVED.value,
            "parsed",
            "reviewed",
            "approved",
        }:
            raise DocumentPublishingError(
                "DOCUMENT_PUBLISH_INVALID_STATUS",
                "Document version is not ready to publish.",
                status_code=409,
            )

    @staticmethod
    def _assert_approvals_ready(session: Any, document_version_id: UUID, content_risk: str) -> None:
        required = list(_REQUIRED_BY_RISK[content_risk])
        now = datetime.now(UTC)
        approvals = list(
            session.execute(
                select(ReviewApproval)
                .where(ReviewApproval.document_version_id == document_version_id)
                .where(ReviewApproval.status == "active")
                .where(
                    (ReviewApproval.valid_until.is_(None))
                    | (ReviewApproval.valid_until > now)
                )
            ).scalars().all()
        )
        active_levels = {approval.approval_level for approval in approvals}
        missing = [level for level in required if level not in active_levels]
        if missing:
            raise DocumentPublishingError(
                "DOCUMENT_PUBLISH_APPROVAL_REQUIRED",
                "Required scholar approvals are missing.",
                status_code=409,
            )

    @staticmethod
    def _is_already_published(document: Document, version: DocumentVersion) -> bool:
        return (
            document.review_status == DocumentStatus.PUBLISHED.value
            and document.published_version_id == version.id
            and version.status == DocumentStatus.PUBLISHED.value
            and version.frozen_at is not None
        )

    @staticmethod
    def _chunks_for_version(session: Any, document_version_id: UUID) -> list[DocumentChunk]:
        return list(
            session.execute(
                select(DocumentChunk)
                .where(DocumentChunk.document_version_id == document_version_id)
                .order_by(DocumentChunk.chunk_index)
            ).scalars().all()
        )

    @staticmethod
    def _published_result(
        *,
        document: Document,
        version: DocumentVersion,
        chunks: list[DocumentChunk],
        published_at: datetime,
        idempotent: bool,
    ) -> DocumentPublishResult:
        return DocumentPublishResult(
            document_id=document.id,
            document_version_id=version.id,
            published_version_id=version.id,
            document_status=document.review_status,
            version_status=version.status,
            chunk_count=len(chunks),
            chunks=tuple(
                PublishedChunkPublic(
                    id=chunk.id,
                    chunk_index=chunk.chunk_index,
                    content_hash=chunk.content_hash,
                    reference=chunk.reference,
                    is_published=chunk.is_published,
                )
                for chunk in sorted(chunks, key=lambda item: item.chunk_index)
            ),
            policy_version=DOCUMENT_PUBLISH_POLICY_VERSION,
            license_policy_version=LICENSE_POLICY_ENGINE_VERSION,
            scholar_approval_policy_version=SCHOLAR_APPROVAL_POLICY_VERSION,
            chunking_strategy_version=CHUNKING_STRATEGY_VERSION,
            embedding_pipeline_version=EMBEDDING_PIPELINE_VERSION,
            citation_pipeline_version=CITATION_PIPELINE_VERSION,
            published_at=published_at,
            idempotent=idempotent,
        )

    @staticmethod
    def _audit(
        session: Any,
        *,
        action: str,
        outcome: str,
        actor_user_id: UUID | None = None,
        resource_id: UUID | None = None,
        reason: str | None = None,
        after_summary: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> None:
        session.add(
            AuditLog(
                id=uuid4(),
                actor_user_id=actor_user_id,
                action=action,
                resource_type="document",
                resource_id=resource_id,
                outcome=outcome,
                reason=reason,
                request_id=trace_id,
                trace_id=trace_id,
                after_summary=after_summary,
                source_context={},
            )
        )

    def _session(self) -> Any:
        if self.uow.session is None:
            raise RuntimeError("Database session not initialised in UoW.")
        return self.uow.session


def _normalize_risk(content_risk: str) -> str:
    normalized = content_risk.strip().lower()
    if normalized not in _REQUIRED_BY_RISK:
        raise DocumentPublishingError(
            "DOCUMENT_PUBLISH_INVALID_STATUS",
            "content_risk must be routine, sensitive, or restricted.",
            status_code=400,
        )
    return normalized


def _document_status(status: str) -> DocumentStatus:
    try:
        return DocumentStatus(status)
    except ValueError as exc:
        raise DocumentPublishingError(
            "DOCUMENT_PUBLISH_INVALID_STATUS",
            "Document status is not supported for publishing.",
            status_code=409,
        ) from exc


def _build_chunks(
    *,
    document: Document,
    version: DocumentVersion,
    text: str,
    license_record: SourceLicense,
    published_at: datetime,
) -> list[DocumentChunk]:
    try:
        chunking_result = chunk_text_for_retrieval(
            document_version_id=version.id,
            canonical_id=document.canonical_id,
            version_number=version.version_number,
            text=text,
            language=document.language,
            document_type=document.document_type,
            max_tokens=_MAX_CHUNK_WORDS,
        )
    except ChunkingError as exc:
        raise DocumentPublishingError(
            "DOCUMENT_PUBLISH_EMPTY_CONTENT",
            "Document version has no chunkable text.",
            status_code=409,
        ) from exc

    built_chunks: list[DocumentChunk] = []
    for draft in chunking_result.chunks:
        content_hash = _chunk_hash(
            version.id,
            draft.chunk_index,
            draft.content_normalized,
            draft.reference,
        )
        built_chunks.append(
            DocumentChunk(
                id=uuid4(),
                document_version_id=version.id,
                chunk_index=draft.chunk_index,
                content=draft.content,
                content_normalized=draft.content_normalized,
                token_count=draft.token_count,
                page_start=draft.page_start,
                page_end=draft.page_end,
                section=draft.section,
                reference=draft.reference,
                metadata_json={
                    **draft.metadata,
                    "publishing_policy_version": DOCUMENT_PUBLISH_POLICY_VERSION,
                    "document_version_id": str(version.id),
                    "embedding": {
                        "pipeline_version": EMBEDDING_PIPELINE_VERSION,
                        "record_status": "pending_provider",
                        "active": False,
                        "source_license_id": str(license_record.id),
                        "source_license_version": license_record.license_version,
                    },
                    "citation": {
                        "pipeline_version": CITATION_PIPELINE_VERSION,
                        "canonical_reference": draft.reference,
                        "verified": False,
                    },
                    "published_at": published_at.isoformat(),
                },
                is_published=False,
                chunking_strategy_version=draft.strategy_version,
                content_hash=content_hash,
            )
        )
    return built_chunks


def _chunk_hash(version_id: UUID, chunk_index: int, normalized: str, reference: str) -> str:
    payload = f"{version_id}:{chunk_index}:{reference}:{normalized}".encode()
    return hashlib.sha256(payload).hexdigest()


def _publishing_metadata(
    *,
    document: Document,
    version: DocumentVersion,
    license_record: SourceLicense,
    license_reason_codes: tuple[str, ...],
    content_risk: str,
    actor_user_id: UUID,
    published_at: datetime,
) -> dict[str, Any]:
    return {
        "policy_version": DOCUMENT_PUBLISH_POLICY_VERSION,
        "document_id": str(document.id),
        "document_version_id": str(version.id),
        "published_version_id": str(version.id),
        "published_at": published_at.isoformat(),
        "published_by": str(actor_user_id),
        "content_risk": content_risk,
        "license_policy_version": LICENSE_POLICY_ENGINE_VERSION,
        "license_reason_codes": list(license_reason_codes),
        "source_license_id": str(license_record.id),
        "source_license_version": license_record.license_version,
        "scholar_approval_policy_version": SCHOLAR_APPROVAL_POLICY_VERSION,
        "chunking_strategy_version": CHUNKING_STRATEGY_VERSION,
        "chunking_strategy_versions": list(chunking_strategy_versions()),
        "embedding_pipeline_version": EMBEDDING_PIPELINE_VERSION,
        "citation_pipeline_version": CITATION_PIPELINE_VERSION,
    }


def _policy_input(license_record: SourceLicense) -> LicensePolicyInput:
    return LicensePolicyInput(
        license_id=license_record.id,
        source_id=license_record.source_id,
        license_version=license_record.license_version,
        status=license_record.status,
        storage_permission=license_record.storage_permission,
        embedding_permission=license_record.embedding_permission,
        commercial_use=license_record.commercial_use,
        redistribution=license_record.redistribution,
        attribution_required=license_record.attribution_required,
        attribution_template=license_record.attribution_template,
        valid_from=license_record.valid_from,
        valid_until=license_record.valid_until,
    )
