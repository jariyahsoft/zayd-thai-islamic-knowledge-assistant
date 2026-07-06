import { describe, expect, it } from "vitest";

import type { ProviderHealth } from "./index.js";

describe("provider sdk", () => {
  it("exposes provider health types", () => {
    const health: ProviderHealth = { status: "ok" };
    expect(health.status).toBe("ok");
  });
});
