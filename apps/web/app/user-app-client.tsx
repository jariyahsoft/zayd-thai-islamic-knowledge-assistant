"use client";

import type { ReactElement, ReactNode } from "react";
import { useEffect } from "react";
import {
  UserAppShell,
  resolveTheme,
  toggleTheme,
  type UserAppNavId,
} from "@zayd/ui";

import { PreferencesProvider, usePreferences } from "./preferences/preferences-provider.js";

function UserAppShellWithTheme(props: {
  readonly activeNav: UserAppNavId | "home";
  readonly children: ReactNode;
}): ReactElement {
  const { preferences, setThemeMode } = usePreferences();

  useEffect(() => {
    const resolved = resolveTheme(preferences.themeMode);
    document.documentElement.dataset.theme = resolved;
  }, [preferences.themeMode]);

  const resolved = resolveTheme(preferences.themeMode);

  return (
    <UserAppShell
      activeNav={props.activeNav}
      themeLabel={resolved === "dark" ? "มืด" : "สว่าง"}
      onThemeToggle={() => {
        void setThemeMode(toggleTheme(preferences.themeMode));
      }}
    >
      {props.children}
    </UserAppShell>
  );
}

export function UserAppClient(props: {
  readonly activeNav: UserAppNavId | "home";
  readonly apiBaseUrl: string;
  readonly children: ReactNode;
}): ReactElement {
  return (
    <PreferencesProvider apiBaseUrl={props.apiBaseUrl}>
      <UserAppShellWithTheme activeNav={props.activeNav}>{props.children}</UserAppShellWithTheme>
    </PreferencesProvider>
  );
}