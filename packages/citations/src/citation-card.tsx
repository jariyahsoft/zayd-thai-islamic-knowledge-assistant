import type { ReactElement } from "react";

import {
  CITATION_KIND_LABELS,
  citationDetailPath,
  isResolvableCitationRef,
  normalizeCitationKind,
} from "./labels.js";
import { SafeCitationText } from "./safe-text.js";
import type { StreamCitation } from "./types.js";

export type CitationCardProps = {
  readonly citation: StreamCitation;
  readonly detailBasePath?: string;
};

function cardClassName(kind: ReturnType<typeof normalizeCitationKind>): string {
  return `zayd-citation-card zayd-citation-card--${kind}`;
}

export function CitationCard(props: CitationCardProps): ReactElement {
  const kind = normalizeCitationKind(props.citation.source_type);
  const resolvable = isResolvableCitationRef(props.citation.citation_id);
  const href = resolvable
    ? props.detailBasePath
      ? `${props.detailBasePath}/${encodeURIComponent(props.citation.citation_id)}`
      : citationDetailPath(props.citation.citation_id)
    : undefined;

  const body = (
    <>
      <p className="zayd-citation-card__kind">{CITATION_KIND_LABELS[kind]}</p>
      <p className="zayd-citation-card__title">
        <SafeCitationText value={props.citation.display} />
      </p>
      <p className="zayd-citation-card__meta">
        สถานะการตรวจสอบ: {props.citation.verification_status}
      </p>
      {!resolvable ? (
        <p className="zayd-citation-card__meta">รายละเอียดแหล่งอ้างอิงจะพร้อมเมื่อเชื่อมกับทะเบียนอ้างอิง</p>
      ) : null}
    </>
  );

  if (!href) {
    return (
      <article className={cardClassName(kind)} aria-label={`อ้างอิง ${props.citation.display}`}>
        {body}
      </article>
    );
  }

  return (
    <a
      className={`${cardClassName(kind)} zayd-citation-card--link`}
      href={href}
      aria-label={`ดูรายละเอียดอ้างอิง ${props.citation.display}`}
    >
      {body}
      <span className="zayd-citation-card__action">ดูแหล่งอ้างอิง</span>
    </a>
  );
}

export function CitationCardList(props: {
  readonly citations: readonly StreamCitation[];
  readonly title?: string;
  readonly detailBasePath?: string;
}): ReactElement | null {
  if (props.citations.length === 0) {
    return null;
  }

  return (
    <section className="zayd-citation-list" aria-label={props.title ?? "อ้างอิงที่ตรวจสอบแล้ว"}>
      <h3 className="zayd-citation-list__title">{props.title ?? "อ้างอิงที่ตรวจสอบแล้ว"}</h3>
      <div className="zayd-citation-list__grid">
        {props.citations.map((citation) => (
          <CitationCard
            key={citation.citation_id}
            citation={citation}
            detailBasePath={props.detailBasePath}
          />
        ))}
      </div>
      <p className="zayd-citation-list__notice" role="note">
        ข้อความในคำตอบด้านบนเป็นคำอธิบายจากระบบ การ์ดด้านล่างแยกข้อมูลจากแหล่งอ้างอิงโดยตรง
      </p>
    </section>
  );
}