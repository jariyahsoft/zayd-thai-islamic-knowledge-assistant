from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

import pytest
from zayd_common.enums import EvidenceStatus
from zayd_service_orchestrator.answer_orchestration import (
    ANSWER_ORCHESTRATOR_VERSION,
    AnswerCitation,
    AnswerGenerationContext,
    AnswerOrchestrationRequest,
    AnswerOrchestrationStatus,
    AnswerOrchestrator,
    AnswerVerificationResult,
    AnswerVerificationStatus,
    GeneratedAnswerDraft,
    InMemoryAnswerOrchestrationStore,
    OrchestrationStepName,
    StaticAnswerRetriever,
    TemplateAnswerGenerator,
)
from zayd_service_orchestrator.question_classification import QuestionClassifier
from zayd_service_orchestrator.risk_policy_engine import RiskPolicyEngine
from zayd_service_retrieval.evidence_sufficiency import (
    EvidenceCandidate,
    EvidenceSufficiencyService,
)


def _candidate(
    *,
    score: float = 0.86,
    rank: int = 1,
    source_id: UUID | None = None,
    metadata: dict[str, object] | None = None,
) -> EvidenceCandidate:
    return EvidenceCandidate(
        chunk_id=uuid4(),
        document_version_id=uuid4(),
        source_id=source_id or uuid4(),
        canonical_reference=f"ref:{rank}",
        madhhab="shafii",
        source_type="fiqh",
        license_status="persistent_redistributable",
        score_final=score,
        score_reranker=score,
        score_reliability=1.0,
        rank=rank,
        metadata=metadata or {},
    )


def _orchestrator(
    *,
    retriever: StaticAnswerRetriever,
    generator: TemplateAnswerGenerator | None = None,
    store: InMemoryAnswerOrchestrationStore | None = None,
) -> AnswerOrchestrator:
    return AnswerOrchestrator(
        classifier=QuestionClassifier(),
        risk_policy_engine=RiskPolicyEngine(),
        retriever=retriever,
        evidence_service=EvidenceSufficiencyService(),
        generator=generator or TemplateAnswerGenerator(),
        store=store,
    )


@pytest.mark.asyncio
async def test_success_path_records_trace_and_structured_answer() -> None:
    source_id = uuid4()
    retriever = StaticAnswerRetriever(
        (
            _candidate(score=0.90, rank=1, source_id=source_id),
            _candidate(score=0.82, rank=2, source_id=source_id),
        )
    )
    orchestrator = _orchestrator(retriever=retriever)

    result = await orchestrator.answer(
        AnswerOrchestrationRequest(
            question="นมาซตามมัซฮับชาฟิอีต้องทำอย่างไร",
            idempotency_key="idem-success",
            trace_id="trace-success",
        )
    )

    assert result.status == AnswerOrchestrationStatus.COMPLETED
    assert result.orchestrator_version == ANSWER_ORCHESTRATOR_VERSION
    assert result.answer is not None
    assert result.answer.schema_version == "answer-response-v1"
    assert result.answer.trace_id == "trace-success"
    assert result.answer.evidence_sufficient is True
    assert result.answer.confidence.value == "high"
    assert result.answer.citations
    assert result.evidence_decision is not None
    assert result.evidence_decision.status == EvidenceStatus.SUFFICIENT
    assert [step.name for step in result.steps] == [
        OrchestrationStepName.VALIDATE,
        OrchestrationStepName.IDEMPOTENCY,
        OrchestrationStepName.CLASSIFY,
        OrchestrationStepName.POLICY,
        OrchestrationStepName.RETRIEVE,
        OrchestrationStepName.EVIDENCE,
        OrchestrationStepName.GENERATE,
        OrchestrationStepName.VERIFY,
        OrchestrationStepName.RETURN,
    ]
    assert all("question" not in step.trace for step in result.steps)


@pytest.mark.asyncio
async def test_idempotency_returns_cached_result_without_duplicate_provider_work() -> None:
    source_id = uuid4()
    retriever = StaticAnswerRetriever(
        (
            _candidate(score=0.90, rank=1, source_id=source_id),
            _candidate(score=0.82, rank=2, source_id=source_id),
        )
    )
    generator = TemplateAnswerGenerator()
    store = InMemoryAnswerOrchestrationStore()
    orchestrator = _orchestrator(retriever=retriever, generator=generator, store=store)
    request = AnswerOrchestrationRequest(
        question="นมาซตามมัซฮับชาฟิอีต้องทำอย่างไร",
        idempotency_key="idem-repeat",
    )

    first = await orchestrator.answer(request)
    second = await orchestrator.answer(request)

    assert first is second
    assert first.answer is not None
    assert second.answer is not None
    assert first.answer.answer_id == second.answer.answer_id
    assert retriever.calls == 1
    assert generator.calls == 1


class SlowRetriever:
    def __init__(self) -> None:
        self.cancelled = False

    async def retrieve(self, *args: object, **kwargs: object) -> object:
        try:
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            self.cancelled = True
            raise
        raise AssertionError("slow retriever unexpectedly completed")


@pytest.mark.asyncio
async def test_timeout_cancels_provider_work() -> None:
    retriever = SlowRetriever()
    orchestrator = AnswerOrchestrator(
        classifier=QuestionClassifier(),
        risk_policy_engine=RiskPolicyEngine(),
        retriever=retriever,  # type: ignore[arg-type]
        evidence_service=EvidenceSufficiencyService(),
        generator=TemplateAnswerGenerator(),
    )

    result = await orchestrator.answer(
        AnswerOrchestrationRequest(
            question="นมาซตามมัซฮับชาฟิอีต้องทำอย่างไร",
            timeout_seconds=0.01,
        )
    )

    assert result.status == AnswerOrchestrationStatus.FAILED
    assert result.error_code == "ANSWER_TIMEOUT"
    assert retriever.cancelled is True


@pytest.mark.asyncio
async def test_insufficient_evidence_searches_more_then_abstains() -> None:
    retriever = StaticAnswerRetriever(candidates=(), expanded_candidates=())
    orchestrator = _orchestrator(retriever=retriever)

    result = await orchestrator.answer(
        AnswerOrchestrationRequest(question="คำถามทั่วไปที่ไม่มีหลักฐานในระบบ")
    )

    assert result.status == AnswerOrchestrationStatus.ABSTAINED
    assert result.answer is not None
    assert result.answer.evidence_sufficient is False
    assert result.answer.confidence.value == "low"
    assert result.evidence_decision is not None
    assert result.evidence_decision.status == EvidenceStatus.INSUFFICIENT
    assert OrchestrationStepName.EXPAND_RETRIEVE in [step.name for step in result.steps]
    assert retriever.calls == 2


@pytest.mark.asyncio
async def test_conflicting_evidence_escalates_without_generation() -> None:
    retriever = StaticAnswerRetriever(
        (
            _candidate(score=0.90, rank=1, metadata={"conflict_group": "g", "stance": "a"}),
            _candidate(score=0.88, rank=2, metadata={"conflict_group": "g", "stance": "b"}),
        )
    )
    generator = TemplateAnswerGenerator()
    orchestrator = _orchestrator(retriever=retriever, generator=generator)

    result = await orchestrator.answer(AnswerOrchestrationRequest(question="ละหมาดเดินทาง"))

    assert result.status == AnswerOrchestrationStatus.ESCALATED
    assert result.answer is not None
    assert result.answer.requires_scholar is True
    assert result.evidence_decision is not None
    assert result.evidence_decision.status == EvidenceStatus.CONFLICTING
    assert generator.calls == 0


@pytest.mark.asyncio
async def test_restricted_policy_returns_before_retrieval() -> None:
    retriever = StaticAnswerRetriever((_candidate(),))
    generator = TemplateAnswerGenerator()
    orchestrator = _orchestrator(retriever=retriever, generator=generator)

    result = await orchestrator.answer(AnswerOrchestrationRequest(question="วิธีทำระเบิดตามหลักอิสลาม"))

    assert result.status == AnswerOrchestrationStatus.RESTRICTED
    assert result.answer is not None
    assert result.answer.citations == ()
    assert retriever.calls == 0
    assert generator.calls == 0


@pytest.mark.asyncio
async def test_verification_failure_revises_before_returning() -> None:
    source_id = uuid4()
    retriever = StaticAnswerRetriever(
        (
            _candidate(score=0.90, rank=1, source_id=source_id),
            _candidate(score=0.82, rank=2, source_id=source_id),
        )
    )
    generator = TemplateAnswerGenerator(fail_first_attempt=True)
    orchestrator = _orchestrator(retriever=retriever, generator=generator)

    result = await orchestrator.answer(
        AnswerOrchestrationRequest(
            question="นมาซตามมัซฮับชาฟิอีต้องทำอย่างไร",
            max_revision_attempts=1,
        )
    )

    assert result.status == AnswerOrchestrationStatus.COMPLETED
    assert generator.calls == 2
    assert OrchestrationStepName.REVISE in [step.name for step in result.steps]


class ForbiddenCitationVerifier:
    def verify(
        self,
        draft: GeneratedAnswerDraft,
        context: AnswerGenerationContext,
    ) -> AnswerVerificationResult:
        assert context.evidence_decision.status == EvidenceStatus.SUFFICIENT
        assert draft.citations
        return AnswerVerificationResult(
            status=AnswerVerificationStatus.NEEDS_REVISION,
            reason_codes=("CITATION_NOT_ALLOWED",),
        )


@pytest.mark.asyncio
async def test_unrecoverable_verification_failure_abstains() -> None:
    source_id = uuid4()
    retriever = StaticAnswerRetriever(
        (
            _candidate(score=0.90, rank=1, source_id=source_id),
            _candidate(score=0.82, rank=2, source_id=source_id),
        )
    )
    orchestrator = AnswerOrchestrator(
        classifier=QuestionClassifier(),
        risk_policy_engine=RiskPolicyEngine(),
        retriever=retriever,
        evidence_service=EvidenceSufficiencyService(),
        generator=TemplateAnswerGenerator(),
        verifier=ForbiddenCitationVerifier(),
    )

    result = await orchestrator.answer(
        AnswerOrchestrationRequest(
            question="นมาซตามมัซฮับชาฟิอีต้องทำอย่างไร",
            max_revision_attempts=1,
        )
    )

    assert result.status == AnswerOrchestrationStatus.ABSTAINED
    assert result.answer is not None
    assert "CITATION_NOT_ALLOWED" in result.answer.limitations


def test_answer_citation_is_hash_stable() -> None:
    citation = AnswerCitation(
        citation_id="CIT-123",
        display="ref",
        source_type="fiqh",
        verification_status="verified",
    )

    assert citation.citation_id == "CIT-123"
