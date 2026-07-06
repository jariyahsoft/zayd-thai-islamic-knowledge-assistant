from datetime import UTC, datetime

from zayd_common.enums import DocumentStatus, PermissionState
from zayd_common.retrievability import can_activate_embedding, is_document_retrievable


def test_is_document_retrievable() -> None:
    now = datetime.now(UTC)
    assert is_document_retrievable(DocumentStatus.PUBLISHED, now) is True
    assert is_document_retrievable(DocumentStatus.PUBLISHED, None) is False
    assert is_document_retrievable(DocumentStatus.SUSPENDED, now) is False
    assert is_document_retrievable(DocumentStatus.DRAFT, now) is False
    assert is_document_retrievable(DocumentStatus.SCHOLAR_APPROVED, now) is False


def test_can_activate_embedding() -> None:
    # All criteria satisfied
    assert (
        can_activate_embedding(
            chunk_published=True,
            document_status=DocumentStatus.PUBLISHED,
            embedding_permission=PermissionState.ALLOWED,
        )
        is True
    )

    # Chunk not published
    assert (
        can_activate_embedding(
            chunk_published=False,
            document_status=DocumentStatus.PUBLISHED,
            embedding_permission=PermissionState.ALLOWED,
        )
        is False
    )

    # Document not published
    assert (
        can_activate_embedding(
            chunk_published=True,
            document_status=DocumentStatus.SCHOLAR_APPROVED,
            embedding_permission=PermissionState.ALLOWED,
        )
        is False
    )

    # Permission not allowed
    assert (
        can_activate_embedding(
            chunk_published=True,
            document_status=DocumentStatus.PUBLISHED,
            embedding_permission=PermissionState.PROHIBITED,
        )
        is False
    )
    assert (
        can_activate_embedding(
            chunk_published=True,
            document_status=DocumentStatus.PUBLISHED,
            embedding_permission=PermissionState.UNKNOWN,
        )
        is False
    )
