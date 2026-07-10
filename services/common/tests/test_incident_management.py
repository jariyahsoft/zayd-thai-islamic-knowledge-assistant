from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from zayd_common.database.models import AuditLog, Base, IncidentEvent, User
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.incident_management import (
    IncidentAlert,
    IncidentCreate,
    IncidentManagementError,
    IncidentManagementService,
)
from zayd_common.rbac import Permission


class AlertSink:
    def __init__(self) -> None:
        self.alerts: list[IncidentAlert] = []

    def send(self, alert: IncidentAlert) -> str:
        self.alerts.append(alert)
        return "sent"


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_p0_alert_and_idempotent_creation(db) -> None:
    actor = uuid4()
    with db() as session:
        session.add(User(id=actor, email="incident@example.test", display_name="Incident Owner"))
        session.commit()
    sink = AlertSink()
    service = IncidentManagementService(SQLAlchemyUnitOfWork(db), sink)
    permissions = frozenset({Permission.FEEDBACK_READ.value, Permission.FEEDBACK_MANAGE.value})
    request = IncidentCreate(
        idempotency_key="report-1", severity="p0", summary="Critical citation issue"
    )
    created, duplicate = service.create(request, actor_user_id=actor, permissions=permissions)
    repeated, repeated_duplicate = service.create(
        request, actor_user_id=actor, permissions=permissions
    )
    assert duplicate is False
    assert repeated_duplicate is True
    assert repeated.id == created.id
    assert created.alert_status == "sent"
    assert len(sink.alerts) == 1


def test_status_timeline_assignment_and_audit(db) -> None:
    actor, owner = uuid4(), uuid4()
    with db() as session:
        session.add_all(
            [
                User(id=actor, email="actor@example.test", display_name="Actor"),
                User(id=owner, email="owner@example.test", display_name="Owner"),
            ]
        )
        session.commit()
    permissions = frozenset({Permission.FEEDBACK_READ.value, Permission.FEEDBACK_MANAGE.value})
    service = IncidentManagementService(SQLAlchemyUnitOfWork(db))
    incident, _ = service.create(
        IncidentCreate("report-2", "p2", "Contained issue"),
        actor_user_id=actor,
        permissions=permissions,
    )
    assigned = service.assign(
        incident.id, owner_id=owner, actor_user_id=actor, permissions=permissions
    )
    triaged = service.transition(
        incident.id,
        target_status="triaged",
        reason="Evidence checked",
        actor_user_id=actor,
        permissions=permissions,
        base_row_version=assigned.row_version,
    )
    assert triaged.status == "triaged"
    assert [
        event.event_type for event in service.timeline(incident.id, permissions=permissions)
    ] == ["created", "assigned", "status_changed"]
    with db() as session:
        assert session.scalar(select(AuditLog).where(AuditLog.action == "incident.transition"))
        assert session.scalar(select(IncidentEvent).where(IncidentEvent.incident_id == incident.id))


def test_invalid_transition_and_redacted_bounded_export(db) -> None:
    actor = uuid4()
    with db() as session:
        session.add(User(id=actor, email="export@example.test", display_name="Exporter"))
        session.commit()
    permissions = frozenset({Permission.FEEDBACK_READ.value, Permission.FEEDBACK_MANAGE.value})
    service = IncidentManagementService(SQLAlchemyUnitOfWork(db))
    incident, _ = service.create(
        IncidentCreate("report-3", "p3", "No personal payload"),
        actor_user_id=actor,
        permissions=permissions,
    )
    with pytest.raises(IncidentManagementError, match="not allowed"):
        service.transition(
            incident.id,
            target_status="resolved",
            reason="Skipped states",
            actor_user_id=actor,
            permissions=permissions,
            base_row_version=1,
        )
    exported = service.export(permissions=permissions, limit=1000)
    assert len(exported) == 1
    assert "feedback_id" not in exported[0]
    assert "affected_answer_id" not in exported[0]


def test_permission_denied(db) -> None:
    service = IncidentManagementService(SQLAlchemyUnitOfWork(db))
    with pytest.raises(IncidentManagementError, match="Forbidden"):
        service.export(permissions=frozenset())
