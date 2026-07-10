import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const workspaceDir = dirname(fileURLToPath(import.meta.url));
const reviewerAppDir = join(workspaceDir, "..", "..");

describe("scholar approval workspace", () => {
  it("renders evidence, license, madhhab, and approval history areas", () => {
    const source = readFileSync(join(workspaceDir, "workspace.tsx"), "utf8");

    expect(source).toContain("Required Evidence");
    expect(source).toContain("Source and License Status");
    expect(source).toContain("Conflicts and Madhhab Metadata");
    expect(source).toContain("Approval Matrix");
    expect(source).toContain("Review History");
    expect(source).toContain("fetchApprovalRequirements");
    expect(source).toContain("fetchApprovalHistory");
  });

  it("surfaces server-side self-approval denial and revoke flow", () => {
    const source = readFileSync(join(workspaceDir, "workspace.tsx"), "utf8");

    expect(source).toContain("SCHOLAR_APPROVAL_SELF_APPROVAL_DENIED");
    expect(source).toContain("separation of duties");
    expect(source).toContain("revoke approval");
    expect(source).toContain("revokeReason");
  });

  it("ships responsive scholar workspace styling hooks", () => {
    const css = readFileSync(join(reviewerAppDir, "globals.css"), "utf8");

    expect(css).toContain(".zayd-approval__grid");
    expect(css).toContain(".zayd-approval__bottom");
    expect(css).toContain(".zayd-approval__history");
    expect(css).toContain("@media (max-width: 980px)");
  });
});
