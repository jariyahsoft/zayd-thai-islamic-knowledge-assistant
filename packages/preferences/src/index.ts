export {
  fetchUserPreferences,
  updateUserPreferences,
  PreferencesClientError,
} from "./api.js";
export { DEFAULT_MADHHAB, DEFAULT_MADHHAB_DISCLOSURE_TH, DEFAULT_PREFERENCES } from "./defaults.js";
export { ANSWER_LENGTH_LABELS, MADHHAB_LABELS } from "./labels.js";
export { guestPreferencesStorageKey, readGuestPreferences, writeGuestPreferences } from "./storage.js";
export type {
  AnswerLengthPreference,
  HistoryModePreference,
  MadhhabPreference,
  SyncedUserPreferences,
  UserPreferences,
} from "./types.js";
export {
  normalizePreferences,
  validatePreferences,
  type PreferenceValidationError,
  type PreferencesInput,
} from "./validation.js";