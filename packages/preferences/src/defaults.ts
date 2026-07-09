import type { UserPreferences } from "./types.js";

export const DEFAULT_MADHHAB = "shafii" as const;

export const DEFAULT_PREFERENCES: UserPreferences = {
  madhhab: DEFAULT_MADHHAB,
  answerLength: "normal",
  showArabic: true,
  historyMode: "enabled",
  themeMode: "system",
};

export const DEFAULT_MADHHAB_DISCLOSURE_TH =
  "ค่าเริ่มต้นของ Zayd คือมัซฮับชาฟิอี คุณสามารถเปลี่ยนได้ด้านล่าง";