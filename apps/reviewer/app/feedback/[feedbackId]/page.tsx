"use client";

import { useEffect, useState, type ReactElement } from "react";
import { fetchFeedbackReviewDetail, ReviewerClientError, type FeedbackReviewDetail } from "../../reviewer-data.js";

export default function FeedbackDetailPage({ params }: { readonly params: { readonly feedbackId: string } }): ReactElement {
  const [detail, setDetail] = useState<FeedbackReviewDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const token = window.localStorage.getItem("zayd.access_token");
    if (!token) { setError("ต้องลงชื่อเข้าใช้ด้วยบัญชี reviewer"); return; }
    void fetchFeedbackReviewDetail(process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000", token, params.feedbackId)
      .then(setDetail)
      .catch((cause: unknown) => setError(cause instanceof ReviewerClientError ? cause.message : "ไม่สามารถโหลดรายการ feedback ได้"));
  }, [params.feedbackId]);
  return <main className="zayd-reviewer"><a className="zayd-reviewer__panel-link" href="/feedback">← คิว feedback</a><h1>ตรวจสอบ feedback</h1>{error ? <p role="alert">{error}</p> : null}{detail ? <section className="zayd-reviewer__panel"><p>สถานะ: {detail.status} · ความสำคัญ: {detail.priority} · ความรุนแรง: {detail.severity.toUpperCase()}</p><p>สาเหตุ: {detail.root_cause ?? "ยังไม่จัดประเภท"}</p><p>บันทึกผู้ตรวจ: {detail.reviewer_notes || "ไม่มี"}</p><p>การแก้ไข: {detail.resolution ?? "ยังไม่ปิดรายการ"}</p><h2>Trace context</h2><p className="zayd-reviewer__task-meta">{detail.trace_context ? "มี retrieval/model/prompt/policy identifiers สำหรับการตรวจสอบ" : "ไม่มี trace context"}</p></section> : null}</main>;
}
