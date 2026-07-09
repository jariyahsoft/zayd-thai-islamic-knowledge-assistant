"use client";

import type { ReactElement } from "react";
import { useCallback, useEffect, useState } from "react";
import {
  ConversationsClientError,
  deleteAllConversations,
  deleteConversation,
  fetchConversations,
  type ConversationSummary,
} from "@zayd/conversations";

import { readStoredAccessToken } from "../chat/chat-stream.js";

function formatUpdatedAt(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString("th-TH", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export function HistoryList(props: { readonly apiBaseUrl: string }): ReactElement {
  const [conversations, setConversations] = useState<readonly ConversationSummary[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [isSignedIn, setIsSignedIn] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const loadConversations = useCallback(
    async (query?: string) => {
      const accessToken = readStoredAccessToken();
      if (!accessToken) {
        setIsSignedIn(false);
        setConversations([]);
        setIsLoading(false);
        return;
      }

      setIsSignedIn(true);
      setIsLoading(true);
      setError(null);
      try {
        const result = await fetchConversations(props.apiBaseUrl, accessToken, {
          query: query?.trim() || undefined,
        });
        setConversations(result.conversations);
      } catch (loadError: unknown) {
        setConversations([]);
        setError(
          loadError instanceof ConversationsClientError
            ? loadError.message
            : "ไม่สามารถโหลดประวัติการสนทนาได้",
        );
      } finally {
        setIsLoading(false);
      }
    },
    [props.apiBaseUrl],
  );

  useEffect(() => {
    void loadConversations();
  }, [loadConversations]);

  const handleSearchSubmit = useCallback(
    (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      void loadConversations(searchQuery);
    },
    [loadConversations, searchQuery],
  );

  const handleDelete = useCallback(
    async (conversationId: string) => {
      const accessToken = readStoredAccessToken();
      if (!accessToken) {
        return;
      }
      setIsDeleting(true);
      setStatusMessage(null);
      try {
        await deleteConversation(props.apiBaseUrl, accessToken, conversationId);
        setConversations((current) => current.filter((item) => item.id !== conversationId));
        setStatusMessage("ลบการสนทนาแล้ว");
      } catch (deleteError: unknown) {
        setError(
          deleteError instanceof ConversationsClientError
            ? deleteError.message
            : "ไม่สามารถลบการสนทนาได้",
        );
      } finally {
        setIsDeleting(false);
      }
    },
    [props.apiBaseUrl],
  );

  const handleDeleteAll = useCallback(async () => {
    const accessToken = readStoredAccessToken();
    if (!accessToken) {
      return;
    }
    if (!window.confirm("ลบประวัติการสนทนาทั้งหมดของคุณหรือไม่?")) {
      return;
    }
    setIsDeleting(true);
    setStatusMessage(null);
    try {
      const deletedCount = await deleteAllConversations(props.apiBaseUrl, accessToken);
      setConversations([]);
      setStatusMessage(`ลบประวัติแล้ว ${deletedCount} รายการ`);
    } catch (deleteError: unknown) {
      setError(
        deleteError instanceof ConversationsClientError
          ? deleteError.message
          : "ไม่สามารถลบประวัติทั้งหมดได้",
      );
    } finally {
      setIsDeleting(false);
    }
  }, [props.apiBaseUrl]);

  if (!isSignedIn) {
    return (
      <section className="zayd-history__guest" aria-live="polite">
        <p>ประวัติการสนทนาพร้อมใช้งานเมื่อลงชื่อเข้าใช้บัญชีแล้ว</p>
        <p className="zayd-history__note">
          โหมดผู้เยี่ยมชมไม่บันทึกประวัติบนเซิร์ฟเวอร์ คุณสามารถเปิดโหมดไม่ใช้ประวัติได้ในการตั้งค่า
        </p>
      </section>
    );
  }

  return (
    <section className="zayd-history" aria-labelledby="history-heading">
      <form className="zayd-history__search" onSubmit={handleSearchSubmit}>
        <label className="zayd-history__search-label" htmlFor="history-search">
          ค้นหาประวัติ
        </label>
        <div className="zayd-history__search-row">
          <input
            id="history-search"
            className="zayd-history__search-input"
            type="search"
            value={searchQuery}
            placeholder="ค้นหาจากหัวข้อหรือคำถาม"
            onChange={(event) => {
              setSearchQuery(event.target.value);
            }}
          />
          <button className="zayd-history__button" type="submit" disabled={isLoading}>
            ค้นหา
          </button>
        </div>
      </form>

      <div className="zayd-history__actions">
        <button
          className="zayd-history__button zayd-history__button--danger"
          type="button"
          disabled={isDeleting || conversations.length === 0}
          onClick={() => {
            void handleDeleteAll();
          }}
        >
          ลบประวัติทั้งหมด
        </button>
      </div>

      {isLoading ? <p className="zayd-history__status">กำลังโหลดประวัติ…</p> : null}
      {statusMessage ? (
        <p className="zayd-history__status" aria-live="polite">
          {statusMessage}
        </p>
      ) : null}
      {error ? (
        <p className="zayd-history__error" role="alert">
          {error}
        </p>
      ) : null}

      {!isLoading && conversations.length === 0 ? (
        <p className="zayd-history__empty">ยังไม่มีประวัติที่บันทึก</p>
      ) : null}

      <ul className="zayd-history__list">
        {conversations.map((conversation) => (
          <li key={conversation.id} className="zayd-history__item">
            <div className="zayd-history__item-main">
              <a className="zayd-history__title" href={`/chat?conversation=${conversation.id}`}>
                {conversation.title ?? conversation.preview ?? "การสนทนา"}
              </a>
              {conversation.preview ? (
                <p className="zayd-history__preview">{conversation.preview}</p>
              ) : null}
              <p className="zayd-history__meta">
                อัปเดต {formatUpdatedAt(conversation.updatedAt)} · {conversation.messageCount} ข้อความ
              </p>
            </div>
            <button
              className="zayd-history__button zayd-history__button--danger"
              type="button"
              disabled={isDeleting}
              onClick={() => {
                void handleDelete(conversation.id);
              }}
            >
              ลบ
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}