import importlib.util
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from zayd_common.database.models import (
    Base,
    Document,
    DocumentChunk,
    DocumentVersion,
    Feedback,
    Incident,
    Role,
    Source,
    SourceLicense,
    User,
    UserRole,
)
from zayd_common.database.seeding import seed_demo_data
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork


@pytest.fixture
def sqlite_session_factory():
    """In-memory SQLite database setup."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def test_run_seed_twice(sqlite_session_factory: Any) -> None:
    # 1. Run seed first time
    uow = SQLAlchemyUnitOfWork(sqlite_session_factory)
    passwords_1 = seed_demo_data(uow)

    assert "demo-admin@zayd.local" in passwords_1
    assert "demo-reviewer@zayd.local" in passwords_1
    assert "demo-scholar@zayd.local" in passwords_1

    # Verify counts in SQLite
    session = sqlite_session_factory()
    assert session.query(User).count() == 3
    assert session.query(Role).count() == 3
    assert session.query(UserRole).count() == 3
    assert session.query(Source).count() == 1
    assert session.query(SourceLicense).count() == 1
    assert session.query(Document).count() == 1
    assert session.query(DocumentVersion).count() == 1
    assert session.query(DocumentChunk).count() == 2
    assert session.query(Feedback).count() == 1
    assert session.query(Incident).count() == 1

    # Check non-authoritative markers are present in names/titles
    source = session.execute(select(Source)).scalar_one()
    assert "DEMO - NON-AUTHORITATIVE" in source.name

    doc = session.execute(select(Document)).scalar_one()
    assert "DEMO - NON-AUTHORITATIVE" in doc.title

    # 2. Run seed the second time (should be idempotent)
    passwords_2 = seed_demo_data(uow)
    assert not passwords_2  # No new passwords generated

    # Verify second runs don't duplicate rows
    assert session.query(User).count() == 3
    assert session.query(Source).count() == 1
    assert session.query(Document).count() == 1
    assert session.query(DocumentChunk).count() == 2

    session.close()


def test_license_manifest_validation(sqlite_session_factory: Any) -> None:
    uow = SQLAlchemyUnitOfWork(sqlite_session_factory)
    seed_demo_data(uow)

    session = sqlite_session_factory()
    license_rec = session.execute(select(SourceLicense)).scalar_one()

    # Verify compliance with Zayd Data License Policy
    assert license_rec.status == "persistent_redistributable"
    assert license_rec.storage_permission == "allowed"
    assert license_rec.embedding_permission == "allowed"
    assert license_rec.redistribution == "allowed"

    session.close()


def test_secret_scan_of_seed_fixtures() -> None:
    seed_files = [
        Path(__file__).parents[1] / "src" / "zayd_common" / "database" / "seeding.py",
        Path(__file__).parents[3] / "database" / "seeds" / "README.md",
        Path(__file__).parents[3] / "database" / "seeds" / "seed.py",
        Path(__file__).parents[3] / "docs" / "development" / "demo-data.md",
    ]

    forbidden_markers = [
        "AWS_SECRET",
        "TELEGRAM_BOT_TOKEN",
        "API_KEY",
        "BOT_TOKEN",
        "JWT_SECRET",
        "SESSION_SECRET",
        "MINIOADMIN",
        "PASSWORD=",
    ]

    for seed_file in seed_files:
        content = seed_file.read_text(encoding="utf-8").upper()
        for forbidden in forbidden_markers:
            assert forbidden not in content


def test_seed_cli_main_success(monkeypatch: pytest.MonkeyPatch, capsys: Any) -> None:
    seed_cli_path = Path(__file__).parents[3] / "database" / "seeds" / "seed.py"
    spec = importlib.util.spec_from_file_location("seed_cli", seed_cli_path)
    assert spec is not None and spec.loader is not None
    seed_cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(seed_cli)

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    monkeypatch.setattr(
        seed_cli.ServiceSettings,
        "from_runtime_env",
        classmethod(
            lambda cls, *, app_name: SimpleNamespace(
                database_url="postgresql://demo:demo@localhost:5432/zayd_demo"
            )
        ),
    )
    monkeypatch.setattr(seed_cli, "get_sessionmaker", lambda database_url: session_factory)

    seed_cli.main()
    first_run = capsys.readouterr()
    assert "Demo database fixtures seeded successfully!" in first_run.out
    assert "Generated demo credentials" in first_run.out
    assert "temporary" in first_run.out.lower()

    seed_cli.main()
    second_run = capsys.readouterr()
    assert "Demo database fixtures seeded successfully!" in second_run.out
    assert "Generated demo credentials" not in second_run.out


def test_seed_cli_main_failure(monkeypatch: pytest.MonkeyPatch, capsys: Any) -> None:
    seed_cli_path = Path(__file__).parents[3] / "database" / "seeds" / "seed.py"
    spec = importlib.util.spec_from_file_location("seed_cli", seed_cli_path)
    assert spec is not None and spec.loader is not None
    seed_cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(seed_cli)

    monkeypatch.setattr(
        seed_cli.ServiceSettings,
        "from_runtime_env",
        classmethod(
            lambda cls, *, app_name: SimpleNamespace(
                database_url="postgresql://demo:demo@localhost:5432/zayd_demo"
            )
        ),
    )
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    monkeypatch.setattr(seed_cli, "get_sessionmaker", lambda database_url: session_factory)
    monkeypatch.setattr(
        seed_cli,
        "seed_demo_data",
        lambda uow: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    with pytest.raises(SystemExit) as excinfo:
        seed_cli.main()

    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "Fatal error seeding database:" in captured.err
