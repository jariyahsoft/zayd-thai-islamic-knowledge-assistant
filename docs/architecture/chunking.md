# Retrieval Chunking

TASK-07-01 introduces a versioned chunking framework for retrieval-visible document text. It is used by the publishing service when a reviewed document version is frozen for retrieval.

## Inputs

The framework accepts either reviewed plain text or parser sections. A section may carry:

- content text
- heading or section label
- page start and end
- content type such as `text`, `heading`, or `table`
- parser metadata

Empty input is rejected with `CHUNKING_EMPTY_CONTENT`. Invalid fixed-window settings fail with stable `CHUNKING_INVALID_WINDOW` or `CHUNKING_INVALID_OVERLAP` errors.

## Strategy Order

Chunking selects the first matching semantic strategy in this order:

1. Quran verse: `quran-verse-v1`
2. Hadith record: `hadith-record-v1`
3. Fiqh issue: `fiqh-issue-v1`
4. Heading section: `heading-section-v1`
5. Table block: `table-block-v1`
6. Paragraph: `paragraph-v1`
7. Fixed window fallback: `fixed-window-v1`

The framework version is `retrieval-chunking-v1`. Publishing records the framework version and the selected per-chunk strategy version so later indexing jobs can identify stale chunks after a strategy change.

## Boundaries

Quran references such as `Quran 2:255` are kept as verse-level chunks. Hadith and fiqh text is split at record or issue boundaries. Markdown headings and parser heading sections become section-level chunks. Parser table sections and markdown-like pipe tables are kept intact as table chunks. Paragraphs are preserved when no higher-priority semantic structure applies. Large unstructured blocks fall back to fixed windows with overlap.

Fixed-window defaults are 180 tokens with 30 tokens of overlap. Publishing uses the same 180 token maximum so it keeps the previous retrieval size envelope while adding semantic boundaries.

## References and Context

Every chunk draft includes:

- immutable `document_version_id`
- zero-based `chunk_index`
- original and normalized content
- token count
- page start and end when supplied
- section label when supplied
- canonical reference in the form `<canonical_id>:v<version_number>:<semantic-suffix>`
- strategy name and version
- framework version
- normalization framework and normalizer version
- optional `context_before` and `context_after`

Publishing stores each draft as a `document_chunks` row. The row `chunking_strategy_version` is the selected semantic strategy version, while metadata also records the framework version, strategy name, embedding placeholder metadata, citation placeholder metadata, source license details, and publish timestamp.

## Publishing Integration

The document publishing service calls `chunk_text_for_retrieval` after approval and license gates pass but before retrieval visibility flips. Chunks are inserted with `is_published=false`, publishing metadata is recorded on the immutable document version, and only then are chunks and the document version made visible in one transaction.

If chunking rejects empty content, publishing returns `DOCUMENT_PUBLISH_EMPTY_CONTENT` and leaves no searchable chunks. Existing idempotency behavior is unchanged: retries for an already published version return existing chunks, while pre-visibility retries regenerate draft chunks deterministically.

## Security and License Notes

Chunking is deterministic local processing. It does not call external providers, import datasets, or bypass publishing gates. Retrieval visibility remains controlled by published document status, chunk `is_published`, and license checks in the publishing pipeline.
