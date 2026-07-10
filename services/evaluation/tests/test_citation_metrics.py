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
from zayd_service_evaluation import CitationMetricsError, CitationMetricsService
from zayd_service_orchestrator.citation_verification import (
    CitationVerificationEngine,
    CitationVerificationRequest,
    CitedClaimInput,
    VerificationEvidencePack,
)


def _seed(claim_results, expected_ids, *, overrides=()):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    actor, dataset_id, run_id = uuid4(), uuid4(), uuid4()
    with factory() as session:
        session.add(
            User(id=actor, email="citation-metrics@example.test", display_name="Citation Metrics")
        )
        session.add(
            EvaluationDataset(
                id=dataset_id,
                name="citations",
                version="1",
                license_status="private",
                visibility="private",
                status="ready",
                manifest_json={},
                created_by=actor,
            )
        )
        case = EvaluationCase(
            dataset_id=dataset_id,
            case_key="citation.case",
            schema_version="evaluation-case-v1",
            case_type="citation",
            visibility="private",
            reviewer_status="approved",
            reviewed_by=actor,
            question="sanitized",
            choices_json=[],
            expected_citations=[{"citation_id": str(value)} for value in expected_ids],
            expected_behavior={"outcome": "cite"},
            source_references=[{"source_id": str(uuid4())}],
            license_metadata={},
            provenance_json={},
            risk_level="low",
        )
        session.add(case)
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
                random_seed=1,
                git_commit="abc",
                started_at=datetime.now(UTC),
            )
        )
        session.flush()
        session.add(
            EvaluationResult(
                evaluation_run_id=run_id,
                evaluation_case_id=case.id,
                passed=True,
                scores_json={},
                output_json={
                    "citation_verification": {"claim_results": claim_results},
                    "human_overrides": list(overrides),
                },
            )
        )
        session.commit()
    return factory, actor, run_id


def _check(name: str, outcome: str) -> dict[str, str]:
    return {"name": name, "outcome": outcome}


def test_golden_metrics_distinguish_all_failure_classes_and_overrides() -> None:
    correct_id, wrong_id, nonexistent_id, missing_id = [uuid4() for _ in range(4)]
    reviewer = uuid4()
    claims = [
        {
            "claim_id": "supported",
            "citation_tokens": [f"CIT-{correct_id}"],
            "support_status": "supported",
            "checks": [_check("existence", "pass"), _check("reference_correctness", "pass")],
        },
        {
            "claim_id": "wrong",
            "citation_tokens": [f"CIT-{wrong_id}"],
            "support_status": "unsupported",
            "checks": [_check("existence", "pass"), _check("reference_correctness", "fail")],
        },
        {
            "claim_id": "fabricated",
            "citation_tokens": [f"CIT-{nonexistent_id}"],
            "support_status": "invalid_citation",
            "checks": [_check("existence", "fail")],
        },
    ]
    overrides = [
        {
            "claim_id": "wrong",
            "reviewer_id": str(reviewer),
            "decision": "supported",
            "reason_code": "SCHOLAR_REVIEW",
            "created_at": "2026-07-10T00:00:00Z",
        },
        {"claim_id": "bad", "decision": "supported"},
    ]
    factory, actor, run_id = _seed(claims, (correct_id, wrong_id, missing_id), overrides=overrides)
    report = CitationMetricsService(SQLAlchemyUnitOfWork(factory)).calculate(
        run_id, permissions=frozenset({Permission.EVALUATIONS_READ.value}), actor_user_id=actor
    )
    assert report.summary.citation_correctness == pytest.approx(1 / 3)
    assert report.summary.citation_completeness == pytest.approx(2 / 3)
    assert report.summary.fabricated_citation_rate == pytest.approx(1 / 3)
    assert report.summary.claim_support_rate == pytest.approx(1 / 3)
    assert report.summary.nonexistent_count == 1
    assert report.summary.wrong_reference_count == 1
    assert report.summary.unsupported_claim_count == 2
    assert report.summary.incomplete_case_count == 1
    assert len(report.overrides) == 1 and report.overrides[0].reviewer_id == reviewer
    assert report.invalid_override_count == 1
    with factory() as session:
        assert session.scalar(
            select(AuditLog).where(AuditLog.action == "evaluation.citation_metrics.calculate")
        )
        run = session.get(EvaluationRun, run_id)
        assert run is not None and run.metrics_json["citation"]["wrong_reference_count"] == 1


def test_metric_integrates_with_deterministic_citation_verifier() -> None:
    citation_id, chunk_id, version_id = uuid4(), uuid4(), uuid4()
    token = f"CIT-{citation_id}"
    decision = CitationVerificationEngine().verify(
        CitationVerificationRequest(
            claims=(
                CitedClaimInput(
                    claim_id="claim-1",
                    claim_text="supported evidence",
                    citation_tokens=(token,),
                    declared_reference="ref:1",
                ),
            ),
            evidence=(
                VerificationEvidencePack(
                    citation_token=token,
                    citation_id=citation_id,
                    canonical_reference="ref:1",
                    citation_type="book",
                    display_title="Reference",
                    chunk_id=chunk_id,
                    document_version_id=version_id,
                    chunk_content="supported evidence",
                ),
            ),
            allowed_tokens=(token,),
        )
    )
    factory, actor, run_id = _seed(decision.claim_results_machine_readable(), (citation_id,))
    report = CitationMetricsService(SQLAlchemyUnitOfWork(factory)).calculate(
        run_id, permissions=frozenset({Permission.EVALUATIONS_READ.value}), actor_user_id=actor
    )
    assert report.summary.citation_correctness == 1.0
    assert report.summary.citation_completeness == 1.0
    assert report.summary.claim_support_rate == 1.0
    assert report.summary.fabricated_citation_rate == 0.0


def test_permission_and_missing_run_fail_closed() -> None:
    factory, _actor, run_id = _seed([], ())
    service = CitationMetricsService(SQLAlchemyUnitOfWork(factory))
    with pytest.raises(CitationMetricsError, match="Forbidden"):
        service.calculate(run_id, permissions=frozenset())
    with pytest.raises(CitationMetricsError, match="not found"):
        service.calculate(uuid4(), permissions=frozenset({Permission.EVALUATIONS_READ.value}))
