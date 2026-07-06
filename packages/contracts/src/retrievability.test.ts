import { describe, expect, it } from "vitest";

import { DocumentStatus, PermissionState } from "./enums.js";
import {
  canActivateEmbedding,
  isDocumentRetrievable,
} from "./retrievability.js";

describe("TypeScript Retrievability", () => {
  it("determines if a document is retrievable", () => {
    const now = new Date();
    expect(isDocumentRetrievable(DocumentStatus.PUBLISHED, now)).toBe(true);
    expect(isDocumentRetrievable(DocumentStatus.PUBLISHED, null)).toBe(false);
    expect(
        isDocumentRetrievable(DocumentStatus.SCHOLAR_APPROVED, now)
    ).toBe(false);
    expect(isDocumentRetrievable(DocumentStatus.SUSPENDED, now)).toBe(false);
  });

  it("determines if an embedding can be active", () => {
    // All criteria satisfied
    expect(
      canActivateEmbedding(
        true,
        DocumentStatus.PUBLISHED,
        PermissionState.ALLOWED
      )
    ).toBe(true);

    // Chunk not published
    expect(
      canActivateEmbedding(
        false,
        DocumentStatus.PUBLISHED,
        PermissionState.ALLOWED
      )
    ).toBe(false);

    // Document not published
    expect(
      canActivateEmbedding(
        true,
        DocumentStatus.SCHOLAR_APPROVED,
        PermissionState.ALLOWED
      )
    ).toBe(false);

    // Permission not allowed
    expect(
      canActivateEmbedding(
        true,
        DocumentStatus.PUBLISHED,
        PermissionState.PROHIBITED
      )
    ).toBe(false);
    expect(
      canActivateEmbedding(
        true,
        DocumentStatus.PUBLISHED,
        PermissionState.UNKNOWN
      )
    ).toBe(false);
  });
});
