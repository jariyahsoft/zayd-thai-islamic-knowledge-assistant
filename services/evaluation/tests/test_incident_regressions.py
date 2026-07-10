from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from zayd_common.database.models import (
    AuditLog,
    Base,
    EvaluationCase,
    EvaluationDataset,
    Incident,
    IncidentEvent,
    User,
)
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.rbac import Permission
from zayd_service_evaluation import (
    EvaluationCaseContract,
    EvaluationCaseType,
    EvaluationVisibility,
    ExpectedBehavior,
    IncidentRegressionError,
    IncidentRegressionService,
    ReviewerStatus,
    SourceReference,
)


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _contract(**updates: object) -> EvaluationCaseContract:
    payload: dict[str, object] = {
        "case_key": "incident.case-001",
        "case_type": EvaluationCaseType.OPEN_ENDED,
        "visibility": EvaluationVisibility.PRIVATE,
        "reviewer_status": ReviewerStatus.DRAFT,
        "question": "Contact person@example.test or 081-234-5678",
        "expected_behavior": ExpectedBehavior(
            outcome="answer", rubric={"note": "Thai ID 1-2345-67890-12-3"}
        ),
        "sources": (
            SourceReference(
                source_id=uuid4(),
                canonical_reference="source:1",
                license_name="Private reviewed license",
                license_status="private",
                redistributable=False,
            ),
        ),
        "provenance": {"untrusted": "must be ignored"},
    }
    payload.update(updates)
    return EvaluationCaseContract.model_validate(payload)


def _seed(db, *, incident_status: str = "closed", dataset_visibility: str = "private"):
    actor = uuid4()
    incident_id, dataset_id = uuid4(), uuid4()
    with db() as session:
        session.add(User(id=actor, email=f"reviewer-{actor}@example.test", display_name="Reviewer"))
        session.add(
            Incident(
                id=incident_id,
                severity="p1",
                status=incident_status,
                summary="Private incident detail that must not be copied",
                opened_by=actor,
                idempotency_key=f"incident-regression-test-{incident_id}",
                policy_version="incident-management-v1",
            )
        )
        session.add(
            EvaluationDataset(
                id=dataset_id,
                name=f"incident-regressions-{dataset_id}",
                version="1.0.0",
                visibility=dataset_visibility,
                license_status="private",
                created_by=actor,
            )
        )
        session.commit()
    return actor, incident_id, dataset_id


def test_creates_sanitized_private_case_with_bounded_provenance_and_audit(db) -> None:
    actor, incident_id, dataset_id = _seed(db)
    service = IncidentRegressionService(SQLAlchemyUnitOfWork(db))
    permissions = frozenset({Permission.FEEDBACK_MANAGE.value, Permission.EVALUATIONS_MANAGE.value})

    result = service.create(
        incident_id,
        dataset_id,
        _contract(),
        actor_user_id=actor,
        permissions=permissions,
        trace_id="trace-regression",
    )

    assert result.redaction_count == 3
    with db() as session:
        case = session.get(EvaluationCase, result.evaluation_case_id)
        assert case is not None
        assert "person@example.test" not in case.question
        assert "081-234-5678" not in case.question
        assert "[REDACTED_EMAIL]" in case.question
        assert case.expected_behavior["rubric"]["note"] == "Thai ID [REDACTED_THAI_ID]"
        assert case.provenance_json == {
            "origin": "incident_regression",
            "incident_id": str(incident_id),
            "incident_severity": "p1",
            "incident_policy_version": "incident-management-v1",
            "regression_policy_version": "incident-regression-v1",
        }
        assert "Private incident detail" not in str(case.provenance_json)
        event = session.scalar(
            select(IncidentEvent).where(IncidentEvent.event_type == "regression_case_created")
        )
        audit = session.scalar(
            select(AuditLog).where(AuditLog.action == "evaluation.incident_regression.create")
        )
        assert event is not None and event.request_id == "trace-regression"
        assert audit is not None and audit.after_summary["redaction_count"] == 3


def test_rejects_unconfirmed_incident_and_public_dataset(db) -> None:
    actor, incident_id, dataset_id = _seed(db, incident_status="triaged")
    service = IncidentRegressionService(SQLAlchemyUnitOfWork(db))
    permissions = frozenset({Permission.FEEDBACK_MANAGE.value, Permission.EVALUATIONS_MANAGE.value})
    with pytest.raises(IncidentRegressionError, match="resolved or closed"):
        service.create(
            incident_id, dataset_id, _contract(), actor_user_id=actor, permissions=permissions
        )

    actor, incident_id, dataset_id = _seed(db, dataset_visibility="public")
    with pytest.raises(IncidentRegressionError, match="private dataset"):
        service.create(
            incident_id, dataset_id, _contract(), actor_user_id=actor, permissions=permissions
        )


def test_requires_both_feedback_and_evaluation_permissions_and_private_draft(db) -> None:
    actor, incident_id, dataset_id = _seed(db)
    service = IncidentRegressionService(SQLAlchemyUnitOfWork(db))
    with pytest.raises(IncidentRegressionError, match="Forbidden"):
        service.create(
            incident_id,
            dataset_id,
            _contract(),
            actor_user_id=actor,
            permissions=frozenset({Permission.FEEDBACK_MANAGE.value}),
        )
    with pytest.raises(IncidentRegressionError, match="private drafts"):
        service.create(
            incident_id,
            dataset_id,
            _contract(reviewer_status=ReviewerStatus.APPROVED, reviewed_by=actor),
            actor_user_id=actor,
            permissions=frozenset(
                {Permission.FEEDBACK_MANAGE.value, Permission.EVALUATIONS_MANAGE.value}
            ),
        )
