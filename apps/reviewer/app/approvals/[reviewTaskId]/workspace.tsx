"use client";

import type { ReactElement } from "react";
import { useEffect, useState } from "react";

import {
  createScholarApproval,
  fetchApprovalHistory,
  fetchApprovalRequirements,
  fetchLicenseDetail,
  fetchLicensePolicyDecision,
  fetchReviewDraft,
  fetchSourceDetail,
  revokeScholarApproval,
  ReviewerClientError,
  type ApprovalListResult,
  type ApprovalRequirement,
  type LicenseDetail,
  type LicensePolicyDecision,
  type ReviewDraft,
  type SourceDetail,
} from "../../reviewer-data.js";

function readStoredAccessToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem("zayd.access_token");
}

function formatDateTime(value: string | null): string {
  if (!value) {
    return "ไม่ระบุ";
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

function errorMessage(error: unknown): string {
  if (error instanceof ReviewerClientError) {
    if (error.code === "SCHOLAR_APPROVAL_SELF_APPROVAL_DENIED") {
      return "ระบบปฏิเสธการอนุมัติเอกสารของตนเองตามหลัก separation of duties";
    }
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "ไม่สามารถทำรายการได้";
}

type WorkspaceState = {
  draft: ReviewDraft;
  source: SourceDetail | null;
  license: LicenseDetail | null;
  policyDecision: LicensePolicyDecision | null;
  approvals: ApprovalListResult;
  requirement: ApprovalRequirement;
};

const CONTENT_RISK_OPTIONS = [
  { value: "routine", label: "Routine" },
  { value: "sensitive", label: "Sensitive" },
  { value: "restricted", label: "Restricted" },
] as const;

const APPROVAL_LEVEL_OPTIONS = [
  { value: "initial", label: "Initial" },
  { value: "scholar", label: "Scholar" },
  { value: "board", label: "Board" },
] as const;

export function ScholarApprovalWorkspace(props: {
  readonly apiBaseUrl: string;
  readonly reviewTaskId: string;
}): ReactElement {
  const [workspace, setWorkspace] = useState<WorkspaceState | null>(null);
  const [contentRisk, setContentRisk] = useState<ApprovalRequirement["content_risk"]>("sensitive");
  const [approvalLevel, setApprovalLevel] = useState<"initial" | "scholar" | "board">("scholar");
  const [reason, setReason] = useState("");
  const [revokeReason, setRevokeReason] = useState("");
  const [selectedApprovalId, setSelectedApprovalId] = useState<string>("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadWorkspace(nextRisk: ApprovalRequirement["content_risk"]): Promise<void> {
    const accessToken = readStoredAccessToken();
    if (!accessToken) {
      setError("ต้องลงชื่อเข้าใช้ด้วยบัญชี senior scholar หรือ admin ก่อนใช้งาน");
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const draft = await fetchReviewDraft(props.apiBaseUrl, accessToken, props.reviewTaskId);
      const [source, license, policyDecision, approvals, requirement] = await Promise.all([
        draft.source_id
          ? fetchSourceDetail(props.apiBaseUrl, accessToken, draft.source_id)
          : Promise.resolve(null),
        draft.source_license_id
          ? fetchLicenseDetail(props.apiBaseUrl, accessToken, draft.source_license_id)
          : Promise.resolve(null),
        draft.source_license_id
          ? fetchLicensePolicyDecision(
              props.apiBaseUrl,
              accessToken,
              draft.source_license_id,
              "retrieval",
            )
          : Promise.resolve(null),
        fetchApprovalHistory(props.apiBaseUrl, accessToken, draft.document_version_id),
        fetchApprovalRequirements(
          props.apiBaseUrl,
          accessToken,
          draft.document_version_id,
          nextRisk,
        ),
      ]);
      setWorkspace({ draft, source, license, policyDecision, approvals, requirement });
      setSelectedApprovalId((current) => current || approvals.approvals[0]?.id || "");
      setNotice("โหลดสถานะการอนุมัติล่าสุดแล้ว");
    } catch (loadError: unknown) {
      setWorkspace(null);
      setError(errorMessage(loadError));
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadWorkspace(contentRisk);
  }, [contentRisk, props.apiBaseUrl, props.reviewTaskId]);

  async function submitApproval(): Promise<void> {
    if (!workspace || !reason.trim()) {
      setError("ต้องระบุเหตุผลการอนุมัติก่อนส่ง");
      return;
    }
    const accessToken = readStoredAccessToken();
    if (!accessToken) {
      setError("เซสชันหมดอายุ กรุณาลงชื่อเข้าใช้อีกครั้ง");
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      await createScholarApproval(props.apiBaseUrl, accessToken, props.reviewTaskId, {
        content_risk: contentRisk,
        approval_level: approvalLevel,
        reason,
      });
      setReason("");
      setNotice("บันทึกการอนุมัติแล้ว");
      await loadWorkspace(contentRisk);
    } catch (submitError: unknown) {
      setError(errorMessage(submitError));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function submitRevoke(): Promise<void> {
    if (!selectedApprovalId || !revokeReason.trim()) {
      setError("ต้องเลือก approval และระบุเหตุผลก่อน revoke");
      return;
    }
    const accessToken = readStoredAccessToken();
    if (!accessToken) {
      setError("เซสชันหมดอายุ กรุณาลงชื่อเข้าใช้อีกครั้ง");
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      await revokeScholarApproval(props.apiBaseUrl, accessToken, selectedApprovalId, {
        reason: revokeReason,
      });
      setRevokeReason("");
      setNotice("เพิกถอน approval แล้ว");
      await loadWorkspace(contentRisk);
    } catch (revokeError: unknown) {
      setError(errorMessage(revokeError));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="zayd-approval">
      <header className="zayd-approval__hero">
        <div>
          <a className="zayd-approval__back" href="/">
            กลับแดชบอร์ด
          </a>
          <p className="zayd-approval__eyebrow">Scholar Approval Workspace</p>
          <h1>หน้าตรวจอนุมัติโดยผู้ทรงคุณวุฒิ</h1>
          <p>
            ตรวจหลักฐาน แหล่งข้อมูล สิทธิ์การใช้งาน มัซฮับ และประวัติ approval ก่อนอนุมัติหรือเพิกถอน
          </p>
        </div>
        <div className="zayd-approval__hero-card">
          <p>Task {props.reviewTaskId}</p>
          <p>{workspace?.draft.document_title ?? "กำลังโหลดเอกสาร"}</p>
          <p>{workspace?.draft.document_review_status ?? "ไม่ทราบสถานะ"}</p>
        </div>
      </header>

      {isLoading ? <p className="zayd-approval__status">กำลังโหลด scholar workspace...</p> : null}
      {notice ? <p className="zayd-approval__notice">{notice}</p> : null}
      {error ? (
        <p className="zayd-approval__error" role="alert">
          {error}
        </p>
      ) : null}

      {workspace ? (
        <>
          <section className="zayd-approval__statebar">
            <span>Document version: {workspace.draft.document_version_id}</span>
            <span>Canonical ID: {workspace.draft.canonical_id ?? "ไม่ระบุ"}</span>
            <span>Madhhab: {workspace.draft.madhhab ?? "ไม่ระบุ"}</span>
            <span>Language: {workspace.draft.language ?? "ไม่ระบุ"}</span>
          </section>

          <section className="zayd-approval__grid">
            <section className="zayd-approval__panel">
              <div className="zayd-approval__panel-header">
                <h2>Required Evidence</h2>
                <span>before approval</span>
              </div>
              <dl className="zayd-approval__facts">
                <div>
                  <dt>Document title</dt>
                  <dd>{workspace.draft.document_title ?? "ไม่ระบุ"}</dd>
                </div>
                <div>
                  <dt>Document type</dt>
                  <dd>{workspace.draft.document_type ?? "ไม่ระบุ"}</dd>
                </div>
                <div>
                  <dt>Original file key</dt>
                  <dd>{workspace.draft.original_file_key ?? "ไม่มีไฟล์ต้นฉบับ"}</dd>
                </div>
                <div>
                  <dt>Review history</dt>
                  <dd>
                    {workspace.draft.revisions.length} revisions · {workspace.draft.comments.length} comments
                  </dd>
                </div>
              </dl>
              <pre className="zayd-approval__preview">
                {workspace.draft.editable_text?.slice(0, 1800) ?? "ไม่มีข้อความฉบับตรวจ"}
              </pre>
            </section>

            <section className="zayd-approval__panel">
              <div className="zayd-approval__panel-header">
                <h2>Source and License Status</h2>
                <span>RBAC protected</span>
              </div>
              <dl className="zayd-approval__facts">
                <div>
                  <dt>Source</dt>
                  <dd>{workspace.source?.source.name ?? "ไม่พบ source"}</dd>
                </div>
                <div>
                  <dt>Reliability</dt>
                  <dd>{workspace.source?.source.reliability_level ?? "ไม่ระบุ"}</dd>
                </div>
                <div>
                  <dt>License</dt>
                  <dd>
                    {workspace.license?.license_name ?? "ไม่พบ license"}{" "}
                    {workspace.license?.license_version ?? ""}
                  </dd>
                </div>
                <div>
                  <dt>License status</dt>
                  <dd>{workspace.license?.status ?? "ไม่ระบุ"}</dd>
                </div>
                <div>
                  <dt>Workflow allowed</dt>
                  <dd>
                    {workspace.policyDecision?.workflow_allowed ? "allowed" : "blocked"} ·{" "}
                    {workspace.policyDecision?.policy_version ?? "n/a"}
                  </dd>
                </div>
                <div>
                  <dt>Warnings</dt>
                  <dd>{workspace.source?.warnings.join(", ") || "ไม่มี"}</dd>
                </div>
              </dl>
              <ul className="zayd-approval__reason-codes">
                {(workspace.policyDecision?.reason_codes ?? []).map((code) => (
                  <li key={code}>{code}</li>
                ))}
              </ul>
            </section>

            <section className="zayd-approval__panel">
              <div className="zayd-approval__panel-header">
                <h2>Conflicts and Madhhab Metadata</h2>
                <span>read-only</span>
              </div>
              <ul className="zayd-approval__reason-codes">
                {workspace.draft.revisions.slice(0, 3).map((revision) => (
                  <li key={revision.id}>
                    revision {revision.revision_number} · changed fields:{" "}
                    {revision.metadata_changed_fields.join(", ") || "text only"}
                  </li>
                ))}
              </ul>
              <pre className="zayd-approval__metadata">
                {JSON.stringify(workspace.draft.editable_metadata, null, 2)}
              </pre>
            </section>

            <section className="zayd-approval__panel">
              <div className="zayd-approval__panel-header">
                <h2>Approval Matrix</h2>
                <span>{workspace.requirement.ready_for_publish ? "ready" : "pending"}</span>
              </div>
              <label className="zayd-approval__field">
                Content risk
                <select
                  value={contentRisk}
                  onChange={(event) =>
                    setContentRisk(event.target.value as ApprovalRequirement["content_risk"])
                  }
                >
                  {CONTENT_RISK_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <p>
                Required levels: {workspace.requirement.required_levels.join(", ") || "none"}
              </p>
              <p>
                Satisfied levels: {workspace.requirement.satisfied_levels.join(", ") || "none"}
              </p>
              <p className="zayd-approval__missing">
                Missing levels: {workspace.requirement.missing_levels.join(", ") || "none"}
              </p>
              {!workspace.requirement.ready_for_publish ? (
                <p className="zayd-approval__warning">
                  License-block UI state remains visible until required approvals are complete.
                </p>
              ) : null}
            </section>
          </section>

          <section className="zayd-approval__bottom">
            <section className="zayd-approval__panel">
              <div className="zayd-approval__panel-header">
                <h2>Approval Actions</h2>
                <span>server-side separation of duties</span>
              </div>
              <label className="zayd-approval__field">
                Approval level
                <select
                  value={approvalLevel}
                  onChange={(event) =>
                    setApprovalLevel(
                      event.target.value as "initial" | "scholar" | "board",
                    )
                  }
                >
                  {APPROVAL_LEVEL_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <textarea
                placeholder="Reason for approval"
                value={reason}
                onChange={(event) => setReason(event.target.value)}
              />
              <button
                type="button"
                className="is-primary"
                onClick={() => void submitApproval()}
                disabled={isSubmitting}
              >
                {isSubmitting ? "กำลังบันทึก" : "สร้าง approval"}
              </button>
            </section>

            <section className="zayd-approval__panel">
              <div className="zayd-approval__panel-header">
                <h2>Review History</h2>
                <span>{workspace.approvals.approvals.length} approvals</span>
              </div>
              <ul className="zayd-approval__history">
                {workspace.approvals.approvals.map((approval) => (
                  <li key={approval.id}>
                    <strong>
                      {approval.approval_level} · {approval.status}
                    </strong>
                    <p>{approval.reason}</p>
                    <span>
                      {formatDateTime(approval.created_at)} · valid until{" "}
                      {formatDateTime(approval.valid_until)}
                    </span>
                    {approval.revoke_reason ? <span>Revoked: {approval.revoke_reason}</span> : null}
                  </li>
                ))}
              </ul>
            </section>

            <section className="zayd-approval__panel">
              <div className="zayd-approval__panel-header">
                <h2>Revoke Approval</h2>
                <span>audited</span>
              </div>
              <label className="zayd-approval__field">
                Approval record
                <select
                  value={selectedApprovalId}
                  onChange={(event) => setSelectedApprovalId(event.target.value)}
                >
                  <option value="">เลือก approval</option>
                  {workspace.approvals.approvals.map((approval) => (
                    <option key={approval.id} value={approval.id}>
                      {approval.approval_level} · {approval.status} · {approval.id}
                    </option>
                  ))}
                </select>
              </label>
              <textarea
                placeholder="Reason for revoke"
                value={revokeReason}
                onChange={(event) => setRevokeReason(event.target.value)}
              />
              <button
                type="button"
                className="is-danger"
                onClick={() => void submitRevoke()}
                disabled={isSubmitting}
              >
                {isSubmitting ? "กำลังประมวลผล" : "revoke approval"}
              </button>
            </section>
          </section>
        </>
      ) : null}
    </main>
  );
}
