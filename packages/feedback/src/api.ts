import type { FeedbackCategory, FeedbackReceipt, FeedbackSubmission } from "./types.js";

type ApiFeedback = {
  readonly id: string;
  readonly category: FeedbackCategory;
  readonly status: string;
  readonly answer_id: string | null;
  readonly citation_id: string | null;
  readonly created_at: string;
  readonly receipt_message: string;
};

type ApiErrorBody = {
  readonly error?: {
    readonly code?: string;
    readonly message?: string;
  };
};

export class FeedbackClientError extends Error {
  readonly code: string;
  readonly statusCode: number;

  constructor(code: string, message: string, statusCode: number) {
    super(message);
    this.name = "FeedbackClientError";
    this.code = code;
    this.statusCode = statusCode;
  }
}

export async function submitFeedback(
  apiBaseUrl: string,
  accessToken: string,
  submission: FeedbackSubmission,
): Promise<FeedbackReceipt> {
  const response = await fetch(new URL("feedback", apiBaseUrl), {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({
      answer_id: submission.answerId,
      category: submission.category,
      notes: submission.notes?.trim() ? submission.notes.trim() : undefined,
      citation_id: submission.citationId,
    }),
  });
  if (!response.ok) {
    throw await toClientError(response);
  }
  return mapFeedback((await response.json()) as ApiFeedback);
}

export async function fetchFeedbackReceipt(
  apiBaseUrl: string,
  accessToken: string,
  feedbackId: string,
): Promise<FeedbackReceipt> {
  const response = await fetch(new URL(`feedback/${feedbackId}`, apiBaseUrl), {
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
  });
  if (!response.ok) {
    throw await toClientError(response);
  }
  return mapFeedback((await response.json()) as ApiFeedback);
}

function mapFeedback(payload: ApiFeedback): FeedbackReceipt {
  return {
    id: payload.id,
    category: payload.category,
    status: payload.status,
    answerId: payload.answer_id,
    citationId: payload.citation_id,
    createdAt: payload.created_at,
    receiptMessage: payload.receipt_message,
  };
}

async function toClientError(response: Response): Promise<FeedbackClientError> {
  try {
    const payload = (await response.json()) as ApiErrorBody;
    return new FeedbackClientError(
      payload.error?.code ?? "FEEDBACK_CLIENT_ERROR",
      payload.error?.message ?? "ไม่สามารถส่งรายงานได้",
      response.status,
    );
  } catch {
    return new FeedbackClientError(
      "FEEDBACK_CLIENT_ERROR",
      "ไม่สามารถส่งรายงานได้",
      response.status,
    );
  }
}