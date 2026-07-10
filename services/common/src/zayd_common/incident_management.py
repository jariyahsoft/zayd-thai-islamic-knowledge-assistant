"""Auditable P0-P3 incident workflow with privacy-safe alerting and exports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from zayd_common.database.models import AuditLog, Feedback, Incident, IncidentEvent, User
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.enums import IncidentSeverity, IncidentStatus
from zayd_common.exceptions import StateTransitionError
from zayd_common.rbac import Permission
from zayd_common.state_machines import IncidentStateMachine, TransitionMetadata

INCIDENT_POLICY_VERSION = "incident-management-v1"
MAX_SUMMARY_LENGTH = 1000
MAX_EXPORT_LIMIT = 200


class IncidentManagementError(Exception):
    def __init__(self, code: str, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.code, self.message, self.status_code = code, message, status_code


@dataclass(frozen=True)
class IncidentAlert:
    incident_id: UUID
    severity: str
    summary: str


class IncidentAlertSink(Protocol):
    def send(self, alert: IncidentAlert) -> str: ...


class DisabledIncidentAlertSink:
    def send(self, alert: IncidentAlert) -> str:
        return "not_configured"


@dataclass(frozen=True)
class IncidentCreate:
    idempotency_key: str
    severity: str
    summary: str
    feedback_id: UUID | None = None
    affected_answer_id: UUID | None = None
    affected_document_id: UUID | None = None
    affected_citation_id: UUID | None = None
    owner_id: UUID | None = None


@dataclass(frozen=True)
class IncidentPublic:
    id: UUID
    severity: str
    status: str
    summary: str
    owner_id: UUID | None
    feedback_id: UUID | None
    affected_answer_id: UUID | None
    affected_document_id: UUID | None
    affected_citation_id: UUID | None
    alert_status: str
    row_version: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class IncidentTimelineItem:
    event_type: str
    status_from: str | None
    status_to: str | None
    actor_user_id: UUID | None
    details: dict[str, object]
    created_at: datetime


class IncidentManagementService:
    def __init__(
        self, uow: SQLAlchemyUnitOfWork, alert_sink: IncidentAlertSink | None = None
    ) -> None:
        self.uow = uow
        self.alert_sink = alert_sink or DisabledIncidentAlertSink()

    def create(
        self,
        request: IncidentCreate,
        *,
        actor_user_id: UUID,
        permissions: frozenset[str],
        trace_id: str | None = None,
    ) -> tuple[IncidentPublic, bool]:
        _require_manage(permissions)
        key = _require_text(request.idempotency_key, "idempotency_key", 200)
        summary = _require_text(request.summary, "summary", MAX_SUMMARY_LENGTH)
        severity = _severity(request.severity)
        with self.uow:
            session = self._session()
            existing = session.scalar(select(Incident).where(Incident.idempotency_key == key))
            if existing is not None:
                public = _public(existing)
                self.uow.commit()
                return public, True
            _validate_links(session, request)
            incident = Incident(
                feedback_id=request.feedback_id,
                severity=severity.value,
                status="open",
                summary=summary,
                affected_answer_id=request.affected_answer_id,
                affected_document_id=request.affected_document_id,
                affected_citation_id=request.affected_citation_id,
                opened_by=actor_user_id,
                owner_id=request.owner_id,
                idempotency_key=key,
                policy_version=INCIDENT_POLICY_VERSION,
                row_version=1,
            )
            session.add(incident)
            session.flush()
            alert_status = "not_required"
            if severity in {IncidentSeverity.P0, IncidentSeverity.P1}:
                alert_status = self.alert_sink.send(
                    IncidentAlert(incident.id, severity.value, summary)
                )
            incident.alert_status = alert_status
            _event(
                session,
                incident.id,
                actor_user_id,
                "created",
                None,
                "open",
                {"severity": severity.value, "alert_status": alert_status},
                trace_id,
            )
            _audit(
                session,
                incident,
                actor_user_id,
                "incident.create",
                trace_id,
                {"severity": severity.value, "alert_status": alert_status},
            )
            public = _public(incident)
            self.uow.commit()
            return public, False

    def transition(
        self,
        incident_id: UUID,
        *,
        target_status: str,
        reason: str,
        actor_user_id: UUID,
        permissions: frozenset[str],
        base_row_version: int,
        trace_id: str | None = None,
    ) -> IncidentPublic:
        _require_manage(permissions)
        normalized_reason = _require_text(reason, "reason", 1000)
        with self.uow:
            session = self._session()
            incident = _get(session, incident_id)
            if incident.row_version != base_row_version:
                raise IncidentManagementError(
                    "INCIDENT_CONFLICT", "Incident row version does not match.", status_code=409
                )
            try:
                source, target = IncidentStatus(incident.status), IncidentStatus(target_status)
                IncidentStateMachine.validate_transition(
                    source,
                    target,
                    TransitionMetadata(actor_id=str(actor_user_id), reason=normalized_reason),
                )
            except (ValueError, StateTransitionError) as exc:
                raise IncidentManagementError(
                    "INCIDENT_INVALID_TRANSITION",
                    "Incident status transition is not allowed.",
                    status_code=409,
                ) from exc
            incident.status = target.value
            incident.row_version += 1
            incident.updated_at = datetime.now(UTC)
            if target == IncidentStatus.CLOSED:
                incident.closed_at = incident.updated_at
            _event(
                session,
                incident.id,
                actor_user_id,
                "status_changed",
                source.value,
                target.value,
                {"reason": normalized_reason},
                trace_id,
            )
            _audit(
                session,
                incident,
                actor_user_id,
                "incident.transition",
                trace_id,
                {"status_from": source.value, "status_to": target.value},
            )
            public = _public(incident)
            self.uow.commit()
            return public

    def assign(
        self,
        incident_id: UUID,
        *,
        owner_id: UUID,
        actor_user_id: UUID,
        permissions: frozenset[str],
        trace_id: str | None = None,
    ) -> IncidentPublic:
        _require_manage(permissions)
        with self.uow:
            session = self._session()
            incident = _get(session, incident_id)
            owner = session.get(User, owner_id)
            if owner is None or owner.deleted_at is not None:
                raise IncidentManagementError(
                    "INCIDENT_OWNER_NOT_FOUND", "Incident owner was not found.", status_code=404
                )
            if incident.owner_id == owner_id:
                public = _public(incident)
                self.uow.commit()
                return public
            incident.owner_id = owner_id
            incident.row_version += 1
            _event(
                session,
                incident.id,
                actor_user_id,
                "assigned",
                None,
                None,
                {"owner_id": str(owner_id)},
                trace_id,
            )
            _audit(
                session,
                incident,
                actor_user_id,
                "incident.assign",
                trace_id,
                {"owner_id": str(owner_id)},
            )
            public = _public(incident)
            self.uow.commit()
            return public

    def timeline(
        self, incident_id: UUID, *, permissions: frozenset[str]
    ) -> list[IncidentTimelineItem]:
        _require_read(permissions)
        with self.uow:
            session = self._session()
            _get(session, incident_id)
            rows = session.scalars(
                select(IncidentEvent)
                .where(IncidentEvent.incident_id == incident_id)
                .order_by(IncidentEvent.created_at, IncidentEvent.id)
            ).all()
            result: list[IncidentTimelineItem] = [
                IncidentTimelineItem(
                    row.event_type,
                    row.status_from,
                    row.status_to,
                    row.actor_user_id,
                    dict(row.details_json),
                    row.created_at,
                )
                for row in rows
            ]
            self.uow.commit()
            return result

    def export(self, *, permissions: frozenset[str], limit: int = 100) -> list[dict[str, object]]:
        _require_read(permissions)
        bounded = min(max(limit, 1), MAX_EXPORT_LIMIT)
        with self.uow:
            rows = (
                self._session()
                .scalars(select(Incident).order_by(Incident.created_at.desc()).limit(bounded))
                .all()
            )
            result: list[dict[str, object]] = [
                {
                    "id": str(row.id),
                    "severity": row.severity,
                    "status": row.status,
                    "summary": row.summary,
                    "owner_id": str(row.owner_id) if row.owner_id else None,
                    "created_at": row.created_at.isoformat(),
                    "policy_version": row.policy_version,
                }
                for row in rows
            ]
            self.uow.commit()
            return result

    def _session(self) -> Session:
        if self.uow.session is None:
            raise RuntimeError("Database session not initialised in UoW.")
        return self.uow.session


def _require_manage(permissions: frozenset[str]) -> None:
    if Permission.FEEDBACK_MANAGE.value not in permissions:
        raise IncidentManagementError("INCIDENT_FORBIDDEN", "Forbidden.", status_code=403)


def _require_read(permissions: frozenset[str]) -> None:
    if Permission.FEEDBACK_READ.value not in permissions:
        raise IncidentManagementError("INCIDENT_FORBIDDEN", "Forbidden.", status_code=403)


def _severity(value: str) -> IncidentSeverity:
    try:
        return IncidentSeverity(value.strip().lower())
    except ValueError as exc:
        raise IncidentManagementError(
            "INCIDENT_INPUT_INVALID", "severity must be p0, p1, p2, or p3."
        ) from exc


def _require_text(value: str, field: str, maximum: int) -> str:
    result = value.strip()
    if not result or len(result) > maximum:
        raise IncidentManagementError(
            "INCIDENT_INPUT_INVALID", f"{field} must contain 1-{maximum} characters."
        )
    return result


def _validate_links(session: Session, request: IncidentCreate) -> None:
    if request.feedback_id is not None and session.get(Feedback, request.feedback_id) is None:
        raise IncidentManagementError(
            "INCIDENT_LINK_NOT_FOUND", "Linked feedback was not found.", status_code=404
        )
    if request.owner_id is not None and session.get(User, request.owner_id) is None:
        raise IncidentManagementError(
            "INCIDENT_OWNER_NOT_FOUND", "Incident owner was not found.", status_code=404
        )


def _get(session: Session, incident_id: UUID) -> Incident:
    incident = session.get(Incident, incident_id)
    if incident is None:
        raise IncidentManagementError(
            "INCIDENT_NOT_FOUND", "Incident was not found.", status_code=404
        )
    return incident


def _event(
    session: Session,
    incident_id: UUID,
    actor: UUID,
    kind: str,
    before: str | None,
    after: str | None,
    details: dict[str, object],
    trace_id: str | None,
) -> None:
    session.add(
        IncidentEvent(
            incident_id=incident_id,
            actor_user_id=actor,
            event_type=kind,
            status_from=before,
            status_to=after,
            details_json=details,
            request_id=trace_id,
        )
    )


def _audit(
    session: Session,
    incident: Incident,
    actor: UUID,
    action: str,
    trace_id: str | None,
    after: dict[str, object],
) -> None:
    session.add(
        AuditLog(
            id=uuid4(),
            actor_user_id=actor,
            action=action,
            resource_type="incident",
            resource_id=incident.id,
            outcome="success",
            request_id=trace_id,
            trace_id=trace_id,
            before_summary={},
            after_summary={**after, "policy_version": INCIDENT_POLICY_VERSION},
            source_context={},
        )
    )


def _public(row: Incident) -> IncidentPublic:
    return IncidentPublic(
        row.id,
        row.severity,
        row.status,
        row.summary,
        row.owner_id,
        row.feedback_id,
        row.affected_answer_id,
        row.affected_document_id,
        row.affected_citation_id,
        row.alert_status,
        row.row_version,
        row.created_at,
        row.updated_at,
    )
