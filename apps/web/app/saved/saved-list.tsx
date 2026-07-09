"use client";

import type { ReactElement } from "react";
import { useCallback, useEffect, useState } from "react";
import { CitationCardList, SourceStatusWarnings } from "@zayd/citations";
import {
  SavedAnswersClientError,
  fetchSavedAnswers,
  unsaveAnswer,
  type SavedAnswerRecord,
} from "@zayd/saved-answers";
import { ArabicText } from "@zayd/ui";

import { readStoredAccessToken } from "../chat/chat-stream.js";

function formatSavedAt(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString("th-TH", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function SavedAnswerBody(props: { readonly value: string }): ReactElement {
  if (/[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]/u.test(props.value)) {
    return <ArabicText>{props.value}</ArabicText>;
  }
  return <>{props.value}</>;
}

export function SavedList(props: { readonly apiBaseUrl: string }): ReactElement {
  const [records, setRecords] = useState<readonly SavedAnswerRecord[]>([]);
  const [isSignedIn, setIsSignedIn] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isUpdating, setIsUpdating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadSavedAnswers = useCallback(async () => {
    const accessToken = readStoredAccessToken();
    if (!accessToken) {
      setIsSignedIn(false);
      setRecords([]);
      setIsLoading(false);
      return;
    }
    setIsSignedIn(true);
    setIsLoading(true);
    setError(null);
    try {
      const result = await fetchSavedAnswers(props.apiBaseUrl, accessToken);
      setRecords(result.savedAnswers);
    } catch (loadError: unknown) {
      setRecords([]);
      setError(
        loadError instanceof SavedAnswersClientError
          ? loadError.message
          : "ไม่สามารถโหลดคำตอบที่บันทึกได้",
      );
    } finally {
      setIsLoading(false);
    }
  }, [props.apiBaseUrl]);

  useEffect(() => {
    void loadSavedAnswers();
  }, [loadSavedAnswers]);

  const handleUnsave = useCallback(
    async (savedAnswerId: string) => {
      const accessToken = readStoredAccessToken();
      if (!accessToken) {
        return;
      }
      setIsUpdating(true);
      setError(null);
      try {
        await unsaveAnswer(props.apiBaseUrl, accessToken, savedAnswerId);
        setRecords((current) => current.filter((item) => item.id !== savedAnswerId));
      } catch (updateError: unknown) {
        setError(
          updateError instanceof SavedAnswersClientError
            ? updateError.message
            : "ไม่สามารถยกเลิกการบันทึกได้",
        );
      } finally {
        setIsUpdating(false);
      }
    },
    [props.apiBaseUrl],
  );

  if (!isSignedIn) {
    return (
      <section className="zayd-saved__guest" aria-live="polite">
        <p>บันทึกคำตอบโปรดได้เมื่อลงชื่อเข้าใช้บัญชีแล้ว</p>
      </section>
    );
  }

  return (
    <section className="zayd-saved" aria-labelledby="saved-heading">
      {isLoading ? <p className="zayd-saved__status">กำลังโหลดคำตอบที่บันทึก…</p> : null}
      {error ? (
        <p className="zayd-saved__error" role="alert">
          {error}
        </p>
      ) : null}
      {!isLoading && records.length === 0 ? (
        <p className="zayd-saved__empty">ยังไม่มีคำตอบที่บันทึก</p>
      ) : null}

      <ul className="zayd-saved__list">
        {records.map((record) => (
          <li key={record.id} className="zayd-saved__item">
            <header className="zayd-saved__item-header">
              <div>
                <h3>{record.summary || "คำตอบที่บันทึก"}</h3>
                <p className="zayd-saved__meta">
                  บันทึกเมื่อ {formatSavedAt(record.savedAt)} · มัซฮับ {record.madhhab}
                </p>
              </div>
              <button
                type="button"
                className="zayd-saved__button"
                disabled={isUpdating}
                onClick={() => {
                  void handleUnsave(record.id);
                }}
              >
                ยกเลิกการบันทึก
              </button>
            </header>

            <SourceStatusWarnings warnings={record.warnings} />

            <p className="zayd-saved__body">
              <SavedAnswerBody value={record.answerTh} />
            </p>

            <CitationCardList
              citations={record.citations.map((citation) => ({
                citation_id: citation.citationId,
                display: citation.display,
                source_type: citation.sourceType,
                verification_status: citation.verificationStatus,
              }))}
            />
          </li>
        ))}
      </ul>
    </section>
  );
}