"""Deterministic retrieval metrics for persisted benchmark runs."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session
from zayd_common.database.models import AuditLog, EvaluationCase, EvaluationResult, EvaluationRun
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.rbac import Permission

RETRIEVAL_METRICS_VERSION = "retrieval-metrics-v1"


class RetrievalMetricsError(Exception):
    def __init__(self, code: str, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.code, self.message, self.status_code = code, message, status_code


@dataclass(frozen=True)
class RetrievalMetricSummary:
    case_count: int
    recall_at_5: float
    recall_at_10: float
    mrr: float
    precision: float
    metadata_filter_correctness: float
    invalid_reference_count: int
    missing_reference_case_count: int


@dataclass(frozen=True)
class RetrievalMetricsReport:
    run_id: UUID
    overall: RetrievalMetricSummary
    by_topic: dict[str, RetrievalMetricSummary]
    by_language: dict[str, RetrievalMetricSummary]
    by_madhhab: dict[str, RetrievalMetricSummary]
    version: str = RETRIEVAL_METRICS_VERSION


class RetrievalMetricsService:
    def __init__(self, uow: SQLAlchemyUnitOfWork) -> None:
        self.uow = uow

    def calculate(
        self,
        run_id: UUID,
        *,
        permissions: frozenset[str],
        actor_user_id: UUID | None = None,
        trace_id: str | None = None,
    ) -> RetrievalMetricsReport:
        if Permission.EVALUATIONS_READ.value not in permissions:
            raise RetrievalMetricsError(
                "RETRIEVAL_METRICS_FORBIDDEN", "Forbidden.", status_code=403
            )
        with self.uow:
            session = self._session()
            run = session.get(EvaluationRun, run_id)
            if run is None:
                raise RetrievalMetricsError(
                    "RETRIEVAL_METRICS_RUN_NOT_FOUND",
                    "Benchmark run was not found.",
                    status_code=404,
                )
            pairs = [
                (row[0], row[1])
                for row in session.execute(
                    select(EvaluationResult, EvaluationCase)
                    .join(EvaluationCase, EvaluationCase.id == EvaluationResult.evaluation_case_id)
                    .where(EvaluationResult.evaluation_run_id == run_id)
                    .where(EvaluationCase.case_type.in_(("retrieval_only", "citation")))
                    .order_by(EvaluationCase.case_key)
                ).all()
            ]
            observations = [_observation(result, case) for result, case in pairs]
            report = RetrievalMetricsReport(
                run_id=run.id,
                overall=_summary(observations),
                by_topic=_groups(observations, "topic"),
                by_language=_groups(observations, "language"),
                by_madhhab=_groups(observations, "madhhab"),
            )
            if actor_user_id is not None:
                metrics = dict(run.metrics_json or {})
                metrics["retrieval"] = _serialize(report)
                run.metrics_json = metrics
                session.add(
                    AuditLog(
                        id=uuid4(),
                        actor_user_id=actor_user_id,
                        action="evaluation.retrieval_metrics.calculate",
                        resource_type="evaluation_run",
                        resource_id=run.id,
                        outcome="success",
                        request_id=trace_id,
                        trace_id=trace_id,
                        before_summary={},
                        after_summary={
                            "case_count": report.overall.case_count,
                            "invalid_reference_count": report.overall.invalid_reference_count,
                            "metrics_version": RETRIEVAL_METRICS_VERSION,
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
    expected: frozenset[UUID]
    retrieved: tuple[UUID, ...]
    invalid_reference_count: int
    metadata_correct: bool
    topic: str
    language: str
    madhhab: str


def _observation(result: EvaluationResult, case: EvaluationCase) -> _Observation:
    expected, expected_invalid = _uuid_values(
        item.get("source_id") for item in case.source_references if isinstance(item, dict)
    )
    output = dict(result.output_json or {})
    retrieved, retrieved_invalid = _uuid_values(output.get("retrieved_source_ids", ()))
    expected_filters = dict(case.expected_behavior.get("rubric", {})).get("metadata_filters", {})
    actual_filters = output.get("metadata_filters", {})
    metadata_correct = isinstance(expected_filters, dict) and expected_filters == actual_filters
    provenance = dict(case.provenance_json or {})
    return _Observation(
        frozenset(expected),
        tuple(retrieved),
        expected_invalid + retrieved_invalid,
        metadata_correct,
        str(provenance.get("topic", "unknown")),
        str(provenance.get("language", "unknown")),
        str(provenance.get("madhhab", "unknown")),
    )


def _uuid_values(values: Any) -> tuple[list[UUID], int]:
    if not isinstance(values, Iterable) or isinstance(values, (str, bytes, dict)):
        return [], 1
    parsed: list[UUID] = []
    invalid = 0
    for value in values:
        try:
            parsed.append(UUID(str(value)))
        except (TypeError, ValueError, AttributeError):
            invalid += 1
    return parsed, invalid


def _summary(items: list[_Observation]) -> RetrievalMetricSummary:
    if not items:
        return RetrievalMetricSummary(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0)
    recall_5 = sum(bool(set(item.retrieved[:5]) & item.expected) for item in items) / len(items)
    recall_10 = sum(bool(set(item.retrieved[:10]) & item.expected) for item in items) / len(items)
    reciprocal_ranks = []
    precisions = []
    for item in items:
        first = next(
            (index + 1 for index, value in enumerate(item.retrieved) if value in item.expected),
            None,
        )
        reciprocal_ranks.append(1 / first if first else 0.0)
        precisions.append(
            sum(value in item.expected for value in item.retrieved) / len(item.retrieved)
            if item.retrieved
            else 0.0
        )
    return RetrievalMetricSummary(
        len(items),
        recall_5,
        recall_10,
        sum(reciprocal_ranks) / len(items),
        sum(precisions) / len(items),
        sum(item.metadata_correct for item in items) / len(items),
        sum(item.invalid_reference_count for item in items),
        sum(not item.expected for item in items),
    )


def _groups(items: list[_Observation], field: str) -> dict[str, RetrievalMetricSummary]:
    grouped: dict[str, list[_Observation]] = {}
    for item in items:
        grouped.setdefault(str(getattr(item, field)), []).append(item)
    return {key: _summary(values) for key, values in sorted(grouped.items())}


def _serialize(report: RetrievalMetricsReport) -> dict[str, object]:
    def item(summary: RetrievalMetricSummary) -> dict[str, object]:
        return {
            "case_count": summary.case_count,
            "recall_at_5": summary.recall_at_5,
            "recall_at_10": summary.recall_at_10,
            "mrr": summary.mrr,
            "precision": summary.precision,
            "metadata_filter_correctness": summary.metadata_filter_correctness,
            "invalid_reference_count": summary.invalid_reference_count,
            "missing_reference_case_count": summary.missing_reference_case_count,
        }

    return {
        "version": report.version,
        "overall": item(report.overall),
        "by_topic": {key: item(value) for key, value in report.by_topic.items()},
        "by_language": {key: item(value) for key, value in report.by_language.items()},
        "by_madhhab": {key: item(value) for key, value in report.by_madhhab.items()},
    }
