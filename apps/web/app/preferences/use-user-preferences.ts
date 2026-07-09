"use client";

import { useCallback, useEffect, useState } from "react";
import {
  DEFAULT_PREFERENCES,
  PreferencesClientError,
  fetchUserPreferences,
  normalizePreferences,
  readGuestPreferences,
  updateUserPreferences,
  validatePreferences,
  writeGuestPreferences,
  type UserPreferences,
} from "@zayd/preferences";
import type { ThemeMode } from "@zayd/ui";

function readAccessToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem("zayd.access_token");
}

export function useUserPreferences(apiBaseUrl: string): {
  readonly preferences: UserPreferences;
  readonly isSignedIn: boolean;
  readonly isSyncing: boolean;
  readonly syncError: string | null;
  readonly updatePreferences: (patch: Partial<UserPreferences>) => Promise<void>;
  readonly setThemeMode: (themeMode: ThemeMode) => Promise<void>;
} {
  const [preferences, setPreferences] = useState<UserPreferences>(DEFAULT_PREFERENCES);
  const [isSignedIn, setIsSignedIn] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncError, setSyncError] = useState<string | null>(null);

  useEffect(() => {
    const accessToken = readAccessToken();
    if (!accessToken) {
      setIsSignedIn(false);
      setPreferences(readGuestPreferences());
      return;
    }

    let cancelled = false;
    setIsSignedIn(true);
    setIsSyncing(true);
    fetchUserPreferences(apiBaseUrl, accessToken)
      .then((synced) => {
        if (cancelled) {
          return;
        }
        const local = readGuestPreferences();
        setPreferences(
          normalizePreferences({
            madhhab: synced.madhhab,
            answerLength: synced.answerLength,
            showArabic: synced.showArabic,
            historyMode: synced.historyMode,
            themeMode: local.themeMode,
          }),
        );
        setSyncError(null);
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return;
        }
        setPreferences(readGuestPreferences());
        setSyncError(
          error instanceof PreferencesClientError
            ? error.message
            : "ไม่สามารถโหลดการตั้งค่าจากบัญชีได้",
        );
      })
      .finally(() => {
        if (!cancelled) {
          setIsSyncing(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [apiBaseUrl]);

  const persist = useCallback(
    async (next: UserPreferences) => {
      const validationError = validatePreferences(next);
      if (validationError) {
        setSyncError(validationError.message);
        return;
      }

      setPreferences(next);
      setSyncError(null);

      if (!isSignedIn) {
        writeGuestPreferences(next);
        return;
      }

      const accessToken = readAccessToken();
      if (!accessToken) {
        writeGuestPreferences(next);
        setIsSignedIn(false);
        return;
      }

      setIsSyncing(true);
      try {
        const synced = await updateUserPreferences(apiBaseUrl, accessToken, next);
        setPreferences(
          normalizePreferences({
            madhhab: synced.madhhab,
            answerLength: synced.answerLength,
            showArabic: synced.showArabic,
            historyMode: synced.historyMode,
            themeMode: next.themeMode,
          }),
        );
        writeGuestPreferences({
          ...next,
          madhhab: synced.madhhab,
          answerLength: synced.answerLength,
          showArabic: synced.showArabic,
          historyMode: synced.historyMode,
        });
      } catch (error: unknown) {
        setSyncError(
          error instanceof PreferencesClientError
            ? error.message
            : "ไม่สามารถบันทึกการตั้งค่าไปยังบัญชีได้",
        );
        writeGuestPreferences(next);
      } finally {
        setIsSyncing(false);
      }
    },
    [apiBaseUrl, isSignedIn],
  );

  const updatePreferences = useCallback(
    async (patch: Partial<UserPreferences>) => {
      await persist(normalizePreferences({ ...preferences, ...patch }));
    },
    [persist, preferences],
  );

  const setThemeMode = useCallback(
    async (themeMode: ThemeMode) => {
      await updatePreferences({ themeMode });
    },
    [updatePreferences],
  );

  return {
    preferences,
    isSignedIn,
    isSyncing,
    syncError,
    updatePreferences,
    setThemeMode,
  };
}