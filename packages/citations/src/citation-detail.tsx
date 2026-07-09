"use client";

import type { ReactElement } from "react";
import { useEffect, useState } from "react";

import { fetchCitationDetail, CitationClientError } from "./api.js";
import { CITATION_KIND_LABELS, normalizeCitationKind } from "./labels.js";
import { AiExplanationNotice, SourceTextBlock } from "./safe-text.js";
import { SourceStatusWarnings } from "./source-warning.js";
import type { CitationDetail } from "./types.js";

function MetadataList(props: {
  readonly items: readonly { readonly label: string; readonly value: string | null }[];
}): ReactElement {
  const visible = props.items.filter((item) => item.value);
  if (visible.length === 0) {
    return <dl className="zayd-citation-detail__metadata" hidden />;
  }
  return (
    <dl className="zayd-citation-detail__metadata">
      {visible.map((item) => (
        <div key={item.label} className="zayd-citation-detail__metadata-row">
          <dt>{item.label}</dt>
          <dd>{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function CitationDetailView(props: {
  readonly apiBaseUrl: string;
  readonly citationRef: string;
}): ReactElement {
  const [detail, setDetail] = useState<CitationDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchCitationDetail(props.apiBaseUrl, props.citationRef)
      .then((payload) => {
        if (!cancelled) {
          setDetail(payload);
        }
      })
      .catch((caught: unknown) => {
        if (cancelled) {
          return;
        }
        const message =
          caught instanceof CitationClientError
            ? caught.message
            : "ไม่สามารถโหลดรายละเอียดอ้างอิงได้";
        setError(message);
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [props.apiBaseUrl, props.citationRef]);

  if (loading) {
    return <p aria-live="polite">กำลังโหลดรายละเอียดอ้างอิง…</p>;
  }

  if (error || !detail) {
    return (
      <p className="zayd-citation-detail__error" role="alert">
        {error ?? "ไม่พบข้อมูลอ้างอิง"}
      </p>
    );
  }

  const kind = normalizeCitationKind(detail.citation.citation_type);
  const verificationLabel = detail.citation.active ? "ตรวจสอบแล้ว" : "ถูกยกเลิก";

  return (
    <article className="zayd-citation-detail" aria-labelledby="citation-detail-title">
      <header className="zayd-citation-detail__header">
        <p className="zayd-citation-detail__kind">{CITATION_KIND_LABELS[kind]}</p>
        <h1 id="citation-detail-title" className="zayd-citation-detail__title">
          {detail.citation.display_title}
        </h1>
        <p className="zayd-citation-detail__status">สถานะ: {verificationLabel}</p>
      </header>

      <SourceStatusWarnings warnings={detail.warnings} />
      <AiExplanationNotice />

      <MetadataList
        items={[
          { label: "อ้างอิงมาตรฐาน", value: detail.citation.canonical_reference },
          { label: "เล่ม", value: detail.citation.volume },
          { label: "หน้า", value: detail.citation.page },
          { label: "สถานะหะดีษ", value: detail.citation.hadith_grade },
          { label: "ชื่อเอกสาร", value: detail.document?.title ?? null },
          { label: "ผู้แต่ง", value: detail.document?.author ?? null },
          { label: "ผู้แปล", value: detail.document?.translator ?? null },
          { label: "สำนักพิมพ์", value: detail.document?.publisher ?? null },
          { label: "ฉบับ", value: detail.document?.edition ?? null },
          { label: "แหล่ง", value: detail.source?.name ?? null },
        ]}
      />

      {detail.citation.arabic_text ? (
        <SourceTextBlock label="ข้อความต้นฉบับ" value={detail.citation.arabic_text} dir="rtl" />
      ) : null}

      {detail.citation.thai_translation ? (
        <SourceTextBlock label="คำแปลไทย" value={detail.citation.thai_translation} dir="ltr" />
      ) : null}

      {detail.source_text &&
      !detail.citation.arabic_text &&
      detail.source_text !== detail.citation.thai_translation ? (
        <SourceTextBlock label="ข้อความจากแหล่ง" value={detail.source_text} />
      ) : null}
    </article>
  );
}