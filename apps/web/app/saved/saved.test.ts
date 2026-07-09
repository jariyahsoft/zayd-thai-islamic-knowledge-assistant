import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const savedDir = dirname(fileURLToPath(import.meta.url));

describe("saved answers page", () => {
  it("references answer ids and shows validity warnings", () => {
    const list = readFileSync(join(savedDir, "saved-list.tsx"), "utf8");
    expect(list).toContain("SourceStatusWarnings");
    expect(list).toContain("CitationCardList");
    expect(list).toContain("unsaveAnswer");
  });

  it("discloses that saved records reference answers", () => {
    const page = readFileSync(join(savedDir, "page.tsx"), "utf8");
    expect(page).toContain("อ้างอิงจากคำตอบในระบบ");
  });
});