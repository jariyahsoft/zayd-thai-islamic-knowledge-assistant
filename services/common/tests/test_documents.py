"""Unit tests for document upload registration."""

from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from zayd_common.database.models import AuditLog, Base
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.documents import (
    DocumentUploadError,
    DocumentUploadRequest,
    DocumentUploadService,
)
from zayd_common.licenses import LicenseCreate, LicenseService
from zayd_common.sources import SourceService


@pytest.fixture
def services() -> tuple[SourceService, LicenseService, DocumentUploadService, sessionmaker]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    return (
        SourceService(SQLAlchemyUnitOfWork(session_factory)),
        LicenseService(SQLAlchemyUnitOfWork(session_factory)),
        DocumentUploadService(SQLAlchemyUnitOfWork(session_factory)),
        session_factory,
    )


@pytest.fixture
def actor_user_id():
    return uuid4()


def _source_and_license(
    source_service: SourceService,
    license_service: LicenseService,
    actor_user_id,
    *,
    source_active: bool = True,
    license_status: str = "persistent_private",
    storage_permission: str = "allowed",
    embedding_permission: str = "allowed",
) -> tuple[object, object]:
    source = source_service.create(
        name="Upload Source",
        source_type="book",
        language="th",
        reliability_level=4,
        is_active=source_active,
        created_by=actor_user_id,
    )
    license_record = license_service.create(
        source_id=source.id,
        data=LicenseCreate(
            license_name="Upload Agreement",
            license_version="2026-01",
            status=license_status,
            storage_permission=storage_permission,
            embedding_permission=embedding_permission,
            commercial_use="conditional",
            redistribution="prohibited",
            attribution_required=True,
            attribution_template="Required attribution.",
            permission_document_key="private/licenses/upload.pdf",
            valid_from=None,
            valid_until=None,
            notes=None,
        ),
        created_by=actor_user_id,
    )
    return source, license_record


def _request(source_id, source_license_id, **overrides: object) -> DocumentUploadRequest:
    values = {
        "source_id": source_id,
        "source_license_id": source_license_id,
        "canonical_id": "doc-001",
        "document_type": "book",
        "title": "Test Upload",
        "language": "th",
        "filename": "test.pdf",
        "content_type": "application/pdf",
        "file_bytes": b"demo content",
        "author": "Author",
        "translator": None,
        "publisher": None,
        "edition": None,
        "madhhab": "unknown",
    }
    values.update(overrides)
    return DocumentUploadRequest(**values)


def test_register_document_upload_success(
    services: tuple[SourceService, LicenseService, DocumentUploadService, sessionmaker],
    actor_user_id,
) -> None:
    source_service, license_service, upload_service, session_factory = services
    source, license_record = _source_and_license(source_service, license_service, actor_user_id)

    result = upload_service.register_upload(
        data=_request(source.id, license_record.id),
        actor_user_id=actor_user_id,
        trace_id="trace-document-upload",
    )

    assert result.upload_status == "accepted"
    assert result.byte_size == len(b"demo content")
    assert result.duplicate is None
    with session_factory() as session:
        logs = session.execute(select(AuditLog)).scalars().all()
    assert any(log.action == "documents.upload.register" for log in logs)


def test_unsupported_file_type_is_rejected(
    services: tuple[SourceService, LicenseService, DocumentUploadService, sessionmaker],
    actor_user_id,
) -> None:
    source_service, license_service, upload_service, _session_factory = services
    source, license_record = _source_and_license(source_service, license_service, actor_user_id)

    with pytest.raises(DocumentUploadError) as exc_info:
        upload_service.register_upload(
            data=_request(
                source.id,
                license_record.id,
                filename="test.exe",
                content_type="application/octet-stream",
            ),
            actor_user_id=actor_user_id,
        )
    assert exc_info.value.code == "DOCUMENT_UNSUPPORTED_FILE_TYPE"


def test_mismatched_filename_extension_is_rejected(
    services: tuple[SourceService, LicenseService, DocumentUploadService, sessionmaker],
    actor_user_id,
) -> None:
    source_service, license_service, upload_service, _session_factory = services
    source, license_record = _source_and_license(source_service, license_service, actor_user_id)

    with pytest.raises(DocumentUploadError) as exc_info:
        upload_service.register_upload(
            data=_request(
                source.id,
                license_record.id,
                filename="test.txt",
                content_type="application/pdf",
            ),
            actor_user_id=actor_user_id,
        )
    assert exc_info.value.code == "DOCUMENT_UNSUPPORTED_FILE_TYPE"


def test_duplicate_detection_returns_safe_result(
    services: tuple[SourceService, LicenseService, DocumentUploadService, sessionmaker],
    actor_user_id,
) -> None:
    source_service, license_service, upload_service, session_factory = services
    source, license_record = _source_and_license(source_service, license_service, actor_user_id)

    first = upload_service.register_upload(
        data=_request(source.id, license_record.id),
        actor_user_id=actor_user_id,
    )
    second = upload_service.register_upload(
        data=_request(
            source.id,
            license_record.id,
            canonical_id="doc-002",
            title="Duplicate Upload",
            filename="duplicate.pdf",
        ),
        actor_user_id=actor_user_id,
    )

    assert first.upload_status == "accepted"
    assert second.upload_status == "duplicate"
    assert second.duplicate is not None
    assert second.duplicate.document_id == first.document_id
    with session_factory() as session:
        logs = session.execute(select(AuditLog)).scalars().all()
    assert any(log.action == "documents.upload.duplicate" for log in logs)


def test_upload_rejected_for_inactive_source(
    services: tuple[SourceService, LicenseService, DocumentUploadService, sessionmaker],
    actor_user_id,
) -> None:
    source_service, license_service, upload_service, _session_factory = services
    source, license_record = _source_and_license(
        source_service,
        license_service,
        actor_user_id,
        source_active=False,
    )

    with pytest.raises(DocumentUploadError) as exc_info:
        upload_service.register_upload(
            data=_request(source.id, license_record.id),
            actor_user_id=actor_user_id,
        )
    assert exc_info.value.code == "DOCUMENT_SOURCE_INACTIVE"


def test_upload_rejected_for_ineligible_license(
    services: tuple[SourceService, LicenseService, DocumentUploadService, sessionmaker],
    actor_user_id,
) -> None:
    source_service, license_service, upload_service, _session_factory = services
    source, license_record = _source_and_license(
        source_service,
        license_service,
        actor_user_id,
        license_status="ephemeral_cache_only",
        storage_permission="prohibited",
        embedding_permission="prohibited",
    )

    with pytest.raises(DocumentUploadError) as exc_info:
        upload_service.register_upload(
            data=_request(source.id, license_record.id),
            actor_user_id=actor_user_id,
        )
    assert exc_info.value.code == "DOCUMENT_LICENSE_INELIGIBLE"


def test_oversized_file_is_rejected(
    services: tuple[SourceService, LicenseService, DocumentUploadService, sessionmaker],
    actor_user_id,
) -> None:
    source_service, license_service, upload_service, _session_factory = services
    source, license_record = _source_and_license(source_service, license_service, actor_user_id)

    with pytest.raises(DocumentUploadError) as exc_info:
        upload_service.register_upload(
            data=_request(
                source.id,
                license_record.id,
                file_bytes=b"x" * ((25 * 1024 * 1024) + 1),
            ),
            actor_user_id=actor_user_id,
        )
    assert exc_info.value.code == "DOCUMENT_FILE_TOO_LARGE"
