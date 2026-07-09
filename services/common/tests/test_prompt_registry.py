from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from zayd_common.audit import AuditLogQuery, AuditService
from zayd_common.auth import AuthService
from zayd_common.database.models import AuditLog, Base, ModelConfiguration
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.prompt_registry import (
    DEFAULT_ANSWER_PROMPT_NAME,
    PromptCreate,
    PromptRegistryError,
    PromptRegistryService,
    PromptTestCase,
    bootstrap_registry_defaults,
)


@pytest.fixture
def services() -> tuple[PromptRegistryService, AuditService, sessionmaker, object]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    user = auth_service.register(
        email="prompt-admin@example.com",
        password="very-strong-password",
        display_name="Prompt Admin",
    )
    return (
        PromptRegistryService(SQLAlchemyUnitOfWork(session_factory)),
        AuditService(SQLAlchemyUnitOfWork(session_factory)),
        session_factory,
        user.user.id,
    )


def _prompt_create(*, version: str = "v1", body: str = "Prompt body v1") -> PromptCreate:
    return PromptCreate(
        name="answer-generation",
        version=version,
        prompt_body=body,
        purpose="Answer generation prompt",
        owner="orchestrator",
        input_schema={"question": "string"},
        output_schema={"answer_th": "string"},
        changelog=("Initial version",),
        test_cases=(
            PromptTestCase(
                name="basic",
                input_payload={"question": "test"},
                expected_assertions=("returns Thai answer",),
            ),
        ),
    )


def test_create_prompt_stores_versioned_record_as_draft(
    services: tuple[PromptRegistryService, AuditService, sessionmaker, object],
) -> None:
    registry, _audit_service, _session_factory, actor_id = services

    prompt = registry.create_prompt(
        data=_prompt_create(),
        actor_user_id=actor_id,
        trace_id="trace-create",
    )

    assert prompt.name == "answer-generation"
    assert prompt.version == "v1"
    assert prompt.status == "draft"
    assert prompt.owner == "orchestrator"
    assert prompt.purpose == "Answer generation prompt"
    assert prompt.test_cases[0].name == "basic"
    assert prompt.active is False


def test_draft_prompt_cannot_be_used_for_answer_generation(
    services: tuple[PromptRegistryService, AuditService, sessionmaker, object],
) -> None:
    registry, _audit_service, _session_factory, actor_id = services
    registry.create_prompt(data=_prompt_create(), actor_user_id=actor_id)
    registry.create_policy(
        policy_name="answer-safety",
        version="v1",
        policy_json={"policy_version": "risk-policy-v1"},
        actor_user_id=actor_id,
        status="approved",
    )

    with pytest.raises(PromptRegistryError, match="approved prompt version"):
        registry.resolve_answer_dependencies(
            prompt_name=DEFAULT_ANSWER_PROMPT_NAME,
            policy_name="answer-safety",
        )


def test_approve_prompt_activates_version_and_audits(
    services: tuple[PromptRegistryService, AuditService, sessionmaker, object],
) -> None:
    registry, audit_service, _session_factory, actor_id = services
    created = registry.create_prompt(
        data=_prompt_create(),
        actor_user_id=actor_id,
        trace_id="trace-approve",
    )

    result = registry.approve_prompt(
        prompt_id=created.id,
        actor_user_id=actor_id,
        trace_id="trace-approve",
    )

    assert result.changed is True
    assert result.prompt.status == "approved"
    assert result.active_prompt is not None
    assert result.active_prompt.version == "v1"
    records = audit_service.list_records(AuditLogQuery(resource_type="prompt_version"))
    assert any(record.action == "prompts.approve" for record in records)


def test_rollback_prompt_switches_active_version(
    services: tuple[PromptRegistryService, AuditService, sessionmaker, object],
) -> None:
    registry, _audit_service, _session_factory, actor_id = services
    v1 = registry.create_prompt(data=_prompt_create(version="v1"), actor_user_id=actor_id)
    v2 = registry.create_prompt(
        data=_prompt_create(version="v2", body="Prompt body v2"),
        actor_user_id=actor_id,
    )
    registry.approve_prompt(prompt_id=v1.id, actor_user_id=actor_id)
    registry.approve_prompt(prompt_id=v2.id, actor_user_id=actor_id)

    rollback = registry.rollback_prompt(
        prompt_name="answer-generation",
        target_version="v1",
        actor_user_id=actor_id,
        trace_id="trace-rollback",
    )

    assert rollback.changed is True
    assert rollback.active_prompt is not None
    assert rollback.active_prompt.version == "v1"
    active = registry.resolve_active_prompt(prompt_name="answer-generation")
    assert active.version == "v1"


def test_compare_versions_reports_differences(
    services: tuple[PromptRegistryService, AuditService, sessionmaker, object],
) -> None:
    registry, _audit_service, _session_factory, actor_id = services
    registry.create_prompt(data=_prompt_create(version="v1"), actor_user_id=actor_id)
    registry.create_prompt(
        data=_prompt_create(version="v2", body="Prompt body v2"),
        actor_user_id=actor_id,
    )

    comparison = registry.compare_versions(
        prompt_name="answer-generation",
        from_version="v1",
        to_version="v2",
    )

    assert comparison.body_changed is True
    assert comparison.from_status == "draft"
    assert comparison.to_status == "draft"


def test_bootstrap_registry_defaults_seeds_approved_dependencies(
    services: tuple[PromptRegistryService, AuditService, sessionmaker, object],
) -> None:
    registry, _audit_service, session_factory, actor_id = services

    bootstrap_registry_defaults(registry, actor_user_id=actor_id)

    prompt, policy_id, model_id = registry.resolve_answer_dependencies(
        prompt_name=DEFAULT_ANSWER_PROMPT_NAME,
        policy_name="answer-safety",
    )
    assert prompt.status == "approved"
    assert policy_id is not None
    assert model_id is not None
    with session_factory() as session:
        model = session.get(ModelConfiguration, model_id)
        assert model is not None
        assert model.is_default is True


def test_create_prompt_rejects_duplicate_name_version(
    services: tuple[PromptRegistryService, AuditService, sessionmaker, object],
) -> None:
    registry, _audit_service, _session_factory, actor_id = services
    registry.create_prompt(data=_prompt_create(), actor_user_id=actor_id)

    with pytest.raises(PromptRegistryError, match="already exists"):
        registry.create_prompt(data=_prompt_create(), actor_user_id=actor_id)


def test_prompt_mutations_write_audit_records(
    services: tuple[PromptRegistryService, AuditService, sessionmaker, object],
) -> None:
    registry, _audit_service, session_factory, actor_id = services
    created = registry.create_prompt(
        data=_prompt_create(),
        actor_user_id=actor_id,
        trace_id="trace-audit",
    )
    registry.approve_prompt(prompt_id=created.id, actor_user_id=actor_id, trace_id="trace-audit")

    with session_factory() as session:
        rows = session.execute(
            select(AuditLog).where(AuditLog.resource_type == "prompt_version")
        ).scalars().all()
        actions = {row.action for row in rows}
        assert "prompts.create" in actions
        assert "prompts.approve" in actions
        assert all(row.outcome == "success" for row in rows)