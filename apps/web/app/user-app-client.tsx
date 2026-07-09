"use client";

import type { ReactElement, ReactNode } from "react";
import { useEffect, useState } from "react";
import {
  UserAppShell,
  resolveTheme,
  toggleTheme,
  type ThemeMode,
  type UserAppNavId,
} from "@zayd/ui";

export function UserAppClient(props: {
  readonly activeNav: UserAppNavId | "home";
  readonly children: ReactNode;
}): ReactElement {
  const [themeMode, setThemeMode] = useState<ThemeMode>("system");

  useEffect(() => {
    const resolved = resolveTheme(themeMode);
    document.documentElement.dataset.theme = resolved;
  }, [themeMode]);

  const resolved = resolveTheme(themeMode);

  return (
    <UserAppShell
      activeNav={props.activeNav}
      themeLabel={resolved === "dark" ? "มืด" : "สว่าง"}
      onThemeToggle={() => {
        setThemeMode((current) => toggleTheme(current));
      }}
    >
      {props.children}
    </UserAppShell>
  );
}