from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from zayd_common.database.models import Base, RetrievalRun
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.enums import EvidenceStatus
from zayd_service_retrieval.evidence_sufficiency import (
    EVIDENCE_SUFFICIENCY_RULES_VERSION,
    EvidenceCandidate,
    EvidenceSufficiencyError,
    EvidenceSufficiencyRequest,
    EvidenceSufficiencyService,
    EvidenceSufficiencyThresholds,
)


def _candidate(
    *,
    score: float = 0.80,
    reliability: float = 1.0,
    source_id=None,
    madhhab: str = "shafii",
    rank: int = 1,
    metadata: dict[str, object] | None = None,
) -> EvidenceCandidate:
    return EvidenceCandidate(
        chunk_id=uuid4(),
        document_version_id=uuid4(),
        source_id=source_id or uuid4(),
        canonical_reference=f"ref:{rank}",
        madhhab=madhhab,
        source_type="fiqh",
        license_status="persistent_redistributable",
        score_final=score,
        score_reranker=score,
        score_reliability=reliability,
        rank=rank,
        metadata=metadata or {},
    )


def test_evidence_sufficiency_decision_table() -> None:
    service = EvidenceSufficiencyService()
    shared_source = uuid4()

    sufficient = service.evaluate(
        EvidenceSufficiencyRequest(
            query="ละหมาดเดินทาง",
            requested_madhhab="shafii",
            candidates=(
                _candidate(score=0.85, source_id=shared_source, rank=1),
                _candidate(score=0.75, source_id=shared_source, rank=2),
            ),
        )
    )
    partial = service.evaluate(
        EvidenceSufficiencyRequest(
            query="ละหมาดเดินทาง",
            candidates=(_candidate(score=0.60, rank=1),),
        )
    )
    insufficient = service.evaluate(
        EvidenceSufficiencyRequest(
            query="ละหมาดเดินทาง",
            candidates=(_candidate(score=0.20, rank=1),),
        )
    )

    assert sufficient.status == EvidenceStatus.SUFFICIENT
    assert sufficient.allow_high_confidence_answer is True
    assert sufficient.reason_codes == ("RULES_PASSED",)
    assert partial.status == EvidenceStatus.PARTIALLY_SUFFICIENT
    assert partial.allow_high_confidence_answer is False
    assert partial.should_search_more is True
    assert "RESULT_COUNT_BELOW_SUFFICIENT_THRESHOLD" in partial.reason_codes
    assert insufficient.status == EvidenceStatus.INSUFFICIENT
    assert insufficient.should_abstain is True
    assert insufficient.allow_high_confidence_answer is False


def test_evidence_sufficiency_conflicting_source_cases() -> None:
    service = EvidenceSufficiencyService()
    conflict_group = "travel-prayer"

    decision = service.evaluate(
        EvidenceSufficiencyRequest(
            query="ละหมาดเดินทาง",
            candidates=(
                _candidate(
                    score=0.85,
                    rank=1,
                    metadata={"conflict_group": conflict_group, "stance": "permit-shortening"},
                ),
                _candidate(
                    score=0.80,
                    rank=2,
                    metadata={"conflict_group": conflict_group, "stance": "forbid-shortening"},
                ),
            ),
        )
    )

    assert decision.status == EvidenceStatus.CONFLICTING
    assert decision.allow_high_confidence_answer is False
    assert decision.should_search_more is False
    assert "CONFLICTING_STANCES" in decision.reason_codes


def test_evidence_sufficiency_threshold_regression_and_citation_completeness() -> None:
    service = EvidenceSufficiencyService()

    decision = service.evaluate(
        EvidenceSufficiencyRequest(
            query="ละหมาดเดินทาง",
            candidates=(
                _candidate(
                    score=0.90,
                    rank=1,
                    metadata={"citation_complete": False},
                ),
                _candidate(score=0.85, rank=2),
            ),
        )
    )

    assert decision.status == EvidenceStatus.PARTIALLY_SUFFICIENT
    assert "CITATION_INCOMPLETE" in decision.reason_codes

    relaxed = service.evaluate(
        EvidenceSufficiencyRequest(
            query="ละหมาดเดินทาง",
            candidates=(_candidate(score=0.50, rank=1),),
            thresholds=EvidenceSufficiencyThresholds(
                min_sufficient_results=1,
                min_sufficient_top_score=0.50,
                min_sufficient_average_score=0.50,
                require_citations=False,
                version="evidence-threshold-test-v2",
            ),
        )
    )
    assert relaxed.status == EvidenceStatus.SUFFICIENT
    assert relaxed.rules_version == "evidence-threshold-test-v2"


def test_evidence_sufficiency_llm_evaluator_failure_is_non_authoritative() -> None:
    class FailingEvaluator:
        def evaluate(self, request: EvidenceSufficiencyRequest) -> dict[str, object]:
            raise RuntimeError("provider failed")

    decision = EvidenceSufficiencyService(llm_evaluator=FailingEvaluator()).evaluate(
        EvidenceSufficiencyRequest(
            query="ละหมาดเดินทาง",
            candidates=(
                _candidate(score=0.85, rank=1),
                _candidate(score=0.75, rank=2),
            ),
            llm_evaluator_enabled=True,
        )
    )

    assert decision.status == EvidenceStatus.SUFFICIENT
    assert decision.llm_signal == {"available": False, "error": "LLM_EVALUATOR_FAILED"}
    assert decision.allow_high_confidence_answer is True


def test_evidence_sufficiency_updates_retrieval_run_flag_and_trace() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, expire_on_commit=False)
    run_id = uuid4()
    with db() as session:
        session.add(
            RetrievalRun(
                id=run_id,
                request_id="evidence-test",
                trace_id="trace-evidence",
                query_original="ละหมาดเดินทาง",
                query_normalized="ละหมาดเดินทาง",
                query_expansions={},
                filters={},
                retriever_version="hybrid-retriever-v1",
                evidence_sufficient=True,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
        session.commit()

    decision = EvidenceSufficiencyService(SQLAlchemyUnitOfWork(db)).evaluate(
        EvidenceSufficiencyRequest(
            query="ละหมาดเดินทาง",
            retrieval_run_id=run_id,
            candidates=(),
        )
    )

    with db() as session:
        run = session.scalar(select(RetrievalRun).where(RetrievalRun.id == run_id))
        assert run is not None
        assert run.evidence_sufficient is False
        assert run.filters["evidence_sufficiency"]["status"] == "INSUFFICIENT"
    assert decision.rules_version == EVIDENCE_SUFFICIENCY_RULES_VERSION


def test_evidence_sufficiency_rejects_invalid_thresholds() -> None:
    service = EvidenceSufficiencyService()

    with pytest.raises(EvidenceSufficiencyError) as error:
        service.evaluate(
            EvidenceSufficiencyRequest(
                query="ละหมาดเดินทาง",
                candidates=(),
                thresholds=EvidenceSufficiencyThresholds(version=" "),
            )
        )

    assert error.value.code == "EVIDENCE_RULES_VERSION_REQUIRED"
