import { describe, expect, it } from "vitest";

import { getPublicEnv } from "@zayd/config/env/public";

describe("admin public environment", () => {
  it("returns only public values", () => {
    expect(
      getPublicEnv({
        NEXT_PUBLIC_API_BASE_URL: "http://localhost:8000",
      }),
    ).toEqual({
      NEXT_PUBLIC_API_BASE_URL: "http://localhost:8000/",
    });
  });
});
