import type { CitationKind } from "./types.js";

export const CITATION_KIND_LABELS: Record<CitationKind, string> = {
  quran: "อัลกุรอาน",
  hadith: "หะดีษ",
  book: "หนังสือ",
  document: "เอกสาร",
};

export const CITATION_WARNING_LABELS: Record<string, string> = {
  citation_invalidated: "อ้างอิงนี้ถูกยกเลิกการใช้งานแล้ว",
  source_suspended: "แหล่งอ้างอิงถูกระงับชั่วคราว",
  document_version_unavailable: "ฉบับเอกสารไม่พร้อมให้แสดง",
};

export function normalizeCitationKind(value: string): CitationKind {
  const normalized = value.trim().toLowerCase();
  if (normalized === "quran") {
    return "quran";
  }
  if (normalized === "hadith") {
    return "hadith";
  }
  if (normalized === "book" || normalized === "fiqh") {
    return "book";
  }
  return "document";
}

export function formatWarning(code: string): string {
  return CITATION_WARNING_LABELS[code] ?? code;
}

const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const TOKEN_PATTERN =
  /^CIT-[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function isResolvableCitationRef(value: string): boolean {
  const normalized = value.trim();
  return UUID_PATTERN.test(normalized) || TOKEN_PATTERN.test(normalized);
}

export function citationDetailPath(citationRef: string): string {
  return `/citations/${encodeURIComponent(citationRef)}`;
}