import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { isValidElement } from "react";
import { describe, expect, it, vi } from "vitest";

import { fetchCitationDetail } from "./api.js";
import { CitationCard, CitationCardList } from "./citation-card.js";
import {
  citationDetailPath,
  formatWarning,
  isResolvableCitationRef,
  normalizeCitationKind,
} from "./labels.js";
import { containsArabic, SafeCitationText } from "./safe-text.js";
import { SourceStatusWarnings } from "./source-warning.js";

const citationsDir = dirname(fileURLToPath(import.meta.url));

describe("citation labels and routing", () => {
  it("normalizes source types into citation kinds", () => {
    expect(normalizeCitationKind("quran")).toBe("quran");
    expect(normalizeCitationKind("hadith")).toBe("hadith");
    expect(normalizeCitationKind("fiqh")).toBe("book");
    expect(normalizeCitationKind("other")).toBe("document");
  });

  it("detects resolvable citation references", () => {
    expect(
      isResolvableCitationRef("CIT-550e8400-e29b-41d4-a716-446655440000"),
    ).toBe(true);
    expect(isResolvableCitationRef("550e8400-e29b-41d4-a716-446655440000")).toBe(true);
    expect(isResolvableCitationRef("CIT-deadbeef")).toBe(false);
  });

  it("formats warning codes in Thai", () => {
    expect(formatWarning("source_suspended")).toContain("ระงับ");
    expect(citationDetailPath("CIT-550e8400-e29b-41d4-a716-446655440000")).toBe(
      "/citations/CIT-550e8400-e29b-41d4-a716-446655440000",
    );
  });
});

describe("citation components", () => {
  it("renders distinct card variants by source type", () => {
    const quran = CitationCard({
      citation: {
        citation_id: "CIT-550e8400-e29b-41d4-a716-446655440000",
        display: "Al-Fatihah 1:1",
        source_type: "quran",
        verification_status: "verified",
      },
    });
    expect(isValidElement(quran)).toBe(true);

    const hadith = CitationCard({
      citation: {
        citation_id: "CIT-550e8400-e29b-41d4-a716-446655440001",
        display: "Sahih Bukhari 1",
        source_type: "hadith",
        verification_status: "verified",
      },
    });
    expect(isValidElement(hadith)).toBe(true);
  });

  it("renders citation list with AI/source separation notice", () => {
    const list = CitationCardList({
      citations: [
        {
          citation_id: "CIT-550e8400-e29b-41d4-a716-446655440000",
          display: "Al-Fatihah 1:1",
          source_type: "quran",
          verification_status: "verified",
        },
      ],
    });
    expect(isValidElement(list)).toBe(true);
    const source = readFileSync(join(citationsDir, "citation-card.tsx"), "utf8");
    expect(source).toContain("คำอธิบายจากระบบ");
  });

  it("shows warning banners for suspended or invalidated sources", () => {
    const warnings = SourceStatusWarnings({ warnings: ["source_suspended"] });
    expect(isValidElement(warnings)).toBe(true);
    if (!isValidElement(warnings)) {
      return;
    }
    const props = warnings.props as { role?: string };
    expect(props.role).toBe("alert");
  });

  it("isolates Arabic rendering for RTL source text", () => {
    expect(containsArabic("بسم الله")).toBe(true);
    const text = SafeCitationText({ value: "بسم الله" });
    expect(isValidElement(text)).toBe(true);
  });
});

describe("citation detail API client", () => {
  it("fetches citation detail from the public API", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        json: async () => ({
          citation: {
            id: "550e8400-e29b-41d4-a716-446655440000",
            token: "CIT-550e8400-e29b-41d4-a716-446655440000",
            canonical_reference: "quran:1:1",
            document_version_id: "1",
            chunk_id: "2",
            citation_type: "quran",
            display_title: "Al-Fatihah 1:1",
            arabic_text: "بسم الله",
            thai_translation: "ด้วยพระนามของอัลลอฮฺ",
            hadith_grade: null,
            volume: "1",
            page: "1",
            verified: true,
            active: true,
            invalidated_at: null,
            registry_version: "citation-registry-v1",
          },
          source_text: "reviewed citation content",
          source: null,
          document: null,
          warnings: [],
          registry_version: "citation-registry-v1",
        }),
      })),
    );

    const detail = await fetchCitationDetail(
      "http://localhost:8000/",
      "CIT-550e8400-e29b-41d4-a716-446655440000",
    );
    expect(detail.citation.citation_type).toBe("quran");
    vi.unstubAllGlobals();
  });
});

describe("safe rendering contract", () => {
  it("does not use dangerouslySetInnerHTML in citation UI", () => {
    for (const file of ["citation-card.tsx", "citation-detail.tsx", "safe-text.tsx"]) {
      const source = readFileSync(join(citationsDir, file), "utf8");
      expect(source).not.toContain("dangerouslySetInnerHTML");
    }
  });
});