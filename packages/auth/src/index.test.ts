import { describe, expect, it } from "vitest";

import { roles } from "./index.js";

describe("auth", () => {
  it("defines stable role names", () => {
    expect(roles).toContain("reviewer");
  });
});
