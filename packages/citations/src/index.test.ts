import { describe, expect, it } from "vitest";

import type { CitationCard } from "./index.js";

describe("citations", () => {
  it("defines display-safe citation shape", () => {
    const citation: CitationCard = { id: "c1", source: "placeholder" };
    expect(citation).toMatchObject<CitationCard>({
      id: "c1",
      source: "placeholder",
    });
  });
});
