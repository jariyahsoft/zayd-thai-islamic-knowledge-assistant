"use client";

import type { ReactElement } from "react";
import { useEffect, useState } from "react";

import {
  fetchPrincipal,
  fetchReviewerDashboard,
  ReviewerClientError,
  type ReviewTaskSummary,
  type ReviewerDashboardData,
} from "./reviewer-data.js";

function readStoredAccessToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem("zayd.access_token");
}

type DashboardFilter = "all" | "assigned" | "overdue";

const REVIEW_STATUS_OPTIONS = [
  { value: "", label: "ทุกสถานะ" },
  { value: "open", label: "รอตรวจ" },
  { value: "in_progress", label: "กำลังตรวจ" },
  { value: "completed", label: "เสร็จแล้ว" },
  { value: "cancelled", label: "ยกเลิก" },
] as const;

const CATEGORY_LABELS: Record<string, string> = {
  incorrect_answer: "คำตอบไม่ถูกต้อง",
  citation_error: "อ้างอิงผิดพลาด",
  incomplete_answer: "คำตอบไม่ครบ",
  inappropriate_content: "เนื้อหาไม่เหมาะสม",
  other: "อื่นๆ",
};

function formatDateTime(value: string | null): string {
  if (!value) {
    return "ไม่มีวันครบกำหนด";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString("th-TH", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function badgeClass(status: string): string {
  switch (status) {
    case "open":
      return "zayd-reviewer__badge zayd-reviewer__badge--open";
    case "in_progress":
      return "zayd-reviewer__badge zayd-reviewer__badge--progress";
    case "completed":
      return "zayd-reviewer__badge zayd-reviewer__badge--done";
    default:
      return "zayd-reviewer__badge";
  }
}

function statusLabel(status: string): string {
  switch (status) {
    case "open":
      return "รอตรวจ";
    case "in_progress":
      return "กำลังตรวจ";
    case "completed":
      return "เสร็จแล้ว";
    case "cancelled":
      return "ยกเลิก";
    default:
      return status;
  }
}

function priorityLabel(priority: string): string {
  switch (priority) {
    case "urgent":
      return "ด่วนมาก";
    case "high":
      return "สูง";
    case "normal":
      return "ปกติ";
    case "low":
      return "ต่ำ";
    default:
      return priority;
  }
}

function reviewLevelLabel(value: string): string {
  return value === "scholar" ? "ระดับผู้ทรงคุณวุฒิ" : "ระดับผู้ตรวจ";
}

function SummaryCard(props: {
  readonly label: string;
  readonly value: number;
  readonly tone?: "neutral" | "warning" | "danger";
}): ReactElement {
  const className =
    props.tone === "danger"
      ? "zayd-reviewer__summary-card zayd-reviewer__summary-card--danger"
      : props.tone === "warning"
        ? "zayd-reviewer__summary-card zayd-reviewer__summary-card--warning"
        : "zayd-reviewer__summary-card";
  return (
    <article className={className}>
      <p className="zayd-reviewer__summary-label">{props.label}</p>
      <p className="zayd-reviewer__summary-value">{props.value}</p>
    </article>
  );
}

function QueueCard(props: { readonly task: ReviewTaskSummary }): ReactElement {
  return (
    <li className="zayd-reviewer__task-card">
      <div className="zayd-reviewer__task-header">
        <span className={badgeClass(props.task.status)}>{statusLabel(props.task.status)}</span>
        <span className="zayd-reviewer__priority">{priorityLabel(props.task.priority)}</span>
      </div>
      <h3 className="zayd-reviewer__task-title">
        <a href={`/reviews/${props.task.id}`}>{props.task.document_title ?? "เอกสารไม่มีชื่อ"}</a>
      </h3>
      <p className="zayd-reviewer__task-meta">
        {reviewLevelLabel(props.task.review_level)} · {props.task.language ?? "ไม่ระบุภาษา"} ·{" "}
        {props.task.madhhab ?? "ไม่ระบุมัซฮับ"}
      </p>
      <p className="zayd-reviewer__task-meta">
        ครบกำหนด {formatDateTime(props.task.due_at)} · อัปเดต {formatDateTime(props.task.updated_at)}
      </p>
      <p className="zayd-reviewer__task-meta">
        ประเภท {props.task.document_type ?? props.task.category ?? "ไม่ระบุ"} · ผู้รับผิดชอบ{" "}
        {props.task.assigned_to ? "มีผู้รับงานแล้ว" : "ยังไม่รับงาน"}
      </p>
    </li>
  );
}

export function ReviewerDashboard(props: {
  readonly apiBaseUrl: string;
}): ReactElement {
  const [dashboard, setDashboard] = useState<ReviewerDashboardData | null>(null);
  const [filter, setFilter] = useState<DashboardFilter>("all");
  const [status, setStatus] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [principalEmail, setPrincipalEmail] = useState<string | null>(null);
  const [principalRoles, setPrincipalRoles] = useState<readonly string[]>([]);

  useEffect(() => {
    let cancelled = false;

    async function load(): Promise<void> {
      const accessToken = readStoredAccessToken();
      if (!accessToken) {
        if (!cancelled) {
          setError("ต้องลงชื่อเข้าใช้ด้วยบัญชี reviewer ก่อนใช้งานแดชบอร์ด");
          setIsLoading(false);
        }
        return;
      }

      setIsLoading(true);
      setError(null);
      try {
        const principal = await fetchPrincipal(props.apiBaseUrl, accessToken);
        const nextDashboard = await fetchReviewerDashboard(props.apiBaseUrl, accessToken, {
          status: status || undefined,
          assignedToUserId: filter === "assigned" ? principal.id : undefined,
          dueOnly: filter === "overdue" ? "overdue" : "all",
          limit: 12,
          feedbackLimit: 5,
        });
        if (cancelled) {
          return;
        }
        setPrincipalEmail(principal.email);
        setPrincipalRoles(principal.roles);
        setDashboard(nextDashboard);
      } catch (loadError: unknown) {
        if (cancelled) {
          return;
        }
        setDashboard(null);
        setError(
          loadError instanceof ReviewerClientError
            ? loadError.message
            : "ไม่สามารถโหลดแดชบอร์ดผู้ตรวจได้",
        );
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [filter, props.apiBaseUrl, status]);

  return (
    <main className="zayd-reviewer">
      <section className="zayd-reviewer__hero">
        <div>
          <p className="zayd-reviewer__eyebrow">Reviewer Portal</p>
          <h1 className="zayd-reviewer__title">แดชบอร์ดผู้ตรวจ</h1>
          <p className="zayd-reviewer__subtitle">
            ติดตามคิวงานเอกสาร งานค้าง กำหนดส่ง และรายงาน feedback โดยไม่เปิดเผยข้อมูลเกินสิทธิ์
          </p>
        </div>
        <div className="zayd-reviewer__identity">
          <p>{principalEmail ?? "ยังไม่ทราบผู้ใช้"}</p>
          <p>{principalRoles.join(", ") || "ยังไม่พบบทบาท"}</p>
        </div>
      </section>

      <section className="zayd-reviewer__filters" aria-label="ตัวกรองแดชบอร์ด">
        <div className="zayd-reviewer__filter-group" role="tablist" aria-label="มุมมองงาน">
          <button
            type="button"
            className={filter === "all" ? "zayd-reviewer__tab is-active" : "zayd-reviewer__tab"}
            onClick={() => setFilter("all")}
          >
            ทั้งหมด
          </button>
          <button
            type="button"
            className={
              filter === "assigned" ? "zayd-reviewer__tab is-active" : "zayd-reviewer__tab"
            }
            onClick={() => setFilter("assigned")}
          >
            งานของฉัน
          </button>
          <button
            type="button"
            className={
              filter === "overdue" ? "zayd-reviewer__tab is-active" : "zayd-reviewer__tab"
            }
            onClick={() => setFilter("overdue")}
          >
            เลยกำหนด
          </button>
        </div>

        <label className="zayd-reviewer__status-filter" htmlFor="review-status">
          สถานะคิว
          <select
            id="review-status"
            value={status}
            onChange={(event) => setStatus(event.target.value)}
          >
            {REVIEW_STATUS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </section>

      {isLoading ? (
        <p className="zayd-reviewer__status" aria-live="polite">
          กำลังโหลดแดชบอร์ดผู้ตรวจ…
        </p>
      ) : null}
      {error ? (
        <p className="zayd-reviewer__error" role="alert">
          {error}
        </p>
      ) : null}

      {dashboard ? (
        <>
          <section className="zayd-reviewer__summary-grid" aria-label="สรุปคิวงาน">
            <SummaryCard label="คิวที่มองเห็น" value={dashboard.summary.total_visible_count} />
            <SummaryCard label="รอตรวจ" value={dashboard.summary.pending_count} />
            <SummaryCard label="งานของฉัน" value={dashboard.summary.assigned_count} />
            <SummaryCard
              label="เลยกำหนด"
              value={dashboard.summary.overdue_count}
              tone={dashboard.summary.overdue_count > 0 ? "danger" : "neutral"}
            />
            <SummaryCard
              label="ต้องแก้ไข"
              value={dashboard.summary.changes_requested_count}
              tone={dashboard.summary.changes_requested_count > 0 ? "warning" : "neutral"}
            />
            <SummaryCard
              label="feedback เปิดอยู่"
              value={dashboard.summary.feedback_open_count}
              tone={dashboard.summary.feedback_open_count > 0 ? "warning" : "neutral"}
            />
          </section>

          <section className="zayd-reviewer__panel">
            <div className="zayd-reviewer__panel-header">
              <div>
                <h2>คิวงานล่าสุด</h2>
                <p>จำนวนทั้งหมด {dashboard.queue.total_count} รายการ</p>
              </div>
              <a className="zayd-reviewer__panel-link" href="/reviews/queue">
                เปิดคิวเต็ม
              </a>
            </div>
            {dashboard.queue.tasks.length === 0 ? (
              <p className="zayd-reviewer__empty">ไม่พบงานตามตัวกรองปัจจุบัน</p>
            ) : (
              <ul className="zayd-reviewer__task-list">
                {dashboard.queue.tasks.map((task) => (
                  <QueueCard key={task.id} task={task} />
                ))}
              </ul>
            )}
          </section>

          <section className="zayd-reviewer__panel">
            <div className="zayd-reviewer__panel-header">
              <div>
                <h2>feedback ที่รอตรวจ</h2>
                <p>แสดงเฉพาะข้อมูลขั้นต่ำเพื่อ triage</p>
              </div>
              <a className="zayd-reviewer__panel-link" href="/feedback">
                เปิดคิว feedback
              </a>
            </div>
            {dashboard.feedback_items.length === 0 ? (
              <p className="zayd-reviewer__empty">ไม่มี feedback เปิดอยู่ในขณะนี้</p>
            ) : (
              <ul className="zayd-reviewer__feedback-list">
                {dashboard.feedback_items.map((item) => (
                  <li key={item.id} className="zayd-reviewer__feedback-item">
                    <div>
                      <p className="zayd-reviewer__feedback-title">
                        {CATEGORY_LABELS[item.category] ?? item.category}
                      </p>
                      <p className="zayd-reviewer__task-meta">
                        สถานะ {statusLabel(item.status)} · ส่งเมื่อ {formatDateTime(item.created_at)}
                      </p>
                    </div>
                    <div className="zayd-reviewer__feedback-refs">
                      <span>Answer {item.answer_id ? "พร้อมอ้างอิง" : "ไม่ระบุคำตอบ"}</span>
                      <span>{item.citation_id ? "มี citation" : "ไม่มี citation"}</span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      ) : null}
    </main>
  );
}
