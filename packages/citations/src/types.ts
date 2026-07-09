export type CitationKind = "quran" | "hadith" | "book" | "document";

export type StreamCitation = {
  readonly citation_id: string;
  readonly display: string;
  readonly source_type: string;
  readonly verification_status: string;
};

export type CitationRecord = {
  readonly id: string;
  readonly token: string;
  readonly canonical_reference: string;
  readonly document_version_id: string;
  readonly chunk_id: string;
  readonly citation_type: string;
  readonly display_title: string;
  readonly arabic_text: string | null;
  readonly thai_translation: string | null;
  readonly hadith_grade: string | null;
  readonly volume: string | null;
  readonly page: string | null;
  readonly verified: boolean;
  readonly active: boolean;
  readonly invalidated_at: string | null;
  readonly registry_version: string;
};

export type CitationSourceSummary = {
  readonly id: string;
  readonly name: string;
  readonly source_type: string;
  readonly language: string;
  readonly is_active: boolean;
  readonly reliability_level: number;
};

export type CitationDocumentSummary = {
  readonly id: string;
  readonly title: string;
  readonly author: string | null;
  readonly translator: string | null;
  readonly publisher: string | null;
  readonly edition: string | null;
  readonly language: string;
  readonly document_type: string;
  readonly version_status: string;
};

export type CitationDetail = {
  readonly citation: CitationRecord;
  readonly source_text: string | null;
  readonly source: CitationSourceSummary | null;
  readonly document: CitationDocumentSummary | null;
  readonly warnings: readonly string[];
  readonly registry_version: string;
};

export type PublicSourceDetail = {
  readonly source: {
    readonly id: string;
    readonly name: string;
    readonly source_type: string;
    readonly owner: string | null;
    readonly website: string | null;
    readonly language: string;
    readonly country: string | null;
    readonly reliability_level: number;
    readonly is_active: boolean;
  };
  readonly warnings: readonly string[];
};