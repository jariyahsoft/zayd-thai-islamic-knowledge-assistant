import type { AnswerLengthPreference, MadhhabPreference } from "./types.js";

export const MADHHAB_LABELS: Record<MadhhabPreference, string> = {
  shafii: "ชาฟิอี",
  hanafi: "ฮันะฟี",
  maliki: "มาลิกี",
  hanbali: "ฮันะบลี",
};

export const ANSWER_LENGTH_LABELS: Record<AnswerLengthPreference, string> = {
  short: "สั้น",
  normal: "ปกติ",
  detailed: "ละเอียด",
};