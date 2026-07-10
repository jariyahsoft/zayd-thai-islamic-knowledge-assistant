"""Unit tests for FeedbackReviewService (TASK-11-02)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from zayd_common.database.models import (
    Answer,
    AuditLog,
    Base,
    Conversation,
    Feedback,
    Message,
    User,
)
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.feedback_review import (
    FeedbackAssignRequest,
    FeedbackClassifyRequest,
    FeedbackQueueQuery,
    FeedbackResolveRequest,
    FeedbackReviewError,
    FeedbackReviewService,
)
from zayd_common.rbac import Permission

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


@pytest.fixture()
def service(db):
    return FeedbackReviewService(SQLAlchemyUnitOfWork(db))


@pytest.fixture()
def reviewer_perms():
    return frozenset({Permission.FEEDBACK_READ.value, Permission.FEEDBACK_MANAGE.value})


@pytest.fixture()
def read_only_perms():
    return frozenset({Permission.FEEDBACK_READ.value})


def _make_feedback(session_factory, *, category="incorrect_answer", status="open"):
    user_id = uuid4()
    conv_id = uuid4()
    msg_id = uuid4()
    answer_id = uuid4()
    feedback_id = uuid4()
    with session_factory() as session:
        session.add(User(id=user_id, email=f"{user_id}@example.test", display_name="User"))
        session.add(
            Conversation(id=conv_id, user_id=user_id, title="q", language="th", madhhab="shafii")
        )
        session.add(
            Message(
                id=msg_id,
                conversation_id=conv_id,
                sender_type="assistant",
                body="a",
                body_hash="h",
                metadata_json={},
            )
        )
        session.add(
            Answer(
                id=answer_id,
                message_id=msg_id,
                retrieval_run_id=uuid4(),
                model_configuration_id=uuid4(),
                prompt_version_id=uuid4(),
                policy_version_id=uuid4(),
                risk_level="low",
                madhhab="shafii",
                answer_json={"summary": "s", "answer_th": "t"},
                confidence_level="high",
                evidence_sufficient=True,
            )
        )
        session.add(
            Feedback(
                id=feedback_id,
                user_id=user_id,
                answer_id=answer_id,
                category=category,
                body="notes from user",
                status=status,
                priority="normal",
                severity="p3",
                reviewer_notes="",
            )
        )
        session.commit()
    return feedback_id


def _make_reviewer_user(session_factory):
    reviewer_id = uuid4()
    with session_factory() as session:
        session.add(
            User(id=reviewer_id, email=f"reviewer-{reviewer_id}@example.test", display_name="Rev")
        )
        session.commit()
    return reviewer_id


# ---------------------------------------------------------------------------
# Queue listing tests
# ---------------------------------------------------------------------------


def test_list_queue_returns_active_items(db, service, reviewer_perms):
    fb1 = _make_feedback(db, category="incorrect_answer")
    fb2 = _make_feedback(db, category="citation_error")
    result = service.list_queue(
        FeedbackQueueQuery(), actor_user_id=uuid4(), actor_permissions=reviewer_perms
    )
    ids = {item.id for item in result.items}
    assert fb1 in ids
    assert fb2 in ids
    assert result.total_count >= 2


def test_list_queue_excludes_resolved(db, service, reviewer_perms):
    _make_feedback(db, status="resolved")
    result = service.list_queue(
        FeedbackQueueQuery(), actor_user_id=uuid4(), actor_permissions=reviewer_perms
    )
    # resolved items should not appear in the default (active) queue
    for item in result.items:
        assert item.status not in {"resolved", "dismissed"}


def test_list_queue_filter_by_category(db, service, reviewer_perms):
    _make_feedback(db, category="incorrect_answer")
    _make_feedback(db, category="other")
    result = service.list_queue(
        FeedbackQueueQuery(status=None, category="incorrect_answer"),
        actor_user_id=uuid4(),
        actor_permissions=reviewer_perms,
    )
    for item in result.items:
        assert item.category == "incorrect_answer"


def test_list_queue_unassigned_only(db, service, reviewer_perms):
    _make_feedback(db, status="open")
    result = service.list_queue(
        FeedbackQueueQuery(unassigned_only=True),
        actor_user_id=uuid4(),
        actor_permissions=reviewer_perms,
    )
    for item in result.items:
        assert item.reviewer_id is None


def test_list_queue_forbidden_without_permission(db, service):
    with pytest.raises(FeedbackReviewError, match="Forbidden"):
        service.list_queue(
            FeedbackQueueQuery(), actor_user_id=uuid4(), actor_permissions=frozenset()
        )


def test_list_queue_rejects_invalid_reviewer_filter(db, service, reviewer_perms):
    with pytest.raises(FeedbackReviewError, match="reviewer_id must be a UUID"):
        service.list_queue(
            FeedbackQueueQuery(reviewer_id="not-a-uuid"),
            actor_user_id=uuid4(),
            actor_permissions=reviewer_perms,
        )


def test_list_queue_pagination(db, service, reviewer_perms):
    for _ in range(5):
        _make_feedback(db)
    page1 = service.list_queue(
        FeedbackQueueQuery(limit=2, offset=0),
        actor_user_id=uuid4(),
        actor_permissions=reviewer_perms,
    )
    assert len(page1.items) == 2
    assert page1.next_offset == 2


def test_list_queue_prioritizes_critical_before_normal(db, service, reviewer_perms):
    normal_id = _make_feedback(db)
    critical_id = _make_feedback(db)
    with db() as session:
        feedback = session.get(Feedback, critical_id)
        assert feedback is not None
        feedback.priority = "critical"
        session.commit()
    result = service.list_queue(
        FeedbackQueueQuery(limit=10), actor_user_id=uuid4(), actor_permissions=reviewer_perms
    )
    assert result.items[0].id == critical_id
    assert normal_id in {item.id for item in result.items}


# ---------------------------------------------------------------------------
# Detail tests
# ---------------------------------------------------------------------------


def test_get_detail_returns_reviewer_notes(db, service, reviewer_perms):
    fb_id = _make_feedback(db)
    detail = service.get_detail(fb_id, actor_permissions=reviewer_perms)
    assert detail.id == fb_id
    assert detail.reviewer_notes == ""
    assert detail.trace_context is not None


def test_get_detail_not_found(db, service, reviewer_perms):
    with pytest.raises(FeedbackReviewError, match="not found"):
        service.get_detail(uuid4(), actor_permissions=reviewer_perms)


def test_get_detail_forbidden_without_permission(db, service):
    fb_id = _make_feedback(db)
    with pytest.raises(FeedbackReviewError, match="Forbidden"):
        service.get_detail(fb_id, actor_permissions=frozenset())


# ---------------------------------------------------------------------------
# Assignment tests
# ---------------------------------------------------------------------------


def test_assign_reviewer_transitions_to_in_review(db, service, reviewer_perms):
    fb_id = _make_feedback(db)
    reviewer_id = _make_reviewer_user(db)
    detail = service.assign(
        fb_id,
        FeedbackAssignRequest(reviewer_id=reviewer_id),
        actor_user_id=uuid4(),
        actor_permissions=reviewer_perms,
    )
    assert detail.reviewer_id == reviewer_id
    assert detail.status == "in_review"


def test_unassign_reviewer_reverts_to_open(db, service, reviewer_perms):
    fb_id = _make_feedback(db)
    reviewer_id = _make_reviewer_user(db)
    # assign first
    service.assign(
        fb_id,
        FeedbackAssignRequest(reviewer_id=reviewer_id),
        actor_user_id=uuid4(),
        actor_permissions=reviewer_perms,
    )
    # then unassign
    detail = service.assign(
        fb_id,
        FeedbackAssignRequest(reviewer_id=None),
        actor_user_id=uuid4(),
        actor_permissions=reviewer_perms,
    )
    assert detail.reviewer_id is None
    assert detail.status == "open"


def test_assign_writes_audit_record(db, service, reviewer_perms):
    fb_id = _make_feedback(db)
    reviewer_id = _make_reviewer_user(db)
    actor_id = uuid4()
    service.assign(
        fb_id,
        FeedbackAssignRequest(reviewer_id=reviewer_id),
        actor_user_id=actor_id,
        actor_permissions=reviewer_perms,
    )
    with db() as session:
        audit = session.scalar(
            select(AuditLog)
            .where(AuditLog.action == "feedback.assign")
            .where(AuditLog.resource_id == fb_id)
        )
    assert audit is not None
    assert audit.actor_user_id == actor_id
    # Reviewer ID logged in summary but NOT the full feedback body
    assert "reviewer_id" in (audit.after_summary or {})


def test_assign_forbidden_on_resolved(db, service, reviewer_perms):
    fb_id = _make_feedback(db, status="resolved")
    with db() as session:
        fb = session.get(Feedback, fb_id)
        # resolution required by model; set directly
        fb.resolved_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        session.commit()

    with pytest.raises(FeedbackReviewError, match="already resolved"):
        service.assign(
            fb_id,
            FeedbackAssignRequest(reviewer_id=uuid4()),
            actor_user_id=uuid4(),
            actor_permissions=reviewer_perms,
        )


def test_assign_rejects_unknown_reviewer(db, service, reviewer_perms):
    fb_id = _make_feedback(db)
    with pytest.raises(FeedbackReviewError, match="Reviewer user was not found"):
        service.assign(
            fb_id,
            FeedbackAssignRequest(reviewer_id=uuid4()),
            actor_user_id=uuid4(),
            actor_permissions=reviewer_perms,
        )


def test_assign_forbidden_without_manage_permission(db, service, read_only_perms):
    fb_id = _make_feedback(db)
    reviewer_id = _make_reviewer_user(db)
    with pytest.raises(FeedbackReviewError, match="Forbidden"):
        service.assign(
            fb_id,
            FeedbackAssignRequest(reviewer_id=reviewer_id),
            actor_user_id=uuid4(),
            actor_permissions=read_only_perms,
        )


# ---------------------------------------------------------------------------
# Classification tests
# ---------------------------------------------------------------------------


def test_classify_sets_root_cause_priority_severity(db, service, reviewer_perms):
    fb_id = _make_feedback(db)
    detail = service.classify(
        fb_id,
        FeedbackClassifyRequest(root_cause="model_error", priority="high", severity="p1"),
        actor_user_id=uuid4(),
        actor_permissions=reviewer_perms,
    )
    assert detail.root_cause == "model_error"
    assert detail.priority == "high"
    assert detail.severity == "p1"


def test_classify_updates_reviewer_notes(db, service, reviewer_perms):
    fb_id = _make_feedback(db)
    detail = service.classify(
        fb_id,
        FeedbackClassifyRequest(reviewer_notes="Confirmed model error on verse X."),
        actor_user_id=uuid4(),
        actor_permissions=reviewer_perms,
    )
    assert detail.reviewer_notes == "Confirmed model error on verse X."


def test_classify_rejects_invalid_root_cause(db, service, reviewer_perms):
    fb_id = _make_feedback(db)
    with pytest.raises(FeedbackReviewError, match="root_cause must be one of"):
        service.classify(
            fb_id,
            FeedbackClassifyRequest(root_cause="bad_value"),
            actor_user_id=uuid4(),
            actor_permissions=reviewer_perms,
        )


def test_classify_rejects_invalid_priority(db, service, reviewer_perms):
    fb_id = _make_feedback(db)
    with pytest.raises(FeedbackReviewError, match="priority must be one of"):
        service.classify(
            fb_id,
            FeedbackClassifyRequest(priority="super"),
            actor_user_id=uuid4(),
            actor_permissions=reviewer_perms,
        )


def test_classify_rejects_notes_over_limit(db, service, reviewer_perms):
    fb_id = _make_feedback(db)
    with pytest.raises(FeedbackReviewError, match="reviewer_notes must be at most"):
        service.classify(
            fb_id,
            FeedbackClassifyRequest(reviewer_notes="X" * 5000),
            actor_user_id=uuid4(),
            actor_permissions=reviewer_perms,
        )


def test_classify_writes_audit_without_user_notes_body(db, service, reviewer_perms):
    fb_id = _make_feedback(db)
    actor_id = uuid4()
    service.classify(
        fb_id,
        FeedbackClassifyRequest(reviewer_notes="internal note"),
        actor_user_id=actor_id,
        actor_permissions=reviewer_perms,
    )
    with db() as session:
        audit = session.scalar(
            select(AuditLog)
            .where(AuditLog.action == "feedback.classify")
            .where(AuditLog.resource_id == fb_id)
        )
    assert audit is not None
    # Notes length but NOT the note body should appear in the audit summary
    assert "reviewer_notes_length" in (audit.after_summary or {})
    assert "internal note" not in str(audit.after_summary)


def test_classify_forbidden_on_dismissed(db, service, reviewer_perms):
    fb_id = _make_feedback(db, status="dismissed")
    with pytest.raises(FeedbackReviewError, match="already dismissed"):
        service.classify(
            fb_id,
            FeedbackClassifyRequest(root_cause="duplicate"),
            actor_user_id=uuid4(),
            actor_permissions=reviewer_perms,
        )


# ---------------------------------------------------------------------------
# Resolution tests
# ---------------------------------------------------------------------------


def test_resolve_sets_status_resolved(db, service, reviewer_perms):
    fb_id = _make_feedback(db)
    detail = service.resolve(
        fb_id,
        FeedbackResolveRequest(resolution="Confirmed and fixed in pipeline."),
        actor_user_id=uuid4(),
        actor_permissions=reviewer_perms,
    )
    assert detail.status == "resolved"
    assert detail.resolution == "Confirmed and fixed in pipeline."
    assert detail.resolved_at is not None


def test_resolve_dismiss_sets_status_dismissed(db, service, reviewer_perms):
    fb_id = _make_feedback(db)
    detail = service.resolve(
        fb_id,
        FeedbackResolveRequest(resolution="Duplicate of earlier report.", dismissed=True),
        actor_user_id=uuid4(),
        actor_permissions=reviewer_perms,
    )
    assert detail.status == "dismissed"


def test_resolve_rejects_empty_resolution(db, service, reviewer_perms):
    fb_id = _make_feedback(db)
    with pytest.raises(FeedbackReviewError, match="resolution must not be empty"):
        service.resolve(
            fb_id,
            FeedbackResolveRequest(resolution="   "),
            actor_user_id=uuid4(),
            actor_permissions=reviewer_perms,
        )


def test_resolve_rejects_resolution_over_limit(db, service, reviewer_perms):
    fb_id = _make_feedback(db)
    with pytest.raises(FeedbackReviewError, match="resolution must be at most"):
        service.resolve(
            fb_id,
            FeedbackResolveRequest(resolution="X" * 5000),
            actor_user_id=uuid4(),
            actor_permissions=reviewer_perms,
        )


def test_resolve_cannot_be_re_resolved(db, service, reviewer_perms):
    fb_id = _make_feedback(db)
    service.resolve(
        fb_id,
        FeedbackResolveRequest(resolution="Done."),
        actor_user_id=uuid4(),
        actor_permissions=reviewer_perms,
    )
    with pytest.raises(FeedbackReviewError, match="already resolved"):
        service.resolve(
            fb_id,
            FeedbackResolveRequest(resolution="Again."),
            actor_user_id=uuid4(),
            actor_permissions=reviewer_perms,
        )


def test_resolve_writes_audit_record(db, service, reviewer_perms):
    fb_id = _make_feedback(db)
    actor_id = uuid4()
    service.resolve(
        fb_id,
        FeedbackResolveRequest(resolution="Issue fixed."),
        actor_user_id=actor_id,
        actor_permissions=reviewer_perms,
    )
    with db() as session:
        audit = session.scalar(
            select(AuditLog)
            .where(AuditLog.action == "feedback.resolve")
            .where(AuditLog.resource_id == fb_id)
        )
    assert audit is not None
    assert audit.actor_user_id == actor_id
    assert "terminal_status" in (audit.after_summary or {})
    # Resolution text body must NOT appear in audit
    assert "Issue fixed." not in str(audit.after_summary)


def test_full_workflow_assign_classify_resolve(db, service, reviewer_perms):
    """End-to-end: assign → classify → resolve."""
    fb_id = _make_feedback(db)
    reviewer_id = _make_reviewer_user(db)
    actor_id = uuid4()

    assigned = service.assign(
        fb_id,
        FeedbackAssignRequest(reviewer_id=reviewer_id),
        actor_user_id=actor_id,
        actor_permissions=reviewer_perms,
    )
    assert assigned.status == "in_review"

    classified = service.classify(
        fb_id,
        FeedbackClassifyRequest(root_cause="model_error", priority="high"),
        actor_user_id=actor_id,
        actor_permissions=reviewer_perms,
    )
    assert classified.root_cause == "model_error"

    resolved = service.resolve(
        fb_id,
        FeedbackResolveRequest(resolution="Model retrained with corrected data."),
        actor_user_id=actor_id,
        actor_permissions=reviewer_perms,
    )
    assert resolved.status == "resolved"

    # Resolved item no longer visible in active queue
    result = service.list_queue(
        FeedbackQueueQuery(), actor_user_id=actor_id, actor_permissions=reviewer_perms
    )
    active_ids = {item.id for item in result.items}
    assert fb_id not in active_ids
