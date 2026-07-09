"use client";

import type { ReactElement, ReactNode } from "react";
import { createContext, useContext } from "react";

import type { UserPreferences } from "@zayd/preferences";
import type { ThemeMode } from "@zayd/ui";

import { useUserPreferences } from "./use-user-preferences.js";

type PreferencesContextValue = {
  readonly preferences: UserPreferences;
  readonly isSignedIn: boolean;
  readonly isSyncing: boolean;
  readonly syncError: string | null;
  readonly updatePreferences: (patch: Partial<UserPreferences>) => Promise<void>;
  readonly setThemeMode: (themeMode: ThemeMode) => Promise<void>;
};

const PreferencesContext = createContext<PreferencesContextValue | null>(null);

export function PreferencesProvider(props: {
  readonly apiBaseUrl: string;
  readonly children: ReactNode;
}): ReactElement {
  const value = useUserPreferences(props.apiBaseUrl);
  return <PreferencesContext.Provider value={value}>{props.children}</PreferencesContext.Provider>;
}

export function usePreferences(): PreferencesContextValue {
  const value = useContext(PreferencesContext);
  if (!value) {
    throw new Error("usePreferences must be used within PreferencesProvider");
  }
  return value;
}