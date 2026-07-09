export type ConversationSummary = {
  readonly id: string;
  readonly title: string | null;
  readonly language: string;
  readonly madhhab: string;
  readonly messageCount: number;
  readonly preview: string | null;
  readonly createdAt: string;
  readonly updatedAt: string;
};

export type ConversationCitation = {
  readonly citation_id: string;
  readonly display: string;
  readonly source_type: string;
  readonly verification_status: string;
};

export type ConversationAnswer = {
  readonly id: string;
  readonly summary: string;
  readonly answerTh: string;
  readonly madhhab: string;
  readonly riskLevel: string;
  readonly confidence: string;
  readonly evidenceSufficient: boolean;
  readonly citations: readonly ConversationCitation[];
  readonly limitations: readonly string[];
  readonly warning: string | null;
  readonly status: string | null;
};

export type ConversationMessage = {
  readonly id: string;
  readonly senderType: "user" | "assistant" | "system";
  readonly body: string;
  readonly createdAt: string;
  readonly answer: ConversationAnswer | null;
};

export type ConversationDetail = {
  readonly conversation: ConversationSummary;
  readonly messages: readonly ConversationMessage[];
};

export type ConversationListResult = {
  readonly conversations: readonly ConversationSummary[];
  readonly totalCount: number;
  readonly limit: number;
  readonly offset: number;
  readonly nextOffset: number | null;
};