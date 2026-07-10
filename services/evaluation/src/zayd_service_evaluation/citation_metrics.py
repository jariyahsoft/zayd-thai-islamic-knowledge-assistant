"""Citation correctness metrics derived from deterministic verifier output."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import TypeGuard
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session
from zayd_common.database.models import AuditLog, EvaluationCase, EvaluationResult, EvaluationRun
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.rbac import Permission

CITATION_METRICS_VERSION = "citation-metrics-v1"


class CitationMetricsError(Exception):
    def __init__(self, code: str, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.code, self.message, self.status_code = code, message, status_code


@dataclass(frozen=True)
class HumanReviewOverride:
    case_key: str
    claim_id: str
    reviewer_id: UUID
    decision: str
    reason_code: str
    created_at: str


@dataclass(frozen=True)
class CitationMetricSummary:
    case_count: int
    claim_count: int
    citation_count: int
    citation_correctness: float
    citation_completeness: float
    fabricated_citation_rate: float
    claim_support_rate: float
    nonexistent_count: int
    wrong_reference_count: int
    unsupported_claim_count: int
    incomplete_case_count: int
    invalid_metric_input_count: int


@dataclass(frozen=True)
class CitationMetricsReport:
    run_id: UUID
    summary: CitationMetricSummary
    overrides: tuple[HumanReviewOverride, ...]
    invalid_override_count: int
    version: str = CITATION_METRICS_VERSION


class CitationMetricsService:
    def __init__(self, uow: SQLAlchemyUnitOfWork) -> None:
        self.uow = uow

    def calculate(
        self,
        run_id: UUID,
        *,
        permissions: frozenset[str],
        actor_user_id: UUID | None = None,
        trace_id: str | None = None,
    ) -> CitationMetricsReport:
        if Permission.EVALUATIONS_READ.value not in permissions:
            raise CitationMetricsError("CITATION_METRICS_FORBIDDEN", "Forbidden.", status_code=403)
        with self.uow:
            session = self._session()
            run = session.get(EvaluationRun, run_id)
            if run is None:
                raise CitationMetricsError(
                    "CITATION_METRICS_RUN_NOT_FOUND",
                    "Benchmark run was not found.",
                    status_code=404,
                )
            rows = [
                (row[0], row[1])
                for row in session.execute(
                    select(EvaluationResult, EvaluationCase)
                    .join(EvaluationCase, EvaluationCase.id == EvaluationResult.evaluation_case_id)
                    .where(EvaluationResult.evaluation_run_id == run_id)
                    .where(EvaluationCase.case_type == "citation")
                    .order_by(EvaluationCase.case_key)
                ).all()
            ]
            observations = [_observe(result, case) for result, case in rows]
            overrides = tuple(value for item in observations for value in item.overrides)
            report = CitationMetricsReport(
                run.id,
                _summarize(observations),
                overrides,
                sum(item.invalid_override_count for item in observations),
            )
            if actor_user_id is not None:
                metrics = dict(run.metrics_json or {})
                metrics["citation"] = _serialize(report)
                run.metrics_json = metrics
                session.add(
                    AuditLog(
                        id=uuid4(),
                        actor_user_id=actor_user_id,
                        action="evaluation.citation_metrics.calculate",
                        resource_type="evaluation_run",
                        resource_id=run.id,
                        outcome="success",
                        request_id=trace_id,
                        trace_id=trace_id,
                        before_summary={},
                        after_summary={
                            "case_count": report.summary.case_count,
                            "nonexistent_count": report.summary.nonexistent_count,
                            "wrong_reference_count": report.summary.wrong_reference_count,
                            "unsupported_claim_count": report.summary.unsupported_claim_count,
                            "incomplete_case_count": report.summary.incomplete_case_count,
                            "override_count": len(report.overrides),
                            "invalid_override_count": report.invalid_override_count,
                            "metrics_version": CITATION_METRICS_VERSION,
                        },
                        source_context={},
                    )
                )
            self.uow.commit()
            return report

    def _session(self) -> Session:
        if self.uow.session is None:
            raise RuntimeError("Database session not initialised in UoW.")
        return self.uow.session


@dataclass(frozen=True)
class _Observation:
    claim_count: int
    citation_count: int
    correct_citation_count: int
    expected_count: int
    expected_found_count: int
    supported_claim_count: int
    nonexistent_count: int
    wrong_reference_count: int
    unsupported_claim_count: int
    invalid_metric_input_count: int
    overrides: tuple[HumanReviewOverride, ...]
    invalid_override_count: int


def _observe(result: EvaluationResult, case: EvaluationCase) -> _Observation:
    output = dict(result.output_json or {})
    verification = output.get("citation_verification", output)
    claims_raw = verification.get("claim_results", ()) if isinstance(verification, Mapping) else ()
    claims = list(claims_raw) if _sequence(claims_raw) else []
    expected_ids, expected_invalid = _expected_ids(case.expected_citations)
    observed_ids: set[UUID] = set()
    citation_count = correct = supported = nonexistent = wrong = unsupported = invalid = 0
    for raw in claims:
        if not isinstance(raw, Mapping):
            invalid += 1
            continue
        tokens = raw.get("citation_tokens", ())
        token_values = list(tokens) if _sequence(tokens) else []
        parsed_tokens, invalid_tokens = _token_ids(token_values)
        citation_count += len(token_values)
        observed_ids.update(parsed_tokens)
        checks_raw = raw.get("checks", ())
        checks = list(checks_raw) if _sequence(checks_raw) else []
        existence_failed = _check_failed(checks, "existence")
        reference_failed = _check_failed(checks, "reference_correctness")
        claim_nonexistent = invalid_tokens
        if existence_failed:
            claim_nonexistent = max(claim_nonexistent, len(token_values), 1)
        nonexistent += claim_nonexistent
        if reference_failed:
            wrong += max(len(parsed_tokens), 1)
        correct += max(len(token_values) - claim_nonexistent - int(reference_failed), 0)
        status = str(raw.get("support_status", ""))
        if status == "supported":
            supported += 1
        elif status in {"partial", "unsupported", "unverifiable", "invalid_citation"}:
            unsupported += 1
        else:
            invalid += 1
    overrides, invalid_overrides = _overrides(case.case_key, output.get("human_overrides", ()))
    return _Observation(
        len(claims),
        citation_count,
        correct,
        len(expected_ids),
        len(expected_ids & observed_ids),
        supported,
        nonexistent,
        wrong,
        unsupported,
        invalid + expected_invalid,
        overrides,
        invalid_overrides,
    )


def _summarize(items: list[_Observation]) -> CitationMetricSummary:
    cases = len(items)
    claims = sum(item.claim_count for item in items)
    citations = sum(item.citation_count for item in items)
    expected = sum(item.expected_count for item in items)
    return CitationMetricSummary(
        cases,
        claims,
        citations,
        sum(item.correct_citation_count for item in items) / citations if citations else 0.0,
        sum(item.expected_found_count for item in items) / expected if expected else 0.0,
        sum(item.nonexistent_count for item in items) / citations if citations else 0.0,
        sum(item.supported_claim_count for item in items) / claims if claims else 0.0,
        sum(item.nonexistent_count for item in items),
        sum(item.wrong_reference_count for item in items),
        sum(item.unsupported_claim_count for item in items),
        sum(item.expected_found_count < item.expected_count for item in items),
        sum(item.invalid_metric_input_count for item in items),
    )


def _expected_ids(values: object) -> tuple[set[UUID], int]:
    if not _sequence(values):
        return set(), 0
    parsed: set[UUID] = set()
    invalid = 0
    for item in values:
        value = item.get("citation_id") if isinstance(item, Mapping) else None
        try:
            parsed.add(UUID(str(value)))
        except (TypeError, ValueError, AttributeError):
            invalid += 1
    return parsed, invalid


def _token_ids(tokens: Iterable[object]) -> tuple[set[UUID], int]:
    parsed: set[UUID] = set()
    invalid = 0
    for token in tokens:
        value = str(token)
        try:
            parsed.add(UUID(value.removeprefix("CIT-")))
        except ValueError:
            invalid += 1
    return parsed, invalid


def _check_failed(checks: list[object], name: str) -> bool:
    return any(
        isinstance(check, Mapping) and check.get("name") == name and check.get("outcome") == "fail"
        for check in checks
    )


def _overrides(case_key: str, values: object) -> tuple[tuple[HumanReviewOverride, ...], int]:
    if not _sequence(values):
        return (), int(values not in (None, (), []))
    result: list[HumanReviewOverride] = []
    invalid = 0
    for item in values:
        if not isinstance(item, Mapping):
            invalid += 1
            continue
        try:
            claim_id = str(item["claim_id"]).strip()
            decision = str(item["decision"]).strip()
            reason = str(item["reason_code"]).strip()
            created_at = str(item["created_at"]).strip()
            reviewer_id = UUID(str(item["reviewer_id"]))
            if not all((claim_id, decision, reason, created_at)):
                raise ValueError
            result.append(
                HumanReviewOverride(case_key, claim_id, reviewer_id, decision, reason, created_at)
            )
        except (KeyError, TypeError, ValueError, AttributeError):
            invalid += 1
    return tuple(result), invalid


def _sequence(value: object) -> TypeGuard[Iterable[object]]:
    return isinstance(value, Iterable) and not isinstance(value, (str, bytes, Mapping))


def _serialize(report: CitationMetricsReport) -> dict[str, object]:
    summary = report.summary
    return {
        "version": report.version,
        "case_count": summary.case_count,
        "claim_count": summary.claim_count,
        "citation_count": summary.citation_count,
        "citation_correctness": summary.citation_correctness,
        "citation_completeness": summary.citation_completeness,
        "fabricated_citation_rate": summary.fabricated_citation_rate,
        "claim_support_rate": summary.claim_support_rate,
        "nonexistent_count": summary.nonexistent_count,
        "wrong_reference_count": summary.wrong_reference_count,
        "unsupported_claim_count": summary.unsupported_claim_count,
        "incomplete_case_count": summary.incomplete_case_count,
        "invalid_metric_input_count": summary.invalid_metric_input_count,
        "override_count": len(report.overrides),
        "invalid_override_count": report.invalid_override_count,
    }
