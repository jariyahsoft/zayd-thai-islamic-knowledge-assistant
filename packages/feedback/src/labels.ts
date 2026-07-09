import type { FeedbackCategory } from "./types.js";

export const FEEDBACK_CATEGORY_LABELS: Record<FeedbackCategory, string> = {
  incorrect_answer: "คำตอบไม่ถูกต้อง",
  citation_error: "อ้างอิงผิดหรือไม่ตรง",
  incomplete_answer: "คำตอบไม่ครบถ้วน",
  inappropriate_content: "เนื้อหาไม่เหมาะสม",
  other: "อื่นๆ",
};