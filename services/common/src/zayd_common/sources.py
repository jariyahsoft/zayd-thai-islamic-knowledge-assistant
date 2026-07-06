"""Source registry service for managing knowledge sources."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from sqlalchemy import select

from zayd_common.database.models import AuditLog, Source
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

SourceErrorCode = Literal[
    "SOURCE_NOT_FOUND",
    "SOURCE_NAME_REQUIRED",
    "SOURCE_INVALID_RELIABILITY",
    "SOURCE_INACTIVE_ASSIGNMENT",
]


class SourceError(Exception):
    def __init__(self, code: SourceErrorCode, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class SourcePublic:
    id: UUID
    name: str
    source_type: str
    owner: str | None
    website: str | None
    language: str
    country: str | None
    reliability_level: int
    is_active: bool
    created_by: UUID
    updated_by: UUID | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class SourceSearchQuery:
    name: str | None = None
    source_type: str | None = None
    language: str | None = None
    country: str | None = None
    is_active: bool | None = None
    reliability_level_min: int | None = None
    reliability_level_max: int | None = None
    limit: int = 100
    offset: int = 0


class SourceService:
    def __init__(self, uow: SQLAlchemyUnitOfWork) -> None:
        self.uow = uow

    def create(
        self,
        *,
        name: str,
        source_type: str,
        language: str,
        reliability_level: int,
        owner: str | None = None,
        website: str | None = None,
        country: str | None = None,
        is_active: bool = True,
        created_by: UUID,
        trace_id: str | None = None,
    ) -> SourcePublic:
        """Create a new source."""
        normalized_name = name.strip()
        if not normalized_name:
            raise SourceError(
                "SOURCE_NAME_REQUIRED",
                "Source name is required.",
                status_code=400,
            )
        if reliability_level < 1 or reliability_level > 5:
            raise SourceError(
                "SOURCE_INVALID_RELIABILITY",
                "Reliability level must be between 1 and 5.",
                status_code=400,
            )

        with self.uow:
            source = Source(
                id=uuid4(),
                name=normalized_name,
                source_type=source_type.strip(),
                owner=owner.strip() if owner else None,
                website=website.strip() if website else None,
                language=language.strip(),
                country=country.strip() if country else None,
                reliability_level=reliability_level,
                is_active=is_active,
                created_by=created_by,
                updated_by=None,
            )
            self.uow.sources.create(source)
            self._audit(
                action="sources.create",
                outcome="success",
                actor_user_id=created_by,
                resource_id=source.id,
                after_summary={
                    "name": source.name,
                    "source_type": source.source_type,
                    "language": source.language,
                    "reliability_level": source.reliability_level,
                    "is_active": source.is_active,
                },
                trace_id=trace_id,
            )
            self.uow.commit()
            return _public_source(source)

    def get_by_id(self, *, source_id: UUID) -> SourcePublic:
        """Get a source by ID."""
        with self.uow:
            source = self.uow.sources.get_by_id(source_id)
            if source is None or source.deleted_at is not None:
                raise SourceError(
                    "SOURCE_NOT_FOUND",
                    "Source not found.",
                    status_code=404,
                )
            self.uow.commit()
            return _public_source(source)

    def update(
        self,
        *,
        source_id: UUID,
        name: str | None = None,
        source_type: str | None = None,
        owner: str | None = None,
        website: str | None = None,
        language: str | None = None,
        country: str | None = None,
        reliability_level: int | None = None,
        updated_by: UUID,
        trace_id: str | None = None,
    ) -> SourcePublic:
        """Update source fields."""
        with self.uow:
            source = self.uow.sources.get_by_id(source_id)
            if source is None or source.deleted_at is not None:
                raise SourceError(
                    "SOURCE_NOT_FOUND",
                    "Source not found.",
                    status_code=404,
                )

            before = _public_source(source)
            if name is not None:
                normalized_name = name.strip()
                if not normalized_name:
                    raise SourceError(
                        "SOURCE_NAME_REQUIRED",
                        "Source name is required.",
                        status_code=400,
                    )
                source.name = normalized_name
            if source_type is not None:
                source.source_type = source_type.strip()
            if owner is not None:
                source.owner = owner.strip() if owner else None
            if website is not None:
                source.website = website.strip() if website else None
            if language is not None:
                source.language = language.strip()
            if country is not None:
                source.country = country.strip() if country else None
            if reliability_level is not None:
                if reliability_level < 1 or reliability_level > 5:
                    raise SourceError(
                        "SOURCE_INVALID_RELIABILITY",
                        "Reliability level must be between 1 and 5.",
                        status_code=400,
                    )
                source.reliability_level = reliability_level

            source.updated_by = updated_by
            source.row_version += 1
            self.uow.sources.update(source)

            self._audit(
                action="sources.update",
                outcome="success",
                actor_user_id=updated_by,
                resource_id=source.id,
                before_summary={"name": before.name, "reliability_level": before.reliability_level},
                after_summary={"name": source.name, "reliability_level": source.reliability_level},
                trace_id=trace_id,
            )
            self.uow.commit()
            return _public_source(source)

    def suspend(
        self,
        *,
        source_id: UUID,
        actor_user_id: UUID,
        trace_id: str | None = None,
    ) -> SourcePublic:
        """Suspend a source (set is_active to False)."""
        with self.uow:
            source = self.uow.sources.get_by_id(source_id)
            if source is None or source.deleted_at is not None:
                raise SourceError(
                    "SOURCE_NOT_FOUND",
                    "Source not found.",
                    status_code=404,
                )

            if not source.is_active:
                self.uow.commit()
                return _public_source(source)

            source.is_active = False
            source.updated_by = actor_user_id
            source.row_version += 1
            self.uow.sources.update(source)

            self._audit(
                action="sources.suspend",
                outcome="success",
                actor_user_id=actor_user_id,
                resource_id=source.id,
                after_summary={"name": source.name, "is_active": source.is_active},
                trace_id=trace_id,
            )
            self.uow.commit()
            return _public_source(source)

    def search(self, query: SourceSearchQuery) -> list[SourcePublic]:
        """Search sources with structured filters and pagination."""
        with self.uow:
            session = self._session()
            statement = select(Source).where(Source.deleted_at.is_(None))

            if query.name is not None:
                pattern = f"%{query.name.strip()}%"
                statement = statement.where(Source.name.ilike(pattern))

            if query.source_type is not None:
                statement = statement.where(Source.source_type == query.source_type.strip())

            if query.language is not None:
                statement = statement.where(Source.language == query.language.strip())

            if query.country is not None:
                statement = statement.where(Source.country == query.country.strip())

            if query.is_active is not None:
                statement = statement.where(Source.is_active == query.is_active)

            if query.reliability_level_min is not None:
                statement = statement.where(Source.reliability_level >= query.reliability_level_min)

            if query.reliability_level_max is not None:
                statement = statement.where(Source.reliability_level <= query.reliability_level_max)

            statement = (
                statement.order_by(Source.created_at.desc())
                .limit(min(max(query.limit, 1), 100))
                .offset(max(query.offset, 0))
            )

            sources = list(session.execute(statement).scalars().all())
            self.uow.commit()
            return [_public_source(source) for source in sources]

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
                resource_type="source",
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

    def _session(self) -> Any:
        if self.uow.session is None:
            raise RuntimeError("Database session not initialized in UoW.")
        return self.uow.session


def _public_source(source: Source) -> SourcePublic:
    return SourcePublic(
        id=source.id,
        name=source.name,
        source_type=source.source_type,
        owner=source.owner,
        website=source.website,
        language=source.language,
        country=source.country,
        reliability_level=source.reliability_level,
        is_active=source.is_active,
        created_by=source.created_by,
        updated_by=source.updated_by,
        created_at=source.created_at,
        updated_at=source.updated_at,
    )
