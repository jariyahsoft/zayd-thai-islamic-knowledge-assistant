"use client";

import { useEffect, useState, type ReactElement } from "react";

import { fetchFeedbackReviewQueue, ReviewerClientError, type FeedbackReviewQueue } from "../reviewer-data.js";

const labels: Record<string, string> = {
  incorrect_answer: "คำตอบไม่ถูกต้อง",
  citation_error: "อ้างอิงผิดพลาด",
  incomplete_answer: "คำตอบไม่ครบ",
  inappropriate_content: "เนื้อหาไม่เหมาะสม",
  other: "อื่นๆ",
};

export function FeedbackReviewQueuePage(props: { readonly apiBaseUrl: string }): ReactElement {
  const [queue, setQueue] = useState<FeedbackReviewQueue | null>(null);
  const [status, setStatus] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = window.localStorage.getItem("zayd.access_token");
    if (!token) {
      setError("ต้องลงชื่อเข้าใช้ด้วยบัญชี reviewer");
      return;
    }
    void fetchFeedbackReviewQueue(props.apiBaseUrl, token, status || undefined)
      .then(setQueue)
      .catch((cause: unknown) => setError(cause instanceof ReviewerClientError ? cause.message : "ไม่สามารถโหลดคิว feedback ได้"));
  }, [props.apiBaseUrl, status]);

  return <main className="zayd-reviewer">
    <a className="zayd-reviewer__panel-link" href="/">← แดชบอร์ดผู้ตรวจ</a>
    <h1>คิวตรวจ feedback</h1>
    <label>สถานะ <select value={status} onChange={(event) => setStatus(event.target.value)}><option value="">รายการที่ดำเนินการได้</option><option value="open">เปิด</option><option value="in_review">กำลังตรวจ</option><option value="resolved">แก้ไขแล้ว</option><option value="dismissed">ปิดโดยไม่ดำเนินการ</option></select></label>
    {error ? <p role="alert" className="zayd-reviewer__empty">{error}</p> : null}
    {queue ? <section className="zayd-reviewer__panel"><p>ทั้งหมด {queue.total_count} รายการ</p><ul className="zayd-reviewer__feedback-list">{queue.items.map((item) => <li key={item.id} className="zayd-reviewer__feedback-item"><div><p className="zayd-reviewer__feedback-title">{labels[item.category] ?? item.category}</p><p className="zayd-reviewer__task-meta">{item.status} · {item.priority} · {item.severity.toUpperCase()}</p><p className="zayd-reviewer__task-meta">{item.root_cause ?? "ยังไม่จัดประเภท"}</p></div><a className="zayd-reviewer__panel-link" href={`/feedback/${item.id}`}>ตรวจสอบ</a></li>)}</ul></section> : null}
  </main>;
}
