import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const workspaceDir = dirname(fileURLToPath(import.meta.url));
const reviewerAppDir = join(workspaceDir, "..", "..");

describe("document review workspace", () => {
  it("protects unsaved edits and surfaces concurrency conflicts", () => {
    const source = readFileSync(join(workspaceDir, "workspace.tsx"), "utf8");

    expect(source).toContain("beforeunload");
    expect(source).toContain("isDirty");
    expect(source).toContain("DOCUMENT_REVIEW_CONFLICT");
    expect(source).toContain("โหลดฉบับล่าสุด");
  });

  it("renders read-only source, editable draft, comments, diff, and audited decision areas", () => {
    const source = readFileSync(join(workspaceDir, "workspace.tsx"), "utf8");

    expect(source).toContain("Original Source");
    expect(source).toContain("read-only");
    expect(source).toContain("Extracted Text");
    expect(source).toContain("Metadata");
    expect(source).toContain("Translation & Chunks");
    expect(source).toContain("Comments");
    expect(source).toContain("Decision");
    expect(source).toContain("audited");
  });

  it("includes responsive workspace styling hooks", () => {
    const css = readFileSync(join(reviewerAppDir, "globals.css"), "utf8");

    expect(css).toContain(".zayd-review-workspace__grid");
    expect(css).toContain(".zayd-review-workspace__bottom");
    expect(css).toContain(".zayd-review-workspace__diff");
    expect(css).toContain("@media (max-width: 980px)");
  });
});
