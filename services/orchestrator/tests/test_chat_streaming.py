from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from zayd_common.auth import AuthService
from zayd_common.database.models import Base
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.prompt_registry import PromptRegistryService, bootstrap_registry_defaults
from zayd_service_orchestrator.answer_orchestration import (
    AnswerCitation,
    AnswerOrchestrationStatus,
    AnswerOrchestrator,
    StaticAnswerRetriever,
    TemplateAnswerGenerator,
)
from zayd_service_orchestrator.chat_streaming import (
    CHAT_RATE_LIMIT_MAX_STREAMS,
    VERIFIED_CITATION_STATUS,
    ChatRequest,
    ChatStatusStage,
    ChatStreamingError,
    ChatStreamingService,
    sse_encode,
)
from zayd_service_orchestrator.question_classification import QuestionClassifier
from zayd_service_orchestrator.risk_policy_engine import RiskPolicyEngine
from zayd_service_retrieval.evidence_sufficiency import (
    EvidenceCandidate,
    EvidenceSufficiencyService,
)


@pytest.fixture
def streaming_service() -> tuple[ChatStreamingService, PromptRegistryService]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    user = auth_service.register(
        email="stream-user@example.com",
        password="very-strong-password",
        display_name="Stream User",
    )
    registry = PromptRegistryService(SQLAlchemyUnitOfWork(session_factory))
    bootstrap_registry_defaults(registry, actor_user_id=user.user.id)
    prompt, policy_version_id, model_configuration_id = registry.resolve_answer_dependencies(
        prompt_name="answer-generation",
        policy_name="answer-safety",
    )
    source_id = uuid4()
    orchestrator = AnswerOrchestrator(
        classifier=QuestionClassifier(),
        risk_policy_engine=RiskPolicyEngine(),
        retriever=StaticAnswerRetriever(
            candidates=(
                _candidate(source_id=source_id, rank=1),
                _candidate(source_id=source_id, rank=2),
            )
        ),
        evidence_service=EvidenceSufficiencyService(),
        generator=TemplateAnswerGenerator(),
        prompt_version=prompt.version,
        prompt_version_id=prompt.id,
        policy_version_id=policy_version_id,
        model_configuration_id=model_configuration_id,
    )
    service = ChatStreamingService(
        uow_factory=lambda: SQLAlchemyUnitOfWork(session_factory),
        orchestrator=orchestrator,
        prompt_registry_factory=lambda: PromptRegistryService(SQLAlchemyUnitOfWork(session_factory)),
    )
    return service, registry


def _candidate(*, source_id, rank: int) -> EvidenceCandidate:
    return EvidenceCandidate(
        chunk_id=uuid4(),
        document_version_id=uuid4(),
        source_id=source_id,
        canonical_reference=f"ref:{rank}",
        madhhab="shafii",
        source_type="fiqh",
        license_status="persistent_redistributable",
        score_final=0.9,
        score_reranker=0.9,
        score_reliability=1.0,
        rank=rank,
        metadata={},
    )


async def _collect_events(handle) -> list[str]:
    frames: list[str] = []
    async for event in handle.events:
        frames.append(sse_encode(event))
    return frames


@pytest.mark.asyncio
async def test_sse_contract_emits_status_and_verified_final_answer(
    streaming_service: tuple[ChatStreamingService, PromptRegistryService],
) -> None:
    service, _registry = streaming_service
    handle = service.start_stream(
        ChatRequest(
            question="ละหมาดคืออะไร",
            actor_user_id=uuid4(),
        )
    )
    frames = await _collect_events(handle)
    joined = "".join(frames)

    assert "event: status" in joined
    assert ChatStatusStage.ACCEPTED.value in joined
    assert "event: final_answer" in joined
    assert "event: complete" in joined
    assert "chain_of_thought" not in joined
    assert "prompt_body" not in joined
    assert f'"verification_status": "{VERIFIED_CITATION_STATUS}"' in joined


@pytest.mark.asyncio
async def test_disconnect_cancels_active_stream(
    streaming_service: tuple[ChatStreamingService, PromptRegistryService],
) -> None:
    service, _registry = streaming_service
    handle = service.start_stream(
        ChatRequest(
            question="ละหมาดคืออะไร",
            actor_user_id=uuid4(),
        )
    )

    await asyncio.sleep(0)
    handle.cancel()
    frames = await _collect_events(handle)
    joined = "".join(frames)

    assert ChatStatusStage.CANCELLED.value in joined
    assert AnswerOrchestrationStatus.CANCELLED.value in joined


@pytest.mark.asyncio
async def test_rate_limit_blocks_excessive_streams(
    streaming_service: tuple[ChatStreamingService, PromptRegistryService],
) -> None:
    service, _registry = streaming_service
    actor_id = uuid4()
    for _ in range(CHAT_RATE_LIMIT_MAX_STREAMS):
        handle = service.start_stream(ChatRequest(question="test", actor_user_id=actor_id))
        handle.cancel()

    with pytest.raises(ChatStreamingError, match="Too many chat stream requests"):
        service.start_stream(ChatRequest(question="test", actor_user_id=actor_id))


@pytest.mark.asyncio
async def test_reconnect_snapshot_replays_events_after_last_event_id(
    streaming_service: tuple[ChatStreamingService, PromptRegistryService],
) -> None:
    service, _registry = streaming_service
    handle = service.start_stream(
        ChatRequest(
            question="ละหมาดคืออะไร",
            actor_user_id=uuid4(),
        )
    )
    events = [event async for event in handle.events]
    assert events
    snapshot = service.get_snapshot(stream_id=handle.stream_id, last_event_id=events[0].event_id)
    assert snapshot.completed is True
    assert snapshot.events
    assert snapshot.events[0].event_id != events[0].event_id


def test_verified_citations_exclude_unverified_entries() -> None:
    from zayd_service_orchestrator.answer_orchestration import ConfidenceLevel, StructuredAnswer
    from zayd_service_orchestrator.chat_streaming import _answer_json

    answer = StructuredAnswer(
        answer_id="ans-1",
        summary="summary",
        answer_th="answer",
        madhhab="shafii",
        risk_level="low",
        evidence_sufficient=True,
        confidence=ConfidenceLevel.HIGH,
        citations=(
            AnswerCitation(
                citation_id="c1",
                display="Verified",
                source_type="fiqh",
                verification_status=VERIFIED_CITATION_STATUS,
            ),
            AnswerCitation(
                citation_id="c2",
                display="Unverified",
                source_type="fiqh",
                verification_status="needs_review",
            ),
        ),
    )

    payload = _answer_json(answer, no_history=False)
    assert len(payload["citations"]) == 1
    assert payload["citations"][0]["citation_id"] == "c1"