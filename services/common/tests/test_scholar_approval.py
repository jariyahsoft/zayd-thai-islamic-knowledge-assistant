"""Tests for scholar approval workflow."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from zayd_common.database.models import (
    AuditLog,
    Base,
    Document,
    DocumentVersion,
    ReviewApproval,
    ReviewDecisionRecord,
    ReviewTask,
    User,
)
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.scholar_approval import ScholarApprovalError, ScholarApprovalService


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def uploader_id(db) -> UUID:
    return _seed_user(db, "uploader@example.com")


@pytest.fixture
def reviewer_id(db) -> UUID:
    return _seed_user(db, "reviewer@example.com")


@pytest.fixture
def scholar_id(db) -> UUID:
    return _seed_user(db, "scholar@example.com")


@pytest.fixture
def board_id(db) -> UUID:
    return _seed_user(db, "board@example.com")


def _seed_user(session_factory, email: str) -> UUID:
    user_id = uuid4()
    with session_factory() as session:
        session.add(
            User(
                id=user_id,
                email=email,
                display_name=email.split("@")[0],
                password_hash=None,
                status="active",
            )
        )
        session.commit()
    return user_id


def _seed_context(
    session_factory,
    *,
    uploader_id: UUID,
    task_creator_id: UUID,
    assigned_to: UUID,
    review_level: str = "scholar",
    task_status: str = "completed",
    document_status: str = "scholar_review",
) -> tuple[UUID, UUID, UUID]:
    doc_id = uuid4()
    version_id = uuid4()
    task_id = uuid4()
    with session_factory() as session:
        session.add(
            Document(
                id=doc_id,
                source_id=uuid4(),
                source_license_id=uuid4(),
                canonical_id=f"doc-{uuid4().hex[:8]}",
                document_type="book",
                title="Sensitive Fiqh Text",
                language="th",
                madhhab="shafii",
                review_status=document_status,
                created_by=uploader_id,
            )
        )
        session.add(
            DocumentVersion(
                id=version_id,
                document_id=doc_id,
                version_number=1,
                status="parsed",
                content_hash="hash",
                extracted_text="reviewed content",
                created_by=uploader_id,
            )
        )
        session.add(
            ReviewTask(
                id=task_id,
                document_version_id=version_id,
                document_id=doc_id,
                assigned_to=assigned_to,
                review_level=review_level,
                status=task_status,
                priority="high",
                category="book",
                language="th",
                madhhab="shafii",
                created_by=task_creator_id,
            )
        )
        session.commit()
    return doc_id, version_id, task_id


def _service(session_factory) -> ScholarApprovalService:
    return ScholarApprovalService(SQLAlchemyUnitOfWork(session_factory))


def _seed_initial_decision(
    session_factory,
    *,
    version_id: UUID,
    task_id: UUID,
    reviewer_id: UUID,
) -> None:
    with session_factory() as session:
        session.add(
            ReviewDecisionRecord(
                id=uuid4(),
                review_task_id=task_id,
                document_version_id=version_id,
                actor_user_id=reviewer_id,
                decision="approve",
                reason="Initial review complete",
                base_task_row_version=1,
                resulting_task_status="completed",
                resulting_document_status="scholar_review",
            )
        )
        session.commit()


def test_restricted_content_requires_initial_scholar_and_board(
    db, uploader_id, reviewer_id, scholar_id
):
    _, version_id, task_id = _seed_context(
        db,
        uploader_id=uploader_id,
        task_creator_id=reviewer_id,
        assigned_to=scholar_id,
    )
    _seed_initial_decision(db, version_id=version_id, task_id=task_id, reviewer_id=reviewer_id)
    service = _service(db)

    requirement = service.get_requirements(
        document_version_id=version_id,
        content_risk="restricted",
    )

    assert requirement.required_levels == ["initial", "scholar", "board"]
    assert requirement.satisfied_levels == []
    assert requirement.missing_levels == ["initial", "scholar", "board"]
    assert requirement.ready_for_publish is False


def test_requirement_counts_only_levels_required_for_risk(db, uploader_id, reviewer_id, scholar_id):
    _, version_id, task_id = _seed_context(
        db,
        uploader_id=uploader_id,
        task_creator_id=uuid4(),
        assigned_to=scholar_id,
    )
    service = _service(db)
    service.approve(
        review_task_id=task_id,
        actor_user_id=scholar_id,
        principal_roles=frozenset({"senior_scholar"}),
        content_risk="sensitive",
        approval_level="scholar",
        reason="Scholar approval only.",
    )

    requirement = service.get_requirements(document_version_id=version_id, content_risk="routine")

    assert requirement.required_levels == ["initial"]
    assert requirement.satisfied_levels == []
    assert requirement.missing_levels == ["initial"]
    assert requirement.ready_for_publish is False


def test_scholar_approval_records_audit_and_satisfies_sensitive_level(
    db, uploader_id, reviewer_id, scholar_id
):
    _, version_id, task_id = _seed_context(
        db,
        uploader_id=uploader_id,
        task_creator_id=reviewer_id,
        assigned_to=scholar_id,
    )
    service = _service(db)

    approval = service.approve(
        review_task_id=task_id,
        actor_user_id=scholar_id,
        principal_roles=frozenset({"senior_scholar"}),
        content_risk="sensitive",
        approval_level="scholar",
        reason="Senior scholar confirms validity.",
        trace_id="trace-approve",
    )

    assert approval.document_version_id == version_id
    assert approval.approval_level == "scholar"
    assert approval.status == "active"
    with db() as session:
        logs = session.execute(
            select(AuditLog).where(AuditLog.action == "scholar_approval.created")
        ).scalars().all()
    assert logs and logs[0].trace_id == "trace-approve"


def test_reviewer_cannot_create_scholar_approval(db, uploader_id, reviewer_id):
    _, _, task_id = _seed_context(
        db,
        uploader_id=uploader_id,
        task_creator_id=uuid4(),
        assigned_to=reviewer_id,
    )
    service = _service(db)

    with pytest.raises(ScholarApprovalError) as exc:
        service.approve(
            review_task_id=task_id,
            actor_user_id=reviewer_id,
            principal_roles=frozenset({"reviewer"}),
            content_risk="sensitive",
            approval_level="scholar",
            reason="Not allowed.",
        )

    assert exc.value.code == "SCHOLAR_APPROVAL_ACCESS_DENIED"


def test_uploader_cannot_self_approve(db, uploader_id, reviewer_id):
    _, _, task_id = _seed_context(
        db,
        uploader_id=uploader_id,
        task_creator_id=reviewer_id,
        assigned_to=uploader_id,
    )
    service = _service(db)

    with pytest.raises(ScholarApprovalError) as exc:
        service.approve(
            review_task_id=task_id,
            actor_user_id=uploader_id,
            principal_roles=frozenset({"senior_scholar"}),
            content_risk="sensitive",
            approval_level="scholar",
            reason="Self approve attempt.",
        )

    assert exc.value.code == "SCHOLAR_APPROVAL_SELF_APPROVAL_DENIED"


def test_initial_reviewer_cannot_satisfy_scholar_level(db, uploader_id, reviewer_id):
    _, version_id, task_id = _seed_context(
        db,
        uploader_id=uploader_id,
        task_creator_id=uuid4(),
        assigned_to=reviewer_id,
    )
    _seed_initial_decision(db, version_id=version_id, task_id=task_id, reviewer_id=reviewer_id)
    service = _service(db)

    with pytest.raises(ScholarApprovalError) as exc:
        service.approve(
            review_task_id=task_id,
            actor_user_id=reviewer_id,
            principal_roles=frozenset({"senior_scholar"}),
            content_risk="sensitive",
            approval_level="scholar",
            reason="Same person attempting second level.",
        )

    assert exc.value.code == "SCHOLAR_APPROVAL_SELF_APPROVAL_DENIED"


def test_two_level_sensitive_approval_is_ready_when_initial_and_scholar_satisfied(
    db, uploader_id, reviewer_id, scholar_id
):
    _, version_id, task_id = _seed_context(
        db,
        uploader_id=uploader_id,
        task_creator_id=uuid4(),
        assigned_to=scholar_id,
    )
    service = _service(db)
    service.approve(
        review_task_id=task_id,
        actor_user_id=reviewer_id,
        principal_roles=frozenset({"reviewer"}),
        content_risk="sensitive",
        approval_level="initial",
        reason="Initial approval.",
    )
    service.approve(
        review_task_id=task_id,
        actor_user_id=scholar_id,
        principal_roles=frozenset({"senior_scholar"}),
        content_risk="sensitive",
        approval_level="scholar",
        reason="Scholar approval.",
    )

    requirement = service.get_requirements(
        document_version_id=version_id,
        content_risk="sensitive",
    )

    assert requirement.ready_for_publish is True
    assert requirement.missing_levels == []
    assert requirement.satisfied_levels == ["initial", "scholar"]


def test_same_approver_cannot_satisfy_multiple_active_levels(db, uploader_id, scholar_id):
    _, _, task_id = _seed_context(
        db,
        uploader_id=uploader_id,
        task_creator_id=uuid4(),
        assigned_to=scholar_id,
    )
    service = _service(db)
    service.approve(
        review_task_id=task_id,
        actor_user_id=scholar_id,
        principal_roles=frozenset({"senior_scholar", "admin"}),
        content_risk="restricted",
        approval_level="scholar",
        reason="Scholar approval.",
    )

    with pytest.raises(ScholarApprovalError) as exc:
        service.approve(
            review_task_id=task_id,
            actor_user_id=scholar_id,
            principal_roles=frozenset({"senior_scholar", "admin"}),
            content_risk="restricted",
            approval_level="board",
            reason="Same actor attempts board approval.",
        )

    assert exc.value.code == "SCHOLAR_APPROVAL_SELF_APPROVAL_DENIED"


def test_unknown_version_requirement_fails_closed(db):
    service = _service(db)

    with pytest.raises(ScholarApprovalError) as exc:
        service.get_requirements(document_version_id=uuid4(), content_risk="routine")

    assert exc.value.code == "SCHOLAR_APPROVAL_VERSION_NOT_FOUND"


def test_expired_approval_no_longer_satisfies_requirement(db, uploader_id, reviewer_id):
    _, version_id, task_id = _seed_context(
        db,
        uploader_id=uploader_id,
        task_creator_id=uuid4(),
        assigned_to=reviewer_id,
        review_level="initial",
    )
    service = _service(db)
    approval = service.approve(
        review_task_id=task_id,
        actor_user_id=reviewer_id,
        principal_roles=frozenset({"reviewer"}),
        content_risk="routine",
        approval_level="initial",
        reason="Initial approval with expiry.",
        valid_until=datetime.now(UTC) - timedelta(minutes=1),
    )

    expired_count = service.expire_approvals(trace_id="trace-expire")
    requirement = service.get_requirements(document_version_id=version_id, content_risk="routine")

    assert expired_count == 1
    assert requirement.ready_for_publish is False
    with db() as session:
        refreshed = session.get(ReviewApproval, approval.id)
        logs = session.execute(
            select(AuditLog).where(AuditLog.action == "scholar_approval.expired")
        ).scalars().all()
    assert refreshed is not None and refreshed.status == "expired"
    assert logs and logs[0].trace_id == "trace-expire"


def test_revoke_approval_marks_explicit_revocation(db, uploader_id, reviewer_id, scholar_id):
    _, version_id, task_id = _seed_context(
        db,
        uploader_id=uploader_id,
        task_creator_id=uuid4(),
        assigned_to=reviewer_id,
        review_level="initial",
    )
    service = _service(db)
    approval = service.approve(
        review_task_id=task_id,
        actor_user_id=reviewer_id,
        principal_roles=frozenset({"reviewer"}),
        content_risk="routine",
        approval_level="initial",
        reason="Routine approval.",
    )

    revoked = service.revoke(
        approval_id=approval.id,
        actor_user_id=scholar_id,
        principal_roles=frozenset({"senior_scholar"}),
        reason="Found citation issue.",
        trace_id="trace-revoke",
    )
    requirement = service.get_requirements(document_version_id=version_id, content_risk="routine")

    assert revoked.status == "revoked"
    assert revoked.revoked_by == scholar_id
    assert requirement.ready_for_publish is False
    with db() as session:
        logs = session.execute(
            select(AuditLog).where(AuditLog.action == "scholar_approval.revoked")
        ).scalars().all()
    assert logs and logs[0].trace_id == "trace-revoke"
