import { isValidElement } from "react";
import { describe, expect, it } from "vitest";

import { ArabicText } from "./arabic-text.js";
import {
  USER_APP_NAV_ITEMS,
  createUserAppManifest,
  validateManifestForInstallability,
} from "./pwa.js";
import { toggleTheme } from "./theme.js";
import { UserAppShell } from "./user-app-shell.js";

describe("user app shell", () => {
  it("renders mobile navigation items for core screens", () => {
    const shell = UserAppShell({
      activeNav: "chat",
      themeLabel: "สว่าง",
      children: "เนื้อหา",
    });

    expect(shell).toBeTruthy();
    expect(USER_APP_NAV_ITEMS.map((item) => item.href)).toEqual([
      "/chat",
      "/history",
      "/settings",
    ]);
  });

  it("isolates Arabic text direction without reversing Thai layout", () => {
    const arabic = ArabicText({ children: "بسم الله الرحمن الرحيم" });
    expect(isValidElement(arabic)).toBe(true);
    if (!isValidElement(arabic)) {
      return;
    }
    const props = arabic.props as {
      dir?: string;
      lang?: string;
      style?: { unicodeBidi?: string };
    };
    expect(props.dir).toBe("rtl");
    expect(props.lang).toBe("ar");
    expect(props.style?.unicodeBidi).toBe("isolate");
  });

  it("passes installability checks for the PWA manifest", () => {
    const manifest = createUserAppManifest();
    expect(validateManifestForInstallability(manifest)).toEqual([]);
    expect(manifest.display).toBe("standalone");
    expect(manifest.lang).toBe("th");
    expect(manifest.icons.length).toBeGreaterThanOrEqual(2);
  });

  it("toggles between light and dark themes", () => {
    expect(toggleTheme("light")).toBe("dark");
    expect(toggleTheme("dark")).toBe("light");
  });
});