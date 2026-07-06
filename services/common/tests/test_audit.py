import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from zayd_common.audit import AuditLogQuery, AuditService
from zayd_common.auth import AuthService
from zayd_common.database.models import AuditLog, Base
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork


@pytest.fixture
def services() -> tuple[AuthService, AuditService, sessionmaker]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    return (
        AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret"),
        AuditService(SQLAlchemyUnitOfWork(session_factory)),
        session_factory,
    )


def test_audit_records_are_hash_chained_and_include_request_metadata(
    services: tuple[AuthService, AuditService, sessionmaker],
) -> None:
    auth_service, audit_service, _session_factory = services
    user = auth_service.register(
        email="audited@example.com",
        password="very-strong-password",
        display_name="Audited",
    )

    record = audit_service.record(
        actor_user_id=user.user.id,
        action="providers.disable",
        resource_type="provider",
        resource_id=user.user.id,
        outcome="success",
        request_id="req-audit-1",
        trace_id="trace-audit-1",
        before_summary={"status": "enabled"},
        after_summary={"status": "disabled"},
    )

    records = audit_service.list_records(AuditLogQuery(request_id="req-audit-1"))
    assert [item.id for item in records] == [record.id]
    assert records[0].request_id == "req-audit-1"
    assert records[0].trace_id == "trace-audit-1"
    assert records[0].hash_algorithm == "sha256"
    assert len(records[0].content_hash) == 64
    assert records[0].previous_hash is not None


def test_application_cannot_update_or_delete_audit_entries(
    services: tuple[AuthService, AuditService, sessionmaker],
) -> None:
    _auth_service, audit_service, session_factory = services
    record = audit_service.record(
        action="prompts.update",
        resource_type="prompt",
        outcome="success",
        after_summary={"version": "1.0.0"},
    )

    with session_factory() as session:
        stored = session.get(AuditLog, record.id)
        assert stored is not None
        stored.reason = "changed"
        with pytest.raises(ValueError, match="append-only"):
            session.commit()
        session.rollback()

    with session_factory() as session:
        stored = session.get(AuditLog, record.id)
        assert stored is not None
        session.delete(stored)
        with pytest.raises(ValueError, match="append-only"):
            session.commit()


def test_audit_redacts_sensitive_summary_keys(
    services: tuple[AuthService, AuditService, sessionmaker],
) -> None:
    _auth_service, audit_service, _session_factory = services
    audit_service.record(
        action="auth.login",
        resource_type="auth",
        outcome="failure",
        before_summary={"email": "user@example.com", "password": "secret-password"},
        after_summary={"nested": {"access_token": "secret-token", "safe": "ok"}},
        source_context={"authorization": "Bearer secret", "ip_hash": "abc"},
    )

    record = audit_service.list_records(AuditLogQuery(action="auth.login"))[0]

    assert record.before_summary == {"email": "user@example.com", "password": "[REDACTED]"}
    assert record.after_summary == {"nested": {"access_token": "[REDACTED]", "safe": "ok"}}
    assert record.source_context == {"authorization": "[REDACTED]", "ip_hash": "abc"}


def test_audit_export_is_jsonl_and_bounded(
    services: tuple[AuthService, AuditService, sessionmaker],
) -> None:
    _auth_service, audit_service, _session_factory = services
    audit_service.record(action="documents.publish", resource_type="document", outcome="success")
    audit_service.record(action="documents.suspend", resource_type="document", outcome="denied")

    exported = audit_service.export_jsonl(AuditLogQuery(resource_type="document", limit=1))

    assert exported.count("\n") == 1
    assert "content_hash" in exported
    assert "documents." in exported


def test_audit_log_query_filters_by_resource_and_outcome(
    services: tuple[AuthService, AuditService, sessionmaker],
) -> None:
    _auth_service, audit_service, session_factory = services
    audit_service.record(action="licenses.update", resource_type="license", outcome="success")
    audit_service.record(action="licenses.delete", resource_type="license", outcome="denied")

    denied = audit_service.list_records(AuditLogQuery(resource_type="license", outcome="denied"))

    assert len(denied) == 1
    assert denied[0].action == "licenses.delete"
    with session_factory() as session:
        assert len(session.execute(select(AuditLog)).scalars().all()) == 2
