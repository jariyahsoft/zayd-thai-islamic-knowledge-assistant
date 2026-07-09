import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import {
  DEFAULT_MADHHAB,
  DEFAULT_MADHHAB_DISCLOSURE_TH,
  DEFAULT_PREFERENCES,
  guestPreferencesStorageKey,
  normalizePreferences,
  validatePreferences,
} from "./index.js";

const preferencesDir = dirname(fileURLToPath(import.meta.url));

describe("user preferences defaults", () => {
  it("discloses the default Shafii madhhab", () => {
    expect(DEFAULT_MADHHAB).toBe("shafii");
    expect(DEFAULT_PREFERENCES.madhhab).toBe("shafii");
    expect(DEFAULT_MADHHAB_DISCLOSURE_TH).toContain("ชาฟิอี");
  });

  it("uses a guest-only local storage key", () => {
    expect(guestPreferencesStorageKey()).toBe("zayd.preferences.guest");
  });
});

describe("user preferences validation", () => {
  it("accepts supported preference values", () => {
    expect(
      validatePreferences({
        madhhab: "hanafi",
        answerLength: "detailed",
        historyMode: "disabled",
        showArabic: false,
        themeMode: "dark",
      }),
    ).toBeNull();
  });

  it("rejects invalid madhhab and answer length", () => {
    expect(validatePreferences({ madhhab: "invalid" as "shafii" })?.field).toBe("madhhab");
    expect(validatePreferences({ answerLength: "huge" as "short" })?.field).toBe("answerLength");
  });

  it("normalizes partial preference payloads", () => {
    expect(normalizePreferences({ madhhab: "maliki" })).toEqual({
      ...DEFAULT_PREFERENCES,
      madhhab: "maliki",
    });
  });
});

describe("guest privacy contract", () => {
  it("documents that guest preferences stay in local storage", () => {
    const source = readFileSync(join(preferencesDir, "storage.ts"), "utf8");
    expect(source).toContain("localStorage");
    expect(source).not.toContain("fetch(");
  });
});