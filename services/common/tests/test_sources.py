"""Unit tests for Source service."""

from uuid import uuid4

import pytest
from zayd_common import (
    SourceError,
    SourceSearchQuery,
    SourceService,
    SQLAlchemyUnitOfWork,
    get_sessionmaker,
)


@pytest.fixture
def source_service():
    """Create a source service with an in-memory SQLite database."""
    session_factory = get_sessionmaker("sqlite:///:memory:")
    from zayd_common.database.models import Base

    Base.metadata.create_all(bind=session_factory.kw["bind"])
    uow = SQLAlchemyUnitOfWork(session_factory)
    return SourceService(uow)


@pytest.fixture
def admin_user_id():
    """Create a test admin user ID."""
    return uuid4()


def test_create_source(source_service, admin_user_id):
    """Test source creation."""
    source = source_service.create(
        name="Test Hadith Collection",
        source_type="hadith",
        language="th",
        reliability_level=5,
        owner="Test Publisher",
        website="https://example.com",
        country="TH",
        is_active=True,
        created_by=admin_user_id,
    )

    assert source.name == "Test Hadith Collection"
    assert source.source_type == "hadith"
    assert source.language == "th"
    assert source.reliability_level == 5
    assert source.owner == "Test Publisher"
    assert source.website == "https://example.com"
    assert source.country == "TH"
    assert source.is_active is True
    assert source.created_by == admin_user_id
    assert source.updated_by is None


def test_create_source_name_required(source_service, admin_user_id):
    """Test that source name is required."""
    with pytest.raises(SourceError) as exc_info:
        source_service.create(
            name="   ",
            source_type="hadith",
            language="th",
            reliability_level=5,
            created_by=admin_user_id,
        )
    assert exc_info.value.code == "SOURCE_NAME_REQUIRED"


def test_create_source_invalid_reliability(source_service, admin_user_id):
    """Test that reliability level must be between 1 and 5."""
    with pytest.raises(SourceError) as exc_info:
        source_service.create(
            name="Test Source",
            source_type="hadith",
            language="th",
            reliability_level=10,
            created_by=admin_user_id,
        )
    assert exc_info.value.code == "SOURCE_INVALID_RELIABILITY"

    with pytest.raises(SourceError) as exc_info:
        source_service.create(
            name="Test Source",
            source_type="hadith",
            language="th",
            reliability_level=0,
            created_by=admin_user_id,
        )
    assert exc_info.value.code == "SOURCE_INVALID_RELIABILITY"


def test_get_source_by_id(source_service, admin_user_id):
    """Test retrieving a source by ID."""
    created = source_service.create(
        name="Test Source",
        source_type="hadith",
        language="th",
        reliability_level=4,
        created_by=admin_user_id,
    )

    retrieved = source_service.get_by_id(source_id=created.id)
    assert retrieved.id == created.id
    assert retrieved.name == "Test Source"
    assert retrieved.reliability_level == 4


def test_get_source_not_found(source_service):
    """Test that get_by_id raises error for non-existent source."""
    with pytest.raises(SourceError) as exc_info:
        source_service.get_by_id(source_id=uuid4())
    assert exc_info.value.code == "SOURCE_NOT_FOUND"
    assert exc_info.value.status_code == 404


def test_update_source(source_service, admin_user_id):
    """Test updating a source."""
    created = source_service.create(
        name="Original Name",
        source_type="hadith",
        language="th",
        reliability_level=3,
        created_by=admin_user_id,
    )

    updated = source_service.update(
        source_id=created.id,
        name="Updated Name",
        reliability_level=5,
        updated_by=admin_user_id,
    )

    assert updated.id == created.id
    assert updated.name == "Updated Name"
    assert updated.reliability_level == 5
    assert updated.source_type == "hadith"
    assert updated.language == "th"
    assert updated.updated_by == admin_user_id


def test_update_source_not_found(source_service, admin_user_id):
    """Test that update raises error for non-existent source."""
    with pytest.raises(SourceError) as exc_info:
        source_service.update(
            source_id=uuid4(),
            name="New Name",
            updated_by=admin_user_id,
        )
    assert exc_info.value.code == "SOURCE_NOT_FOUND"


def test_suspend_source(source_service, admin_user_id):
    """Test suspending a source."""
    created = source_service.create(
        name="Active Source",
        source_type="hadith",
        language="th",
        reliability_level=4,
        is_active=True,
        created_by=admin_user_id,
    )

    suspended = source_service.suspend(
        source_id=created.id,
        actor_user_id=admin_user_id,
    )

    assert suspended.id == created.id
    assert suspended.is_active is False
    assert suspended.updated_by == admin_user_id


def test_suspend_source_idempotent(source_service, admin_user_id):
    """Test that suspending an already suspended source is idempotent."""
    created = source_service.create(
        name="Active Source",
        source_type="hadith",
        language="th",
        reliability_level=4,
        is_active=False,
        created_by=admin_user_id,
    )

    suspended = source_service.suspend(
        source_id=created.id,
        actor_user_id=admin_user_id,
    )

    assert suspended.is_active is False


def test_search_sources_empty(source_service):
    """Test search returns empty list when no sources exist."""
    query = SourceSearchQuery()
    sources = source_service.search(query)
    assert sources == []


def test_search_sources_by_name(source_service, admin_user_id):
    """Test searching sources by name."""
    source_service.create(
        name="Sahih Bukhari",
        source_type="hadith",
        language="th",
        reliability_level=5,
        created_by=admin_user_id,
    )
    source_service.create(
        name="Quran Thai Translation",
        source_type="quran",
        language="th",
        reliability_level=5,
        created_by=admin_user_id,
    )

    query = SourceSearchQuery(name="Bukhari")
    sources = source_service.search(query)
    assert len(sources) == 1
    assert sources[0].name == "Sahih Bukhari"


def test_search_sources_by_source_type(source_service, admin_user_id):
    """Test searching sources by source type."""
    source_service.create(
        name="Hadith Source",
        source_type="hadith",
        language="th",
        reliability_level=5,
        created_by=admin_user_id,
    )
    source_service.create(
        name="Fiqh Book",
        source_type="fiqh",
        language="th",
        reliability_level=4,
        created_by=admin_user_id,
    )

    query = SourceSearchQuery(source_type="hadith")
    sources = source_service.search(query)
    assert len(sources) == 1
    assert sources[0].source_type == "hadith"


def test_search_sources_by_language(source_service, admin_user_id):
    """Test searching sources by language."""
    source_service.create(
        name="Thai Source",
        source_type="hadith",
        language="th",
        reliability_level=5,
        created_by=admin_user_id,
    )
    source_service.create(
        name="Arabic Source",
        source_type="hadith",
        language="ar",
        reliability_level=5,
        created_by=admin_user_id,
    )

    query = SourceSearchQuery(language="th")
    sources = source_service.search(query)
    assert len(sources) == 1
    assert sources[0].language == "th"


def test_search_sources_by_active_status(source_service, admin_user_id):
    """Test searching sources by active status."""
    source_service.create(
        name="Active Source",
        source_type="hadith",
        language="th",
        reliability_level=5,
        is_active=True,
        created_by=admin_user_id,
    )
    source_service.create(
        name="Inactive Source",
        source_type="hadith",
        language="th",
        reliability_level=5,
        is_active=False,
        created_by=admin_user_id,
    )

    query = SourceSearchQuery(is_active=True)
    sources = source_service.search(query)
    assert len(sources) == 1
    assert sources[0].is_active is True


def test_search_sources_by_reliability_range(source_service, admin_user_id):
    """Test searching sources by reliability level range."""
    source_service.create(
        name="High Reliability",
        source_type="hadith",
        language="th",
        reliability_level=5,
        created_by=admin_user_id,
    )
    source_service.create(
        name="Medium Reliability",
        source_type="hadith",
        language="th",
        reliability_level=3,
        created_by=admin_user_id,
    )
    source_service.create(
        name="Low Reliability",
        source_type="hadith",
        language="th",
        reliability_level=1,
        created_by=admin_user_id,
    )

    query = SourceSearchQuery(reliability_level_min=4)
    sources = source_service.search(query)
    assert len(sources) == 1
    assert sources[0].reliability_level == 5

    query = SourceSearchQuery(reliability_level_min=2, reliability_level_max=3)
    sources = source_service.search(query)
    assert len(sources) == 1
    assert sources[0].reliability_level == 3


def test_search_sources_pagination(source_service, admin_user_id):
    """Test source search pagination."""
    for i in range(5):
        source_service.create(
            name=f"Source {i}",
            source_type="hadith",
            language="th",
            reliability_level=5,
            created_by=admin_user_id,
        )

    query = SourceSearchQuery(limit=2, offset=0)
    page1 = source_service.search(query)
    assert len(page1) == 2

    query = SourceSearchQuery(limit=2, offset=2)
    page2 = source_service.search(query)
    assert len(page2) == 2

    assert page1[0].id != page2[0].id
