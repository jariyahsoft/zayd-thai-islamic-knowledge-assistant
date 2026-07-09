import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const savedAnswersDir = dirname(fileURLToPath(import.meta.url));

describe("saved answers client", () => {
  it("references answer ids instead of duplicating source payloads", () => {
    const source = readFileSync(join(savedAnswersDir, "api.ts"), "utf8");
    expect(source).toContain("answer_id");
    expect(source).not.toContain("answer_text");
  });
});