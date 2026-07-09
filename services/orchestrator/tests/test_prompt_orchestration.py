from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from zayd_common.auth import AuthService
from zayd_common.database.models import Base
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.prompt_registry import (
    DEFAULT_ANSWER_PROMPT_NAME,
    PromptRegistryService,
    bootstrap_registry_defaults,
)
from zayd_service_orchestrator.answer_orchestration import (
    AnswerOrchestrationRequest,
    AnswerOrchestrationStatus,
    StaticAnswerRetriever,
    TemplateAnswerGenerator,
)
from zayd_service_retrieval.evidence_sufficiency import EvidenceCandidate


@pytest.fixture
def managed_orchestrator():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    user = auth_service.register(
        email="orchestrator-prompt@example.com",
        password="very-strong-password",
        display_name="Orchestrator Prompt",
    )
    registry = PromptRegistryService(SQLAlchemyUnitOfWork(session_factory))
    bootstrap_registry_defaults(registry, actor_user_id=user.user.id)
    prompt, policy_version_id, model_configuration_id = registry.resolve_answer_dependencies(
        prompt_name=DEFAULT_ANSWER_PROMPT_NAME,
        policy_name="answer-safety",
    )
    from zayd_service_orchestrator.answer_orchestration import (
        AnswerOrchestrator,
        QuestionClassifier,
    )
    from zayd_service_orchestrator.risk_policy_engine import RiskPolicyEngine
    from zayd_service_retrieval.evidence_sufficiency import EvidenceSufficiencyService

    orchestrator = AnswerOrchestrator(
        classifier=QuestionClassifier(),
        risk_policy_engine=RiskPolicyEngine(),
        retriever=StaticAnswerRetriever(candidates=()),
        evidence_service=EvidenceSufficiencyService(),
        generator=TemplateAnswerGenerator(),
        prompt_version=prompt.version,
        prompt_version_id=prompt.id,
        policy_version_id=policy_version_id,
        model_configuration_id=model_configuration_id,
    )
    return orchestrator, registry


def _candidate(*, source_id=None, rank: int = 1) -> EvidenceCandidate:
    return EvidenceCandidate(
        chunk_id=uuid4(),
        document_version_id=uuid4(),
        source_id=source_id or uuid4(),
        canonical_reference=f"ref:{rank}",
        madhhab="shafii",
        source_type="fiqh",
        license_status="persistent_redistributable",
        score_final=0.9,
        score_reranker=0.9,
        score_reliability=1.0,
        rank=1,
        metadata={},
    )


@pytest.mark.asyncio
async def test_managed_orchestrator_records_prompt_version_in_trace(managed_orchestrator) -> None:
    orchestrator, registry = managed_orchestrator
    source_id = uuid4()
    orchestrator.retriever = StaticAnswerRetriever(
        candidates=(
            _candidate(source_id=source_id, rank=1),
            _candidate(source_id=source_id, rank=2),
        )
    )

    result = await orchestrator.answer(
        AnswerOrchestrationRequest(
            question="ละหมาดคืออะไร",
            idempotency_key="prompt-version-trace",
            trace_id="trace-prompt-version",
        )
    )

    active_prompt = registry.resolve_active_prompt(prompt_name=DEFAULT_ANSWER_PROMPT_NAME)
    assert result.status == AnswerOrchestrationStatus.COMPLETED
    assert result.trace["prompt_version"] == active_prompt.version
    assert result.trace["prompt_version_id"] == str(active_prompt.id)
    assert result.trace["policy_version_id"] is not None
    assert result.trace["model_configuration_id"] is not None