export type WebManifestIcon = {
  readonly src: string;
  readonly sizes: string;
  readonly type: string;
  readonly purpose?: "any" | "maskable" | "monochrome";
};

export type WebManifest = {
  readonly name: string;
  readonly short_name: string;
  readonly description: string;
  readonly start_url: string;
  readonly display: "standalone" | "browser";
  readonly background_color: string;
  readonly theme_color: string;
  readonly lang: string;
  readonly dir: "ltr";
  readonly icons: readonly WebManifestIcon[];
};

export const USER_APP_NAV_ITEMS = [
  { id: "chat", href: "/chat", label: "ถาม", labelEn: "Chat" },
  { id: "history", href: "/history", label: "ประวัติ", labelEn: "History" },
  { id: "settings", href: "/settings", label: "ตั้งค่า", labelEn: "Settings" },
] as const;

export type UserAppNavId = (typeof USER_APP_NAV_ITEMS)[number]["id"];

export function createUserAppManifest(): WebManifest {
  return {
    name: "Zayd — Thai Islamic Knowledge Assistant",
    short_name: "Zayd",
    description:
      "Mobile-first assistant for Thai Islamic knowledge with verified citations.",
    start_url: "/",
    display: "standalone",
    background_color: "#f7f4ef",
    theme_color: "#1f4d3a",
    lang: "th",
    dir: "ltr",
    icons: [
      {
        src: "/icons/icon-192.svg",
        sizes: "192x192",
        type: "image/svg+xml",
        purpose: "any",
      },
      {
        src: "/icons/icon-512.svg",
        sizes: "512x512",
        type: "image/svg+xml",
        purpose: "maskable",
      },
    ],
  };
}

export function validateManifestForInstallability(
  manifest: WebManifest,
): readonly string[] {
  const errors: string[] = [];
  if (!manifest.name.trim()) {
    errors.push("Manifest name is required.");
  }
  if (!manifest.short_name.trim()) {
    errors.push("Manifest short_name is required.");
  }
  if (!manifest.start_url.startsWith("/")) {
    errors.push("Manifest start_url must be an app-relative path.");
  }
  if (manifest.display !== "standalone") {
    errors.push("Manifest display must be standalone for installability.");
  }
  if (manifest.icons.length === 0) {
    errors.push("Manifest requires at least one icon.");
  }
  for (const icon of manifest.icons) {
    if (!icon.src.startsWith("/")) {
      errors.push("Manifest icon src must be an app-relative path.");
    }
    if (!icon.sizes.includes("x")) {
      errors.push("Manifest icon sizes must include dimensions.");
    }
  }
  return errors;
}