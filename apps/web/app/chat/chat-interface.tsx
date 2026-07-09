"use client";

import type { ReactElement } from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import { ArabicText } from "@zayd/ui";

import type { ChatMessage, ChatStreamStage, ParsedChatEvent } from "./chat-types.js";
import {
  ChatClientError,
  consumeChatStream,
  ensureGuestSession,
  readStoredAccessToken,
} from "./chat-stream.js";
import {
  CHAT_STAGE_LABELS,
  abstentionMessage,
  cancellationMessage,
  containsArabic,
  createMessageId,
  formatChatError,
  mapCompleteStatus,
} from "./chat-ui.js";

function SafeText(props: { readonly value: string }): ReactElement {
  if (containsArabic(props.value)) {
    return <ArabicText>{props.value}</ArabicText>;
  }
  return <>{props.value}</>;
}

function MessageBubble(props: { readonly message: ChatMessage }): ReactElement {
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
        <SafeText value={props.message.content} />
      </p>

      {props.message.warning ? (
        <p className="zayd-chat__warning" role="note">
          <SafeText value={props.message.warning} />
        </p>
      ) : null}

      {props.message.limitations && props.message.limitations.length > 0 ? (
        <ul className="zayd-chat__limitations">
          {props.message.limitations.map((item) => (
            <li key={item}>
              <SafeText value={item} />
            </li>
          ))}
        </ul>
      ) : null}

      {props.message.citations && props.message.citations.length > 0 ? (
        <div className="zayd-chat__citations">
          <h3 className="zayd-chat__citations-title">อ้างอิงที่ตรวจสอบแล้ว</h3>
          <ul>
            {props.message.citations.map((citation) => (
              <li key={citation.citation_id}>
                <SafeText value={citation.display} />
                <span className="zayd-chat__citation-meta"> ({citation.source_type})</span>
              </li>
            ))}
          </ul>
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

export function ChatInterface(props: { readonly apiBaseUrl: string }): ReactElement {
  const [messages, setMessages] = useState<readonly ChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [stage, setStage] = useState<ChatStreamStage | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [sessionError, setSessionError] = useState<string | null>(null);
  const [guestReady, setGuestReady] = useState(false);
  const [retryQuestion, setRetryQuestion] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const guestTokenRef = useRef<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

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
          conversationId,
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
    [applyStreamEvent, conversationId, isStreaming, props.apiBaseUrl],
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
          messages.map((message) => <MessageBubble key={message.id} message={message} />)
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