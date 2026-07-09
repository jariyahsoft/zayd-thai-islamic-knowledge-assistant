import type { SavedAnswerListResult, SavedAnswerRecord } from "./types.js";

type ApiSavedAnswer = {
  readonly id: string;
  readonly answer_id: string;
  readonly saved_at: string;
  readonly summary: string;
  readonly answer_th: string;
  readonly madhhab: string;
  readonly warnings: readonly string[];
  readonly citations: readonly {
    readonly citation_id: string;
    readonly display: string;
    readonly source_type: string;
    readonly verification_status: string;
  }[];
};

type ApiSavedAnswerListResponse = {
  readonly saved_answers: readonly ApiSavedAnswer[];
  readonly total_count: number;
};

type ApiErrorBody = {
  readonly error?: {
    readonly code?: string;
    readonly message?: string;
  };
};

export class SavedAnswersClientError extends Error {
  readonly code: string;
  readonly statusCode: number;

  constructor(code: string, message: string, statusCode: number) {
    super(message);
    this.name = "SavedAnswersClientError";
    this.code = code;
    this.statusCode = statusCode;
  }
}

export async function fetchSavedAnswers(
  apiBaseUrl: string,
  accessToken: string,
): Promise<SavedAnswerListResult> {
  const response = await fetch(new URL("saved-answers", apiBaseUrl), {
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
  });
  if (!response.ok) {
    throw await toClientError(response);
  }
  const payload = (await response.json()) as ApiSavedAnswerListResponse;
  return {
    savedAnswers: payload.saved_answers.map(mapSavedAnswer),
    totalCount: payload.total_count,
  };
}

export async function saveAnswer(
  apiBaseUrl: string,
  accessToken: string,
  answerId: string,
): Promise<SavedAnswerRecord> {
  const response = await fetch(new URL("saved-answers", apiBaseUrl), {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({ answer_id: answerId }),
  });
  if (!response.ok) {
    throw await toClientError(response);
  }
  return mapSavedAnswer((await response.json()) as ApiSavedAnswer);
}

export async function unsaveAnswer(
  apiBaseUrl: string,
  accessToken: string,
  savedAnswerId: string,
): Promise<void> {
  const response = await fetch(new URL(`saved-answers/${savedAnswerId}`, apiBaseUrl), {
    method: "DELETE",
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
  });
  if (!response.ok) {
    throw await toClientError(response);
  }
}

function mapSavedAnswer(payload: ApiSavedAnswer): SavedAnswerRecord {
  return {
    id: payload.id,
    answerId: payload.answer_id,
    savedAt: payload.saved_at,
    summary: payload.summary,
    answerTh: payload.answer_th,
    madhhab: payload.madhhab,
    warnings: payload.warnings,
    citations: payload.citations.map((citation) => ({
      citationId: citation.citation_id,
      display: citation.display,
      sourceType: citation.source_type,
      verificationStatus: citation.verification_status,
    })),
  };
}

async function toClientError(response: Response): Promise<SavedAnswersClientError> {
  try {
    const payload = (await response.json()) as ApiErrorBody;
    return new SavedAnswersClientError(
      payload.error?.code ?? "SAVED_ANSWERS_CLIENT_ERROR",
      payload.error?.message ?? "ไม่สามารถจัดการคำตอบที่บันทึกได้",
      response.status,
    );
  } catch {
    return new SavedAnswersClientError(
      "SAVED_ANSWERS_CLIENT_ERROR",
      "ไม่สามารถจัดการคำตอบที่บันทึกได้",
      response.status,
    );
  }
}