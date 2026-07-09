import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const conversationsDir = dirname(fileURLToPath(import.meta.url));

describe("conversation history client", () => {
  it("targets authenticated conversation history endpoints", () => {
    const source = readFileSync(join(conversationsDir, "api.ts"), "utf8");
    expect(source).toContain("chat/conversations");
    expect(source).toContain("delete-all");
    expect(source).toContain("Authorization");
  });
});