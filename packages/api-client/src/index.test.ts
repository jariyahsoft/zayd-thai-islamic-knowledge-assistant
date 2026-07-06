import { describe, expect, it } from "vitest";

import { createApiClient } from "./index.js";

describe("api client", () => {
  it("returns a placeholder health response", async () => {
    await expect(
      createApiClient({ baseUrl: "http://localhost:8000" }).getHealth(),
    ).resolves.toEqual({
      status: "ok",
      service: "placeholder",
    });
  });
});
