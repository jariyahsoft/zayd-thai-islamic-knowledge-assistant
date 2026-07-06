from datetime import datetime

from zayd_common.enums import DocumentStatus, PermissionState


def is_document_retrievable(status: DocumentStatus, frozen_at: datetime | None) -> bool:
    """Check if a document is eligible for production retrieval.

    Only PUBLISHED documents with a valid freeze timestamp are eligible.
    """
    return status == DocumentStatus.PUBLISHED and frozen_at is not None


def can_activate_embedding(
    chunk_published: bool,
    document_status: DocumentStatus,
    embedding_permission: PermissionState,
) -> bool:
    """Validate if an embedding record can be active for production vector search.

    Active embeddings must reference a published chunk, a published document,
    and have explicit allowed embedding permission.
    """
    return (
        chunk_published
        and document_status == DocumentStatus.PUBLISHED
        and embedding_permission == PermissionState.ALLOWED
    )
