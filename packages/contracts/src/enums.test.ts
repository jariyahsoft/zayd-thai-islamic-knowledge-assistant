import { describe, expect, it } from "vitest";

import { DocumentStatus, EvidenceStatus, ReviewTaskStatus } from "./enums.js";

describe("TypeScript Enums", () => {
  it("defines expected string values", () => {
    expect(DocumentStatus.DRAFT).toBe("draft");
    expect(DocumentStatus.PUBLISHED).toBe("published");
    expect(ReviewTaskStatus.OPEN).toBe("open");
    expect(EvidenceStatus.SUFFICIENT).toBe("SUFFICIENT");
  });
});
