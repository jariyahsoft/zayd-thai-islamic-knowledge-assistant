"""Unit tests for source license registry behavior."""

from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from zayd_common.database.models import AuditLog, Base
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.licenses import LicenseCreate, LicenseError, LicenseService
from zayd_common.sources import SourceService


@pytest.fixture
def services() -> tuple[SourceService, LicenseService, sessionmaker]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    return (
        SourceService(SQLAlchemyUnitOfWork(session_factory)),
        LicenseService(SQLAlchemyUnitOfWork(session_factory)),
        session_factory,
    )


@pytest.fixture
def actor_user_id():
    return uuid4()


def _source(source_service: SourceService, actor_user_id):
    return source_service.create(
        name="Thai Islamic Library",
        source_type="fiqh",
        language="th",
        reliability_level=4,
        created_by=actor_user_id,
    )


def _license_data(**overrides: object) -> LicenseCreate:
    values = {
        "license_name": "Publisher Agreement",
        "license_version": "2026-01",
        "status": "persistent_redistributable",
        "storage_permission": "allowed",
        "embedding_permission": "allowed",
        "commercial_use": "conditional",
        "redistribution": "allowed",
        "attribution_required": True,
        "attribution_template": "Courtesy of the publisher.",
        "permission_document_key": "private/licenses/publisher-agreement.pdf",
        "valid_from": date(2026, 1, 1),
        "valid_until": date(2027, 1, 1),
        "notes": "Approved for Zayd publication.",
    }
    values.update(overrides)
    return LicenseCreate(**values)


def test_create_get_and_list_license(
    services: tuple[SourceService, LicenseService, sessionmaker],
    actor_user_id,
) -> None:
    source_service, license_service, _session_factory = services
    source = _source(source_service, actor_user_id)

    created = license_service.create(
        source_id=source.id,
        data=_license_data(),
        created_by=actor_user_id,
        trace_id="trace-license-create",
    )

    assert created.source_id == source.id
    assert created.status == "persistent_redistributable"
    assert created.storage_permission == "allowed"
    assert created.permission_document_key == "private/licenses/publisher-agreement.pdf"
    assert license_service.get_by_id(license_id=created.id).id == created.id
    assert [item.id for item in license_service.list_by_source(source_id=source.id)] == [created.id]


def test_unknown_prohibited_and_expired_license_statuses_block_publication(
    services: tuple[SourceService, LicenseService, sessionmaker],
    actor_user_id,
) -> None:
    source_service, license_service, _session_factory = services
    source = _source(source_service, actor_user_id)

    for status in ("unknown", "prohibited", "expired"):
        license_record = license_service.create(
            source_id=source.id,
            data=_license_data(
                license_name=f"Agreement {status}",
                status=status,
                valid_from=None,
                valid_until=None,
            ),
            created_by=actor_user_id,
        )

        authorization = license_service.check_publication_authorization(
            license_id=license_record.id,
            actor_user_id=actor_user_id,
            today=date(2026, 7, 1),
        )

        assert authorization.authorized is False
        assert status in authorization.reason


def test_date_expiry_blocks_publication(
    services: tuple[SourceService, LicenseService, sessionmaker],
    actor_user_id,
) -> None:
    source_service, license_service, _session_factory = services
    source = _source(source_service, actor_user_id)
    license_record = license_service.create(
        source_id=source.id,
        data=_license_data(valid_until=date(2026, 1, 31)),
        created_by=actor_user_id,
    )

    authorization = license_service.check_publication_authorization(
        license_id=license_record.id,
        actor_user_id=actor_user_id,
        today=date(2026, 2, 1),
    )

    assert authorization.authorized is False
    assert authorization.reason == "License is expired."
    with pytest.raises(LicenseError) as exc_info:
        license_service.assert_publication_authorized(
            license_id=license_record.id,
            actor_user_id=actor_user_id,
            today=date(2026, 2, 1),
        )
    assert exc_info.value.code == "LICENSE_PUBLICATION_BLOCKED"


def test_replacement_creates_new_row_without_overwriting_history(
    services: tuple[SourceService, LicenseService, sessionmaker],
    actor_user_id,
) -> None:
    source_service, license_service, _session_factory = services
    source = _source(source_service, actor_user_id)
    original = license_service.create(
        source_id=source.id,
        data=_license_data(license_name="Original Agreement", valid_until=date(2026, 7, 1)),
        created_by=actor_user_id,
    )

    replacement = license_service.replace(
        license_id=original.id,
        data=_license_data(
            license_name="Replacement Agreement",
            license_version="2026-07",
            valid_from=date(2026, 7, 2),
            valid_until=date(2028, 7, 1),
        ),
        actor_user_id=actor_user_id,
    )

    assert replacement.id != original.id
    assert replacement.source_id == original.source_id
    assert replacement.license_name == "Replacement Agreement"
    historical = license_service.get_by_id(license_id=original.id)
    assert historical.license_name == "Original Agreement"
    assert {item.id for item in license_service.list_by_source(source_id=source.id)} == {
        original.id,
        replacement.id,
    }


def test_permission_document_access_is_audited(
    services: tuple[SourceService, LicenseService, sessionmaker],
    actor_user_id,
) -> None:
    source_service, license_service, session_factory = services
    source = _source(source_service, actor_user_id)
    license_record = license_service.create(
        source_id=source.id,
        data=_license_data(),
        created_by=actor_user_id,
    )

    access = license_service.get_permission_document(
        license_id=license_record.id,
        actor_user_id=actor_user_id,
        trace_id="trace-permission-document",
    )

    assert access.permission_document_key == "private/licenses/publisher-agreement.pdf"
    assert access.audited is True
    with session_factory() as session:
        logs = session.execute(select(AuditLog)).scalars().all()
    assert any(log.action == "licenses.permission_document.access" for log in logs)
    assert any(
        log.action == "licenses.permission_document.access"
        and log.after_summary
        == {
            "source_id": str(source.id),
            "access": "metadata_only",
            "permission_document_key_present": True,
        }
        for log in logs
    )


def test_missing_permission_document_access_fails_closed_and_is_audited(
    services: tuple[SourceService, LicenseService, sessionmaker],
    actor_user_id,
) -> None:
    source_service, license_service, session_factory = services
    source = _source(source_service, actor_user_id)
    license_record = license_service.create(
        source_id=source.id,
        data=_license_data(permission_document_key=None),
        created_by=actor_user_id,
    )

    with pytest.raises(LicenseError) as exc_info:
        license_service.get_permission_document(
            license_id=license_record.id,
            actor_user_id=actor_user_id,
        )

    assert exc_info.value.code == "LICENSE_PERMISSION_DOCUMENT_REQUIRED"
    with session_factory() as session:
        logs = session.execute(select(AuditLog)).scalars().all()
    assert any(
        log.action == "licenses.permission_document.access" and log.outcome == "denied"
        for log in logs
    )
