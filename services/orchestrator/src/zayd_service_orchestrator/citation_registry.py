"""Canonical citation registry and invalidation workflow."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from sqlalchemy import select
from zayd_common.database.models import (
    Answer,
    AuditLog,
    Citation,
    DocumentChunk,
    DocumentVersion,
    RetrievalResult,
)
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

CITATION_REGISTRY_VERSION = "citation-registry-v1"
CITATION_TOKEN_PREFIX = "CIT"

CitationRegistryErrorCode = Literal[
    "CITATION_INPUT_INVALID",
    "CITATION_DOCUMENT_VERSION_NOT_FOUND",
    "CITATION_CHUNK_NOT_FOUND",
    "CITATION_CHUNK_VERSION_MISMATCH",
    "CITATION_TYPE_INVALID",
    "CITATION_SCHEMA_INVALID",
    "CITATION_CANONICAL_COLLISION",
    "CITATION_NOT_REGISTERED",
    "CITATION_INACTIVE",
]


class CitationType(StrEnum):
    """Supported citation metadata families."""

    QURAN = "quran"
    HADITH = "hadith"
    BOOK = "book"
    DOCUMENT = "document"


class CitationRegistryError(Exception):
    """Stable citation registry error."""

    def __init__(
        self,
        code: CitationRegistryErrorCode,
        message: str,
        *,
        status_code: int = 400,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class CitationRegistrationRequest:
    """Input for creating or resolving one canonical citation row."""

    document_version_id: UUID
    chunk_id: UUID
    citation_type: CitationType | str
    canonical_reference: str
    display_title: str
    actor_user_id: UUID | None = None
    arabic_text: str | None = None
    thai_translation: str | None = None
    hadith_grade: str | None = None
    volume: str | None = None
    page: str | None = None
    verified: bool = True
    trace_id: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class CitationPublic:
    """Safe citation registry record."""

    id: UUID
    token: str
    canonical_reference: str
    document_version_id: UUID
    chunk_id: UUID
    citation_type: CitationType
    display_title: str
    arabic_text: str | None
    thai_translation: str | None
    hadith_grade: str | None
    volume: str | None
    page: str | None
    verified: bool
    invalidated_at: datetime | None
    registry_version: str = CITATION_REGISTRY_VERSION

    @property
    def active(self) -> bool:
        return self.verified and self.invalidated_at is None


@dataclass(frozen=True)
class CitationRegistrationResult:
    """Registration output."""

    citation: CitationPublic
    idempotent: bool
    registry_version: str
    trace: dict[str, object]


@dataclass(frozen=True)
class CitationInvalidationResult:
    """Invalidation output with downstream impact counts."""

    citation: CitationPublic
    affected_retrieval_result_count: int
    affected_answer_count: int
    invalidated_at: datetime
    registry_version: str
    trace: dict[str, object]


class CitationRegistryService:
    """Registers canonical citation rows and maps LLM-visible tokens."""

    def __init__(self, uow: SQLAlchemyUnitOfWork) -> None:
        self.uow = uow

    def register_citation(self, request: CitationRegistrationRequest) -> CitationRegistrationResult:
        """Create an idempotent citation record for a reviewed document chunk."""
        citation_type = _normalize_citation_type(request.citation_type)
        canonical_reference = _require_text(
            request.canonical_reference,
            field_name="canonical_reference",
        )
        display_title = _require_text(request.display_title, field_name="display_title")
        _validate_type_schema(citation_type, request)

        with self.uow:
            session = self._session()
            version = session.get(DocumentVersion, request.document_version_id)
            if version is None:
                raise CitationRegistryError(
                    "CITATION_DOCUMENT_VERSION_NOT_FOUND",
                    "Document version not found.",
                    status_code=404,
                )
            chunk = session.get(DocumentChunk, request.chunk_id)
            if chunk is None:
                raise CitationRegistryError(
                    "CITATION_CHUNK_NOT_FOUND",
                    "Document chunk not found.",
                    status_code=404,
                )
            if chunk.document_version_id != version.id:
                raise CitationRegistryError(
                    "CITATION_CHUNK_VERSION_MISMATCH",
                    "Citation chunk does not belong to the requested document version.",
                    status_code=409,
                )

            existing = session.scalar(
                select(Citation)
                .where(Citation.document_version_id == version.id)
                .where(Citation.canonical_reference == canonical_reference)
            )
            if existing is not None:
                if existing.chunk_id != chunk.id:
                    raise CitationRegistryError(
                        "CITATION_CANONICAL_COLLISION",
                        "Canonical reference already points to another chunk in this version.",
                        status_code=409,
                    )
                public = _public(existing)
                self.uow.commit()
                return CitationRegistrationResult(
                    citation=public,
                    idempotent=True,
                    registry_version=CITATION_REGISTRY_VERSION,
                    trace=_trace(
                        "register",
                        public,
                        request.trace_id,
                        idempotent=True,
                    ),
                )

            citation_id = _stable_citation_id(version.id, canonical_reference)
            citation = Citation(
                id=citation_id,
                canonical_reference=canonical_reference,
                document_version_id=version.id,
                chunk_id=chunk.id,
                citation_type=citation_type.value,
                display_title=display_title,
                arabic_text=_optional_text(request.arabic_text),
                thai_translation=_optional_text(request.thai_translation),
                hadith_grade=_optional_text(request.hadith_grade),
                volume=_optional_text(request.volume),
                page=_optional_text(request.page),
                verified=request.verified,
            )
            session.add(citation)
            _audit(
                session,
                action="citations.register",
                outcome="success",
                actor_user_id=request.actor_user_id,
                resource_id=citation.id,
                trace_id=request.trace_id,
                after_summary={
                    "citation_id": str(citation.id),
                    "citation_token": citation_token(citation.id),
                    "document_version_id": str(version.id),
                    "chunk_id": str(chunk.id),
                    "citation_type": citation_type.value,
                    "canonical_reference": canonical_reference,
                    "registry_version": CITATION_REGISTRY_VERSION,
                    "metadata_keys": sorted(request.metadata.keys()),
                },
            )
            public = _public(citation)
            result = CitationRegistrationResult(
                citation=public,
                idempotent=False,
                registry_version=CITATION_REGISTRY_VERSION,
                trace=_trace("register", public, request.trace_id, idempotent=False),
            )
            self.uow.commit()
            return result

    def register_from_chunk(
        self,
        *,
        chunk_id: UUID,
        citation_type: CitationType | str,
        display_title: str,
        actor_user_id: UUID | None = None,
        trace_id: str | None = None,
    ) -> CitationRegistrationResult:
        """Register a citation using canonical metadata already stored on a chunk."""
        with self.uow:
            session = self._session()
            chunk = session.get(DocumentChunk, chunk_id)
            if chunk is None:
                raise CitationRegistryError(
                    "CITATION_CHUNK_NOT_FOUND",
                    "Document chunk not found.",
                    status_code=404,
                )
            citation_payload = (chunk.metadata_json or {}).get("citation")
            citation_metadata = (
                dict(citation_payload) if isinstance(citation_payload, Mapping) else {}
            )
            canonical_reference = str(
                citation_metadata.get("canonical_reference") or chunk.reference or ""
            )
            document_version_id = chunk.document_version_id
        return self.register_citation(
            CitationRegistrationRequest(
                document_version_id=document_version_id,
                chunk_id=chunk_id,
                citation_type=citation_type,
                canonical_reference=canonical_reference,
                display_title=display_title,
                actor_user_id=actor_user_id,
                arabic_text=_metadata_text(citation_metadata, "arabic_text"),
                thai_translation=_metadata_text(citation_metadata, "thai_translation"),
                hadith_grade=_metadata_text(citation_metadata, "hadith_grade"),
                volume=_metadata_text(citation_metadata, "volume"),
                page=_metadata_text(citation_metadata, "page"),
                trace_id=trace_id,
                metadata=citation_metadata,
            )
        )

    def resolve_llm_token(self, token: str, *, require_active: bool = True) -> CitationPublic:
        """Resolve an LLM-visible citation token to one registered citation row."""
        citation_id = citation_id_from_token(token)
        with self.uow:
            session = self._session()
            citation = session.get(Citation, citation_id)
            if citation is None:
                raise CitationRegistryError(
                    "CITATION_NOT_REGISTERED",
                    "Citation token is not registered.",
                    status_code=404,
                )
            public = _public(citation)
            if require_active and not public.active:
                raise CitationRegistryError(
                    "CITATION_INACTIVE",
                    "Citation token is registered but inactive.",
                    status_code=409,
                )
            self.uow.commit()
            return public

    def llm_tokens_for_citations(self, citation_ids: tuple[UUID, ...]) -> tuple[str, ...]:
        """Return LLM-visible tokens only for active registered citations."""
        if not citation_ids:
            return ()
        with self.uow:
            session = self._session()
            citations = list(
                session.execute(select(Citation).where(Citation.id.in_(citation_ids)))
                .scalars()
                .all()
            )
            found_ids = {citation.id for citation in citations}
            missing = [citation_id for citation_id in citation_ids if citation_id not in found_ids]
            if missing:
                raise CitationRegistryError(
                    "CITATION_NOT_REGISTERED",
                    "One or more citation IDs are not registered.",
                    status_code=404,
                )
            inactive = [
                citation.id
                for citation in citations
                if citation.invalidated_at is not None or not citation.verified
            ]
            if inactive:
                raise CitationRegistryError(
                    "CITATION_INACTIVE",
                    "One or more citation IDs are inactive.",
                    status_code=409,
                )
            tokens_by_id = {citation.id: citation_token(citation.id) for citation in citations}
            self.uow.commit()
            return tuple(tokens_by_id[citation_id] for citation_id in citation_ids)

    def invalidate_citation(
        self,
        *,
        citation_id: UUID,
        reason: str,
        actor_user_id: UUID | None = None,
        trace_id: str | None = None,
    ) -> CitationInvalidationResult:
        """Invalidate one citation while preserving retrieval and answer history."""
        normalized_reason = _require_text(reason, field_name="reason")
        with self.uow:
            session = self._session()
            citation = session.get(Citation, citation_id)
            if citation is None:
                raise CitationRegistryError(
                    "CITATION_NOT_REGISTERED",
                    "Citation is not registered.",
                    status_code=404,
                )
            changed_at = citation.invalidated_at or datetime.now(UTC)
            citation.invalidated_at = changed_at
            citation.verified = False
            citation.updated_at = changed_at

            retrieval_results = list(
                session.execute(
                    select(RetrievalResult).where(RetrievalResult.citation_id == citation.id)
                )
                .scalars()
                .all()
            )
            for result in retrieval_results:
                metadata = dict(result.metadata_json or {})
                metadata["citation_invalidation"] = {
                    "citation_id": str(citation.id),
                    "citation_token": citation_token(citation.id),
                    "reason": normalized_reason,
                    "invalidated_at": changed_at.isoformat(),
                    "registry_version": CITATION_REGISTRY_VERSION,
                }
                result.metadata_json = metadata
                result.updated_at = changed_at

            retrieval_run_ids = {result.retrieval_run_id for result in retrieval_results}
            answers = (
                list(
                    session.execute(
                        select(Answer).where(Answer.retrieval_run_id.in_(retrieval_run_ids))
                    )
                    .scalars()
                    .all()
                )
                if retrieval_run_ids
                else []
            )
            for answer in answers:
                if answer.invalidated_at is None:
                    answer.invalidated_at = changed_at
                answer.answer_json = _answer_with_invalidation_warning(
                    answer.answer_json,
                    citation=citation,
                    reason=normalized_reason,
                    changed_at=changed_at,
                )
                answer.updated_at = changed_at

            _audit(
                session,
                action="citations.invalidate",
                outcome="success",
                actor_user_id=actor_user_id,
                resource_id=citation.id,
                reason=normalized_reason,
                trace_id=trace_id,
                after_summary={
                    "citation_id": str(citation.id),
                    "citation_token": citation_token(citation.id),
                    "affected_retrieval_result_count": len(retrieval_results),
                    "affected_answer_count": len(answers),
                    "registry_version": CITATION_REGISTRY_VERSION,
                },
            )
            public = _public(citation)
            result = CitationInvalidationResult(
                citation=public,
                affected_retrieval_result_count=len(retrieval_results),
                affected_answer_count=len(answers),
                invalidated_at=changed_at,
                registry_version=CITATION_REGISTRY_VERSION,
                trace=_trace("invalidate", public, trace_id, reason_code="CITATION_INVALIDATED"),
            )
            self.uow.commit()
            return result

    def _session(self) -> Any:
        if self.uow.session is None:
            raise RuntimeError("Database session not initialised in UoW.")
        return self.uow.session


def citation_token(citation_id: UUID) -> str:
    """Return a stable LLM-visible token for a registered citation ID."""
    return f"{CITATION_TOKEN_PREFIX}-{citation_id}"


def citation_id_from_token(token: str) -> UUID:
    prefix = f"{CITATION_TOKEN_PREFIX}-"
    if not token.startswith(prefix):
        raise CitationRegistryError(
            "CITATION_INPUT_INVALID",
            "Citation token has an invalid prefix.",
            status_code=400,
        )
    try:
        return UUID(token[len(prefix) :])
    except ValueError as exc:
        raise CitationRegistryError(
            "CITATION_INPUT_INVALID",
            "Citation token has an invalid UUID payload.",
            status_code=400,
        ) from exc


def _stable_citation_id(document_version_id: UUID, canonical_reference: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"zayd:citation:{document_version_id}:{canonical_reference}")


def _normalize_citation_type(value: CitationType | str) -> CitationType:
    try:
        return CitationType(str(value).strip().lower())
    except ValueError as exc:
        raise CitationRegistryError(
            "CITATION_TYPE_INVALID",
            "Citation type must be quran, hadith, book, or document.",
            status_code=400,
        ) from exc


def _validate_type_schema(
    citation_type: CitationType, request: CitationRegistrationRequest
) -> None:
    if citation_type == CitationType.QURAN and not (
        _optional_text(request.arabic_text) or _optional_text(request.thai_translation)
    ):
        raise CitationRegistryError(
            "CITATION_SCHEMA_INVALID",
            "Quran citations require Arabic text or Thai translation metadata.",
            status_code=400,
        )
    if citation_type == CitationType.HADITH and not _optional_text(request.hadith_grade):
        raise CitationRegistryError(
            "CITATION_SCHEMA_INVALID",
            "Hadith citations require hadith grade metadata.",
            status_code=400,
        )
    if citation_type == CitationType.BOOK and not (
        _optional_text(request.volume) or _optional_text(request.page)
    ):
        raise CitationRegistryError(
            "CITATION_SCHEMA_INVALID",
            "Book citations require volume or page metadata.",
            status_code=400,
        )


def _require_text(value: str, *, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise CitationRegistryError(
            "CITATION_INPUT_INVALID",
            f"{field_name} is required.",
            status_code=400,
        )
    return normalized


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _metadata_text(metadata: Mapping[str, Any], key: str) -> str | None:
    value = metadata.get(key)
    if value is None:
        return None
    return _optional_text(str(value))


def _public(citation: Citation) -> CitationPublic:
    return CitationPublic(
        id=citation.id,
        token=citation_token(citation.id),
        canonical_reference=citation.canonical_reference,
        document_version_id=citation.document_version_id,
        chunk_id=citation.chunk_id,
        citation_type=_normalize_citation_type(citation.citation_type),
        display_title=citation.display_title,
        arabic_text=citation.arabic_text,
        thai_translation=citation.thai_translation,
        hadith_grade=citation.hadith_grade,
        volume=citation.volume,
        page=citation.page,
        verified=citation.verified,
        invalidated_at=citation.invalidated_at,
    )


def _answer_with_invalidation_warning(
    answer_json: dict[str, Any],
    *,
    citation: Citation,
    reason: str,
    changed_at: datetime,
) -> dict[str, Any]:
    payload = dict(answer_json or {})
    warning = {
        "type": "citation_invalidated",
        "citation_id": str(citation.id),
        "citation_token": citation_token(citation.id),
        "canonical_reference": citation.canonical_reference,
        "reason": reason,
        "invalidated_at": changed_at.isoformat(),
        "registry_version": CITATION_REGISTRY_VERSION,
    }
    warnings = list(payload.get("warnings", []))
    if warning not in warnings:
        warnings.append(warning)
    payload["warnings"] = warnings
    payload["citation_invalidation_warning"] = (
        "One or more citations used by this answer have been invalidated."
    )
    return payload


def _trace(
    action: str,
    citation: CitationPublic,
    trace_id: str | None,
    **extra: object,
) -> dict[str, object]:
    return {
        "action": action,
        "registry_version": CITATION_REGISTRY_VERSION,
        "citation_id": str(citation.id),
        "citation_token": citation.token,
        "canonical_reference": citation.canonical_reference,
        "document_version_id": str(citation.document_version_id),
        "chunk_id": str(citation.chunk_id),
        "citation_type": citation.citation_type.value,
        "verified": citation.verified,
        "active": citation.active,
        "trace_id": trace_id,
        **extra,
    }


def _audit(
    session: Any,
    *,
    action: str,
    outcome: str,
    actor_user_id: UUID | None,
    resource_id: UUID,
    trace_id: str | None,
    reason: str | None = None,
    after_summary: dict[str, Any] | None = None,
) -> None:
    session.add(
        AuditLog(
            id=uuid4(),
            actor_user_id=actor_user_id,
            action=action,
            resource_type="citation",
            resource_id=resource_id,
            outcome=outcome,
            reason=reason,
            request_id=trace_id,
            trace_id=trace_id,
            after_summary=after_summary,
            source_context={"registry_version": CITATION_REGISTRY_VERSION},
        )
    )
