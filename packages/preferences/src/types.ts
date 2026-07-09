export type ThemeMode = "light" | "dark" | "system";

export type MadhhabPreference = "shafii" | "hanafi" | "maliki" | "hanbali";
export type AnswerLengthPreference = "short" | "normal" | "detailed";
export type HistoryModePreference = "enabled" | "disabled";

export type UserPreferences = {
  readonly madhhab: MadhhabPreference;
  readonly answerLength: AnswerLengthPreference;
  readonly showArabic: boolean;
  readonly historyMode: HistoryModePreference;
  readonly themeMode: ThemeMode;
};

export type SyncedUserPreferences = UserPreferences & {
  readonly defaultMadhhab: MadhhabPreference;
  readonly preferredLanguage: string;
  readonly synced: boolean;
};