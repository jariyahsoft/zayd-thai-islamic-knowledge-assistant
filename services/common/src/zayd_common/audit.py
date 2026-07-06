from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from zayd_common.database.models import AuditLog
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

AuditOutcome = Literal["success", "failure", "denied", "error"]


@dataclass(frozen=True)
class AuditLogQuery:
    actor_user_id: UUID | None = None
    action: str | None = None
    resource_type: str | None = None
    resource_id: UUID | None = None
    outcome: str | None = None
    request_id: str | None = None
    trace_id: str | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None
    limit: int = 100


class AuditService:
    def __init__(self, uow: SQLAlchemyUnitOfWork) -> None:
        self.uow = uow

    def record(
        self,
        *,
        action: str,
        resource_type: str,
        outcome: AuditOutcome,
        actor_user_id: UUID | None = None,
        resource_id: UUID | None = None,
        reason: str | None = None,
        request_id: str | None = None,
        trace_id: str | None = None,
        before_summary: dict[str, Any] | None = None,
        after_summary: dict[str, Any] | None = None,
        source_context: dict[str, Any] | None = None,
    ) -> AuditLog:
        with self.uow:
            record = AuditLog(
                id=uuid4(),
                actor_user_id=actor_user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                outcome=outcome,
                reason=reason,
                request_id=request_id,
                trace_id=trace_id,
                before_summary=before_summary,
                after_summary=after_summary,
                source_context=source_context or {},
            )
            self._session().add(record)
            self.uow.commit()
            return record

    def list_records(self, query: AuditLogQuery) -> list[AuditLog]:
        with self.uow:
            statement = _build_query(query)
            records = list(self._session().execute(statement).scalars().all())
            self.uow.commit()
            return records

    def export_jsonl(self, query: AuditLogQuery) -> str:
        bounded_query = AuditLogQuery(
            actor_user_id=query.actor_user_id,
            action=query.action,
            resource_type=query.resource_type,
            resource_id=query.resource_id,
            outcome=query.outcome,
            request_id=query.request_id,
            trace_id=query.trace_id,
            created_from=query.created_from,
            created_to=query.created_to,
            limit=min(max(query.limit, 1), 1000),
        )
        lines = [
            json.dumps(serialize_audit_log(record), sort_keys=True)
            for record in self.list_records(bounded_query)
        ]
        return "\n".join(lines) + ("\n" if lines else "")

    def _session(self) -> Session:
        if self.uow.session is None:
            raise RuntimeError("Database session not initialized in UoW.")
        return self.uow.session


def serialize_audit_log(record: AuditLog) -> dict[str, Any]:
    return {
        "id": str(record.id),
        "actor_user_id": str(record.actor_user_id) if record.actor_user_id else None,
        "action": record.action,
        "resource_type": record.resource_type,
        "resource_id": str(record.resource_id) if record.resource_id else None,
        "outcome": record.outcome,
        "reason": record.reason,
        "request_id": record.request_id,
        "trace_id": record.trace_id,
        "before_summary": record.before_summary,
        "after_summary": record.after_summary,
        "source_context": record.source_context,
        "created_at": record.created_at.isoformat(),
        "hash_algorithm": record.hash_algorithm,
        "previous_hash": record.previous_hash,
        "content_hash": record.content_hash,
    }


def _build_query(query: AuditLogQuery) -> Select[tuple[AuditLog]]:
    statement = select(AuditLog)
    if query.actor_user_id is not None:
        statement = statement.where(AuditLog.actor_user_id == query.actor_user_id)
    if query.action is not None:
        statement = statement.where(AuditLog.action == query.action)
    if query.resource_type is not None:
        statement = statement.where(AuditLog.resource_type == query.resource_type)
    if query.resource_id is not None:
        statement = statement.where(AuditLog.resource_id == query.resource_id)
    if query.outcome is not None:
        statement = statement.where(AuditLog.outcome == query.outcome)
    if query.request_id is not None:
        statement = statement.where(AuditLog.request_id == query.request_id)
    if query.trace_id is not None:
        statement = statement.where(AuditLog.trace_id == query.trace_id)
    if query.created_from is not None:
        statement = statement.where(AuditLog.created_at >= query.created_from)
    if query.created_to is not None:
        statement = statement.where(AuditLog.created_at <= query.created_to)
    return statement.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(
        min(max(query.limit, 1), 1000)
    )
