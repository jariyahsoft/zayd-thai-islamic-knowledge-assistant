from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from zayd_common.database.models import (
    Base,
    Document,
    DocumentChunk,
    DocumentVersion,
    Feedback,
    Incident,
    Source,
    SourceLicense,
    User,
)
from zayd_common.database.repositories import (
    AbstractUserRepository,
    SQLAlchemyDocumentRepository,
    SQLAlchemyIncidentRepository,
    SQLAlchemySourceRepository,
    SQLAlchemyUserRepository,
)
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork


@pytest.fixture
def sqlite_session_factory():
    """Create an in-memory SQLite engine and session factory for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    return session_factory


def test_user_repository(sqlite_session_factory: Any) -> None:
    session = sqlite_session_factory()
    repo = SQLAlchemyUserRepository(session)

    # Create user
    user = User(
        id=uuid4(),
        email="test@example.com",
        display_name="Test User",
        mfa_enabled=False,
    )
    repo.create(user)
    session.commit()

    # Read user
    retrieved = repo.get_by_id(user.id)
    assert retrieved is not None
    assert retrieved.email == "test@example.com"

    # Query by email
    by_email = repo.get_by_email("test@example.com")
    assert by_email is not None
    assert by_email.id == user.id

    # Update user
    by_email.display_name = "Updated Name"
    repo.update(by_email)
    session.commit()

    retrieved2 = repo.get_by_id(user.id)
    assert retrieved2 is not None
    assert retrieved2.display_name == "Updated Name"

    # List users
    users = repo.get_users()
    assert len(users) == 1
    assert users[0].email == "test@example.com"

    session.close()


def test_source_and_license_repository(sqlite_session_factory: Any) -> None:
    session = sqlite_session_factory()
    user_repo = SQLAlchemyUserRepository(session)
    source_repo = SQLAlchemySourceRepository(session)

    # Prerequisite User
    user = User(id=uuid4(), email="admin@example.com", display_name="Admin")
    user_repo.create(user)
    session.commit()

    # Create Source
    source = Source(
        id=uuid4(),
        name="Quran th",
        source_type="quran",
        language="th",
        reliability_level=5,
        created_by=user.id,
    )
    source_repo.create(source)
    session.commit()

    # Add License
    license_rec = SourceLicense(
        id=uuid4(),
        source_id=source.id,
        license_name="Public Domain",
        status="persistent_redistributable",
        storage_permission="allowed",
        embedding_permission="allowed",
        commercial_use="allowed",
        redistribution="allowed",
        created_by=user.id,
    )
    source_repo.add_license(license_rec)
    session.commit()

    # Query Source and Licenses
    retrieved_source = source_repo.get_by_id(source.id)
    assert retrieved_source is not None
    assert retrieved_source.name == "Quran th"

    licenses = source_repo.get_licenses_by_source(source.id)
    assert len(licenses) == 1
    assert licenses[0].license_name == "Public Domain"

    retrieved_lic = source_repo.get_license_by_id(license_rec.id)
    assert retrieved_lic is not None
    assert retrieved_lic.source_id == source.id

    sources = source_repo.get_sources()
    assert len(sources) == 1
    assert sources[0].id == source.id

    session.close()


def test_document_and_version_repository(sqlite_session_factory: Any) -> None:
    session = sqlite_session_factory()
    user_repo = SQLAlchemyUserRepository(session)
    source_repo = SQLAlchemySourceRepository(session)
    doc_repo = SQLAlchemyDocumentRepository(session)

    # Prerequisites
    user = User(id=uuid4(), email="reviewer@example.com", display_name="Reviewer")
    user_repo.create(user)
    session.commit()

    source = Source(
        id=uuid4(),
        name="Book A",
        source_type="book",
        language="th",
        reliability_level=4,
        created_by=user.id,
    )
    source_repo.create(source)
    session.commit()

    license_rec = SourceLicense(
        id=uuid4(),
        source_id=source.id,
        license_name="Standard License",
        status="persistent_private",
        storage_permission="allowed",
        embedding_permission="allowed",
        commercial_use="prohibited",
        redistribution="prohibited",
        created_by=user.id,
    )
    source_repo.add_license(license_rec)
    session.commit()

    # Create Document
    doc = Document(
        id=uuid4(),
        source_id=source.id,
        source_license_id=license_rec.id,
        canonical_id="book-a-canonical",
        document_type="book",
        title="Book A Title",
        language="th",
        created_by=user.id,
    )
    doc_repo.create(doc)
    session.commit()

    # Add Version
    version = DocumentVersion(
        id=uuid4(),
        document_id=doc.id,
        version_number=1,
        status="uploaded",
        content_hash="v1-hash-abc",
        created_by=user.id,
    )
    doc_repo.add_version(version)
    session.commit()

    # Add Chunk
    chunks = [
        DocumentChunk(
            id=uuid4(),
            document_version_id=version.id,
            chunk_index=0,
            content="Page 1 Content",
            content_normalized="page 1 content",
            token_count=3,
            chunking_strategy_version="v1",
            content_hash="chunk-hash-1",
        )
    ]
    doc_repo.add_chunks(chunks)
    session.commit()

    # Query Documents, Versions, Chunks
    retrieved_doc = doc_repo.get_by_id(doc.id)
    assert retrieved_doc is not None
    assert retrieved_doc.title == "Book A Title"

    by_canonical = doc_repo.get_by_source_and_canonical(source.id, "book-a-canonical")
    assert by_canonical is not None
    assert by_canonical.id == doc.id

    versions = doc_repo.get_versions_by_document(doc.id)
    assert len(versions) == 1
    assert versions[0].id == version.id

    retrieved_ver = doc_repo.get_version_by_id(version.id)
    assert retrieved_ver is not None
    assert retrieved_ver.content_hash == "v1-hash-abc"

    retrieved_chunks = doc_repo.get_chunks_by_version(version.id)
    assert len(retrieved_chunks) == 1
    assert retrieved_chunks[0].content == "Page 1 Content"

    docs = doc_repo.get_documents()
    assert len(docs) == 1
    assert docs[0].id == doc.id

    session.close()


def test_incident_repository(sqlite_session_factory: Any) -> None:
    session = sqlite_session_factory()
    user_repo = SQLAlchemyUserRepository(session)
    incident_repo = SQLAlchemyIncidentRepository(session)

    # Prerequisites
    user = User(id=uuid4(), email="incident-owner@example.com", display_name="Admin")
    user_repo.create(user)

    feedback = Feedback(id=uuid4(), status="open")
    session.add(feedback)
    session.commit()

    # Create Incident
    incident = Incident(
        id=uuid4(),
        feedback_id=feedback.id,
        severity="p1",
        status="open",
        summary="Retrieved incorrect fatwa explanation",
        opened_by=user.id,
    )
    incident_repo.create(incident)
    session.commit()

    retrieved = incident_repo.get_by_id(incident.id)
    assert retrieved is not None
    assert retrieved.severity == "p1"
    assert retrieved.summary == "Retrieved incorrect fatwa explanation"

    incidents = incident_repo.get_incidents()
    assert len(incidents) == 1
    assert incidents[0].id == incident.id

    session.close()


def test_unit_of_work_commit(sqlite_session_factory: Any) -> None:
    uow = SQLAlchemyUnitOfWork(sqlite_session_factory)

    with uow:
        # Create User
        user = User(
            id=uuid4(),
            email="uow-test@example.com",
            display_name="UoW Test User",
            mfa_enabled=False,
        )
        uow.users.create(user)
        user_id = user.id
        uow.commit()

    # Verify committed outside the block
    session = sqlite_session_factory()
    retrieved = session.get(User, user_id)
    assert retrieved is not None
    assert retrieved.email == "uow-test@example.com"
    session.close()


def test_unit_of_work_rollback_on_failure(sqlite_session_factory: Any) -> None:
    uow = SQLAlchemyUnitOfWork(sqlite_session_factory)

    user_id = uuid4()
    try:
        with uow:
            # Create User
            user = User(
                id=user_id,
                email="uow-test-fail@example.com",
                display_name="UoW Fail",
                mfa_enabled=False,
            )
            uow.users.create(user)
            # Raise exception to trigger rollback
            raise ValueError("Forced error")
    except ValueError:
        pass

    # Verify rolled back (does not exist in DB)
    session = sqlite_session_factory()
    retrieved = session.get(User, user_id)
    assert retrieved is None
    session.close()


def test_unit_of_work_explicit_rollback(sqlite_session_factory: Any) -> None:
    uow = SQLAlchemyUnitOfWork(sqlite_session_factory)

    user_id = uuid4()
    with uow:
        user = User(
            id=user_id,
            email="uow-explicit@example.com",
            display_name="UoW Explicit",
            mfa_enabled=False,
        )
        uow.users.create(user)
        uow.rollback()

    session = sqlite_session_factory()
    retrieved = session.get(User, user_id)
    assert retrieved is None
    session.close()


def test_mockable_interfaces() -> None:
    # Test that UserRepository is mockable
    mock_repo = MagicMock(spec=AbstractUserRepository)
    mock_repo.get_by_email.return_value = User(
        id=uuid4(), email="mocked@example.com", display_name="Mock"
    )

    user = mock_repo.get_by_email("mocked@example.com")
    assert user is not None
    assert user.email == "mocked@example.com"
    mock_repo.get_by_email.assert_called_once_with("mocked@example.com")
