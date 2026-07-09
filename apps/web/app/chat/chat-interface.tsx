"use client";

import type { ReactElement } from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import { CitationCardList } from "@zayd/citations";
import { ArabicText } from "@zayd/ui";

import type { ChatMessage, ChatStreamStage, ParsedChatEvent } from "./chat-types.js";
import {
  ConversationsClientError,
  fetchConversationDetail,
  type ConversationMessage,
} from "@zayd/conversations";
import {
  SavedAnswersClientError,
  fetchSavedAnswers,
  saveAnswer,
  unsaveAnswer,
} from "@zayd/saved-answers";
import {
  ChatClientError,
  consumeChatStream,
  ensureGuestSession,
  readStoredAccessToken,
} from "./chat-stream.js";
import { usePreferences } from "../preferences/preferences-provider.js";
import {
  CHAT_STAGE_LABELS,
  abstentionMessage,
  cancellationMessage,
  containsArabic,
  createMessageId,
  formatChatError,
  mapCompleteStatus,
} from "./chat-ui.js";

function SafeText(props: {
  readonly value: string;
  readonly showArabic: boolean;
}): ReactElement {
  if (!props.showArabic && containsArabic(props.value)) {
    return <>[อักษรอาหรับถูกซ่อนตามการตั้งค่า]</>;
  }
  if (containsArabic(props.value)) {
    return <ArabicText>{props.value}</ArabicText>;
  }
  return <>{props.value}</>;
}

function MessageBubble(props: {
  readonly message: ChatMessage;
  readonly showArabic: boolean;
  readonly canSave: boolean;
  readonly isSaving: boolean;
  readonly onSave?: (answerId: string) => void;
  readonly onUnsave?: (savedAnswerId: string, answerId: string) => void;
}): ReactElement {
  const isUser = props.message.role === "user";
  const status = props.message.status;

  return (
    <article
      className={
        isUser ? "zayd-chat__message zayd-chat__message--user" : "zayd-chat__message"
      }
      aria-label={isUser ? "คำถามของคุณ" : "คำตอบจาก Zayd"}
    >
      <p className="zayd-chat__message-body">
        <SafeText value={props.message.content} showArabic={props.showArabic} />
      </p>

      {props.message.warning ? (
        <p className="zayd-chat__warning" role="note">
          <SafeText value={props.message.warning} showArabic={props.showArabic} />
        </p>
      ) : null}

      {props.message.limitations && props.message.limitations.length > 0 ? (
        <ul className="zayd-chat__limitations">
          {props.message.limitations.map((item) => (
            <li key={item}>
              <SafeText value={item} showArabic={props.showArabic} />
            </li>
          ))}
        </ul>
      ) : null}

      {props.message.citations && props.message.citations.length > 0 ? (
        <CitationCardList citations={props.message.citations} />
      ) : null}

      {props.canSave && props.message.answerId && status === "completed" ? (
        <div className="zayd-chat__save-actions">
          {props.message.savedAnswerId ? (
            <button
              type="button"
              className="zayd-chat__save-button"
              disabled={props.isSaving}
              onClick={() => {
                props.onUnsave?.(props.message.savedAnswerId as string, props.message.answerId as string);
              }}
            >
              ยกเลิกการบันทึก
            </button>
          ) : (
            <button
              type="button"
              className="zayd-chat__save-button"
              disabled={props.isSaving}
              onClick={() => {
                props.onSave?.(props.message.answerId as string);
              }}
            >
              บันทึกคำตอบ
            </button>
          )}
        </div>
      ) : null}

      {status === "streaming" ? (
        <p className="zayd-chat__message-status" aria-live="polite">
          กำลังสร้างคำตอบ…
        </p>
      ) : null}
      {status === "abstained" ? (
        <p className="zayd-chat__message-status zayd-chat__message-status--abstained">
          ระบบเลือกที่จะไม่ตอบ
        </p>
      ) : null}
      {status === "cancelled" ? (
        <p className="zayd-chat__message-status">ยกเลิกแล้ว</p>
      ) : null}
      {status === "error" && props.message.errorCode ? (
        <p className="zayd-chat__message-status zayd-chat__message-status--error" role="alert">
          {formatChatError(props.message.errorCode, props.message.content)}
        </p>
      ) : null}
    </article>
  );
}

function mapHistoryMessage(message: ConversationMessage): ChatMessage {
  if (message.senderType === "user") {
    return {
      id: message.id,
      role: "user",
      content: message.body,
    };
  }
  return {
    id: message.id,
    role: "assistant",
    content: message.answer?.answerTh ?? message.body,
    answerId: message.answer?.id ?? null,
    status:
      message.answer?.status === "abstained"
        ? "abstained"
        : message.answer?.status === "cancelled"
          ? "cancelled"
          : message.answer?.status === "failed"
            ? "error"
            : "completed",
    citations: message.answer?.citations,
    limitations: message.answer?.limitations,
    warning: message.answer?.warning,
  };
}

export function ChatInterface(props: {
  readonly apiBaseUrl: string;
  readonly initialConversationId?: string | null;
}): ReactElement {
  const { preferences } = usePreferences();
  const [messages, setMessages] = useState<readonly ChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [conversationId, setConversationId] = useState<string | null>(
    props.initialConversationId ?? null,
  );
  const [stage, setStage] = useState<ChatStreamStage | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [sessionError, setSessionError] = useState<string | null>(null);
  const [guestReady, setGuestReady] = useState(false);
  const [retryQuestion, setRetryQuestion] = useState<string | null>(null);
  const [isSavingAnswer, setIsSavingAnswer] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const guestTokenRef = useRef<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const conversationToOpen = props.initialConversationId;
    if (!conversationToOpen || preferences.historyMode === "disabled") {
      return;
    }
    const accessToken = readStoredAccessToken();
    if (!accessToken) {
      return;
    }
    let cancelled = false;
    fetchConversationDetail(props.apiBaseUrl, accessToken, conversationToOpen)
      .then((detail) => {
        if (cancelled) {
          return;
        }
        setConversationId(detail.conversation.id);
        setMessages(detail.messages.map(mapHistoryMessage));
        setSessionError(null);
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return;
        }
        setSessionError(
          error instanceof ConversationsClientError
            ? error.message
            : "ไม่สามารถเปิดประวัติการสนทนานี้ได้",
        );
      });
    return () => {
      cancelled = true;
    };
  }, [props.apiBaseUrl, props.initialConversationId, preferences.historyMode]);

  useEffect(() => {
    let cancelled = false;
    ensureGuestSession(props.apiBaseUrl)
      .then((session) => {
        if (cancelled) {
          return;
        }
        guestTokenRef.current = session.guestToken;
        setGuestReady(true);
        setSessionError(null);
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return;
        }
        const message =
          error instanceof ChatClientError
            ? formatChatError(error.code, error.message)
            : "ไม่สามารถเริ่มเซสชันผู้เยี่ยมชมได้";
        setSessionError(message);
      });
    return () => {
      cancelled = true;
    };
  }, [props.apiBaseUrl]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, stage, isStreaming]);

  const syncSavedState = useCallback(async () => {
    const accessToken = readStoredAccessToken();
    if (!accessToken) {
      return;
    }
    try {
      const saved = await fetchSavedAnswers(props.apiBaseUrl, accessToken);
      const byAnswerId = new Map(saved.savedAnswers.map((item) => [item.answerId, item.id]));
      setMessages((current) =>
        current.map((message) =>
          message.answerId && byAnswerId.has(message.answerId)
            ? { ...message, savedAnswerId: byAnswerId.get(message.answerId) ?? null }
            : message,
        ),
      );
    } catch {
      // Saved-state sync is best-effort in chat.
    }
  }, [props.apiBaseUrl]);

  useEffect(() => {
    void syncSavedState();
  }, [syncSavedState, messages.length]);

  const handleSaveAnswer = useCallback(
    async (answerId: string) => {
      const accessToken = readStoredAccessToken();
      if (!accessToken) {
        setSaveError("ต้องลงชื่อเข้าใช้ก่อนบันทึกคำตอบ");
        return;
      }
      setIsSavingAnswer(true);
      setSaveError(null);
      try {
        const saved = await saveAnswer(props.apiBaseUrl, accessToken, answerId);
        setMessages((current) =>
          current.map((message) =>
            message.answerId === answerId
              ? { ...message, savedAnswerId: saved.id }
              : message,
          ),
        );
      } catch (error: unknown) {
        setSaveError(
          error instanceof SavedAnswersClientError
            ? error.message
            : "ไม่สามารถบันทึกคำตอบได้",
        );
      } finally {
        setIsSavingAnswer(false);
      }
    },
    [props.apiBaseUrl],
  );

  const handleUnsaveAnswer = useCallback(
    async (savedAnswerId: string, answerId: string) => {
      const accessToken = readStoredAccessToken();
      if (!accessToken) {
        return;
      }
      setIsSavingAnswer(true);
      setSaveError(null);
      try {
        await unsaveAnswer(props.apiBaseUrl, accessToken, savedAnswerId);
        setMessages((current) =>
          current.map((message) =>
            message.answerId === answerId ? { ...message, savedAnswerId: null } : message,
          ),
        );
      } catch (error: unknown) {
        setSaveError(
          error instanceof SavedAnswersClientError
            ? error.message
            : "ไม่สามารถยกเลิกการบันทึกได้",
        );
      } finally {
        setIsSavingAnswer(false);
      }
    },
    [props.apiBaseUrl],
  );

  const applyStreamEvent = useCallback(
    (assistantId: string, event: ParsedChatEvent) => {
      if (event.type === "status") {
        setStage(event.stage);
        return;
      }

      if (event.type === "final_answer") {
        setConversationId(event.payload.conversation_id);
        setMessages((current) =>
          current.map((message) =>
            message.id === assistantId
              ? {
                  ...message,
                  content: event.payload.answer.answer_th,
                  status: "completed",
                  answerId: event.payload.answer_id,
                  citations: event.payload.answer.citations,
                  limitations: event.payload.answer.limitations,
                  warning: event.payload.answer.warning,
                }
              : message,
          ),
        );
        return;
      }

      if (event.type === "error") {
        setMessages((current) =>
          current.map((message) =>
            message.id === assistantId
              ? {
                  ...message,
                  content: event.message,
                  status: "error",
                  errorCode: event.code,
                }
              : message,
          ),
        );
        return;
      }

      if (event.type === "complete") {
        const mappedStatus = mapCompleteStatus(event.status);
        setMessages((current) =>
          current.map((message) => {
            if (message.id !== assistantId) {
              return message;
            }
            if (message.status === "completed") {
              return message;
            }
            if (mappedStatus === "abstained") {
              return {
                ...message,
                content: abstentionMessage(),
                status: "abstained",
              };
            }
            if (mappedStatus === "cancelled") {
              return {
                ...message,
                content: cancellationMessage(),
                status: "cancelled",
              };
            }
            if (mappedStatus === "error") {
              return {
                ...message,
                content: "ไม่สามารถสร้างคำตอบได้",
                status: "error",
                errorCode: "CHAT_STREAM_ERROR",
              };
            }
            return {
              ...message,
              status: mappedStatus,
            };
          }),
        );
      }
    },
    [],
  );

  const runQuestion = useCallback(
    async (prompt: string) => {
      if (!prompt.trim() || isStreaming) {
        return;
      }

      const accessToken = readStoredAccessToken();
      const guestToken = guestTokenRef.current;
      if (!accessToken && !guestToken) {
        setSessionError("ยังไม่พร้อมสำหรับการสนทนา กรุณารีเฟรชหน้า");
        return;
      }

      const userMessage: ChatMessage = {
        id: createMessageId("user"),
        role: "user",
        content: prompt.trim(),
      };
      const assistantId = createMessageId("assistant");
      const assistantMessage: ChatMessage = {
        id: assistantId,
        role: "assistant",
        content: "",
        status: "streaming",
        retryQuestion: prompt.trim(),
      };

      setMessages((current) => [...current, userMessage, assistantMessage]);
      setQuestion("");
      setRetryQuestion(null);
      setStage("accepted");
      setIsStreaming(true);
      setSessionError(null);

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        await consumeChatStream({
          apiBaseUrl: props.apiBaseUrl,
          question: prompt.trim(),
          guestToken,
          accessToken,
          conversationId: preferences.historyMode === "enabled" ? conversationId : null,
          requestedMadhhab: preferences.madhhab,
          answerLength: preferences.answerLength,
          noHistory: preferences.historyMode === "disabled",
          signal: controller.signal,
          onEvent: (event) => {
            applyStreamEvent(assistantId, event);
          },
        });
      } catch (error: unknown) {
        if (error instanceof DOMException && error.name === "AbortError") {
          setMessages((current) =>
            current.map((message) =>
              message.id === assistantId
                ? {
                    ...message,
                    content: cancellationMessage(),
                    status: "cancelled",
                  }
                : message,
            ),
          );
        } else if (error instanceof ChatClientError) {
          setMessages((current) =>
            current.map((message) =>
              message.id === assistantId
                ? {
                    ...message,
                    content: error.message,
                    status: "error",
                    errorCode: error.code,
                    retryQuestion: prompt.trim(),
                  }
                : message,
            ),
          );
          setRetryQuestion(prompt.trim());
        } else {
          setMessages((current) =>
            current.map((message) =>
              message.id === assistantId
                ? {
                    ...message,
                    content: "เกิดข้อผิดพลาดที่ไม่คาดคิด",
                    status: "error",
                    errorCode: "CHAT_STREAM_ERROR",
                    retryQuestion: prompt.trim(),
                  }
                : message,
            ),
          );
          setRetryQuestion(prompt.trim());
        }
      } finally {
        abortRef.current = null;
        setIsStreaming(false);
        setStage(null);
      }
    },
    [applyStreamEvent, conversationId, isStreaming, preferences, props.apiBaseUrl],
  );

  const handleSubmit = useCallback(
    (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      void runQuestion(question);
    },
    [question, runQuestion],
  );

  const handleStop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const handleRetry = useCallback(() => {
    if (!retryQuestion) {
      const lastFailed = [...messages]
        .reverse()
        .find((message) => message.role === "assistant" && message.retryQuestion);
      if (!lastFailed?.retryQuestion) {
        return;
      }
      void runQuestion(lastFailed.retryQuestion);
      return;
    }
    void runQuestion(retryQuestion);
  }, [messages, retryQuestion, runQuestion]);

  const canRetry =
    !isStreaming &&
    (retryQuestion !== null ||
      messages.some((message) => message.role === "assistant" && message.status === "error"));

  return (
    <section className="zayd-chat" aria-labelledby="chat-heading">
      <header className="zayd-panel zayd-chat__intro">
        <h2 id="chat-heading">ถามคำถาม</h2>
        <p>ถามเกี่ยวกับความรู้อิสลามภาษาไทย ระบบจะแสดงสถานะการทำงานและคำตอบที่ตรวจสอบแล้ว</p>
      </header>

      {sessionError ? (
        <p className="zayd-chat__session-error" role="alert">
          {sessionError}
        </p>
      ) : null}
      {saveError ? (
        <p className="zayd-chat__session-error" role="alert">
          {saveError}
        </p>
      ) : null}

      <div
        className="zayd-chat__messages"
        role="log"
        aria-live="polite"
        aria-relevant="additions text"
        aria-busy={isStreaming}
      >
        {messages.length === 0 ? (
          <p className="zayd-chat__empty">พิมพ์คำถามด้านล่างเพื่อเริ่มสนทนา</p>
        ) : (
          messages.map((message) => (
            <MessageBubble
              key={message.id}
              message={message}
              showArabic={preferences.showArabic}
              canSave={readStoredAccessToken() !== null}
              isSaving={isSavingAnswer}
              onSave={(answerId) => {
                void handleSaveAnswer(answerId);
              }}
              onUnsave={(savedAnswerId, answerId) => {
                void handleUnsaveAnswer(savedAnswerId, answerId);
              }}
            />
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {isStreaming && stage ? (
        <p className="zayd-chat__progress" aria-live="polite">
          {CHAT_STAGE_LABELS[stage]}
        </p>
      ) : null}

      <form className="zayd-chat__composer" onSubmit={handleSubmit}>
        <label className="zayd-chat__label" htmlFor="chat-question">
          คำถามของคุณ
        </label>
        <textarea
          id="chat-question"
          className="zayd-chat__input"
          value={question}
          onChange={(event) => {
            setQuestion(event.target.value);
          }}
          placeholder="เช่น ละหมาดคืออะไร"
          rows={3}
          disabled={!guestReady || isStreaming || sessionError !== null}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              void runQuestion(question);
            }
          }}
        />
        <div className="zayd-chat__actions">
          {isStreaming ? (
            <button
              type="button"
              className="zayd-chat__button zayd-chat__button--secondary"
              onClick={handleStop}
            >
              หยุดสร้างคำตอบ
            </button>
          ) : null}
          {canRetry ? (
            <button
              type="button"
              className="zayd-chat__button zayd-chat__button--secondary"
              onClick={handleRetry}
            >
              ลองอีกครั้ง
            </button>
          ) : null}
          <button
            type="submit"
            className="zayd-chat__button zayd-chat__button--primary"
            disabled={!guestReady || isStreaming || question.trim().length === 0}
          >
            ส่งคำถาม
          </button>
        </div>
      </form>
    </section>
  );
}