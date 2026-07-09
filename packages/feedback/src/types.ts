export type FeedbackCategory =
  | "incorrect_answer"
  | "citation_error"
  | "incomplete_answer"
  | "inappropriate_content"
  | "other";

export type FeedbackSubmission = {
  readonly answerId: string;
  readonly category: FeedbackCategory;
  readonly notes?: string;
  readonly citationId?: string;
};

export type FeedbackReceipt = {
  readonly id: string;
  readonly category: FeedbackCategory;
  readonly status: string;
  readonly answerId: string | null;
  readonly citationId: string | null;
  readonly createdAt: string;
  readonly receiptMessage: string;
};