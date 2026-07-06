import { describe, expect, it } from "vitest";

import type { HealthResponse } from "./index.js";

describe("contracts", () => {
  it("defines a health response shape", () => {
    const response: HealthResponse = {
      status: "ok",
      service: "placeholder",
    };

    expect(response).toMatchObject<HealthResponse>({
      status: "ok",
      service: "placeholder",
    });
  });
});
