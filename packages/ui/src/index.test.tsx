import { describe, expect, it } from "vitest";

import { AppShell } from "./index.js";

describe("ui", () => {
  it("returns a renderable JSX object", () => {
    expect(AppShell({ title: "Zayd", children: "placeholder" })).toBeTruthy();
  });
});
