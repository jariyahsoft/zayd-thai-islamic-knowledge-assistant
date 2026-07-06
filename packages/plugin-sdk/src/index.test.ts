import { describe, expect, it } from "vitest";

import type { PluginManifest } from "./index.js";

describe("plugin sdk", () => {
  it("describes a plugin manifest shape", () => {
    const manifest: PluginManifest = {
      name: "placeholder",
      type: "knowledge_provider",
      version: "0.0.0",
    };

    expect(manifest.type).toBe("knowledge_provider");
  });
});
