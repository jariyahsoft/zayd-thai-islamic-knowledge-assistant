"""Comparison service for evaluating benchmark runs (TASK-12-07)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session
from zayd_common.database.models import EvaluationCase, EvaluationResult, EvaluationRun
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.rbac import Permission

COMPARISON_SERVICE_VERSION = "comparison-service-v1"


class BenchmarkComparisonError(Exception):
    def __init__(self, code: str, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.code, self.message, self.status_code = code, message, status_code


@dataclass(frozen=True)
class CaseComparison:
    case_key: str
    case_type: str
    risk_level: str
    visibility: str
    base_passed: bool
    target_passed: bool
    regression: bool
    improvement: bool
    base_scores: dict[str, float]
    target_scores: dict[str, float]
    topic: str
    language: str
    madhhab: str


@dataclass(frozen=True)
class RunInfo:
    run_id: UUID
    dataset_name: str
    dataset_version: str
    provider_name: str
    model_name: str
    retriever_version: str
    embedding_version: str | None
    reranker_version: str | None
    git_commit: str
    random_seed: int
    started_at: str
    finished_at: str | None
    metrics: dict[str, Any]


@dataclass(frozen=True)
class RunComparisonReport:
    base_run: RunInfo
    target_run: RunInfo
    regression_count: int
    improvement_count: int
    overall_base_pass_rate: float
    overall_target_pass_rate: float
    comparisons: list[CaseComparison]
    version: str = COMPARISON_SERVICE_VERSION


class BenchmarkComparisonService:
    def __init__(self, uow: SQLAlchemyUnitOfWork) -> None:
        self.uow = uow

    def list_runs(
        self,
        *,
        permissions: frozenset[str],
        dataset_id: UUID | None = None,
    ) -> list[RunInfo]:
        # Listing runs is allowed if the user has read permissions
        if Permission.EVALUATIONS_READ.value not in permissions:
            raise BenchmarkComparisonError(
                "BENCHMARK_COMPARISON_FORBIDDEN", "Forbidden.", status_code=403
            )

        with self.uow:
            session = self._session()
            stmt = select(EvaluationRun)
            if dataset_id is not None:
                stmt = stmt.where(EvaluationRun.dataset_id == dataset_id)
            runs = session.scalars(stmt.order_by(EvaluationRun.started_at.desc())).all()
            result = [_run_info(run) for run in runs]
            self.uow.commit()
            return result

    def get_run(
        self,
        run_id: UUID,
        *,
        permissions: frozenset[str],
    ) -> RunInfo:
        if Permission.EVALUATIONS_READ.value not in permissions:
            raise BenchmarkComparisonError(
                "BENCHMARK_COMPARISON_FORBIDDEN", "Forbidden.", status_code=403
            )

        with self.uow:
            session = self._session()
            run = session.get(EvaluationRun, run_id)
            if run is None:
                raise BenchmarkComparisonError(
                    "BENCHMARK_RUN_NOT_FOUND", "Run was not found.", status_code=404
                )
            info = _run_info(run)
            self.uow.commit()
            return info

    def compare_runs(
        self,
        base_run_id: UUID,
        target_run_id: UUID,
        *,
        permissions: frozenset[str],
    ) -> RunComparisonReport:
        # If the user lacks Permission.EVALUATIONS_READ, they can only compare
        # public approved cases. However, to compare runs at all, they still need
        # basic auth.
        with self.uow:
            session = self._session()
            base_run = session.get(EvaluationRun, base_run_id)
            target_run = session.get(EvaluationRun, target_run_id)

            if base_run is None or target_run is None:
                raise BenchmarkComparisonError(
                    "BENCHMARK_RUN_NOT_FOUND",
                    "One or both benchmark runs were not found.",
                    status_code=404,
                )

            # Retrieve results + cases
            base_results = _get_results(session, base_run_id)
            target_results = _get_results(session, target_run_id)

            can_read_private = Permission.EVALUATIONS_READ.value in permissions

            comparisons: list[CaseComparison] = []
            regressions = 0
            improvements = 0

            # Match by case key
            keys = set(base_results.keys()) & set(target_results.keys())
            for key in sorted(keys):
                base_res, base_case = base_results[key]
                target_res, target_case = target_results[key]

                # Security Gate: if user can't read private, skip private/unapproved cases
                if not can_read_private:
                    if (
                        base_case.visibility != "public"
                        or base_case.reviewer_status != "approved"
                    ):
                        continue
                    if (
                        target_case.visibility != "public"
                        or target_case.reviewer_status != "approved"
                    ):
                        continue

                regression = base_res.passed and not target_res.passed
                improvement = not base_res.passed and target_res.passed

                if regression:
                    regressions += 1
                if improvement:
                    improvements += 1

                provenance = dict(base_case.provenance_json or {})

                comparisons.append(
                    CaseComparison(
                        case_key=base_case.case_key,
                        case_type=base_case.case_type,
                        risk_level=base_case.risk_level,
                        visibility=base_case.visibility,
                        base_passed=base_res.passed,
                        target_passed=target_res.passed,
                        regression=regression,
                        improvement=improvement,
                        base_scores=dict(base_res.scores_json or {}),
                        target_scores=dict(target_res.scores_json or {}),
                        topic=str(provenance.get("topic", "unknown")),
                        language=str(provenance.get("language", "unknown")),
                        madhhab=str(provenance.get("madhhab", "unknown")),
                    )
                )

            total = len(comparisons)
            base_pass_rate = (
                sum(c.base_passed for c in comparisons) / total if total > 0 else 0.0
            )
            target_pass_rate = (
                sum(c.target_passed for c in comparisons) / total if total > 0 else 0.0
            )

            report = RunComparisonReport(
                base_run=_run_info(base_run),
                target_run=_run_info(target_run),
                regression_count=regressions,
                improvement_count=improvements,
                overall_base_pass_rate=base_pass_rate,
                overall_target_pass_rate=target_pass_rate,
                comparisons=comparisons,
            )
            self.uow.commit()
            return report

    def _session(self) -> Session:
        if self.uow.session is None:
            raise RuntimeError("Database session not initialised in UoW.")
        return self.uow.session


def _run_info(run: EvaluationRun) -> RunInfo:
    cfg = dict(run.run_config_json or {})
    return RunInfo(
        run_id=run.id,
        dataset_name=str(cfg.get("dataset_name", "unknown")),
        dataset_version=str(cfg.get("dataset_version", "unknown")),
        provider_name=str(cfg.get("provider_name", "unknown")),
        model_name=str(cfg.get("model_name", "unknown")),
        retriever_version=str(cfg.get("retriever_version", "unknown")),
        embedding_version=cfg.get("embedding_version"),
        reranker_version=cfg.get("reranker_version"),
        git_commit=run.git_commit,
        random_seed=run.random_seed,
        started_at=run.started_at.isoformat(),
        finished_at=run.finished_at.isoformat() if run.finished_at else None,
        metrics=dict(run.metrics_json or {}),
    )


def _get_results(
    session: Session, run_id: UUID
) -> dict[str, tuple[EvaluationResult, EvaluationCase]]:
    stmt = (
        select(EvaluationResult, EvaluationCase)
        .join(EvaluationCase, EvaluationCase.id == EvaluationResult.evaluation_case_id)
        .where(EvaluationResult.evaluation_run_id == run_id)
    )
    rows = session.execute(stmt).all()
    return {case.case_key: (res, case) for res, case in rows}
