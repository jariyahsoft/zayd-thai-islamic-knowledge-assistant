export type SavedAnswerCitation = {
  readonly citationId: string;
  readonly display: string;
  readonly sourceType: string;
  readonly verificationStatus: string;
};

export type SavedAnswerRecord = {
  readonly id: string;
  readonly answerId: string;
  readonly savedAt: string;
  readonly summary: string;
  readonly answerTh: string;
  readonly madhhab: string;
  readonly warnings: readonly string[];
  readonly citations: readonly SavedAnswerCitation[];
};

export type SavedAnswerListResult = {
  readonly savedAnswers: readonly SavedAnswerRecord[];
  readonly totalCount: number;
};