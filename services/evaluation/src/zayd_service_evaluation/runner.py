"""Reproducible benchmark runner with isolated case failures and safe exports."""

from __future__ import annotations

import csv
import io
import json
import random
from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import monotonic
from typing import Any, Protocol
from uuid import UUID, uuid4

from sqlalchemy import Select, select
from sqlalchemy.orm import Session
from zayd_common.database.models import (
    AuditLog,
    EvaluationCase,
    EvaluationDataset,
    EvaluationResult,
    EvaluationRun,
)
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.rbac import Permission

BENCHMARK_RUNNER_VERSION = "benchmark-runner-v1"


class BenchmarkRunnerError(Exception):
    def __init__(self, code: str, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.code, self.message, self.status_code = code, message, status_code


@dataclass(frozen=True)
class BenchmarkRunConfig:
    dataset_id: UUID
    model_configuration_id: UUID
    prompt_version_id: UUID
    policy_version_id: UUID
    random_seed: int
    git_commit: str
    provider_name: str
    model_name: str
    retriever_version: str
    embedding_version: str | None = None
    reranker_version: str | None = None
    include_private: bool = True
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class BenchmarkCaseInput:
    id: UUID
    case_key: str
    case_type: str
    question: str
    choices: tuple[dict[str, object], ...]
    expected_behavior: dict[str, object]
    source_references: tuple[dict[str, object], ...]
    risk_level: str


@dataclass(frozen=True)
class CaseExecutionResult:
    passed: bool
    scores: dict[str, float] = field(default_factory=dict)
    output: dict[str, object] = field(default_factory=dict)
    failure_reason: str | None = None


class BenchmarkExecutor(Protocol):
    def execute(
        self,
        case: BenchmarkCaseInput,
        config: BenchmarkRunConfig,
        rng: random.Random,
    ) -> CaseExecutionResult: ...


@dataclass(frozen=True)
class BenchmarkRunSummary:
    run_id: UUID
    status: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    metrics: dict[str, object]


class BenchmarkRunner:
    def __init__(self, uow: SQLAlchemyUnitOfWork, executor: BenchmarkExecutor) -> None:
        self.uow = uow
        self.executor = executor

    def run(
        self,
        config: BenchmarkRunConfig,
        *,
        actor_user_id: UUID,
        permissions: frozenset[str],
        trace_id: str | None = None,
    ) -> BenchmarkRunSummary:
        _require(permissions, Permission.EVALUATIONS_MANAGE)
        git_commit = config.git_commit.strip()
        if not git_commit or not config.provider_name.strip() or not config.model_name.strip():
            raise BenchmarkRunnerError(
                "BENCHMARK_CONFIG_INVALID",
                "git_commit, provider_name, and model_name are required.",
            )
        with self.uow:
            session = self._session()
            dataset = session.get(EvaluationDataset, config.dataset_id)
            if dataset is None:
                raise BenchmarkRunnerError(
                    "BENCHMARK_DATASET_NOT_FOUND", "Dataset was not found.", status_code=404
                )
            cases = list(
                session.scalars(_case_query(config).order_by(EvaluationCase.case_key)).all()
            )
            rng = random.Random(config.random_seed)
            rng.shuffle(cases)
            started_at = datetime.now(UTC)
            run = EvaluationRun(
                dataset_id=dataset.id,
                model_configuration_id=config.model_configuration_id,
                prompt_version_id=config.prompt_version_id,
                policy_version_id=config.policy_version_id,
                status="running",
                metrics_json={},
                run_config_json=_config_payload(config, dataset),
                random_seed=config.random_seed,
                git_commit=git_commit,
                started_at=started_at,
            )
            session.add(run)
            session.flush()
            _audit(
                session,
                actor_user_id,
                "evaluation.run.start",
                run.id,
                trace_id,
                {
                    "dataset_id": str(dataset.id),
                    "case_count": len(cases),
                    "random_seed": config.random_seed,
                    "runner_version": BENCHMARK_RUNNER_VERSION,
                },
            )
            passed = 0
            for case in cases:
                before = monotonic()
                try:
                    execution = self.executor.execute(_case_input(case), config, rng)
                    failure_reason = execution.failure_reason
                    output = _safe_output(execution.output)
                except Exception as exc:  # case isolation boundary
                    execution = CaseExecutionResult(False)
                    failure_reason = f"executor_error:{type(exc).__name__}"
                    output = {}
                duration_ms = (monotonic() - before) * 1000
                passed += int(execution.passed)
                session.add(
                    EvaluationResult(
                        evaluation_run_id=run.id,
                        evaluation_case_id=case.id,
                        passed=execution.passed,
                        scores_json=dict(execution.scores),
                        failure_reason=failure_reason,
                        output_json=output,
                        duration_ms=duration_ms,
                    )
                )
            failed = len(cases) - passed
            run.status = "passed" if failed == 0 else "failed"
            run.finished_at = datetime.now(UTC)
            run.metrics_json = {
                "total_cases": len(cases),
                "passed_cases": passed,
                "failed_cases": failed,
                "pass_rate": passed / len(cases) if cases else 0.0,
                "runner_version": BENCHMARK_RUNNER_VERSION,
            }
            _audit(
                session,
                actor_user_id,
                "evaluation.run.complete",
                run.id,
                trace_id,
                {"status": run.status, **run.metrics_json},
            )
            summary = BenchmarkRunSummary(
                run.id, run.status, len(cases), passed, failed, dict(run.metrics_json)
            )
            self.uow.commit()
            return summary

    def export(
        self,
        run_id: UUID,
        *,
        format: str,
        permissions: frozenset[str],
        public_only: bool = False,
    ) -> str:
        if not public_only:
            _require(permissions, Permission.EVALUATIONS_READ)
        with self.uow:
            session = self._session()
            run = session.get(EvaluationRun, run_id)
            if run is None:
                raise BenchmarkRunnerError(
                    "BENCHMARK_RUN_NOT_FOUND", "Run was not found.", status_code=404
                )
            rows = [
                (row[0], row[1])
                for row in session.execute(
                    select(EvaluationResult, EvaluationCase)
                    .join(EvaluationCase, EvaluationCase.id == EvaluationResult.evaluation_case_id)
                    .where(EvaluationResult.evaluation_run_id == run_id)
                    .order_by(EvaluationCase.case_key)
                ).all()
            ]
            if public_only:
                rows = [
                    pair
                    for pair in rows
                    if pair[1].visibility == "public" and pair[1].reviewer_status == "approved"
                ]
            report = _report_payload(run, rows)
            self.uow.commit()
        normalized = format.strip().lower()
        if normalized == "json":
            return json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2)
        if normalized == "csv":
            return _csv_report(report)
        if normalized in {"md", "markdown"}:
            return _markdown_report(report)
        raise BenchmarkRunnerError(
            "BENCHMARK_EXPORT_FORMAT_INVALID", "format must be json, csv, or markdown."
        )

    def _session(self) -> Session:
        if self.uow.session is None:
            raise RuntimeError("Database session not initialised in UoW.")
        return self.uow.session


def _case_query(config: BenchmarkRunConfig) -> Select[tuple[EvaluationCase]]:
    stmt = select(EvaluationCase).where(EvaluationCase.dataset_id == config.dataset_id)
    if not config.include_private:
        stmt = stmt.where(
            EvaluationCase.visibility == "public", EvaluationCase.reviewer_status == "approved"
        )
    return stmt


def _case_input(row: EvaluationCase) -> BenchmarkCaseInput:
    return BenchmarkCaseInput(
        row.id,
        row.case_key,
        row.case_type,
        row.question,
        tuple(dict(item) for item in row.choices_json),
        dict(row.expected_behavior),
        tuple(dict(item) for item in row.source_references),
        row.risk_level,
    )


def _config_payload(config: BenchmarkRunConfig, dataset: EvaluationDataset) -> dict[str, object]:
    return {
        "runner_version": BENCHMARK_RUNNER_VERSION,
        "dataset_name": dataset.name,
        "dataset_version": dataset.version,
        "provider_name": config.provider_name,
        "model_name": config.model_name,
        "retriever_version": config.retriever_version,
        "embedding_version": config.embedding_version,
        "reranker_version": config.reranker_version,
        "include_private": config.include_private,
        "metadata": dict(config.metadata),
    }


def _safe_output(output: dict[str, object]) -> dict[str, object]:
    blocked = {"question", "answer", "prompt", "conversation", "document_text", "secret", "token"}
    return {key: value for key, value in output.items() if key.lower() not in blocked}


def _report_payload(
    run: EvaluationRun, rows: list[tuple[EvaluationResult, EvaluationCase]]
) -> dict[str, Any]:
    return {
        "run": {
            "id": str(run.id),
            "status": run.status,
            "dataset_id": str(run.dataset_id),
            "model_configuration_id": str(run.model_configuration_id),
            "prompt_version_id": str(run.prompt_version_id),
            "policy_version_id": str(run.policy_version_id),
            "random_seed": run.random_seed,
            "git_commit": run.git_commit,
            "configuration": run.run_config_json,
            "metrics": run.metrics_json,
        },
        "results": [
            {
                "case_key": case.case_key,
                "case_type": case.case_type,
                "passed": result.passed,
                "scores": result.scores_json,
                "failure_reason": result.failure_reason,
                "duration_ms": result.duration_ms,
            }
            for result, case in rows
        ],
    }


def _csv_report(report: dict[str, Any]) -> str:
    stream = io.StringIO()
    writer = csv.DictWriter(
        stream,
        fieldnames=["case_key", "case_type", "passed", "scores", "failure_reason", "duration_ms"],
    )
    writer.writeheader()
    for row in report["results"]:
        item = dict(row)
        item["scores"] = json.dumps(item["scores"], sort_keys=True)
        writer.writerow(item)
    return stream.getvalue()


def _markdown_report(report: dict[str, Any]) -> str:
    run = report["run"]
    lines = [
        "# Zayd Benchmark Report",
        "",
        f"- Run: `{run['id']}`",
        f"- Status: `{run['status']}`",
        f"- Seed: `{run['random_seed']}`",
        "",
        "| Case | Type | Passed |",
        "|---|---|---:|",
    ]
    for row in report["results"]:
        lines.append(f"| {row['case_key']} | {row['case_type']} | {str(row['passed']).lower()} |")
    return "\n".join(lines) + "\n"


def _require(permissions: frozenset[str], permission: Permission) -> None:
    if permission.value not in permissions:
        raise BenchmarkRunnerError("BENCHMARK_FORBIDDEN", "Forbidden.", status_code=403)


def _audit(
    session: Session,
    actor: UUID,
    action: str,
    resource_id: UUID,
    trace_id: str | None,
    after: dict[str, object],
) -> None:
    session.add(
        AuditLog(
            id=uuid4(),
            actor_user_id=actor,
            action=action,
            resource_type="evaluation_run",
            resource_id=resource_id,
            outcome="success",
            request_id=trace_id,
            trace_id=trace_id,
            before_summary={},
            after_summary=after,
            source_context={},
        )
    )
