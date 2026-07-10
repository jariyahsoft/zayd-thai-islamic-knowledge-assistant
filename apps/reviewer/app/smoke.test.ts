import { describe, expect, it } from "vitest";

describe("reviewer workspace", () => {
  it("points the page at the reviewer dashboard", async () => {
    const page = await import("./page.js");
    expect(page.default).toBeTypeOf("function");
  });

  it("exports the scholar approval route entry", async () => {
    const page = await import("./approvals/[reviewTaskId]/page.js");
    expect(page.default).toBeTypeOf("function");
  });
});
