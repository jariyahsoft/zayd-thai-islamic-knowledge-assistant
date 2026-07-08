# Metadata Extraction Architecture

## Overview

The **Metadata Extraction Service** uses configurable rule-based extractors to
suggest structured metadata from parsed document text.  All suggested fields
are marked **UNVERIFIED** so they cannot overwrite reviewed metadata without
explicit human approval.

```
Parser Output → Normalisation → Metadata Extraction → Review Queue
                                    ↓
              Suggestions stored as version metadata (all UNVERIFIED)
```

## Design Principles

1. **All machine-generated fields are UNVERIFIED.**  A reviewer must
   explicitly promote suggestions to VERIFIED before they overwrite the
   canonical Document metadata.  Extraction cannot publish or overwrite
   reviewed metadata automatically.

2. **Original text preserved.**  Extraction never mutates the source text.
   All extracted metadata is stored separately in version metadata.

3. **Deterministic and versioned.**  The same input always produces the same
   suggestions.  Each extractor has a version string; the policy version is
   recorded in every result.

4. **Extractor protocol.**  The `MetadataExtractor` protocol allows
   rule-based, AI/LLM, or hybrid providers to be swapped without changing
   the service layer.

## Extracted Fields

| Field | Sources | Default |
|---|---|---|
| `title` | First non-empty line | None |
| `author` | Thai: โดย/ผู้แต่ง/เขียนโดย — Arabic: تأليف/المؤلف — English: Author:/authored by | None |
| `translator` | Thai: ผู้แปล/แปลโดย — Arabic: ترجمة/المترجم — English: Translated by:/Translator: | None |
| `madhhab` | Keyword match: shafii, hanafi, maliki, hanbali, jafari | `unknown` |
| `document_type` | Filename extension → type mapping | `unknown` |
| `publisher` | Not yet detected (rule-based) | [] |
| `edition` | Not yet detected (rule-based) | [] |
| `chapters` | ATX-like heading patterns (บทที่, فصل, باب) | [] |
| `references` | Quranic (อัลกุรอาน X:Y, Quran X:Y) and Hadith patterns | [] |

## Schema Validation

The service validates structured output before persistence:

- **Confidence:** Must be between 0.0 and 1.0.
- **Madhhab:** Must be in the approved set or defaults to `unknown`.
- **Document type:** Must be in the approved set or defaults to `unknown`.

Invalid output raises `MetadataExtractionError` with code
`EXTRACTION_MALFORMED_OUTPUT`.

## Extractor Protocol

```python
class MetadataExtractor(Protocol):
    @property
    def name(self) -> str: ...
    @property
    def version(self) -> str: ...
    @property
    def prompt_version(self) -> str | None: ...

    def extract(
        self,
        *,
        text: str,
        sections: list[dict[str, Any]],
        filename: str,
        content_type: str,
    ) -> MetadataExtractionResult: ...
```

### RuleBasedExtractor

The default extractor uses deterministic rules:

1. **Title:** First non-empty line of the extracted text.
2. **Author:** Searches the first 50 lines for Thai (`โดย`, `ผู้แต่ง`,
   `เขียนโดย`), Arabic (`تأليف`, `المؤلف`), or English (`Author:`,
   `authored by`) markers and takes the text after the marker.
3. **Translator:** Searches for Thai (`ผู้แปล`, `แปลโดย`), Arabic
   (`ترجمة`, `المترجم`), or English (`Translated by:`, `Translator:`)
   markers.
4. **Madhhab:** Scans the full text for known madhhab names.
5. **Document type:** Inferred from the filename extension.
6. **Chapters:** Detected by ATX-like heading patterns.
7. **References:** Quranic verse patterns and hadith reference patterns.

### AI Providers

When an AI/LLM extractor is used, the `prompt_version` field records the
exact prompt version that generated the suggestion.  This enables prompt
provenance and regression testing.

## Result Types

### NormalizationResult

```python
@dataclass(frozen=True)
class ExtractedField:
    name: str                          # field name (e.g. "title", "author")
    value: str | None                  # suggested value
    confidence: float                  # 0.0–1.0
    verification_status: str           # "unverified" | "verified" | "overridden_by_reviewer"
    extractor_name: str                # which extractor produced this
    extractor_version: str             # extractor version
    prompt_version: str | None         # prompt version (AI providers only)
    reason: str | None                 # why this value was suggested
```

### MetadataExtractionResult

Contains lists of `ExtractedField`, `ExtractedChapter`, and `ExtractedReference`
for all supported metadata dimensions.

## API

The extraction service is not exposed via API in this task.  It is called
programmatically during document ingestion:

```python
from zayd_common.metadata_extraction import MetadataExtractionService, RuleBasedExtractor

service = MetadataExtractionService(uow, extractor=RuleBasedExtractor())
result = service.extract(document_version_id=version_id)
```

## Security

- All extracted fields are marked UNVERIFIED and cannot overwrite reviewed
  metadata.
- Extraction operates on in-memory strings only; no filesystem access.
- No secrets, production data, or restricted religious content are stored
  in extraction metadata.
- Extractor output is validated schematically before persistence.
- The service enforces RBAC through the caller (typically the ingestion
  pipeline).
