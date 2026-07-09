import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";
import {
  USER_APP_NAV_ITEMS,
  createUserAppManifest,
  validateManifestForInstallability,
} from "@zayd/ui";

const appDir = dirname(fileURLToPath(import.meta.url));

describe("user application shell", () => {
  it("defines mobile-first navigation for core screens", () => {
    expect(USER_APP_NAV_ITEMS).toEqual([
      { id: "chat", href: "/chat", label: "ถาม", labelEn: "Chat" },
      { id: "history", href: "/history", label: "ประวัติ", labelEn: "History" },
      { id: "settings", href: "/settings", label: "ตั้งค่า", labelEn: "Settings" },
    ]);
  });

  it("includes responsive and RTL-safe global styles", () => {
    const css = readFileSync(join(appDir, "globals.css"), "utf8");
    expect(css).toContain("min-height: 100dvh");
    expect(css).toContain("overflow-wrap: anywhere");
    expect(css).toContain("--zayd-font-thai");
    expect(css).toContain("grid-template-columns: repeat(4");
  });

  it("passes PWA installability validation and ships icons", () => {
    const manifest = createUserAppManifest();
    expect(validateManifestForInstallability(manifest)).toEqual([]);
    expect(readFileSync(join(appDir, "../public/icons/icon-192.svg"), "utf8")).toContain(
      "<svg",
    );
    expect(readFileSync(join(appDir, "../public/icons/icon-512.svg"), "utf8")).toContain(
      "<svg",
    );
  });

  it("exposes accessible landmarks in the shell markup contract", () => {
    const css = readFileSync(join(appDir, "globals.css"), "utf8");
    expect(css).toContain(".zayd-user-shell__main");
    expect(css).toContain(".zayd-user-shell__nav");
  });
});