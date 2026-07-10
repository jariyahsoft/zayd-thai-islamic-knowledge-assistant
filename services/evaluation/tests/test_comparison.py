from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
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
    BenchmarkComparisonError,
    BenchmarkComparisonService,
)


@pytest.fixture()
def seeded_runs():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    actor, dataset_id = uuid4(), uuid4()

    run_a_id = uuid4()
    run_b_id = uuid4()

    with factory() as session:
        session.add(User(id=actor, email="comp@example.test", display_name="Comp"))
        session.add(
            EvaluationDataset(
                id=dataset_id,
                name="dataset",
                version="1.0.0",
                license_status="private",
                visibility="private",
                status="ready",
                manifest_json={},
                created_by=actor,
            )
        )
        cases = [
            EvaluationCase(
                dataset_id=dataset_id,
                case_key="case.public",
                schema_version="evaluation-case-v1",
                case_type="open_ended",
                visibility="public",
                reviewer_status="approved",
                reviewed_by=actor,
                question="q public",
                choices_json=[],
                expected_citations=[],
                expected_behavior={"outcome": "answer"},
                source_references=[],
                license_metadata={},
                provenance_json={"topic": "taharah", "language": "th", "madhhab": "shafii"},
                risk_level="low",
            ),
            EvaluationCase(
                dataset_id=dataset_id,
                case_key="case.private",
                schema_version="evaluation-case-v1",
                case_type="open_ended",
                visibility="private",
                reviewer_status="approved",
                reviewed_by=actor,
                question="q private",
                choices_json=[],
                expected_citations=[],
                expected_behavior={"outcome": "answer"},
                source_references=[],
                license_metadata={},
                provenance_json={"topic": "salah", "language": "th", "madhhab": "shafii"},
                risk_level="high",
            ),
        ]
        session.add_all(cases)
        session.add_all(
            [
                EvaluationRun(
                    id=run_a_id,
                    dataset_id=dataset_id,
                    model_configuration_id=uuid4(),
                    prompt_version_id=uuid4(),
                    policy_version_id=uuid4(),
                    status="passed",
                    metrics_json={},
                    run_config_json={
                        "dataset_name": "dataset",
                        "dataset_version": "1.0.0",
                        "provider_name": "prov",
                        "model_name": "model_a",
                        "retriever_version": "v1",
                    },
                    random_seed=7,
                    git_commit="abc",
                    started_at=datetime.now(UTC),
                ),
                EvaluationRun(
                    id=run_b_id,
                    dataset_id=dataset_id,
                    model_configuration_id=uuid4(),
                    prompt_version_id=uuid4(),
                    policy_version_id=uuid4(),
                    status="passed",
                    metrics_json={},
                    run_config_json={
                        "dataset_name": "dataset",
                        "dataset_version": "1.0.0",
                        "provider_name": "prov",
                        "model_name": "model_b",
                        "retriever_version": "v1",
                    },
                    random_seed=7,
                    git_commit="def",
                    started_at=datetime.now(UTC),
                ),
            ]
        )
        session.flush()

        # Seed outcomes:
        # case.public: passed on A, failed on B -> Regression
        # case.private: failed on A, passed on B -> Improvement
        session.add_all(
            [
                EvaluationResult(
                    evaluation_run_id=run_a_id,
                    evaluation_case_id=cases[0].id,
                    passed=True,
                    scores_json={"correctness": 1.0},
                    output_json={"outcome": "answer"},
                ),
                EvaluationResult(
                    evaluation_run_id=run_b_id,
                    evaluation_case_id=cases[0].id,
                    passed=False,
                    scores_json={"correctness": 0.0},
                    output_json={"outcome": "answer"},
                ),
                EvaluationResult(
                    evaluation_run_id=run_a_id,
                    evaluation_case_id=cases[1].id,
                    passed=False,
                    scores_json={"correctness": 0.0},
                    output_json={"outcome": "answer"},
                ),
                EvaluationResult(
                    evaluation_run_id=run_b_id,
                    evaluation_case_id=cases[1].id,
                    passed=True,
                    scores_json={"correctness": 1.0},
                    output_json={"outcome": "answer"},
                ),
            ]
        )
        session.commit()
    return factory, run_a_id, run_b_id


def test_list_runs(seeded_runs) -> None:
    factory, run_a, run_b = seeded_runs
    service = BenchmarkComparisonService(SQLAlchemyUnitOfWork(factory))
    permissions = frozenset({Permission.EVALUATIONS_READ.value})
    runs = service.list_runs(permissions=permissions)
    assert len(runs) >= 2
    assert {run.run_id for run in runs} == {run_a, run_b}


def test_compare_runs_with_private_permission(seeded_runs) -> None:
    factory, run_a, run_b = seeded_runs
    service = BenchmarkComparisonService(SQLAlchemyUnitOfWork(factory))
    permissions = frozenset({Permission.EVALUATIONS_READ.value})

    report = service.compare_runs(run_a, run_b, permissions=permissions)

    assert report.regression_count == 1
    assert report.improvement_count == 1
    assert len(report.comparisons) == 2

    # public
    public_comp = [c for c in report.comparisons if c.case_key == "case.public"][0]
    assert public_comp.regression is True
    assert public_comp.improvement is False

    # private
    private_comp = [c for c in report.comparisons if c.case_key == "case.private"][0]
    assert private_comp.regression is False
    assert private_comp.improvement is True


def test_compare_runs_restricts_private_cases_without_permission(seeded_runs) -> None:
    factory, run_a, run_b = seeded_runs
    service = BenchmarkComparisonService(SQLAlchemyUnitOfWork(factory))

    report = service.compare_runs(run_a, run_b, permissions=frozenset())

    # Should only compare public cases
    assert len(report.comparisons) == 1
    assert report.comparisons[0].case_key == "case.public"
    assert report.regression_count == 1
    assert report.improvement_count == 0


def test_compare_runs_run_not_found(seeded_runs) -> None:
    factory, run_a, _run_b = seeded_runs
    service = BenchmarkComparisonService(SQLAlchemyUnitOfWork(factory))
    with pytest.raises(BenchmarkComparisonError, match="not found"):
        service.compare_runs(run_a, uuid4(), permissions=frozenset())
