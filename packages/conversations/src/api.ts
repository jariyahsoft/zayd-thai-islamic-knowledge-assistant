import type {
  ConversationDetail,
  ConversationListResult,
  ConversationMessage,
  ConversationSummary,
} from "./types.js";

type ApiConversationSummary = {
  readonly id: string;
  readonly title: string | null;
  readonly language: string;
  readonly madhhab: string;
  readonly message_count: number;
  readonly preview: string | null;
  readonly created_at: string;
  readonly updated_at: string;
};

type ApiConversationListResponse = {
  readonly conversations: readonly ApiConversationSummary[];
  readonly total_count: number;
  readonly limit: number;
  readonly offset: number;
  readonly next_offset: number | null;
};

type ApiConversationMessage = {
  readonly id: string;
  readonly sender_type: string;
  readonly body: string;
  readonly created_at: string;
  readonly answer?: {
    readonly id: string;
    readonly summary: string;
    readonly answer_th: string;
    readonly madhhab: string;
    readonly risk_level: string;
    readonly confidence: string;
    readonly evidence_sufficient: boolean;
    readonly citations: readonly {
      readonly citation_id: string;
      readonly display: string;
      readonly source_type: string;
      readonly verification_status: string;
    }[];
    readonly limitations: readonly string[];
    readonly warning: string | null;
    readonly status: string | null;
  } | null;
};

type ApiConversationDetailResponse = {
  readonly conversation: ApiConversationSummary;
  readonly messages: readonly ApiConversationMessage[];
};

type ApiDeleteAllResponse = {
  readonly deleted_count: number;
};

type ApiErrorBody = {
  readonly error?: {
    readonly code?: string;
    readonly message?: string;
  };
};

export class ConversationsClientError extends Error {
  readonly code: string;
  readonly statusCode: number;

  constructor(code: string, message: string, statusCode: number) {
    super(message);
    this.name = "ConversationsClientError";
    this.code = code;
    this.statusCode = statusCode;
  }
}

export async function fetchConversations(
  apiBaseUrl: string,
  accessToken: string,
  options?: {
    readonly query?: string;
    readonly limit?: number;
    readonly offset?: number;
  },
): Promise<ConversationListResult> {
  const url = new URL("chat/conversations", apiBaseUrl);
  if (options?.query) {
    url.searchParams.set("q", options.query);
  }
  if (options?.limit !== undefined) {
    url.searchParams.set("limit", String(options.limit));
  }
  if (options?.offset !== undefined) {
    url.searchParams.set("offset", String(options.offset));
  }
  const response = await fetch(url, {
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
  });
  if (!response.ok) {
    throw await toClientError(response);
  }
  return mapConversationList((await response.json()) as ApiConversationListResponse);
}

export async function fetchConversationDetail(
  apiBaseUrl: string,
  accessToken: string,
  conversationId: string,
): Promise<ConversationDetail> {
  const response = await fetch(new URL(`chat/conversations/${conversationId}`, apiBaseUrl), {
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
  });
  if (!response.ok) {
    throw await toClientError(response);
  }
  return mapConversationDetail((await response.json()) as ApiConversationDetailResponse);
}

export async function deleteConversation(
  apiBaseUrl: string,
  accessToken: string,
  conversationId: string,
): Promise<void> {
  const response = await fetch(new URL(`chat/conversations/${conversationId}`, apiBaseUrl), {
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

export async function deleteAllConversations(
  apiBaseUrl: string,
  accessToken: string,
): Promise<number> {
  const response = await fetch(new URL("chat/conversations/delete-all", apiBaseUrl), {
    method: "POST",
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
  });
  if (!response.ok) {
    throw await toClientError(response);
  }
  const payload = (await response.json()) as ApiDeleteAllResponse;
  return payload.deleted_count;
}

function mapConversationList(payload: ApiConversationListResponse): ConversationListResult {
  return {
    conversations: payload.conversations.map(mapConversationSummary),
    totalCount: payload.total_count,
    limit: payload.limit,
    offset: payload.offset,
    nextOffset: payload.next_offset,
  };
}

function mapConversationDetail(payload: ApiConversationDetailResponse): ConversationDetail {
  return {
    conversation: mapConversationSummary(payload.conversation),
    messages: payload.messages.map(mapConversationMessage),
  };
}

function mapConversationSummary(summary: ApiConversationSummary): ConversationSummary {
  return {
    id: summary.id,
    title: summary.title,
    language: summary.language,
    madhhab: summary.madhhab,
    messageCount: summary.message_count,
    preview: summary.preview,
    createdAt: summary.created_at,
    updatedAt: summary.updated_at,
  };
}

function mapConversationMessage(message: ApiConversationMessage): ConversationMessage {
  return {
    id: message.id,
    senderType: message.sender_type as ConversationMessage["senderType"],
    body: message.body,
    createdAt: message.created_at,
    answer: message.answer
      ? {
          id: message.answer.id,
          summary: message.answer.summary,
          answerTh: message.answer.answer_th,
          madhhab: message.answer.madhhab,
          riskLevel: message.answer.risk_level,
          confidence: message.answer.confidence,
          evidenceSufficient: message.answer.evidence_sufficient,
          citations: message.answer.citations,
          limitations: message.answer.limitations,
          warning: message.answer.warning,
          status: message.answer.status,
        }
      : null,
  };
}

async function toClientError(response: Response): Promise<ConversationsClientError> {
  try {
    const payload = (await response.json()) as ApiErrorBody;
    return new ConversationsClientError(
      payload.error?.code ?? "CONVERSATIONS_CLIENT_ERROR",
      payload.error?.message ?? "ไม่สามารถโหลดประวัติการสนทนาได้",
      response.status,
    );
  } catch {
    return new ConversationsClientError(
      "CONVERSATIONS_CLIENT_ERROR",
      "ไม่สามารถโหลดประวัติการสนทนาได้",
      response.status,
    );
  }
}