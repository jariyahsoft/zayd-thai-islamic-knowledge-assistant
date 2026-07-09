import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import {
  DEFAULT_MADHHAB_DISCLOSURE_TH,
  guestPreferencesStorageKey,
} from "@zayd/preferences";

const settingsDir = dirname(fileURLToPath(import.meta.url));

describe("settings page", () => {
  it("discloses the default Shafii madhhab in the settings UI", () => {
    const form = readFileSync(join(settingsDir, "settings-form.tsx"), "utf8");
    expect(form).toContain("DEFAULT_MADHHAB_DISCLOSURE_TH");
    expect(DEFAULT_MADHHAB_DISCLOSURE_TH).toContain("ชาฟิอี");
  });

  it("stores guest preferences locally only", () => {
    const storage = readFileSync(
      join(settingsDir, "../preferences/use-user-preferences.ts"),
      "utf8",
    );
    expect(storage).toContain("writeGuestPreferences");
    expect(guestPreferencesStorageKey()).toBe("zayd.preferences.guest");
  });

  it("includes accessible settings controls and styles", () => {
    const form = readFileSync(join(settingsDir, "settings-form.tsx"), "utf8");
    const css = readFileSync(join(settingsDir, "../globals.css"), "utf8");
    expect(form).toContain('aria-labelledby="settings-heading"');
    expect(form).toContain('htmlFor="settings-madhhab"');
    expect(css).toContain(".zayd-settings__disclosure");
  });
});