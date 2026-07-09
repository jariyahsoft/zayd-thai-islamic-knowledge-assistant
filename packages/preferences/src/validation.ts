import { DEFAULT_PREFERENCES } from "./defaults.js";
import type {
  AnswerLengthPreference,
  HistoryModePreference,
  MadhhabPreference,
  UserPreferences,
} from "./types.js";

const MADHHABS = new Set<MadhhabPreference>(["shafii", "hanafi", "maliki", "hanbali"]);
const ANSWER_LENGTHS = new Set<AnswerLengthPreference>(["short", "normal", "detailed"]);
const HISTORY_MODES = new Set<HistoryModePreference>(["enabled", "disabled"]);
const THEME_MODES = new Set(["light", "dark", "system"]);

export type PreferenceValidationError = {
  readonly field: keyof UserPreferences | "unknown";
  readonly message: string;
};

export type PreferencesInput = {
  readonly madhhab?: string;
  readonly answerLength?: string;
  readonly showArabic?: boolean;
  readonly historyMode?: string;
  readonly themeMode?: string;
};

function isMadhhab(value: string): value is MadhhabPreference {
  return MADHHABS.has(value as MadhhabPreference);
}

function isAnswerLength(value: string): value is AnswerLengthPreference {
  return ANSWER_LENGTHS.has(value as AnswerLengthPreference);
}

function isHistoryMode(value: string): value is HistoryModePreference {
  return HISTORY_MODES.has(value as HistoryModePreference);
}

export function validatePreferences(value: PreferencesInput): PreferenceValidationError | null {
  if (value.madhhab !== undefined && !isMadhhab(value.madhhab)) {
    return { field: "madhhab", message: "มัซฮับไม่ถูกต้อง" };
  }
  if (value.answerLength !== undefined && !isAnswerLength(value.answerLength)) {
    return { field: "answerLength", message: "ความยาวคำตอบไม่ถูกต้อง" };
  }
  if (value.historyMode !== undefined && !isHistoryMode(value.historyMode)) {
    return { field: "historyMode", message: "โหมดประวัติไม่ถูกต้อง" };
  }
  if (value.themeMode !== undefined && !THEME_MODES.has(value.themeMode)) {
    return { field: "themeMode", message: "ธีมไม่ถูกต้อง" };
  }
  if (value.showArabic !== undefined && typeof value.showArabic !== "boolean") {
    return { field: "showArabic", message: "การแสดงอักษรอาหรับไม่ถูกต้อง" };
  }
  return null;
}

export function normalizePreferences(value: PreferencesInput): UserPreferences {
  return {
    madhhab:
      value.madhhab !== undefined && isMadhhab(value.madhhab)
        ? value.madhhab
        : DEFAULT_PREFERENCES.madhhab,
    answerLength:
      value.answerLength !== undefined && isAnswerLength(value.answerLength)
        ? value.answerLength
        : DEFAULT_PREFERENCES.answerLength,
    showArabic:
      typeof value.showArabic === "boolean" ? value.showArabic : DEFAULT_PREFERENCES.showArabic,
    historyMode:
      value.historyMode !== undefined && isHistoryMode(value.historyMode)
        ? value.historyMode
        : DEFAULT_PREFERENCES.historyMode,
    themeMode:
      value.themeMode === "light" || value.themeMode === "dark" || value.themeMode === "system"
        ? value.themeMode
        : DEFAULT_PREFERENCES.themeMode,
  };
}