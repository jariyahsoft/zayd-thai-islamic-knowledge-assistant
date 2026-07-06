import os
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from zayd_common.database.models import (
    Document,
    DocumentChunk,
    DocumentVersion,
    Source,
    SourceLicense,
    User,
)
from zayd_common.database.repositories import (
    SQLAlchemyDocumentRepository,
    SQLAlchemySourceRepository,
    SQLAlchemyUserRepository,
)
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

# Default connection URL matching dev docker-compose setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://zayd_dev:zayd_dev@localhost:5432/zayd_dev")


@pytest.fixture(scope="module")
def postgres_engine():
    """Create a PostgreSQL engine; skip tests if server is unavailable."""
    engine = create_engine(DATABASE_URL)
    try:
        with engine.connect():
            pass
    except OperationalError:
        pytest.skip(f"PostgreSQL database is not reachable at {DATABASE_URL}")
    return engine


@pytest.fixture
def pg_session(postgres_engine):
    """Provide a session wrapped in a transaction that is rolled back after each test."""
    connection = postgres_engine.connect()
    # Begin a transaction on the connection
    transaction = connection.begin()
    # Bind the session to the transaction
    session_factory = sessionmaker(bind=connection)
    session = session_factory()

    try:
        yield session
    finally:
        session.close()
        # Roll back transaction to clean up DB state
        transaction.rollback()
        connection.close()


def test_postgres_user_repository_crud(pg_session: Any) -> None:
    # Verify we can perform end-to-end user operations against real PostgreSQL
    repo = SQLAlchemyUserRepository(pg_session)

    user = User(
        id=uuid4(),
        email=f"pg-test-{uuid4().hex[:8]}@example.com",
        display_name="PG Test User",
        mfa_enabled=True,
        preferred_language="th",
        preferred_madhhab="shafii",
        status="active",
        row_version=1,
    )

    repo.create(user)
    pg_session.flush()

    retrieved = repo.get_by_id(user.id)
    assert retrieved is not None
    assert retrieved.email == user.email
    assert retrieved.mfa_enabled is True

    # Update
    retrieved.display_name = "PG Updated User"
    repo.update(retrieved)
    pg_session.flush()

    retrieved2 = repo.get_by_id(user.id)
    assert retrieved2 is not None
    assert retrieved2.display_name == "PG Updated User"


def test_postgres_document_repository_lifecycle(pg_session: Any) -> None:
    # Connect and verify document insertion against Postgres schema types
    user_repo = SQLAlchemyUserRepository(pg_session)
    source_repo = SQLAlchemySourceRepository(pg_session)
    doc_repo = SQLAlchemyDocumentRepository(pg_session)

    # Prerequisite User
    user = User(
        id=uuid4(),
        email=f"reviewer-{uuid4().hex[:8]}@example.com",
        display_name="Reviewer PG",
        mfa_enabled=False,
    )
    user_repo.create(user)
    pg_session.flush()

    # Create Source
    source = Source(
        id=uuid4(),
        name="Source PG",
        source_type="hadith_collection",
        language="th",
        reliability_level=5,
        created_by=user.id,
    )
    source_repo.create(source)
    pg_session.flush()

    # Create License
    license_rec = SourceLicense(
        id=uuid4(),
        source_id=source.id,
        license_name=" Hadith License",
        status="persistent_redistributable",
        storage_permission="allowed",
        embedding_permission="allowed",
        commercial_use="allowed",
        redistribution="allowed",
        created_by=user.id,
    )
    source_repo.add_license(license_rec)
    pg_session.flush()

    # Create Document
    doc = Document(
        id=uuid4(),
        source_id=source.id,
        source_license_id=license_rec.id,
        canonical_id=f"doc-{uuid4().hex[:8]}",
        document_type="hadith",
        title="Hadith PG Test",
        language="th",
        created_by=user.id,
    )
    doc_repo.create(doc)
    pg_session.flush()

    # Create version
    version = DocumentVersion(
        id=uuid4(),
        document_id=doc.id,
        version_number=1,
        status="uploaded",
        content_hash=f"hash-{uuid4().hex[:8]}",
        created_by=user.id,
    )
    doc_repo.add_version(version)
    pg_session.flush()

    # Add chunk
    chunks = [
        DocumentChunk(
            id=uuid4(),
            document_version_id=version.id,
            chunk_index=0,
            content="Hadith text",
            content_normalized="hadith text",
            token_count=2,
            chunking_strategy_version="simple-v1",
            content_hash=f"chunk-hash-{uuid4().hex[:8]}",
        )
    ]
    doc_repo.add_chunks(chunks)
    pg_session.flush()

    # Query checks
    db_doc = doc_repo.get_by_id(doc.id)
    assert db_doc is not None
    assert db_doc.title == "Hadith PG Test"

    db_chunks = doc_repo.get_chunks_by_version(version.id)
    assert len(db_chunks) == 1
    assert db_chunks[0].content == "Hadith text"


def test_postgres_unit_of_work_transaction(postgres_engine: Any) -> None:
    # Wrap in transaction but roll back at connection level to keep DB clean
    connection = postgres_engine.connect()
    tx = connection.begin()
    session_factory_bound = sessionmaker(bind=connection)
    bound_uow = SQLAlchemyUnitOfWork(session_factory_bound)

    user_id = uuid4()
    with bound_uow:
        user = User(
            id=user_id,
            email=f"uow-pg-{uuid4().hex[:8]}@example.com",
            display_name="UoW User",
            mfa_enabled=False,
        )
        bound_uow.users.create(user)
        bound_uow.commit()

    # Explicitly verify it was committed in the session scope
    res = connection.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    assert res is not None

    tx.rollback()
    connection.close()
