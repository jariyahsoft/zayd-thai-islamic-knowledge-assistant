export {
  FeedbackClientError,
  fetchFeedbackReceipt,
  submitFeedback,
} from "./api.js";
export { FEEDBACK_CATEGORY_LABELS } from "./labels.js";
export { validateFeedbackSubmission } from "./validation.js";
export type { FeedbackValidationError } from "./validation.js";
export type {
  FeedbackCategory,
  FeedbackReceipt,
  FeedbackSubmission,
} from "./types.js";

import type { FeedbackCategory } from "./types.js";
import { FEEDBACK_CATEGORY_LABELS } from "./labels.js";

export const FEEDBACK_CATEGORIES = Object.keys(
  FEEDBACK_CATEGORY_LABELS,
) as FeedbackCategory[];