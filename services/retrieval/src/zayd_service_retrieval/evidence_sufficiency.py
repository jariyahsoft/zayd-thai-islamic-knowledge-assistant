"""Deterministic evidence sufficiency evaluation for retrieved results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from zayd_common.database.models import RetrievalRun
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.enums import EvidenceStatus

from .reranker import RerankResponse

EVIDENCE_SUFFICIENCY_RULES_VERSION = "evidence-sufficiency-rules-v1"


class EvidenceSufficiencyError(Exception):
    def __init__(self, code: str, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class EvidenceSufficiencyThresholds:
    min_sufficient_results: int = 2
    min_partial_results: int = 1
    min_sufficient_top_score: float = 0.70
    min_partial_top_score: float = 0.45
    min_sufficient_average_score: float = 0.55
    min_reliability_score: float = 0.60
    min_distinct_sources: int = 1
    require_citations: bool = True
    version: str = EVIDENCE_SUFFICIENCY_RULES_VERSION


@dataclass(frozen=True)
class EvidenceCandidate:
    chunk_id: UUID
    document_version_id: UUID
    source_id: UUID
    canonical_reference: str
    madhhab: str
    source_type: str
    license_status: str
    score_final: float
    score_reranker: float | None
    score_reliability: float
    rank: int
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceSufficiencyRequest:
    query: str
    candidates: tuple[EvidenceCandidate, ...]
    requested_madhhab: str | None = None
    retrieval_run_id: UUID | None = None
    thresholds: EvidenceSufficiencyThresholds = field(default_factory=EvidenceSufficiencyThresholds)
    llm_evaluator_enabled: bool = False
    trace_id: str | None = None


@dataclass(frozen=True)
class EvidenceSufficiencyDecision:
    status: EvidenceStatus
    reason_codes: tuple[str, ...]
    rules_version: str
    allow_high_confidence_answer: bool
    should_search_more: bool
    should_abstain: bool
    candidate_count: int
    distinct_source_count: int
    top_score: float
    average_score: float
    trace: dict[str, object]
    llm_signal: dict[str, object] | None = None


class EvidenceSufficiencyEvaluator(Protocol):
    def evaluate(self, request: EvidenceSufficiencyRequest) -> dict[str, object]:
        pass


class EvidenceSufficiencyService:
    def __init__(
        self,
        uow: SQLAlchemyUnitOfWork | None = None,
        *,
        llm_evaluator: EvidenceSufficiencyEvaluator | None = None,
    ) -> None:
        self.uow = uow
        self.llm_evaluator = llm_evaluator

    def evaluate(self, request: EvidenceSufficiencyRequest) -> EvidenceSufficiencyDecision:
        self._validate(request)
        candidates = tuple(sorted(request.candidates, key=lambda item: item.rank))
        reason_codes: list[str] = []
        candidate_count = len(candidates)
        distinct_source_count = len({candidate.source_id for candidate in candidates})
        top_score = max((candidate.score_final for candidate in candidates), default=0.0)
        average_score = (
            sum(candidate.score_final for candidate in candidates) / candidate_count
            if candidate_count
            else 0.0
        )

        llm_signal = self._llm_signal(request)
        if not candidates:
            reason_codes.append("NO_RETRIEVAL_RESULTS")
            return self._decision(
                request=request,
                status=EvidenceStatus.INSUFFICIENT,
                reason_codes=reason_codes,
                candidates=candidates,
                distinct_source_count=distinct_source_count,
                top_score=top_score,
                average_score=average_score,
                llm_signal=llm_signal,
            )

        conflict_reasons = self._conflict_reasons(candidates)
        if conflict_reasons:
            reason_codes.extend(conflict_reasons)
            return self._decision(
                request=request,
                status=EvidenceStatus.CONFLICTING,
                reason_codes=reason_codes,
                candidates=candidates,
                distinct_source_count=distinct_source_count,
                top_score=top_score,
                average_score=average_score,
                llm_signal=llm_signal,
            )

        reason_codes.extend(self._quality_reasons(request, candidates, distinct_source_count))
        if top_score < request.thresholds.min_partial_top_score:
            reason_codes.append("TOP_SCORE_BELOW_PARTIAL_THRESHOLD")
        elif top_score < request.thresholds.min_sufficient_top_score:
            reason_codes.append("TOP_SCORE_BELOW_SUFFICIENT_THRESHOLD")
        if average_score < request.thresholds.min_sufficient_average_score:
            reason_codes.append("AVERAGE_SCORE_BELOW_SUFFICIENT_THRESHOLD")
        if candidate_count < request.thresholds.min_partial_results:
            reason_codes.append("RESULT_COUNT_BELOW_PARTIAL_THRESHOLD")
        elif candidate_count < request.thresholds.min_sufficient_results:
            reason_codes.append("RESULT_COUNT_BELOW_SUFFICIENT_THRESHOLD")

        if "TOP_SCORE_BELOW_PARTIAL_THRESHOLD" in reason_codes or (
            "RESULT_COUNT_BELOW_PARTIAL_THRESHOLD" in reason_codes
        ):
            status = EvidenceStatus.INSUFFICIENT
        elif reason_codes:
            status = EvidenceStatus.PARTIALLY_SUFFICIENT
        else:
            status = EvidenceStatus.SUFFICIENT

        return self._decision(
            request=request,
            status=status,
            reason_codes=reason_codes or ["RULES_PASSED"],
            candidates=candidates,
            distinct_source_count=distinct_source_count,
            top_score=top_score,
            average_score=average_score,
            llm_signal=llm_signal,
        )

    def evaluate_reranked(
        self,
        response: RerankResponse,
        *,
        requested_madhhab: str | None = None,
        retrieval_run_id: UUID | None = None,
        thresholds: EvidenceSufficiencyThresholds | None = None,
    ) -> EvidenceSufficiencyDecision:
        candidates = tuple(
            EvidenceCandidate(
                chunk_id=result.hybrid_result.chunk_id,
                document_version_id=result.hybrid_result.document_version_id,
                source_id=result.hybrid_result.source_id,
                canonical_reference=result.hybrid_result.canonical_reference,
                madhhab=result.hybrid_result.madhhab,
                source_type=result.hybrid_result.source_type,
                license_status=result.hybrid_result.license_status,
                score_final=result.score_final,
                score_reranker=result.score_reranker,
                score_reliability=result.hybrid_result.score_reliability,
                rank=result.rank,
                metadata=result.metadata,
            )
            for result in response.results
        )
        return self.evaluate(
            EvidenceSufficiencyRequest(
                query=response.query_original,
                candidates=candidates,
                requested_madhhab=requested_madhhab,
                retrieval_run_id=retrieval_run_id,
                thresholds=thresholds or EvidenceSufficiencyThresholds(),
                trace_id=None,
            )
        )

    def _quality_reasons(
        self,
        request: EvidenceSufficiencyRequest,
        candidates: tuple[EvidenceCandidate, ...],
        distinct_source_count: int,
    ) -> list[str]:
        reasons: list[str] = []
        if distinct_source_count < request.thresholds.min_distinct_sources:
            reasons.append("SOURCE_DIVERSITY_BELOW_THRESHOLD")
        if any(
            candidate.score_reliability < request.thresholds.min_reliability_score
            for candidate in candidates
        ):
            reasons.append("SOURCE_RELIABILITY_BELOW_THRESHOLD")
        if request.requested_madhhab is not None and any(
            candidate.madhhab not in {request.requested_madhhab, "multi", "not_applicable"}
            for candidate in candidates
        ):
            reasons.append("MADHHAB_MISMATCH")
        if request.thresholds.require_citations and any(
            not _citation_complete(candidate) for candidate in candidates
        ):
            reasons.append("CITATION_INCOMPLETE")
        if any(
            candidate.license_status not in _ELIGIBLE_LICENSE_STATUSES for candidate in candidates
        ):
            reasons.append("LICENSE_NOT_ELIGIBLE")
        return reasons

    def _conflict_reasons(self, candidates: tuple[EvidenceCandidate, ...]) -> list[str]:
        reasons: list[str] = []
        if any(candidate.metadata.get("conflict_signal") is True for candidate in candidates):
            reasons.append("EXPLICIT_CONFLICT_SIGNAL")
        stances_by_group: dict[str, set[str]] = {}
        for candidate in candidates:
            group = candidate.metadata.get("conflict_group")
            stance = candidate.metadata.get("stance")
            if isinstance(group, str) and isinstance(stance, str):
                stances_by_group.setdefault(group, set()).add(stance)
        if any(len(stances) > 1 for stances in stances_by_group.values()):
            reasons.append("CONFLICTING_STANCES")
        return reasons

    def _llm_signal(self, request: EvidenceSufficiencyRequest) -> dict[str, object] | None:
        if not request.llm_evaluator_enabled or self.llm_evaluator is None:
            return None
        try:
            signal = dict(self.llm_evaluator.evaluate(request))
        except Exception:
            return {"available": False, "error": "LLM_EVALUATOR_FAILED"}
        signal["available"] = True
        signal["authoritative"] = False
        return signal

    def _decision(
        self,
        *,
        request: EvidenceSufficiencyRequest,
        status: EvidenceStatus,
        reason_codes: list[str],
        candidates: tuple[EvidenceCandidate, ...],
        distinct_source_count: int,
        top_score: float,
        average_score: float,
        llm_signal: dict[str, object] | None,
    ) -> EvidenceSufficiencyDecision:
        allow_high_confidence_answer = status == EvidenceStatus.SUFFICIENT
        decision = EvidenceSufficiencyDecision(
            status=status,
            reason_codes=tuple(reason_codes),
            rules_version=request.thresholds.version,
            allow_high_confidence_answer=allow_high_confidence_answer,
            should_search_more=status
            in {EvidenceStatus.INSUFFICIENT, EvidenceStatus.PARTIALLY_SUFFICIENT},
            should_abstain=status == EvidenceStatus.INSUFFICIENT,
            candidate_count=len(candidates),
            distinct_source_count=distinct_source_count,
            top_score=top_score,
            average_score=average_score,
            llm_signal=llm_signal,
            trace={
                "rules_version": request.thresholds.version,
                "status": status.value,
                "reason_codes": reason_codes,
                "candidate_count": len(candidates),
                "distinct_source_count": distinct_source_count,
                "top_score": top_score,
                "average_score": average_score,
                "requested_madhhab": request.requested_madhhab,
                "allow_high_confidence_answer": allow_high_confidence_answer,
                "should_search_more": status
                in {EvidenceStatus.INSUFFICIENT, EvidenceStatus.PARTIALLY_SUFFICIENT},
                "should_abstain": status == EvidenceStatus.INSUFFICIENT,
                "llm_signal": llm_signal,
            },
        )
        self._persist_run_flag(request, decision)
        return decision

    def _persist_run_flag(
        self,
        request: EvidenceSufficiencyRequest,
        decision: EvidenceSufficiencyDecision,
    ) -> None:
        if self.uow is None or request.retrieval_run_id is None:
            return
        with self.uow:
            session = self.uow.session
            if session is None:
                raise RuntimeError("Database session not initialised in UoW.")
            run = session.scalar(
                select(RetrievalRun).where(RetrievalRun.id == request.retrieval_run_id)
            )
            if run is not None:
                run.evidence_sufficient = decision.status == EvidenceStatus.SUFFICIENT
                run.filters = {
                    **run.filters,
                    "evidence_sufficiency": decision.trace,
                }
            self.uow.commit()

    def _validate(self, request: EvidenceSufficiencyRequest) -> None:
        if not request.query.strip():
            raise EvidenceSufficiencyError(
                "EVIDENCE_QUERY_REQUIRED",
                "Evidence sufficiency query is required.",
                status_code=400,
            )
        thresholds = request.thresholds
        if not thresholds.version.strip():
            raise EvidenceSufficiencyError(
                "EVIDENCE_RULES_VERSION_REQUIRED",
                "Evidence sufficiency rules version is required.",
                status_code=400,
            )
        if thresholds.min_sufficient_results < 1 or thresholds.min_partial_results < 0:
            raise EvidenceSufficiencyError(
                "EVIDENCE_INVALID_RESULT_THRESHOLDS",
                "Evidence result thresholds are invalid.",
                status_code=400,
            )
        if thresholds.min_partial_results > thresholds.min_sufficient_results:
            raise EvidenceSufficiencyError(
                "EVIDENCE_INVALID_RESULT_THRESHOLDS",
                "Partial result threshold cannot exceed sufficient result threshold.",
                status_code=400,
            )
        score_values = (
            thresholds.min_sufficient_top_score,
            thresholds.min_partial_top_score,
            thresholds.min_sufficient_average_score,
            thresholds.min_reliability_score,
        )
        if any(value < 0.0 or value > 1.0 for value in score_values):
            raise EvidenceSufficiencyError(
                "EVIDENCE_INVALID_SCORE_THRESHOLDS",
                "Evidence score thresholds must be between 0 and 1.",
                status_code=400,
            )


def _citation_complete(candidate: EvidenceCandidate) -> bool:
    if candidate.metadata.get("citation_complete") is False:
        return False
    return bool(
        candidate.canonical_reference and candidate.document_version_id and candidate.chunk_id
    )


_ELIGIBLE_LICENSE_STATUSES = frozenset({"persistent_private", "persistent_redistributable"})
