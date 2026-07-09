import type { FeedbackCategory, FeedbackSubmission } from "./types.js";

const CATEGORIES = new Set<FeedbackCategory>([
  "incorrect_answer",
  "citation_error",
  "incomplete_answer",
  "inappropriate_content",
  "other",
]);

const MAX_NOTES_LENGTH = 2000;

export type FeedbackValidationError = {
  readonly field: keyof FeedbackSubmission | "unknown";
  readonly message: string;
};

export function validateFeedbackSubmission(
  value: FeedbackSubmission,
): FeedbackValidationError | null {
  if (!value.answerId.trim()) {
    return { field: "answerId", message: "ต้องระบุคำตอบที่ต้องการรายงาน" };
  }
  if (!CATEGORIES.has(value.category)) {
    return { field: "category", message: "ประเภทปัญหาไม่ถูกต้อง" };
  }
  if (value.notes !== undefined && value.notes.length > MAX_NOTES_LENGTH) {
    return { field: "notes", message: "คำอธิบายยาวเกินไป" };
  }
  return null;
}