export type ChatStreamStage =
  | "accepted"
  | "classifying"
  | "retrieving"
  | "verifying"
  | "completed"
  | "cancelled";

export type ChatAnswerStatus = "completed" | "abstained" | "cancelled" | "failed";

export type ChatCitation = {
  readonly citation_id: string;
  readonly display: string;
  readonly source_type: string;
  readonly verification_status: string;
};

export type ChatAnswerPayload = {
  readonly summary: string;
  readonly answer_th: string;
  readonly madhhab: string;
  readonly risk_level: string;
  readonly confidence: string;
  readonly evidence_sufficient: boolean;
  readonly citations: readonly ChatCitation[];
  readonly limitations: readonly string[];
  readonly warning: string | null;
};

export type ChatFinalAnswerPayload = {
  readonly conversation_id: string;
  readonly message_id: string;
  readonly answer_id: string | null;
  readonly status: string;
  readonly answer: ChatAnswerPayload;
};

export type ParsedChatEvent =
  | {
      readonly type: "status";
      readonly eventId: string;
      readonly stage: ChatStreamStage;
      readonly streamId?: string;
      readonly status?: string;
    }
  | {
      readonly type: "final_answer";
      readonly eventId: string;
      readonly payload: ChatFinalAnswerPayload;
    }
  | {
      readonly type: "error";
      readonly eventId: string;
      readonly code: string;
      readonly message: string;
    }
  | {
      readonly type: "complete";
      readonly eventId: string;
      readonly status: ChatAnswerStatus;
      readonly streamId: string;
    };

export type ChatMessageRole = "user" | "assistant";

export type ChatMessageStatus =
  | "streaming"
  | "completed"
  | "abstained"
  | "cancelled"
  | "error";

export type ChatMessage = {
  readonly id: string;
  readonly role: ChatMessageRole;
  readonly content: string;
  readonly status?: ChatMessageStatus;
  readonly citations?: readonly ChatCitation[];
  readonly limitations?: readonly string[];
  readonly warning?: string | null;
  readonly errorCode?: string;
  readonly retryQuestion?: string;
};

export type GuestSession = {
  readonly guestToken: string;
  readonly expiresAt: string;
  readonly messageQuota: number;
  readonly messagesUsed: number;
};