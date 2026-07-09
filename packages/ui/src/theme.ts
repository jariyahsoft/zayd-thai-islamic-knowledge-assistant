export type ThemeMode = "light" | "dark" | "system";

export function resolveTheme(mode: ThemeMode): "light" | "dark" {
  if (mode === "light" || mode === "dark") {
    return mode;
  }
  if (typeof window !== "undefined" && window.matchMedia) {
    return window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  }
  return "light";
}

export function toggleTheme(mode: ThemeMode): ThemeMode {
  const resolved = resolveTheme(mode);
  return resolved === "dark" ? "light" : "dark";
}