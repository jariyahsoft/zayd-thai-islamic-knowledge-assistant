import tempfile
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from zayd_common.database.models import Base, User
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.rbac import Permission
from zayd_service_evaluation import (
    StarterSetSeedError,
    load_starter_set_files,
    seed_starter_set,
)


@pytest.fixture()
def dataset_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        manifest = {
            "name": "Zayd-IslamicQA-TH",
            "version": "1.0.0",
            "visibility": "private",
            "license_status": "persistent_private",
            "manifest": {"description": "desc"},
        }
        public_cases = [
            {
                "case_key": "taharah.test",
                "case_type": "open_ended",
                "visibility": "public",
                "reviewer_status": "approved",
                "question": "question 1",
                "choices": [],
                "expected_behavior": {"outcome": "answer"},
                "sources": [
                    {
                        "source_id": str(uuid4()),
                        "citation_id": str(uuid4()),
                        "canonical_reference": "ref 1",
                        "license_name": "Public Domain",
                        "license_status": "persistent_redistributable",
                        "redistributable": True,
                    }
                ],
                "risk_level": "low",
                "provenance": {"topic": "taharah"},
            }
        ]
        private_cases = [
            {
                "case_key": "high_risk.test",
                "case_type": "risk_routing",
                "visibility": "private",
                "reviewer_status": "approved",
                "question": "question 2",
                "choices": [],
                "expected_behavior": {"outcome": "route_high_risk"},
                "sources": [
                    {
                        "source_id": str(uuid4()),
                        "citation_id": str(uuid4()),
                        "canonical_reference": "ref 2",
                        "license_name": "Restricted",
                        "license_status": "persistent_private",
                        "redistributable": False,  # JSON boolean
                    }
                ],
                "risk_level": "high",
                "provenance": {"topic": "high_risk"},
            }
        ]

        (tmp_path / "starter_set_manifest.json").write_text(
            __import__("json").dumps(manifest), encoding="utf-8"
        )
        (tmp_path / "public_cases.json").write_text(
            __import__("json").dumps(public_cases), encoding="utf-8"
        )
        (tmp_path / "private_cases.json").write_text(
            __import__("json").dumps(private_cases).replace("false", "false"), encoding="utf-8"
        )
        yield tmp_path


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


@pytest.fixture()
def manage_perms():
    return frozenset({Permission.EVALUATIONS_MANAGE.value})


def test_load_and_validate_correct_starter_set(dataset_dir) -> None:
    reviewer = uuid4()
    req, cases = load_starter_set_files(dataset_dir, reviewed_by=reviewer)
    assert req.name == "Zayd-IslamicQA-TH"
    assert len(cases) == 2
    assert cases[0].case_key == "taharah.test"
    assert cases[0].reviewed_by == reviewer
    assert cases[1].case_key == "high_risk.test"
    assert cases[1].reviewed_by == reviewer


def test_load_rejects_unapproved_cases(dataset_dir) -> None:
    # Modify public_cases to be unapproved
    public_path = dataset_dir / "public_cases.json"
    cases = __import__("json").loads(public_path.read_text(encoding="utf-8"))
    cases[0]["reviewer_status"] = "draft"
    public_path.write_text(__import__("json").dumps(cases), encoding="utf-8")

    reviewer = uuid4()
    with pytest.raises((StarterSetSeedError, ValidationError), match="must be approved"):
        load_starter_set_files(dataset_dir, reviewed_by=reviewer)


def test_load_rejects_missing_license(dataset_dir) -> None:
    public_path = dataset_dir / "public_cases.json"
    cases = __import__("json").loads(public_path.read_text(encoding="utf-8"))
    cases[0]["sources"][0]["license_name"] = " "  # empty license
    public_path.write_text(__import__("json").dumps(cases), encoding="utf-8")

    reviewer = uuid4()
    with pytest.raises((StarterSetSeedError, ValidationError), match="license name and status"):
        load_starter_set_files(dataset_dir, reviewed_by=reviewer)


def test_load_rejects_missing_canonical_ref(dataset_dir) -> None:
    public_path = dataset_dir / "public_cases.json"
    cases = __import__("json").loads(public_path.read_text(encoding="utf-8"))
    cases[0]["sources"][0]["canonical_reference"] = ""  # empty reference
    public_path.write_text(__import__("json").dumps(cases), encoding="utf-8")

    reviewer = uuid4()
    with pytest.raises((StarterSetSeedError, ValidationError), match="canonical_reference"):
        load_starter_set_files(dataset_dir, reviewed_by=reviewer)


def test_seed_starter_set_success(dataset_dir, db, manage_perms) -> None:
    actor, reviewer = uuid4(), uuid4()
    with db() as session:
        session.add(User(id=actor, email="actor@zayd.test", display_name="Actor"))
        session.add(User(id=reviewer, email="reviewer@zayd.test", display_name="Reviewer"))
        session.commit()

    uow = SQLAlchemyUnitOfWork(db)
    result = seed_starter_set(
        uow,
        dataset_dir=dataset_dir,
        actor_user_id=actor,
        reviewed_by=reviewer,
        permissions=manage_perms,
    )

    assert result.created_cases == 2
    assert result.skipped_cases == 0
    assert result.total_cases == 2
    assert result.dataset_created is True

    # Test idempotency (should skip cases)
    result_second = seed_starter_set(
        uow,
        dataset_dir=dataset_dir,
        actor_user_id=actor,
        reviewed_by=reviewer,
        permissions=manage_perms,
    )
    assert result_second.created_cases == 0
    assert result_second.skipped_cases == 2
    assert result_second.dataset_created is False


def test_seed_starter_set_forbidden(dataset_dir, db) -> None:
    uow = SQLAlchemyUnitOfWork(db)
    with pytest.raises(StarterSetSeedError, match="Forbidden"):
        seed_starter_set(
            uow,
            dataset_dir=dataset_dir,
            actor_user_id=uuid4(),
            reviewed_by=uuid4(),
            permissions=frozenset(),
        )
