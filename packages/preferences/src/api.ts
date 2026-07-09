import type { SyncedUserPreferences, UserPreferences } from "./types.js";
import { normalizePreferences } from "./validation.js";

type ApiPreferencesResponse = {
  readonly madhhab: string;
  readonly default_madhhab: string;
  readonly answer_length: string;
  readonly show_arabic: boolean;
  readonly history_mode: string;
  readonly preferred_language: string;
  readonly synced?: boolean;
};

type ApiErrorBody = {
  readonly error?: {
    readonly code?: string;
    readonly message?: string;
  };
};

export class PreferencesClientError extends Error {
  readonly code: string;
  readonly statusCode: number;

  constructor(code: string, message: string, statusCode: number) {
    super(message);
    this.name = "PreferencesClientError";
    this.code = code;
    this.statusCode = statusCode;
  }
}

export async function fetchUserPreferences(
  apiBaseUrl: string,
  accessToken: string,
): Promise<SyncedUserPreferences> {
  const response = await fetch(new URL("auth/me/preferences", apiBaseUrl), {
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
  });
  if (!response.ok) {
    throw await toClientError(response);
  }
  return mapApiPreferences((await response.json()) as ApiPreferencesResponse);
}

export async function updateUserPreferences(
  apiBaseUrl: string,
  accessToken: string,
  preferences: Partial<UserPreferences>,
): Promise<SyncedUserPreferences> {
  const response = await fetch(new URL("auth/me/preferences", apiBaseUrl), {
    method: "PATCH",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({
      madhhab: preferences.madhhab,
      answer_length: preferences.answerLength,
      show_arabic: preferences.showArabic,
      history_mode: preferences.historyMode,
    }),
  });
  if (!response.ok) {
    throw await toClientError(response);
  }
  return mapApiPreferences((await response.json()) as ApiPreferencesResponse);
}

function mapApiPreferences(payload: ApiPreferencesResponse): SyncedUserPreferences {
  const normalized = normalizePreferences({
    madhhab: payload.madhhab,
    answerLength: payload.answer_length,
    showArabic: payload.show_arabic,
    historyMode: payload.history_mode,
  });
  return {
    ...normalized,
    defaultMadhhab: normalizePreferences({ madhhab: payload.default_madhhab }).madhhab,
    preferredLanguage: payload.preferred_language,
    synced: payload.synced ?? true,
  };
}

async function toClientError(response: Response): Promise<PreferencesClientError> {
  try {
    const payload = (await response.json()) as ApiErrorBody;
    return new PreferencesClientError(
      payload.error?.code ?? "PREFERENCES_CLIENT_ERROR",
      payload.error?.message ?? "ไม่สามารถบันทึกการตั้งค่าได้",
      response.status,
    );
  } catch {
    return new PreferencesClientError(
      "PREFERENCES_CLIENT_ERROR",
      "ไม่สามารถบันทึกการตั้งค่าได้",
      response.status,
    );
  }
}