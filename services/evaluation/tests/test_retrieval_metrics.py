from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from zayd_common.database.models import (
    AuditLog,
    Base,
    EvaluationCase,
    EvaluationDataset,
    EvaluationResult,
    EvaluationRun,
    User,
)
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.rbac import Permission
from zayd_service_evaluation import RetrievalMetricsError, RetrievalMetricsService


@pytest.fixture()
def seeded_run():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    actor, dataset_id, run_id = uuid4(), uuid4(), uuid4()
    source_a, source_b, source_c, source_d, source_e = [uuid4() for _ in range(5)]
    with factory() as session:
        session.add(User(id=actor, email="metrics@example.test", display_name="Metrics"))
        session.add(
            EvaluationDataset(
                id=dataset_id,
                name="metrics",
                version="1",
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
                case_key="retrieval.thai",
                schema_version="evaluation-case-v1",
                case_type="retrieval_only",
                visibility="private",
                reviewer_status="approved",
                reviewed_by=actor,
                question="q1",
                choices_json=[],
                expected_citations=[],
                expected_behavior={"rubric": {"metadata_filters": {"language": "th"}}},
                source_references=[{"source_id": str(source_a)}, {"source_id": str(source_b)}],
                license_metadata={},
                provenance_json={"topic": "fiqh", "language": "th", "madhhab": "shafii"},
                risk_level="low",
            ),
            EvaluationCase(
                dataset_id=dataset_id,
                case_key="citation.arabic",
                schema_version="evaluation-case-v1",
                case_type="citation",
                visibility="private",
                reviewer_status="approved",
                reviewed_by=actor,
                question="q2",
                choices_json=[],
                expected_citations=[],
                expected_behavior={"rubric": {"metadata_filters": {"language": "ar"}}},
                source_references=[{"source_id": str(source_d)}],
                license_metadata={},
                provenance_json={"topic": "hadith", "language": "ar", "madhhab": "unknown"},
                risk_level="medium",
            ),
        ]
        session.add_all(cases)
        session.add(
            EvaluationRun(
                id=run_id,
                dataset_id=dataset_id,
                model_configuration_id=uuid4(),
                prompt_version_id=uuid4(),
                policy_version_id=uuid4(),
                status="passed",
                metrics_json={},
                run_config_json={},
                random_seed=7,
                git_commit="abc",
                started_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
            )
        )
        session.flush()
        session.add_all(
            [
                EvaluationResult(
                    evaluation_run_id=run_id,
                    evaluation_case_id=cases[0].id,
                    passed=True,
                    scores_json={},
                    output_json={
                        "retrieved_source_ids": [str(source_c), str(source_a), str(source_b)],
                        "metadata_filters": {"language": "th"},
                    },
                ),
                EvaluationResult(
                    evaluation_run_id=run_id,
                    evaluation_case_id=cases[1].id,
                    passed=False,
                    scores_json={},
                    output_json={
                        "retrieved_source_ids": [str(source_e), "not-a-uuid"],
                        "metadata_filters": {"language": "th"},
                    },
                ),
            ]
        )
        session.commit()
    return factory, actor, run_id


def test_hand_calculated_metrics_multiple_sources_invalid_refs_and_groups(seeded_run) -> None:
    factory, actor, run_id = seeded_run
    service = RetrievalMetricsService(SQLAlchemyUnitOfWork(factory))
    permissions = frozenset({Permission.EVALUATIONS_READ.value})
    report = service.calculate(run_id, permissions=permissions, actor_user_id=actor)
    assert report.overall.case_count == 2
    assert report.overall.recall_at_5 == 0.5
    assert report.overall.recall_at_10 == 0.5
    assert report.overall.mrr == 0.25
    assert report.overall.precision == pytest.approx(1 / 3)
    assert report.overall.metadata_filter_correctness == 0.5
    assert report.overall.invalid_reference_count == 1
    assert report.by_topic["fiqh"].recall_at_5 == 1.0
    assert report.by_language["ar"].metadata_filter_correctness == 0.0
    assert report.by_madhhab["shafii"].case_count == 1
    with factory() as session:
        assert session.scalar(
            select(AuditLog).where(AuditLog.action == "evaluation.retrieval_metrics.calculate")
        )
        run = session.get(EvaluationRun, run_id)
        assert (
            run is not None and run.metrics_json["retrieval"]["version"] == "retrieval-metrics-v1"
        )


def test_metrics_require_read_permission_and_known_run(seeded_run) -> None:
    factory, _actor, run_id = seeded_run
    service = RetrievalMetricsService(SQLAlchemyUnitOfWork(factory))
    with pytest.raises(RetrievalMetricsError, match="Forbidden"):
        service.calculate(run_id, permissions=frozenset())
    with pytest.raises(RetrievalMetricsError, match="not found"):
        service.calculate(uuid4(), permissions=frozenset({Permission.EVALUATIONS_READ.value}))


def test_empty_retrieval_run_has_zero_metrics(seeded_run) -> None:
    factory, _actor, _run_id = seeded_run
    service = RetrievalMetricsService(SQLAlchemyUnitOfWork(factory))
    with factory() as session:
        empty = EvaluationRun(
            dataset_id=session.scalar(select(EvaluationDataset.id)),
            model_configuration_id=uuid4(),
            prompt_version_id=uuid4(),
            policy_version_id=uuid4(),
            status="passed",
            metrics_json={},
            run_config_json={},
            random_seed=1,
            git_commit="def",
            started_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
        )
        session.add(empty)
        session.commit()
    report = service.calculate(empty.id, permissions=frozenset({Permission.EVALUATIONS_READ.value}))
    assert report.overall.case_count == 0
    assert report.overall.invalid_reference_count == 0
