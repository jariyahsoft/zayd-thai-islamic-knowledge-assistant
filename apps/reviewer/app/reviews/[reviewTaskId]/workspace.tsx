"use client";

import type { ReactElement } from "react";
import { useEffect, useMemo, useState } from "react";

import {
  addReviewComment,
  fetchReviewDraft,
  ReviewerClientError,
  submitReviewDecision,
  updateReviewDraft,
  type ReviewDraft,
  type ReviewRevision,
} from "../../reviewer-data.js";

function readStoredAccessToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem("zayd.access_token");
}

function stringifyMetadata(value: Record<string, unknown>): string {
  return JSON.stringify(value, null, 2);
}

function parseMetadata(value: string): Record<string, unknown> {
  const parsed = JSON.parse(value) as unknown;
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("metadata must be an object");
  }
  return parsed as Record<string, unknown>;
}

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString("th-TH", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function errorMessage(error: unknown): string {
  if (error instanceof ReviewerClientError) {
    if (error.code === "DOCUMENT_REVIEW_CONFLICT") {
      return "มีการแก้ไขจากที่อื่นแล้ว โหลดฉบับล่าสุดก่อนบันทึกอีกครั้ง";
    }
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "ไม่สามารถทำรายการได้";
}

export function DocumentReviewWorkspace(props: {
  readonly apiBaseUrl: string;
  readonly reviewTaskId: string;
}): ReactElement {
  const [draft, setDraft] = useState<ReviewDraft | null>(null);
  const [originalText, setOriginalText] = useState("");
  const [text, setText] = useState("");
  const [metadataText, setMetadataText] = useState("{}");
  const [comment, setComment] = useState("");
  const [commentLine, setCommentLine] = useState("");
  const [decision, setDecision] = useState<"approve" | "request_changes" | "reject">(
    "request_changes",
  );
  const [reason, setReason] = useState("");
  const [lastRevision, setLastRevision] = useState<ReviewRevision | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isDirty, setIsDirty] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadDraft(): Promise<void> {
    const accessToken = readStoredAccessToken();
    if (!accessToken) {
      setError("ต้องลงชื่อเข้าใช้ด้วยบัญชี reviewer ก่อนใช้งาน workspace");
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const nextDraft = await fetchReviewDraft(
        props.apiBaseUrl,
        accessToken,
        props.reviewTaskId,
      );
      setDraft(nextDraft);
      setOriginalText(nextDraft.editable_text ?? "");
      setText(nextDraft.editable_text ?? "");
      setMetadataText(stringifyMetadata(nextDraft.editable_metadata));
      setIsDirty(false);
      setNotice("โหลดฉบับล่าสุดแล้ว");
    } catch (loadError: unknown) {
      setError(errorMessage(loadError));
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadDraft();
  }, [props.apiBaseUrl, props.reviewTaskId]);

  useEffect(() => {
    function beforeUnload(event: BeforeUnloadEvent): void {
      if (!isDirty) {
        return;
      }
      event.preventDefault();
      event.returnValue = "";
    }

    window.addEventListener("beforeunload", beforeUnload);
    return () => window.removeEventListener("beforeunload", beforeUnload);
  }, [isDirty]);

  const textLineCount = useMemo(() => text.split(/\r?\n/).length, [text]);
  const metadataKeys = useMemo(() => {
    try {
      return Object.keys(parseMetadata(metadataText));
    } catch {
      return [];
    }
  }, [metadataText]);

  useEffect(() => {
    if (!draft || !isDirty || isSaving) {
      return undefined;
    }
    const timeoutId = window.setTimeout(() => {
      void saveDraft();
    }, 12000);
    return () => window.clearTimeout(timeoutId);
  }, [draft, isDirty, isSaving, metadataText, text]);

  async function saveDraft(): Promise<void> {
    if (!draft) {
      return;
    }
    const accessToken = readStoredAccessToken();
    if (!accessToken) {
      setError("เซสชันหมดอายุ กรุณาลงชื่อเข้าใช้อีกครั้ง");
      return;
    }

    let metadataUpdates: Record<string, unknown>;
    try {
      metadataUpdates = parseMetadata(metadataText);
    } catch {
      setError("metadata ต้องเป็น JSON object ที่ถูกต้อง");
      return;
    }

    setIsSaving(true);
    setError(null);
    try {
      const result = await updateReviewDraft(
        props.apiBaseUrl,
        accessToken,
        props.reviewTaskId,
        {
          base_task_row_version: draft.task_row_version,
          text,
          metadata_updates: metadataUpdates,
        },
      );
      setDraft({
        ...draft,
        task_row_version: result.task_row_version,
        editable_text: result.editable_text,
        editable_metadata: result.editable_metadata,
        latest_revision_number: result.revision.revision_number,
      });
      setLastRevision(result.revision);
      setIsDirty(false);
      setNotice(`บันทึก revision ${result.revision.revision_number} แล้ว`);
    } catch (saveError: unknown) {
      setError(errorMessage(saveError));
    } finally {
      setIsSaving(false);
    }
  }

  async function autosaveDraft(): Promise<void> {
    await saveDraft();
  }

  async function postComment(): Promise<void> {
    if (!comment.trim() || !draft) {
      return;
    }
    const accessToken = readStoredAccessToken();
    if (!accessToken) {
      setError("เซสชันหมดอายุ กรุณาลงชื่อเข้าใช้อีกครั้ง");
      return;
    }
    setError(null);
    try {
      const nextComment = await addReviewComment(
        props.apiBaseUrl,
        accessToken,
        props.reviewTaskId,
        {
          body: comment,
          anchor: commentLine ? { line: Number(commentLine) } : undefined,
        },
      );
      setDraft({ ...draft, comments: [...draft.comments, nextComment] });
      setComment("");
      setCommentLine("");
      setNotice("เพิ่ม comment แล้ว");
    } catch (commentError: unknown) {
      setError(errorMessage(commentError));
    }
  }

  async function decide(): Promise<void> {
    if (isDirty) {
      setError("ต้องบันทึกหรือโหลดฉบับล่าสุดก่อนส่ง decision");
      return;
    }
    if (!draft || !reason.trim()) {
      setError("ต้องระบุเหตุผลก่อนตัดสินใจ");
      return;
    }
    const accessToken = readStoredAccessToken();
    if (!accessToken) {
      setError("เซสชันหมดอายุ กรุณาลงชื่อเข้าใช้อีกครั้ง");
      return;
    }
    setError(null);
    try {
      const result = await submitReviewDecision(
        props.apiBaseUrl,
        accessToken,
        props.reviewTaskId,
        {
          decision,
          reason,
          base_task_row_version: draft.task_row_version,
        },
      );
      setDraft({
        ...draft,
        task_status: result.decision.resulting_task_status,
        document_review_status: result.decision.resulting_document_status,
        task_row_version: result.task_row_version,
      });
      setReason("");
      setNotice(`บันทึก decision: ${result.decision.decision}`);
    } catch (decisionError: unknown) {
      setError(errorMessage(decisionError));
    }
  }

  return (
    <main className="zayd-review-workspace">
      <header className="zayd-review-workspace__topbar">
        <div>
          <a className="zayd-review-workspace__back" href="/">
            กลับแดชบอร์ด
          </a>
          <h1>Document Review Workspace</h1>
          <p>Task {props.reviewTaskId}</p>
        </div>
        <div className="zayd-review-workspace__actions">
          <button type="button" onClick={() => void loadDraft()}>
            โหลดล่าสุด
          </button>
          <button type="button" onClick={() => void autosaveDraft()} disabled={!isDirty || isSaving}>
            {isSaving ? "กำลังบันทึก" : "Autosave"}
          </button>
          <button
            type="button"
            className="is-primary"
            onClick={() => void saveDraft()}
            disabled={!isDirty || isSaving}
          >
            บันทึก
          </button>
        </div>
      </header>

      {isLoading ? <p className="zayd-review-workspace__status">กำลังโหลด workspace...</p> : null}
      {notice ? <p className="zayd-review-workspace__notice">{notice}</p> : null}
      {error ? (
        <p className="zayd-review-workspace__error" role="alert">
          {error}
        </p>
      ) : null}

      {draft ? (
        <>
          <section className="zayd-review-workspace__statebar" aria-label="สถานะ review">
            <span>Task: {draft.task_status}</span>
            <span>Document: {draft.document_review_status}</span>
            <span>Row version: {draft.task_row_version}</span>
            <span>Revision: {draft.latest_revision_number}</span>
            <span>{isDirty ? "มีการแก้ไขที่ยังไม่บันทึก" : "ไม่มีการแก้ไขค้าง"}</span>
          </section>

          <section className="zayd-review-workspace__grid">
            <section className="zayd-review-workspace__pane" aria-label="ต้นฉบับแบบอ่านอย่างเดียว">
              <div className="zayd-review-workspace__pane-header">
                <h2>Original Source</h2>
                <span>read-only</span>
              </div>
              <dl className="zayd-review-workspace__facts">
                <div>
                  <dt>Original file key</dt>
                  <dd>{draft.original_file_key ?? "ไม่มีไฟล์ต้นฉบับ"}</dd>
                </div>
                <div>
                  <dt>Document version</dt>
                  <dd>{draft.document_version_id}</dd>
                </div>
              </dl>
              <pre className="zayd-review-workspace__source-preview">
                {originalText || "ไม่มี extracted text"}
              </pre>
            </section>

            <section className="zayd-review-workspace__pane" aria-label="ข้อความที่แก้ไขได้">
              <div className="zayd-review-workspace__pane-header">
                <h2>Extracted Text</h2>
                <span>{textLineCount} lines</span>
              </div>
              <textarea
                value={text}
                onChange={(event) => {
                  setText(event.target.value);
                  setIsDirty(true);
                }}
                spellCheck={false}
              />
            </section>

            <section className="zayd-review-workspace__pane" aria-label="metadata">
              <div className="zayd-review-workspace__pane-header">
                <h2>Metadata</h2>
                <span>{metadataKeys.length} fields</span>
              </div>
              <textarea
                value={metadataText}
                onChange={(event) => {
                  setMetadataText(event.target.value);
                  setIsDirty(true);
                }}
                spellCheck={false}
              />
            </section>

            <section className="zayd-review-workspace__pane" aria-label="translation and chunks">
              <div className="zayd-review-workspace__pane-header">
                <h2>Translation & Chunks</h2>
                <span>preview</span>
              </div>
              <div className="zayd-review-workspace__chunk-list">
                {text
                  .split(/\n{2,}/)
                  .filter(Boolean)
                  .slice(0, 4)
                  .map((chunk, index) => (
                    <article key={`${index}-${chunk.slice(0, 8)}`}>
                      <strong>Chunk {index + 1}</strong>
                      <p>{chunk.slice(0, 280)}</p>
                    </article>
                  ))}
              </div>
            </section>
          </section>

          <section className="zayd-review-workspace__bottom">
            <section className="zayd-review-workspace__pane" aria-label="diff">
              <div className="zayd-review-workspace__pane-header">
                <h2>Diff</h2>
                <span>{lastRevision ? `revision ${lastRevision.revision_number}` : "none"}</span>
              </div>
              <pre className="zayd-review-workspace__diff">
                {lastRevision?.diff_text ?? "Diff จะแสดงหลังจากบันทึก revision"}
              </pre>
            </section>

            <section className="zayd-review-workspace__pane" aria-label="comments">
              <div className="zayd-review-workspace__pane-header">
                <h2>Comments</h2>
                <span>{draft.comments.length}</span>
              </div>
              <div className="zayd-review-workspace__comment-form">
                <input
                  aria-label="line"
                  inputMode="numeric"
                  placeholder="line"
                  value={commentLine}
                  onChange={(event) => setCommentLine(event.target.value)}
                />
                <textarea
                  aria-label="comment"
                  placeholder="Comment"
                  value={comment}
                  onChange={(event) => setComment(event.target.value)}
                />
                <button type="button" onClick={() => void postComment()}>
                  เพิ่ม comment
                </button>
              </div>
              <ul className="zayd-review-workspace__comments">
                {draft.comments.map((item) => (
                  <li key={item.id}>
                    <p>{item.body}</p>
                    <span>
                      {formatDateTime(item.created_at)} · {JSON.stringify(item.anchor)}
                    </span>
                  </li>
                ))}
              </ul>
            </section>

            <section className="zayd-review-workspace__pane" aria-label="decision">
              <div className="zayd-review-workspace__pane-header">
                <h2>Decision</h2>
                <span>audited</span>
              </div>
              <select
                value={decision}
                onChange={(event) =>
                  setDecision(event.target.value as "approve" | "request_changes" | "reject")
                }
              >
                <option value="request_changes">Request changes</option>
                <option value="approve">Approve</option>
                <option value="reject">Reject</option>
              </select>
              <textarea
                placeholder="Reason"
                value={reason}
                onChange={(event) => setReason(event.target.value)}
              />
              <button type="button" className="is-danger" onClick={() => void decide()}>
                ส่ง decision
              </button>
            </section>
          </section>
        </>
      ) : null}
    </main>
  );
}
