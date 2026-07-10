import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const reviewerDir = dirname(fileURLToPath(import.meta.url));

describe("reviewer dashboard", () => {
  it("renders summary counters, queue cards, and feedback triage labels", () => {
    const source = readFileSync(join(reviewerDir, "reviewer-dashboard.tsx"), "utf8");
    expect(source).toContain("แดชบอร์ดผู้ตรวจ");
    expect(source).toContain("feedback ที่รอตรวจ");
    expect(source).toContain("SummaryCard");
    expect(source).toContain("QueueCard");
    expect(source).toContain("assignedToUserId");
  });

  it("ships mobile-safe dashboard styling and state badges", () => {
    const css = readFileSync(join(reviewerDir, "globals.css"), "utf8");
    expect(css).toContain(".zayd-reviewer__summary-grid");
    expect(css).toContain(".zayd-reviewer__task-list");
    expect(css).toContain(".zayd-reviewer__badge--open");
    expect(css).toContain("@media (max-width: 640px)");
  });
});
