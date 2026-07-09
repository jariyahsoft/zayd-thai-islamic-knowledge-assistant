import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const citationsDir = dirname(fileURLToPath(import.meta.url));

describe("citation detail page", () => {
  it("renders governed citation detail inside the user shell", () => {
    const page = readFileSync(join(citationsDir, "[citationId]/page.tsx"), "utf8");
    expect(page).toContain("CitationDetailView");
    expect(page).toContain("UserAppClient");
    expect(page).toContain("getPublicEnv");
  });

  it("includes citation styles for cards and detail layout", () => {
    const css = readFileSync(join(citationsDir, "../globals.css"), "utf8");
    expect(css).toContain(".zayd-citation-card");
    expect(css).toContain(".zayd-citation-detail__source-text--rtl");
    expect(css).toContain(".zayd-citation-warnings");
  });
});