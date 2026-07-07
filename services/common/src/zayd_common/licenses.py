"""License registry service for source usage permissions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from sqlalchemy import select

from zayd_common.database.models import AuditLog, SourceLicense
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

LicenseStatus = Literal[
    "unknown",
    "review_required",
    "ephemeral_cache_only",
    "persistent_private",
    "persistent_redistributable",
    "prohibited",
    "expired",
]
LicensePermissionState = Literal["unknown", "allowed", "prohibited", "conditional"]
LicenseErrorCode = Literal[
    "LICENSE_NOT_FOUND",
    "LICENSE_SOURCE_NOT_FOUND",
    "LICENSE_NAME_REQUIRED",
    "LICENSE_INVALID_STATUS",
    "LICENSE_INVALID_PERMISSION",
    "LICENSE_INVALID_DATE_RANGE",
    "LICENSE_PERMISSION_DOCUMENT_REQUIRED",
    "LICENSE_PUBLICATION_BLOCKED",
]

LICENSE_REGISTRY_POLICY_VERSION = "license-registry-v1"
PUBLICATION_ALLOWED_STATUSES = {"persistent_private", "persistent_redistributable"}
BLOCKING_STATUSES = {"unknown", "prohibited", "expired"}
VALID_LICENSE_STATUSES = {
    "unknown",
    "review_required",
    "ephemeral_cache_only",
    "persistent_private",
    "persistent_redistributable",
    "prohibited",
    "expired",
}
VALID_PERMISSION_STATES = {"unknown", "allowed", "prohibited", "conditional"}
ALLOWING_PERMISSION_STATES = {"allowed", "conditional"}


class LicenseError(Exception):
    def __init__(self, code: LicenseErrorCode, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class LicensePublic:
    id: UUID
    source_id: UUID
    license_name: str
    license_version: str | None
    status: str
    storage_permission: str
    embedding_permission: str
    commercial_use: str
    redistribution: str
    attribution_required: bool
    attribution_template: str | None
    permission_document_key: str | None
    valid_from: date | None
    valid_until: date | None
    notes: str | None
    created_by: UUID
    updated_by: UUID | None
    created_at: datetime
    updated_at: datetime
    row_version: int


@dataclass(frozen=True)
class LicenseCreate:
    license_name: str
    status: str
    storage_permission: str
    embedding_permission: str
    commercial_use: str
    redistribution: str
    license_version: str | None = None
    attribution_required: bool = True
    attribution_template: str | None = None
    permission_document_key: str | None = None
    valid_from: date | None = None
    valid_until: date | None = None
    notes: str | None = None


@dataclass(frozen=True)
class PermissionDocumentAccess:
    license_id: UUID
    permission_document_key: str
    access: Literal["metadata_only"]
    audited: bool


@dataclass(frozen=True)
class PublicationAuthorization:
    license_id: UUID
    authorized: bool
    policy_version: str
    reason: str


class LicenseService:
    def __init__(self, uow: SQLAlchemyUnitOfWork) -> None:
        self.uow = uow

    def create(
        self,
        *,
        source_id: UUID,
        data: LicenseCreate,
        created_by: UUID,
        trace_id: str | None = None,
    ) -> LicensePublic:
        normalized = self._normalize_create(data)
        with self.uow:
            source = self.uow.sources.get_by_id(source_id)
            if source is None or source.deleted_at is not None:
                raise LicenseError(
                    "LICENSE_SOURCE_NOT_FOUND",
                    "Source not found.",
                    status_code=404,
                )

            license_record = SourceLicense(
                id=uuid4(),
                source_id=source_id,
                license_name=normalized.license_name,
                license_version=normalized.license_version,
                status=normalized.status,
                storage_permission=normalized.storage_permission,
                embedding_permission=normalized.embedding_permission,
                commercial_use=normalized.commercial_use,
                redistribution=normalized.redistribution,
                attribution_required=normalized.attribution_required,
                attribution_template=normalized.attribution_template,
                permission_document_key=normalized.permission_document_key,
                valid_from=normalized.valid_from,
                valid_until=normalized.valid_until,
                notes=normalized.notes,
                created_by=created_by,
                updated_by=None,
            )
            self.uow.sources.add_license(license_record)
            self._audit(
                action="licenses.create",
                outcome="success",
                actor_user_id=created_by,
                resource_id=license_record.id,
                after_summary=self._audit_summary(license_record),
                trace_id=trace_id,
            )
            self.uow.commit()
            return _public_license(license_record)

    def get_by_id(self, *, license_id: UUID) -> LicensePublic:
        with self.uow:
            license_record = self.uow.sources.get_license_by_id(license_id)
            if license_record is None:
                raise LicenseError("LICENSE_NOT_FOUND", "License not found.", status_code=404)
            self.uow.commit()
            return _public_license(license_record)

    def list_by_source(self, *, source_id: UUID) -> list[LicensePublic]:
        with self.uow:
            source = self.uow.sources.get_by_id(source_id)
            if source is None or source.deleted_at is not None:
                raise LicenseError(
                    "LICENSE_SOURCE_NOT_FOUND",
                    "Source not found.",
                    status_code=404,
                )
            session = self._session()
            statement = (
                select(SourceLicense)
                .where(SourceLicense.source_id == source_id)
                .order_by(SourceLicense.created_at.desc(), SourceLicense.id.desc())
            )
            records = list(session.execute(statement).scalars().all())
            self.uow.commit()
            return [_public_license(record) for record in records]

    def replace(
        self,
        *,
        license_id: UUID,
        data: LicenseCreate,
        actor_user_id: UUID,
        trace_id: str | None = None,
    ) -> LicensePublic:
        normalized = self._normalize_create(data)
        with self.uow:
            previous = self.uow.sources.get_license_by_id(license_id)
            if previous is None:
                raise LicenseError("LICENSE_NOT_FOUND", "License not found.", status_code=404)

            replacement = SourceLicense(
                id=uuid4(),
                source_id=previous.source_id,
                license_name=normalized.license_name,
                license_version=normalized.license_version,
                status=normalized.status,
                storage_permission=normalized.storage_permission,
                embedding_permission=normalized.embedding_permission,
                commercial_use=normalized.commercial_use,
                redistribution=normalized.redistribution,
                attribution_required=normalized.attribution_required,
                attribution_template=normalized.attribution_template,
                permission_document_key=normalized.permission_document_key,
                valid_from=normalized.valid_from,
                valid_until=normalized.valid_until,
                notes=normalized.notes,
                created_by=actor_user_id,
                updated_by=None,
            )
            self.uow.sources.add_license(replacement)
            self._audit(
                action="licenses.replace",
                outcome="success",
                actor_user_id=actor_user_id,
                resource_id=replacement.id,
                before_summary=self._audit_summary(previous),
                after_summary={
                    **self._audit_summary(replacement),
                    "replaces_license_id": str(previous.id),
                },
                trace_id=trace_id,
            )
            self.uow.commit()
            return _public_license(replacement)

    def get_permission_document(
        self,
        *,
        license_id: UUID,
        actor_user_id: UUID,
        trace_id: str | None = None,
    ) -> PermissionDocumentAccess:
        with self.uow:
            license_record = self.uow.sources.get_license_by_id(license_id)
            if license_record is None:
                raise LicenseError("LICENSE_NOT_FOUND", "License not found.", status_code=404)
            if not license_record.permission_document_key:
                self._audit(
                    action="licenses.permission_document.access",
                    outcome="denied",
                    actor_user_id=actor_user_id,
                    resource_id=license_record.id,
                    reason="permission document missing",
                    trace_id=trace_id,
                )
                self.uow.commit()
                raise LicenseError(
                    "LICENSE_PERMISSION_DOCUMENT_REQUIRED",
                    "Permission document is not registered.",
                    status_code=409,
                )
            self._audit(
                action="licenses.permission_document.access",
                outcome="success",
                actor_user_id=actor_user_id,
                resource_id=license_record.id,
                after_summary={
                    "source_id": str(license_record.source_id),
                    "access": "metadata_only",
                    "permission_document_key_present": True,
                },
                trace_id=trace_id,
            )
            self.uow.commit()
            return PermissionDocumentAccess(
                license_id=license_record.id,
                permission_document_key=license_record.permission_document_key,
                access="metadata_only",
                audited=True,
            )

    def check_publication_authorization(
        self,
        *,
        license_id: UUID,
        actor_user_id: UUID | None = None,
        trace_id: str | None = None,
        today: date | None = None,
    ) -> PublicationAuthorization:
        evaluation_date = today or datetime.now(UTC).date()
        with self.uow:
            license_record = self.uow.sources.get_license_by_id(license_id)
            if license_record is None:
                raise LicenseError("LICENSE_NOT_FOUND", "License not found.", status_code=404)
            authorized, reason = self._evaluate_publication(license_record, evaluation_date)
            self._audit(
                action="licenses.publication_authorization.check",
                outcome="success" if authorized else "denied",
                actor_user_id=actor_user_id,
                resource_id=license_record.id,
                reason=reason,
                after_summary={
                    "authorized": authorized,
                    "policy_version": LICENSE_REGISTRY_POLICY_VERSION,
                    "status": license_record.status,
                    "storage_permission": license_record.storage_permission,
                    "embedding_permission": license_record.embedding_permission,
                    "redistribution": license_record.redistribution,
                    "evaluation_date": evaluation_date.isoformat(),
                },
                trace_id=trace_id,
            )
            self.uow.commit()
            return PublicationAuthorization(
                license_id=license_record.id,
                authorized=authorized,
                policy_version=LICENSE_REGISTRY_POLICY_VERSION,
                reason=reason,
            )

    def assert_publication_authorized(
        self,
        *,
        license_id: UUID,
        actor_user_id: UUID | None = None,
        trace_id: str | None = None,
        today: date | None = None,
    ) -> PublicationAuthorization:
        authorization = self.check_publication_authorization(
            license_id=license_id,
            actor_user_id=actor_user_id,
            trace_id=trace_id,
            today=today,
        )
        if not authorization.authorized:
            raise LicenseError(
                "LICENSE_PUBLICATION_BLOCKED",
                authorization.reason,
                status_code=409,
            )
        return authorization

    def _normalize_create(self, data: LicenseCreate) -> LicenseCreate:
        license_name = data.license_name.strip()
        if not license_name:
            raise LicenseError(
                "LICENSE_NAME_REQUIRED",
                "License name is required.",
                status_code=400,
            )

        status = data.status.strip().lower()
        if status not in VALID_LICENSE_STATUSES:
            raise LicenseError(
                "LICENSE_INVALID_STATUS",
                "License status is not supported.",
                status_code=400,
            )

        storage_permission = self._normalize_permission(data.storage_permission)
        embedding_permission = self._normalize_permission(data.embedding_permission)
        commercial_use = self._normalize_permission(data.commercial_use)
        redistribution = self._normalize_permission(data.redistribution)
        if data.valid_from is not None and data.valid_until is not None:
            if data.valid_until < data.valid_from:
                raise LicenseError(
                    "LICENSE_INVALID_DATE_RANGE",
                    "License valid_until must be on or after valid_from.",
                    status_code=400,
                )

        return LicenseCreate(
            license_name=license_name,
            license_version=data.license_version.strip() if data.license_version else None,
            status=status,
            storage_permission=storage_permission,
            embedding_permission=embedding_permission,
            commercial_use=commercial_use,
            redistribution=redistribution,
            attribution_required=data.attribution_required,
            attribution_template=data.attribution_template.strip()
            if data.attribution_template
            else None,
            permission_document_key=data.permission_document_key.strip()
            if data.permission_document_key
            else None,
            valid_from=data.valid_from,
            valid_until=data.valid_until,
            notes=data.notes.strip() if data.notes else None,
        )

    def _normalize_permission(self, value: str) -> str:
        permission = value.strip().lower()
        if permission not in VALID_PERMISSION_STATES:
            raise LicenseError(
                "LICENSE_INVALID_PERMISSION",
                "License permission value is not supported.",
                status_code=400,
            )
        return permission

    def _evaluate_publication(
        self,
        license_record: SourceLicense,
        evaluation_date: date,
    ) -> tuple[bool, str]:
        if license_record.status in BLOCKING_STATUSES:
            return False, f"License status {license_record.status} blocks publication."
        if license_record.valid_until is not None and license_record.valid_until < evaluation_date:
            return False, "License is expired."
        if license_record.status not in PUBLICATION_ALLOWED_STATUSES:
            return False, f"License status {license_record.status} does not authorize publication."
        if license_record.storage_permission not in ALLOWING_PERMISSION_STATES:
            return False, "Storage permission does not authorize publication."
        if license_record.embedding_permission not in ALLOWING_PERMISSION_STATES:
            return False, "Embedding permission does not authorize publication."
        if license_record.status == "persistent_redistributable":
            if license_record.redistribution not in ALLOWING_PERMISSION_STATES:
                return False, "Redistribution permission does not authorize publication."
        return True, "License authorizes publication under policy."

    def _audit_summary(self, license_record: SourceLicense) -> dict[str, Any]:
        return {
            "source_id": str(license_record.source_id),
            "license_name": license_record.license_name,
            "license_version": license_record.license_version,
            "status": license_record.status,
            "storage_permission": license_record.storage_permission,
            "embedding_permission": license_record.embedding_permission,
            "commercial_use": license_record.commercial_use,
            "redistribution": license_record.redistribution,
            "valid_from": license_record.valid_from.isoformat()
            if license_record.valid_from is not None
            else None,
            "valid_until": license_record.valid_until.isoformat()
            if license_record.valid_until is not None
            else None,
            "permission_document_key_present": bool(license_record.permission_document_key),
        }

    def _audit(
        self,
        *,
        action: str,
        outcome: str,
        actor_user_id: UUID | None = None,
        resource_id: UUID | None = None,
        reason: str | None = None,
        before_summary: dict[str, Any] | None = None,
        after_summary: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> None:
        self._session().add(
            AuditLog(
                id=uuid4(),
                actor_user_id=actor_user_id,
                action=action,
                resource_type="license",
                resource_id=resource_id,
                outcome=outcome,
                reason=reason,
                request_id=trace_id,
                trace_id=trace_id,
                before_summary=before_summary,
                after_summary=after_summary,
                source_context={},
            )
        )

    def _session(self) -> Any:
        if self.uow.session is None:
            raise RuntimeError("Database session not initialized in UoW.")
        return self.uow.session


def _public_license(license_record: SourceLicense) -> LicensePublic:
    return LicensePublic(
        id=license_record.id,
        source_id=license_record.source_id,
        license_name=license_record.license_name,
        license_version=license_record.license_version,
        status=license_record.status,
        storage_permission=license_record.storage_permission,
        embedding_permission=license_record.embedding_permission,
        commercial_use=license_record.commercial_use,
        redistribution=license_record.redistribution,
        attribution_required=license_record.attribution_required,
        attribution_template=license_record.attribution_template,
        permission_document_key=license_record.permission_document_key,
        valid_from=license_record.valid_from,
        valid_until=license_record.valid_until,
        notes=license_record.notes,
        created_by=license_record.created_by,
        updated_by=license_record.updated_by,
        created_at=license_record.created_at,
        updated_at=license_record.updated_at,
        row_version=license_record.row_version,
    )
