import { describe, expect, it } from "vitest";

import { createPlaceholderId } from "./index.js";

describe("testing helpers", () => {
  it("creates deterministic placeholder ids", () => {
    expect(createPlaceholderId("task")).toBe("task-placeholder");
  });
});
