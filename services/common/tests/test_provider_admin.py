from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from zayd_common.auth import AuthService
from zayd_common.database.models import AuditLog, Base
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.provider_admin import (
    ModelConfigurationCreate,
    ProviderAdminError,
    ProviderAdminService,
    ProviderCreate,
)


@pytest.fixture
def service() -> tuple[ProviderAdminService, sessionmaker, object]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    admin = auth_service.register(
        email="provider-admin@example.com",
        password="very-strong-password",
        display_name="Provider Admin",
    )
    return (
        ProviderAdminService(SQLAlchemyUnitOfWork(session_factory)),
        session_factory,
        admin.user.id,
    )


def test_secret_is_write_only_and_not_returned(service) -> None:
    admin_service, _session_factory, actor_id = service
    provider = admin_service.create_provider(
        data=ProviderCreate(
            name="OpenAI Compatible",
            provider_type="llm",
            status="enabled",
            base_url="https://api.example.com",
            secret_ref="vault://providers/openai",
            terms_url="https://example.com/terms",
            data_policy_json={"classification": "restricted"},
        ),
        actor_user_id=actor_id,
        trace_id="trace-provider-create",
    )

    assert provider.secret_configured is True
    assert provider.secret_mask == "configured"
    assert "vault://" not in str(provider)


def test_connection_test_is_rate_limited_and_audited(service) -> None:
    admin_service, session_factory, actor_id = service
    provider = admin_service.create_provider(
        data=ProviderCreate(
            name="Local LLM",
            provider_type="llm",
            status="enabled",
            base_url="https://local.example.com",
        ),
        actor_user_id=actor_id,
    )

    for _ in range(5):
        result = admin_service.test_connection(provider_id=provider.id, actor_user_id=actor_id)
        assert result.status == "ok"

    with pytest.raises(ProviderAdminError) as exc_info:
        admin_service.test_connection(
            provider_id=provider.id,
            actor_user_id=actor_id,
            trace_id="trace-provider-rate-limit",
        )

    assert exc_info.value.code == "PROVIDER_CONNECTION_RATE_LIMITED"
    with session_factory() as session:
        rows = session.execute(select(AuditLog)).scalars().all()
        assert any(log.action == "providers.connection_test" for log in rows)
        assert any(log.action == "providers.connection_test.rate_limit" for log in rows)


def test_disable_impact_requires_fallback_readiness(service) -> None:
    admin_service, _session_factory, actor_id = service
    primary = admin_service.create_provider(
        data=ProviderCreate(
            name="Primary LLM",
            provider_type="llm",
            status="enabled",
            base_url="https://primary.example.com",
        ),
        actor_user_id=actor_id,
    )
    secondary = admin_service.create_provider(
        data=ProviderCreate(
            name="Fallback LLM",
            provider_type="llm",
            status="enabled",
            base_url="https://fallback.example.com",
        ),
        actor_user_id=actor_id,
    )
    fallback = admin_service.create_model(
        data=ModelConfigurationCreate(
            provider_id=secondary.id,
            model_name="fallback-model",
            model_type="llm",
            status="enabled",
            is_default=False,
        ),
        actor_user_id=actor_id,
    )
    primary_provider = admin_service.create_model(
        data=ModelConfigurationCreate(
            provider_id=primary.id,
            model_name="primary-model",
            model_type="llm",
            status="enabled",
            is_default=True,
            fallback_model_id=fallback.id,
        ),
        actor_user_id=actor_id,
    )

    listed = admin_service.get_provider(provider_id=primary_provider.provider_id)
    assert listed.disable_impact.safe_to_disable is True
    assert listed.disable_impact.fallback_readiness[0].fallback_ready is True
