# Citation Cards and Source Detail

Implementation notes for TASK-09-03.

## Architecture

| Area | Location |
|---|---|
| Shared citation UI | `packages/citations` |
| Citation detail page | `apps/web/app/citations/[citationId]/page.tsx` |
| Chat integration | `apps/web/app/chat/chat-interface.tsx` |
| Public APIs | `GET /citations/{citation_id}`, `GET /sources/{source_id}` |
| Styles | `apps/web/app/globals.css` (`.zayd-citation*` classes) |

## Citation Cards

`CitationCard` renders visually distinct cards by type:

| Type | Visual treatment |
|---|---|
| `quran` | Green accent, label "อัลกุรอาน" |
| `hadith` | Amber accent, label "หะดีษ" |
| `book` / `fiqh` | Blue accent, label "หนังสือ" |
| `document` | Neutral accent, label "เอกสาร" |

Cards link to `/citations/{citation_id}` when the streaming `citation_id` is a registry UUID or `CIT-{uuid}` token.

`CitationCardList` adds a notice that AI explanation in the answer body is separate from direct source references (FR-CIT-008).

## Source Detail View

`CitationDetailView` loads governed metadata via `GET /citations/{citation_id}` and shows:

- Verification state and warning banners (`citation_invalidated`, `source_suspended`, `document_version_unavailable`)
- Type-specific metadata (volume/page, hadith grade, document author/translator/publisher)
- Original Arabic text (`dir="rtl"`) and Thai translation in dedicated blocks
- Chunk `source_text` when no dedicated Arabic/Thai fields exist

An `AiExplanationNotice` clarifies that model explanation stays in the chat answer, not mixed with quoted source text.

## Security and Safe Rendering

- No `dangerouslySetInnerHTML`; all text uses React text nodes or `ArabicText`.
- Public APIs return only governed registry fields; no hidden prompts or chain-of-thought.
- Invalidated or suspended sources remain readable with explicit warnings instead of silent omission.

## Accessibility

- Warning banners use `role="alert"`.
- Citation cards expose descriptive `aria-label`s.
- Source blocks use semantic headings and `dir`/`lang` attributes for RTL/LTR content.

## Tests

- `packages/citations/src/citations.test.ts` — card variants, warnings, API client, XSS contract
- `services/orchestrator/tests/test_citation_detail.py` — registry detail reader
- `services/api/tests/test_citations_api.py` — public citation/source endpoints
- `apps/web/app/citations/citations.test.ts` — page wiring and styles

## Follow-up Tasks

- TASK-09-06 — saved answers may reuse citation cards for bookmarked references.