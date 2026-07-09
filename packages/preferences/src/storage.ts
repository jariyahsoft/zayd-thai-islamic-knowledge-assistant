import { DEFAULT_PREFERENCES } from "./defaults.js";
import { normalizePreferences } from "./validation.js";
import type { UserPreferences } from "./types.js";

const GUEST_STORAGE_KEY = "zayd.preferences.guest";

export function readGuestPreferences(): UserPreferences {
  if (typeof window === "undefined") {
    return DEFAULT_PREFERENCES;
  }
  try {
    const raw = window.localStorage.getItem(GUEST_STORAGE_KEY);
    if (!raw) {
      return DEFAULT_PREFERENCES;
    }
    return normalizePreferences(JSON.parse(raw) as Partial<UserPreferences>);
  } catch {
    return DEFAULT_PREFERENCES;
  }
}

export function writeGuestPreferences(preferences: UserPreferences): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(GUEST_STORAGE_KEY, JSON.stringify(preferences));
}

export function guestPreferencesStorageKey(): string {
  return GUEST_STORAGE_KEY;
}