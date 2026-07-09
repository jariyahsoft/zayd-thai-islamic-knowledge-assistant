import type { ReactElement, ReactNode } from "react";
import { ArabicText } from "@zayd/ui";

const ARABIC_PATTERN = /[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]/u;

export function containsArabic(value: string): boolean {
  return ARABIC_PATTERN.test(value);
}

export function SafeCitationText(props: { readonly value: string }): ReactElement {
  if (containsArabic(props.value)) {
    return <ArabicText>{props.value}</ArabicText>;
  }
  return <>{props.value}</>;
}

export function SourceTextBlock(props: {
  readonly label: string;
  readonly value: string;
  readonly dir?: "rtl" | "ltr";
}): ReactElement {
  const isArabic = props.dir === "rtl" || containsArabic(props.value);
  return (
    <section className="zayd-citation-detail__source-block">
      <h3 className="zayd-citation-detail__source-label">{props.label}</h3>
      <p
        className={
          isArabic
            ? "zayd-citation-detail__source-text zayd-citation-detail__source-text--rtl"
            : "zayd-citation-detail__source-text"
        }
        dir={isArabic ? "rtl" : "ltr"}
        lang={isArabic ? "ar" : "th"}
      >
        {isArabic ? <ArabicText>{props.value}</ArabicText> : props.value}
      </p>
    </section>
  );
}

export function AiExplanationNotice(props: { readonly children?: ReactNode }): ReactElement {
  return (
    <p className="zayd-citation-detail__ai-notice" role="note">
      {props.children ??
        "คำอธิบายจากระบบอยู่ในคำตอบหลักด้านบน ส่วนนี้แสดงเฉพาะข้อความจากแหล่งอ้างอิงที่ตรวจสอบแล้ว"}
    </p>
  );
}