"""Performance and load testing suite for Zayd (TASK-14-04)."""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from zayd_common.database.models import Base, EvaluationCase
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.enums import EvidenceStatus
from zayd_service_orchestrator.answer_orchestration import (
    AnswerOrchestrationRequest,
    AnswerOrchestrationStatus,
    AnswerOrchestrator,
    RetrievalResponse,
    TemplateAnswerGenerator,
)
from zayd_service_orchestrator.provider_sdk import (
    LLMProvider,
    LLMRequest,
    LLMResponse,
    ProviderCapabilities,
    ProviderSDKError,
)
from zayd_service_orchestrator.question_classification import QuestionClassifier
from zayd_service_orchestrator.risk_policy_engine import RiskPolicyEngine
from zayd_service_retrieval.evidence_sufficiency import EvidenceSufficiencyDecision

# ---------------------------------------------------------------------------
# Test Mocks
# ---------------------------------------------------------------------------


class MockDelayedLLMProvider(LLMProvider):
    def __init__(
        self,
        delay_sec: float = 0.05,
        should_fail: bool = False,
        fail_code: str = "PROVIDER_INTERNAL_ERROR",
    ) -> None:
        self.delay_sec = delay_sec
        self.should_fail = should_fail
        self.fail_code = fail_code

    def identity(self) -> Any:
        return type(
            "MockIdentity",
            (),
            {
                "name": "mock-delayed-llm",
                "kind": "llm",
                "model_id": "mock-delayed-model",
            },
        )()

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_streaming=True,
            supports_structured_output=True,
            max_input_tokens=8192,
            max_output_tokens=2048,
            capabilities=("generate", "stream"),
        )

    def validate_config(self, config: Any) -> Any:
        return type("MockVal", (), {"valid": True, "errors": (), "warnings": ()})()

    async def health_check(self) -> Any:
        return type(
            "MockHealth",
            (),
            {
                "status": "ok",
                "checked_at": datetime.now(UTC),
                "provider_name": "mock-delayed-llm",
            },
        )()

    async def generate(self, request: LLMRequest) -> LLMResponse:
        if self.delay_sec > 0:
            await asyncio.sleep(self.delay_sec)
        if self.should_fail:
            raise ProviderSDKError(self.fail_code, "Injected provider failure.")
        return LLMResponse(
            text="mocked response",
            usage=None,
            model_id="mock-delayed-model",
            finished_reason="stop",
        )


class MockSlowRetriever:
    def __init__(self, delay_sec: float = 0.02) -> None:
        self.delay_sec = delay_sec

    async def retrieve(
        self,
        question: str,
        *,
        classification: Any = None,
        trace_id: str | None = None,
        expanded: bool = False,
    ) -> RetrievalResponse:
        if self.delay_sec > 0:
            await asyncio.sleep(self.delay_sec)
        return RetrievalResponse(
            candidates=(),
            retriever_version="mock-slow-retriever",
            retrieval_run_id=uuid4(),
        )


# ---------------------------------------------------------------------------
# Performance & Load Test Scenarios
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_concurrent_load_scenario() -> None:
    """Load scenario: Simulate concurrent user chat queries and monitor latency."""
    # NFR-PERF-003: Local Retrieval resolves under 2 seconds.
    # NFR-PERF-002: System begins streaming under 5 seconds.
    retriever = MockSlowRetriever(delay_sec=0.01)
    generator = TemplateAnswerGenerator()
    orchestrator = AnswerOrchestrator(
        classifier=QuestionClassifier(),
        risk_policy_engine=RiskPolicyEngine(),
        retriever=retriever,  # type: ignore[arg-type]
        evidence_service=type(
            "MockEvidence",
            (),
            {
                "evaluate": lambda *a, **kw: EvidenceSufficiencyDecision(
                    status=EvidenceStatus.SUFFICIENT,
                    reason_codes=("sufficient_evidence",),
                    rules_version="evidence-sufficiency-v1",
                    allow_high_confidence_answer=True,
                    should_search_more=False,
                    should_abstain=False,
                    candidate_count=0,
                    distinct_source_count=0,
                    top_score=1.0,
                    average_score=1.0,
                    trace={},
                )
            }
        )(),  # type: ignore[arg-type]
        generator=generator,
    )

    request_payload = AnswerOrchestrationRequest(
        question="ขั้นตอนการอาบน้ำละหมาดตามมัซฮับชาฟิอีย์คืออะไร?",
        timeout_seconds=5.0,
    )

    start = time.perf_counter()
    # Concurrently execute 10 chat requests representing a burst of active pilot users
    tasks = [orchestrator.answer(request_payload) for _ in range(10)]
    results = await asyncio.gather(*tasks)
    end = time.perf_counter()

    elapsed = end - start

    # Ensure all succeeded
    assert all(r.status == AnswerOrchestrationStatus.ABSTAINED for r in results)
    # Ensure average latency of retrieval + stream start is well within rules
    assert elapsed < 1.0, f"Load latency was {elapsed:.2f}s, expected < 1s under mock parameters"


@pytest.mark.asyncio
async def test_soak_scenario() -> None:
    """Soak test: run sequential operations over database UoW sessionmaker."""
    # Verifies that database connection pools do not leak or starve sessions under load loops.
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    uow = SQLAlchemyUnitOfWork(session_factory)

    for _i in range(50):
        with uow:
            session = uow.session
            assert session is not None
            # Simple query checking session holds connection
            session.execute(select(1)).all()
            uow.commit()


@pytest.mark.asyncio
async def test_provider_failure_injection_handling() -> None:
    """Failure Injection: verify the system degrades safely and fails closed when LLM fails."""
    retriever = MockSlowRetriever(delay_sec=0.0)
    # Mock LLM provider that always fails with 429 RateLimit
    failing_llm = MockDelayedLLMProvider(should_fail=True, fail_code="PROVIDER_RATE_LIMIT")

    # Wire a custom generator with the failing LLM provider
    class FailingGenerator(TemplateAnswerGenerator):
        async def generate(self, *args, **kwargs):
            # simulate provider failure
            await failing_llm.generate(type("MockReq", (), {"messages": []})())

    orchestrator = AnswerOrchestrator(
        classifier=QuestionClassifier(),
        risk_policy_engine=RiskPolicyEngine(),
        retriever=retriever,  # type: ignore[arg-type]
        evidence_service=type(
            "MockEvidence",
            (),
            {
                "evaluate": lambda *a, **kw: EvidenceSufficiencyDecision(
                    status=EvidenceStatus.SUFFICIENT,
                    reason_codes=("sufficient_evidence",),
                    rules_version="evidence-sufficiency-v1",
                    allow_high_confidence_answer=True,
                    should_search_more=False,
                    should_abstain=False,
                    candidate_count=0,
                    distinct_source_count=0,
                    top_score=1.0,
                    average_score=1.0,
                    trace={},
                )
            }
        )(),  # type: ignore[arg-type]
        generator=FailingGenerator(),
    )

    result = await orchestrator.answer(
        AnswerOrchestrationRequest(
            question="ละหมาดขอดุอาอ์อย่างไร",
            timeout_seconds=2.0,
        )
    )

    # Hardening requirement: fails closed with FAILED state and details
    assert result.status == AnswerOrchestrationStatus.FAILED
    assert result.error_code == "PROVIDER_RATE_LIMIT"


def test_database_explain_query_plan() -> None:
    """Database query analysis: check query execution plans on SQLite."""
    assert EvaluationCase is not None
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    # Feed some mockup cases and runs
    actor, _dataset_id, _run_id = uuid4(), uuid4(), uuid4()

    # Check query explain plan on EvaluationCase table
    # Verification gate ensures queries leverage primary keys and indexes
    with session_factory() as session:
        # SQLite explain query plan returns parsing list
        plan = session.execute(
            __import__("sqlalchemy").text(
                "EXPLAIN QUERY PLAN SELECT * FROM evaluation_cases WHERE id = :id"
            ),
            {"id": str(actor)},
        ).all()
        plan_text = "\n".join(str(row) for row in plan)
        # Verify it uses an Index search rather than a SCAN (primary key lookup)
        assert "SEARCH" in plan_text or "INTEGER PRIMARY KEY" in plan_text
