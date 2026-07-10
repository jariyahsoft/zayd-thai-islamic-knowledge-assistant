from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from zayd_common.database.models import Base, User
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.rbac import Permission
from zayd_service_evaluation import (
    Choice,
    DatasetCreate,
    EvaluationCaseContract,
    EvaluationCaseStore,
    EvaluationCaseStoreError,
    EvaluationCaseType,
    EvaluationVisibility,
    ExpectedBehavior,
    ReviewerStatus,
    SourceReference,
)


def _source(*, redistributable: bool = True) -> SourceReference:
    return SourceReference(
        source_id=uuid4(),
        citation_id=uuid4(),
        canonical_reference="book:1:1",
        license_name="Test License",
        license_status="persistent_redistributable",
        redistributable=redistributable,
    )


def _contract(**updates) -> EvaluationCaseContract:
    payload = {
        "case_key": "case.001",
        "case_type": EvaluationCaseType.OPEN_ENDED,
        "visibility": EvaluationVisibility.PRIVATE,
        "reviewer_status": ReviewerStatus.DRAFT,
        "question": "Sanitized test question",
        "expected_behavior": ExpectedBehavior(
            outcome="answer", rubric={"must_include": ["evidence"]}
        ),
        "sources": (_source(),),
        "provenance": {"origin": "manual"},
    }
    payload.update(updates)
    return EvaluationCaseContract.model_validate(payload)


def test_all_case_types_validate_deterministically() -> None:
    reviewer = uuid4()
    cases = [
        _contract(
            case_type="multiple_choice",
            choices=(Choice(key="a", text="A"), Choice(key="b", text="B")),
            expected_behavior=ExpectedBehavior(outcome="answer", expected_choice_keys=("a",)),
        ),
        _contract(case_key="case.open", case_type="open_ended"),
        _contract(
            case_key="case.retrieval",
            case_type="retrieval_only",
            expected_behavior=ExpectedBehavior(outcome="retrieve"),
        ),
        _contract(
            case_key="case.citation",
            case_type="citation",
            expected_behavior=ExpectedBehavior(outcome="cite", required_citation_ids=(uuid4(),)),
        ),
        _contract(
            case_key="case.abstain",
            case_type="abstention",
            expected_behavior=ExpectedBehavior(outcome="abstain"),
        ),
        _contract(
            case_key="case.risk",
            case_type="risk_routing",
            expected_behavior=ExpectedBehavior(outcome="route_high_risk"),
            reviewer_status="approved",
            reviewed_by=reviewer,
        ),
    ]
    assert {case.case_type for case in cases} == set(EvaluationCaseType)
    assert all(
        EvaluationCaseContract.model_validate_json(case.model_dump_json()) == case for case in cases
    )


def test_public_case_requires_approval_and_redistributable_sources() -> None:
    with pytest.raises(ValidationError, match="public cases must be approved"):
        _contract(visibility="public")
    with pytest.raises(ValidationError, match="redistributable"):
        _contract(
            visibility="public",
            reviewer_status="approved",
            reviewed_by=uuid4(),
            sources=(_source(redistributable=False),),
        )


def test_multiple_choice_rules_are_fail_closed() -> None:
    with pytest.raises(ValidationError, match="expected choice keys"):
        _contract(
            case_type="multiple_choice",
            choices=(Choice(key="a", text="A"), Choice(key="b", text="B")),
            expected_behavior=ExpectedBehavior(outcome="answer", expected_choice_keys=("c",)),
        )


def test_store_enforces_private_visibility_and_manage_permission() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    actor = uuid4()
    with factory() as session:
        session.add(User(id=actor, email="evaluation@example.test", display_name="Evaluation"))
        session.commit()
    store = EvaluationCaseStore(SQLAlchemyUnitOfWork(factory))
    manage = frozenset({Permission.EVALUATIONS_MANAGE.value, Permission.EVALUATIONS_READ.value})
    dataset = store.create_dataset(
        DatasetCreate(
            "private-set", "1.0.0", EvaluationVisibility.PRIVATE, "persistent_private", {}
        ),
        actor_user_id=actor,
        permissions=manage,
    )
    row = store.create_case(dataset.id, _contract(), actor_user_id=actor, permissions=manage)
    assert row.schema_version == "evaluation-case-v1"
    assert store.list_cases(dataset.id, permissions=frozenset()) == []
    assert [item.id for item in store.list_cases(dataset.id, permissions=manage)] == [row.id]
    with pytest.raises(EvaluationCaseStoreError, match="Forbidden"):
        store.create_case(
            dataset.id, _contract(case_key="case.002"), actor_user_id=actor, permissions=frozenset()
        )


def test_public_approved_case_is_visible_without_private_permission() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    actor = uuid4()
    with factory() as session:
        session.add(User(id=actor, email="public-eval@example.test", display_name="Public Eval"))
        session.commit()
    store = EvaluationCaseStore(SQLAlchemyUnitOfWork(factory))
    manage = frozenset({Permission.EVALUATIONS_MANAGE.value})
    dataset = store.create_dataset(
        DatasetCreate(
            "public-set", "1.0.0", EvaluationVisibility.PUBLIC, "persistent_redistributable", {}
        ),
        actor_user_id=actor,
        permissions=manage,
    )
    row = store.create_case(
        dataset.id,
        _contract(visibility="public", reviewer_status="approved", reviewed_by=actor),
        actor_user_id=actor,
        permissions=manage,
    )
    assert [item.id for item in store.list_cases(dataset.id, permissions=frozenset())] == [row.id]
