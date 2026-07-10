import json
import random
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from zayd_common.database.models import (
    Base,
    EvaluationCase,
    EvaluationDataset,
    EvaluationResult,
    EvaluationRun,
    User,
)
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.rbac import Permission
from zayd_service_evaluation import (
    BenchmarkRunConfig,
    BenchmarkRunner,
    BenchmarkRunnerError,
    CaseExecutionResult,
)


class DeterministicExecutor:
    def execute(self, case, config, rng: random.Random) -> CaseExecutionResult:
        value = rng.random()
        return CaseExecutionResult(
            True, {"score": value}, {"trace_code": case.case_key, "answer": "must be stripped"}
        )


class IsolatingExecutor:
    def execute(self, case, config, rng: random.Random) -> CaseExecutionResult:
        if case.case_key == "private.failure":
            raise RuntimeError("private payload must not escape")
        return CaseExecutionResult(True, {"score": 1.0})


@pytest.fixture()
def seeded_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    actor, dataset_id = uuid4(), uuid4()
    with factory() as session:
        session.add(User(id=actor, email="runner@example.test", display_name="Runner"))
        session.add(
            EvaluationDataset(
                id=dataset_id,
                name="benchmark",
                version="1.0.0",
                license_status="persistent_private",
                visibility="private",
                status="ready",
                manifest_json={},
                created_by=actor,
            )
        )
        session.add_all(
            [
                EvaluationCase(
                    dataset_id=dataset_id,
                    case_key="public.pass",
                    schema_version="evaluation-case-v1",
                    case_type="open_ended",
                    visibility="public",
                    reviewer_status="approved",
                    reviewed_by=actor,
                    question="Public sanitized question",
                    choices_json=[],
                    expected_citations=[],
                    expected_behavior={"outcome": "answer"},
                    source_references=[{"source_id": str(uuid4()), "redistributable": True}],
                    license_metadata={},
                    provenance_json={},
                    risk_level="low",
                ),
                EvaluationCase(
                    dataset_id=dataset_id,
                    case_key="private.failure",
                    schema_version="evaluation-case-v1",
                    case_type="abstention",
                    visibility="private",
                    reviewer_status="approved",
                    reviewed_by=actor,
                    question="Private sanitized question",
                    choices_json=[],
                    expected_citations=[],
                    expected_behavior={"outcome": "abstain"},
                    source_references=[{"source_id": str(uuid4()), "redistributable": False}],
                    license_metadata={},
                    provenance_json={},
                    risk_level="high",
                ),
            ]
        )
        session.commit()
    return factory, actor, dataset_id


def _config(dataset_id, *, seed=42, provider="local") -> BenchmarkRunConfig:
    return BenchmarkRunConfig(
        dataset_id=dataset_id,
        model_configuration_id=uuid4(),
        prompt_version_id=uuid4(),
        policy_version_id=uuid4(),
        random_seed=seed,
        git_commit="abc1234",
        provider_name=provider,
        model_name="test-model",
        retriever_version="retriever-v1",
    )


def test_runner_is_deterministic_and_records_versions(seeded_db) -> None:
    factory, actor, dataset_id = seeded_db
    permissions = frozenset(
        {Permission.EVALUATIONS_MANAGE.value, Permission.EVALUATIONS_READ.value}
    )
    config = _config(dataset_id)
    runner = BenchmarkRunner(SQLAlchemyUnitOfWork(factory), DeterministicExecutor())
    first = runner.run(config, actor_user_id=actor, permissions=permissions)
    second = runner.run(config, actor_user_id=actor, permissions=permissions)
    first_report = json.loads(runner.export(first.run_id, format="json", permissions=permissions))
    second_report = json.loads(runner.export(second.run_id, format="json", permissions=permissions))
    assert [row["scores"] for row in first_report["results"]] == [
        row["scores"] for row in second_report["results"]
    ]
    assert first_report["run"]["random_seed"] == 42
    assert first_report["run"]["git_commit"] == "abc1234"
    assert first_report["run"]["configuration"]["dataset_version"] == "1.0.0"


def test_case_failure_is_isolated_and_sanitized(seeded_db) -> None:
    factory, actor, dataset_id = seeded_db
    permissions = frozenset(
        {Permission.EVALUATIONS_MANAGE.value, Permission.EVALUATIONS_READ.value}
    )
    runner = BenchmarkRunner(SQLAlchemyUnitOfWork(factory), IsolatingExecutor())
    summary = runner.run(_config(dataset_id), actor_user_id=actor, permissions=permissions)
    assert summary.total_cases == 2 and summary.failed_cases == 1
    with factory() as session:
        failures = session.scalars(
            select(EvaluationResult).where(
                EvaluationResult.evaluation_run_id == summary.run_id,
                EvaluationResult.passed.is_(False),
            )
        ).all()
        assert len(failures) == 1
        assert failures[0].failure_reason == "executor_error:RuntimeError"
        assert "private payload" not in failures[0].failure_reason


def test_json_csv_markdown_exports_and_private_filter(seeded_db) -> None:
    factory, actor, dataset_id = seeded_db
    permissions = frozenset(
        {Permission.EVALUATIONS_MANAGE.value, Permission.EVALUATIONS_READ.value}
    )
    runner = BenchmarkRunner(SQLAlchemyUnitOfWork(factory), DeterministicExecutor())
    summary = runner.run(_config(dataset_id), actor_user_id=actor, permissions=permissions)
    public_json = json.loads(
        runner.export(summary.run_id, format="json", permissions=frozenset(), public_only=True)
    )
    assert [row["case_key"] for row in public_json["results"]] == ["public.pass"]
    assert "public.pass" in runner.export(summary.run_id, format="csv", permissions=permissions)
    assert "# Zayd Benchmark Report" in runner.export(
        summary.run_id, format="markdown", permissions=permissions
    )
    with pytest.raises(BenchmarkRunnerError, match="Forbidden"):
        runner.export(summary.run_id, format="json", permissions=frozenset())


def test_provider_comparison_configuration_is_recorded(seeded_db) -> None:
    factory, actor, dataset_id = seeded_db
    permissions = frozenset({Permission.EVALUATIONS_MANAGE.value})
    runner = BenchmarkRunner(SQLAlchemyUnitOfWork(factory), DeterministicExecutor())
    local = runner.run(
        _config(dataset_id, provider="local"), actor_user_id=actor, permissions=permissions
    )
    external = runner.run(
        _config(dataset_id, provider="external"), actor_user_id=actor, permissions=permissions
    )
    with factory() as session:
        runs = {
            row.id: row
            for row in session.scalars(
                select(EvaluationRun).where(EvaluationRun.id.in_((local.run_id, external.run_id)))
            ).all()
        }
    assert runs[local.run_id].run_config_json["provider_name"] == "local"
    assert runs[external.run_id].run_config_json["provider_name"] == "external"
