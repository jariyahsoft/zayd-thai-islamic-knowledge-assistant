import { DocumentStatus, PermissionState } from "./enums.js";

/**
 * Check if a document is eligible for production retrieval.
 * Only PUBLISHED documents with a valid freeze timestamp are eligible.
 */
export function isDocumentRetrievable(
  status: DocumentStatus,
  frozenAt: Date | string | null
): boolean {
  return status === DocumentStatus.PUBLISHED && frozenAt !== null;
}

/**
 * Validate if an embedding record can be active for production vector search.
 * Active embeddings require a published chunk, a published document,
 * and explicit allowed embedding permission.
 */
export function canActivateEmbedding(
  chunkPublished: boolean,
  documentStatus: DocumentStatus,
  embeddingPermission: PermissionState
): boolean {
  return (
    chunkPublished &&
    documentStatus === DocumentStatus.PUBLISHED &&
    embeddingPermission === PermissionState.ALLOWED
  );
}
