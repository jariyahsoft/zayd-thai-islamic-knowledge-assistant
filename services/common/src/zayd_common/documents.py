"""Document upload and registration service."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Literal
from uuid import UUID, uuid4

from zayd_common.database.models import AuditLog, Document, DocumentVersion, SourceLicense
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.license_policy import LicensePolicyInput, evaluate_license_policy
from zayd_common.storage import (
    DEFAULT_SIGNED_URL_TTL_SECONDS,
    ObjectStorage,
    SignedUrl,
    StorageError,
)

DocumentUploadErrorCode = Literal[
    "DOCUMENT_SOURCE_NOT_FOUND",
    "DOCUMENT_SOURCE_INACTIVE",
    "DOCUMENT_LICENSE_NOT_FOUND",
    "DOCUMENT_LICENSE_SOURCE_MISMATCH",
    "DOCUMENT_LICENSE_INELIGIBLE",
    "DOCUMENT_FILENAME_REQUIRED",
    "DOCUMENT_INVALID_FILENAME",
    "DOCUMENT_UNSUPPORTED_FILE_TYPE",
    "DOCUMENT_INVALID_FILE_PAYLOAD",
    "DOCUMENT_FILE_TOO_LARGE",
    "DOCUMENT_CANONICAL_ID_REQUIRED",
    "DOCUMENT_TITLE_REQUIRED",
    "DOCUMENT_DUPLICATE",
]

DOCUMENT_UPLOAD_POLICY_VERSION = "document-upload-v1"
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
SUPPORTED_FILE_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "text/plain": ".txt",
    "text/markdown": ".md",
    "text/html": ".html",
    "application/json": ".json",
    "text/csv": ".csv",
}


class DocumentUploadError(Exception):
    def __init__(
        self,
        code: DocumentUploadErrorCode,
        message: str,
        *,
        status_code: int = 400,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class DocumentUploadRequest:
    source_id: UUID
    source_license_id: UUID
    canonical_id: str
    document_type: str
    title: str
    language: str
    filename: str
    content_type: str
    file_bytes: bytes
    author: str | None = None
    translator: str | None = None
    publisher: str | None = None
    edition: str | None = None
    madhhab: str = "unknown"


@dataclass(frozen=True)
class DocumentUploadDuplicate:
    document_id: UUID
    document_version_id: UUID
    canonical_id: str
    title: str
    content_hash: str


@dataclass(frozen=True)
class DocumentUploadResult:
    document_id: UUID
    document_version_id: UUID
    content_hash: str
    filename: str
    content_type: str
    byte_size: int
    duplicate: DocumentUploadDuplicate | None
    upload_status: Literal["accepted", "duplicate"]
    original_file_key: str
    download_url: SignedUrl
    policy_version: str


class DocumentUploadService:
    def __init__(self, uow: SQLAlchemyUnitOfWork, storage: ObjectStorage) -> None:
        self.uow = uow
        self.storage = storage

    def register_upload(
        self,
        *,
        data: DocumentUploadRequest,
        actor_user_id: UUID,
        trace_id: str | None = None,
    ) -> DocumentUploadResult:
        normalized = self._normalize_request(data)
        content_hash = hashlib.sha256(normalized.file_bytes).hexdigest()
        file_size = len(normalized.file_bytes)

        with self.uow:
            source = self.uow.sources.get_by_id(normalized.source_id)
            if source is None or source.deleted_at is not None:
                raise DocumentUploadError(
                    "DOCUMENT_SOURCE_NOT_FOUND",
                    "Source not found.",
                    status_code=404,
                )
            if not source.is_active:
                raise DocumentUploadError(
                    "DOCUMENT_SOURCE_INACTIVE",
                    "Source is suspended and cannot accept uploads.",
                    status_code=409,
                )

            license_record = self.uow.sources.get_license_by_id(normalized.source_license_id)
            if license_record is None:
                raise DocumentUploadError(
                    "DOCUMENT_LICENSE_NOT_FOUND",
                    "Source license not found.",
                    status_code=404,
                )
            if license_record.source_id != normalized.source_id:
                raise DocumentUploadError(
                    "DOCUMENT_LICENSE_SOURCE_MISMATCH",
                    "Source license does not belong to the selected source.",
                    status_code=409,
                )

            decision = evaluate_license_policy(
                _policy_input(license_record),
                workflow="ingestion",
            )
            if not decision.workflow_allowed:
                raise DocumentUploadError(
                    "DOCUMENT_LICENSE_INELIGIBLE",
                    f"Ingestion blocked by license policy: {', '.join(decision.reason_codes)}.",
                    status_code=409,
                )

            duplicate = self._find_duplicate(content_hash)
            if duplicate is not None:
                self._audit(
                    action="documents.upload.duplicate",
                    outcome="denied",
                    actor_user_id=actor_user_id,
                    resource_id=duplicate.document_id,
                    reason="duplicate_content_hash",
                    after_summary={
                        "canonical_id": duplicate.canonical_id,
                        "content_hash": duplicate.content_hash,
                        "source_id": str(normalized.source_id),
                    },
                    trace_id=trace_id,
                )
                signed_url = self.storage.create_signed_get_url(
                    key=self._duplicate_object_key(duplicate, normalized.filename),
                    filename=normalized.filename,
                    content_type=normalized.content_type,
                )
                self.uow.commit()
                return DocumentUploadResult(
                    document_id=duplicate.document_id,
                    document_version_id=duplicate.document_version_id,
                    content_hash=duplicate.content_hash,
                    filename=normalized.filename,
                    content_type=normalized.content_type,
                    byte_size=file_size,
                    duplicate=duplicate,
                    upload_status="duplicate",
                    original_file_key=self._duplicate_object_key(duplicate, normalized.filename),
                    download_url=signed_url,
                    policy_version=DOCUMENT_UPLOAD_POLICY_VERSION,
                )

            document = Document(
                id=uuid4(),
                source_id=normalized.source_id,
                source_license_id=normalized.source_license_id,
                canonical_id=normalized.canonical_id,
                document_type=normalized.document_type,
                title=normalized.title,
                author=normalized.author,
                translator=normalized.translator,
                publisher=normalized.publisher,
                edition=normalized.edition,
                language=normalized.language,
                madhhab=normalized.madhhab,
                review_status="draft",
                created_by=actor_user_id,
                updated_by=None,
            )
            self.uow.documents.create(document)

            object_key = self._object_key(document.id, normalized.filename)
            uploaded = False
            try:
                self.storage.put_private_bytes(
                    key=object_key,
                    content=normalized.file_bytes,
                    content_type=normalized.content_type,
                    metadata={
                        "document_id": str(document.id),
                        "canonical_id": normalized.canonical_id,
                        "content_hash": content_hash,
                    },
                )
                uploaded = True
            except StorageError:
                raise
            except Exception as exc:  # pragma: no cover - defensive conversion
                raise StorageError(
                    "STORAGE_UPLOAD_FAILED",
                    "Object storage upload failed.",
                    operation="put",
                ) from exc

            version = DocumentVersion(
                id=uuid4(),
                document_id=document.id,
                version_number=1,
                status="uploaded",
                content_hash=content_hash,
                original_file_key=object_key,
                extracted_text=None,
                metadata_json={
                    "filename": normalized.filename,
                    "content_type": normalized.content_type,
                    "byte_size": file_size,
                    "policy_version": DOCUMENT_UPLOAD_POLICY_VERSION,
                    "source_license_id": str(normalized.source_license_id),
                },
                created_by=actor_user_id,
            )
            self.uow.documents.add_version(version)

            self._audit(
                action="documents.upload.register",
                outcome="success",
                actor_user_id=actor_user_id,
                resource_id=document.id,
                after_summary={
                    "document_id": str(document.id),
                    "document_version_id": str(version.id),
                    "canonical_id": document.canonical_id,
                    "title": document.title,
                    "content_hash": content_hash,
                    "content_type": normalized.content_type,
                    "byte_size": file_size,
                    "source_id": str(document.source_id),
                    "source_license_id": str(document.source_license_id),
                    "policy_version": DOCUMENT_UPLOAD_POLICY_VERSION,
                },
                trace_id=trace_id,
            )
            try:
                self.uow.commit()
            except Exception:
                if uploaded:
                    self.storage.delete_object(key=object_key)
                raise
            signed_url = self.storage.create_signed_get_url(
                key=object_key,
                filename=normalized.filename,
                content_type=normalized.content_type,
                expires_in_seconds=DEFAULT_SIGNED_URL_TTL_SECONDS,
            )
            return DocumentUploadResult(
                document_id=document.id,
                document_version_id=version.id,
                content_hash=content_hash,
                filename=normalized.filename,
                content_type=normalized.content_type,
                byte_size=file_size,
                duplicate=None,
                upload_status="accepted",
                original_file_key=version.original_file_key or "",
                download_url=signed_url,
                policy_version=DOCUMENT_UPLOAD_POLICY_VERSION,
            )

    def _normalize_request(self, data: DocumentUploadRequest) -> DocumentUploadRequest:
        filename = data.filename.strip()
        if not filename:
            raise DocumentUploadError(
                "DOCUMENT_FILENAME_REQUIRED",
                "Filename is required.",
                status_code=400,
            )
        if "/" in filename or "\\" in filename or filename in {".", ".."}:
            raise DocumentUploadError(
                "DOCUMENT_INVALID_FILENAME",
                "Filename contains an invalid path segment.",
                status_code=400,
            )
        content_type = data.content_type.strip().lower()
        expected_extension = SUPPORTED_FILE_TYPES.get(content_type)
        if expected_extension is None or not filename.lower().endswith(expected_extension):
            raise DocumentUploadError(
                "DOCUMENT_UNSUPPORTED_FILE_TYPE",
                "File type is not supported.",
                status_code=400,
            )
        if len(data.file_bytes) > MAX_UPLOAD_BYTES:
            raise DocumentUploadError(
                "DOCUMENT_FILE_TOO_LARGE",
                "File exceeds the maximum allowed size.",
                status_code=413,
            )
        canonical_id = data.canonical_id.strip()
        if not canonical_id:
            raise DocumentUploadError(
                "DOCUMENT_CANONICAL_ID_REQUIRED",
                "Canonical ID is required.",
                status_code=400,
            )
        title = data.title.strip()
        if not title:
            raise DocumentUploadError(
                "DOCUMENT_TITLE_REQUIRED",
                "Document title is required.",
                status_code=400,
            )
        return DocumentUploadRequest(
            source_id=data.source_id,
            source_license_id=data.source_license_id,
            canonical_id=canonical_id,
            document_type=data.document_type.strip(),
            title=title,
            language=data.language.strip(),
            filename=filename,
            content_type=content_type,
            file_bytes=data.file_bytes,
            author=data.author.strip() if data.author else None,
            translator=data.translator.strip() if data.translator else None,
            publisher=data.publisher.strip() if data.publisher else None,
            edition=data.edition.strip() if data.edition else None,
            madhhab=data.madhhab.strip() if data.madhhab else "unknown",
        )

    def _object_key(self, document_id: UUID, filename: str) -> str:
        return f"uploads/quarantine/{document_id}/{filename}"

    def _duplicate_object_key(self, duplicate: DocumentUploadDuplicate, filename: str) -> str:
        return f"uploads/quarantine/{duplicate.document_version_id}/{filename}"

    def _find_duplicate(self, content_hash: str) -> DocumentUploadDuplicate | None:
        for document in self.uow.documents.get_documents():
            versions = self.uow.documents.get_versions_by_document(document.id)
            for version in versions:
                if version.content_hash == content_hash:
                    return DocumentUploadDuplicate(
                        document_id=document.id,
                        document_version_id=version.id,
                        canonical_id=document.canonical_id,
                        title=document.title,
                        content_hash=version.content_hash,
                    )
        return None

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
                resource_type="document",
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


def _policy_input(license_record: SourceLicense) -> LicensePolicyInput:
    return LicensePolicyInput(
        license_id=license_record.id,
        source_id=license_record.source_id,
        license_version=license_record.license_version,
        status=license_record.status,
        storage_permission=license_record.storage_permission,
        embedding_permission=license_record.embedding_permission,
        commercial_use=license_record.commercial_use,
        redistribution=license_record.redistribution,
        attribution_required=license_record.attribution_required,
        attribution_template=license_record.attribution_template,
        valid_from=license_record.valid_from,
        valid_until=license_record.valid_until,
    )
