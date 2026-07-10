from datetime import UTC, datetime
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
from zayd_service_evaluation import SafetyMetricsError, SafetyMetricsService


@pytest.fixture()
def seeded_run():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    actor, dataset_id, run_id = uuid4(), uuid4(), uuid4()

    with factory() as session:
        session.add(User(id=actor, email="safety-metrics@example.test", display_name="Safety Metrics"))
        session.add(
            EvaluationDataset(
                id=dataset_id,
                name="safety-dataset",
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
                case_key="routing.case.1",
                schema_version="evaluation-case-v1",
                case_type="risk_routing",
                visibility="private",
                reviewer_status="approved",
                reviewed_by=actor,
                question="High risk question 1",
                choices_json=[],
                expected_citations=[],
                expected_behavior={"outcome": "route_high_risk"},
                source_references=[],
                license_metadata={},
                provenance_json={"topic": "high_risk", "language": "th", "madhhab": "shafii"},
                risk_level="high",
            ),
            EvaluationCase(
                dataset_id=dataset_id,
                case_key="routing.case.2",
                schema_version="evaluation-case-v1",
                case_type="risk_routing",
                visibility="private",
                reviewer_status="approved",
                reviewed_by=actor,
                question="High risk question 2",
                choices_json=[],
                expected_citations=[],
                expected_behavior={"outcome": "route_high_risk"},
                source_references=[],
                license_metadata={},
                provenance_json={"topic": "high_risk", "language": "th", "madhhab": "shafii"},
                risk_level="high",
            ),
            EvaluationCase(
                dataset_id=dataset_id,
                case_key="abstention.case.1",
                schema_version="evaluation-case-v1",
                case_type="abstention",
                visibility="private",
                reviewer_status="approved",
                reviewed_by=actor,
                question="Abstain question 1",
                choices_json=[],
                expected_citations=[],
                expected_behavior={"outcome": "abstain"},
                source_references=[],
                license_metadata={},
                provenance_json={"topic": "unanswerable", "language": "ar", "madhhab": "unknown"},
                risk_level="low",
            ),
            EvaluationCase(
                dataset_id=dataset_id,
                case_key="open.case.1",
                schema_version="evaluation-case-v1",
                case_type="open_ended",
                visibility="private",
                reviewer_status="approved",
                reviewed_by=actor,
                question="Open question 1",
                choices_json=[],
                expected_citations=[],
                expected_behavior={"outcome": "answer"},
                source_references=[],
                license_metadata={},
                provenance_json={"topic": "taharah", "language": "th", "madhhab": "shafii"},
                risk_level="low",
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
                random_seed=42,
                git_commit="gitcommitval",
                started_at=datetime.now(UTC),
            )
        )
        session.flush()
        # Seed outcomes:
        # Case 0 (routing expected): routed to high risk -> TP for routing
        # Case 1 (routing expected): answered instead of routed -> FN for routing (safety failure)
        # Case 2 (abstaining expected): abstained -> TP for abstention
        # Case 3 (answering expected): routed to high risk instead -> FP for routing, TN for abstention
        session.add_all(
            [
                EvaluationResult(
                    evaluation_run_id=run_id,
                    evaluation_case_id=cases[0].id,
                    passed=True,
                    scores_json={},
                    output_json={"outcome": "route_high_risk"},
                ),
                EvaluationResult(
                    evaluation_run_id=run_id,
                    evaluation_case_id=cases[1].id,
                    passed=False,
                    scores_json={},
                    output_json={"outcome": "answer"},
                ),
                EvaluationResult(
                    evaluation_run_id=run_id,
                    evaluation_case_id=cases[2].id,
                    passed=True,
                    scores_json={},
                    output_json={"outcome": "abstain"},
                ),
                EvaluationResult(
                    evaluation_run_id=run_id,
                    evaluation_case_id=cases[3].id,
                    passed=False,
                    scores_json={},
                    output_json={"outcome": "route_high_risk"},
                ),
            ]
        )
        session.commit()
    return factory, actor, run_id


def test_calculate_safety_metrics_overall_and_slice(seeded_run) -> None:
    factory, actor, run_id = seeded_run
    service = SafetyMetricsService(SQLAlchemyUnitOfWork(factory))
    permissions = frozenset({Permission.EVALUATIONS_READ.value})
    report = service.calculate(run_id, permissions=permissions, actor_user_id=actor)

    assert report.overall.case_count == 4

    # Routing
    assert report.overall.routing_expected_count == 2
    assert report.overall.routing_true_positives == 1
    assert report.overall.routing_false_negatives == 1
    assert report.overall.routing_false_positives == 1  # Open case 1 routed
    assert report.overall.routing_true_negatives == 1  # Abstain case 1 abstained
    assert report.overall.routing_true_positive_rate == 0.5
    assert report.overall.routing_false_negative_rate == 0.5
    assert report.overall.routing_false_positive_rate == 0.5

    # Abstention
    assert report.overall.abstention_expected_count == 1
    assert report.overall.abstention_true_positives == 1
    assert report.overall.abstention_false_negatives == 0
    assert report.overall.abstention_false_positives == 0
    assert report.overall.abstention_true_negatives == 3
    assert report.overall.abstention_true_positive_rate == 1.0
    assert report.overall.abstention_false_negative_rate == 0.0
    assert report.overall.abstention_false_positive_rate == 0.0

    # Overall Rates
    assert report.overall.unsafe_answer_rate == pytest.approx(1 / 3)  # 1 routing FN, 0 abstention FN. Total safety expected = 3
    assert report.overall.policy_compliance_rate == 0.5  # 2 correct outcomes matching expected (routing case 1, abstention case 1) out of 4 cases

    # Slice grouping
    assert report.by_topic["high_risk"].case_count == 2
    assert report.by_topic["high_risk"].routing_true_positive_rate == 0.5

    assert report.by_language["ar"].case_count == 1
    assert report.by_language["ar"].abstention_true_positive_rate == 1.0

    assert report.by_madhhab["shafii"].case_count == 3

    with factory() as session:
        assert session.scalar(
            select(AuditLog).where(AuditLog.action == "evaluation.safety_metrics.calculate")
        )
        run = session.get(EvaluationRun, run_id)
        assert run is not None and "safety" in run.metrics_json


def test_calculate_safety_metrics_requires_read_permission(seeded_run) -> None:
    factory, _actor, run_id = seeded_run
    service = SafetyMetricsService(SQLAlchemyUnitOfWork(factory))
    with pytest.raises(SafetyMetricsError, match="Forbidden"):
        service.calculate(run_id, permissions=frozenset())


def test_calculate_safety_metrics_run_not_found(seeded_run) -> None:
    factory, _actor, _run_id = seeded_run
    service = SafetyMetricsService(SQLAlchemyUnitOfWork(factory))
    permissions = frozenset({Permission.EVALUATIONS_READ.value})
    with pytest.raises(SafetyMetricsError, match="not found"):
        service.calculate(uuid4(), permissions=permissions)
