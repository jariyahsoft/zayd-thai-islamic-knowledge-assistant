"""Deterministic multilingual query expansion for retrieval."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from zayd_common.normalization import NORMALIZATION_FRAMEWORK_VERSION, normalize_text

QUERY_EXPANSION_VERSION = "query-expansion-v1"
QUERY_EXPANSION_POLICY_VERSION = "query-expansion-policy-v1"

ExpansionLanguage = Literal["th", "ar", "en", "mixed"]
ExpansionKind = Literal["original", "normalized", "terminology_variant"]

_SUPPORTED_LANGUAGES = frozenset({"th", "ar", "en", "mixed"})
_REFERENCE_PATTERN = re.compile(
    r"\b(?:[a-z][a-z0-9_-]*:){1,}[a-z0-9_.:-]+\b|\b(?:quran|hadith)\s+\d+[:.]\d+\b",
    re.IGNORECASE,
)

_TERM_GROUPS: dict[str, dict[str, tuple[str, ...]]] = {
    "prayer": {
        "th": ("ละหมาด", "ซอลาต"),
        "ar": ("الصلاة", "صلاة"),
        "en": ("prayer", "salat", "salah"),
    },
    "hadith": {
        "th": ("ฮะดีษ", "หะดีษ"),
        "ar": ("حديث", "الحديث"),
        "en": ("hadith",),
    },
    "quran": {
        "th": ("อัลกุรอาน", "กุรอาน"),
        "ar": ("القرآن", "قرآن"),
        "en": ("quran", "al-quran"),
    },
    "zakat": {
        "th": ("ซะกาต", "ซะกาห์"),
        "ar": ("زكاة", "الزكاة"),
        "en": ("zakat",),
    },
    "fasting": {
        "th": ("ถือศีลอด", "ศีลอด"),
        "ar": ("صيام", "الصيام"),
        "en": ("fasting", "sawm"),
    },
    "ablution": {
        "th": ("วุฎูอ์", "อาบน้ำละหมาด"),
        "ar": ("وضوء", "الوضوء"),
        "en": ("wudu", "ablution"),
    },
}


class QueryExpansionError(Exception):
    def __init__(self, code: str, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class QueryExpansionPolicy:
    enabled: bool = True
    include_cross_language: bool = True
    include_terminology_variants: bool = True
    preserve_named_references: bool = True
    max_expansions: int = 8
    version: str = QUERY_EXPANSION_POLICY_VERSION


@dataclass(frozen=True)
class QueryExpansionRequest:
    text: str
    language: ExpansionLanguage
    madhhab: str | None = None
    policy: QueryExpansionPolicy = QueryExpansionPolicy()


@dataclass(frozen=True)
class QueryExpansionItem:
    text: str
    normalized_text: str
    language: ExpansionLanguage
    kind: ExpansionKind
    source_terms: tuple[str, ...] = ()
    concept_id: str | None = None


@dataclass(frozen=True)
class QueryExpansionResponse:
    original_text: str
    query_language: ExpansionLanguage
    detected_language: ExpansionLanguage
    expansion_version: str
    policy_version: str
    disabled: bool
    limited: bool
    named_reference_preserved: bool
    expansions: tuple[QueryExpansionItem, ...]
    trace: dict[str, object]

    def as_retrieval_trace(self) -> dict[str, object]:
        return self.trace


class QueryExpansionService:
    """Expand retrieval queries without changing intent or metadata filters."""

    def expand(self, request: QueryExpansionRequest) -> QueryExpansionResponse:
        self._validate(request)
        text = request.text.strip()
        detected_language = _detect_language(text, request.language)
        named_reference_preserved = bool(_REFERENCE_PATTERN.search(text))
        normalized = normalize_text(text, language=request.language).normalized

        if not request.policy.enabled:
            disabled_expansions: tuple[QueryExpansionItem, ...] = (
                QueryExpansionItem(
                    text=text,
                    normalized_text=normalized,
                    language=request.language,
                    kind="original",
                ),
            )
            return self._response(
                request=request,
                detected_language=detected_language,
                named_reference_preserved=named_reference_preserved,
                expansions=disabled_expansions,
                disabled=True,
                limited=False,
            )

        candidates: list[QueryExpansionItem] = [
            QueryExpansionItem(
                text=text,
                normalized_text=normalized,
                language=request.language,
                kind="original",
            )
        ]
        if normalized != text:
            candidates.append(
                QueryExpansionItem(
                    text=normalized,
                    normalized_text=normalized,
                    language=request.language,
                    kind="normalized",
                )
            )

        if request.policy.include_terminology_variants and not (
            named_reference_preserved and request.policy.preserve_named_references
        ):
            candidates.extend(
                self._terminology_variants(
                    text=text,
                    query_language=request.language,
                    include_cross_language=request.policy.include_cross_language,
                )
            )

        deduped_expansions = _dedupe(candidates)
        limited = len(deduped_expansions) > request.policy.max_expansions
        expansions: tuple[QueryExpansionItem, ...] = tuple(
            deduped_expansions[: request.policy.max_expansions]
        )
        return self._response(
            request=request,
            detected_language=detected_language,
            named_reference_preserved=named_reference_preserved,
            expansions=expansions,
            disabled=False,
            limited=limited,
        )

    def _terminology_variants(
        self,
        *,
        text: str,
        query_language: ExpansionLanguage,
        include_cross_language: bool,
    ) -> list[QueryExpansionItem]:
        matched = _matched_concepts(text)
        variants: list[QueryExpansionItem] = []
        target_languages: tuple[str, ...]
        if include_cross_language:
            target_languages = ("th", "ar", "en")
        elif query_language == "mixed":
            target_languages = ("th", "ar", "en")
        else:
            target_languages = (query_language,)

        for concept_id in matched:
            group = _TERM_GROUPS[concept_id]
            source_terms = tuple(
                term for terms in group.values() for term in terms if _contains(text, term)
            )
            for language in target_languages:
                for term in group.get(language, ()):
                    normalized = normalize_text(term, language=language).normalized
                    variants.append(
                        QueryExpansionItem(
                            text=term,
                            normalized_text=normalized,
                            language=language,  # type: ignore[arg-type]
                            kind="terminology_variant",
                            source_terms=source_terms,
                            concept_id=concept_id,
                        )
                    )
        return variants

    def _validate(self, request: QueryExpansionRequest) -> None:
        if not request.text.strip():
            raise QueryExpansionError(
                "QUERY_EXPANSION_TEXT_REQUIRED",
                "Query text is required for expansion.",
                status_code=400,
            )
        if request.language not in _SUPPORTED_LANGUAGES:
            raise QueryExpansionError(
                "QUERY_EXPANSION_LANGUAGE_UNSUPPORTED",
                "Query expansion language must be th, ar, en, or mixed.",
                status_code=400,
            )
        if request.policy.max_expansions < 1 or request.policy.max_expansions > 50:
            raise QueryExpansionError(
                "QUERY_EXPANSION_INVALID_LIMIT",
                "max_expansions must be between 1 and 50.",
                status_code=400,
            )
        if not request.policy.version.strip():
            raise QueryExpansionError(
                "QUERY_EXPANSION_POLICY_VERSION_REQUIRED",
                "Query expansion policy version is required.",
                status_code=400,
            )

    def _response(
        self,
        *,
        request: QueryExpansionRequest,
        detected_language: ExpansionLanguage,
        named_reference_preserved: bool,
        expansions: tuple[QueryExpansionItem, ...],
        disabled: bool,
        limited: bool,
    ) -> QueryExpansionResponse:
        trace: dict[str, object] = {
            "expansion_version": QUERY_EXPANSION_VERSION,
            "policy_version": request.policy.version,
            "normalization_framework_version": NORMALIZATION_FRAMEWORK_VERSION,
            "query_language": request.language,
            "detected_language": detected_language,
            "madhhab": request.madhhab,
            "disabled": disabled,
            "limited": limited,
            "named_reference_preserved": named_reference_preserved,
            "max_expansions": request.policy.max_expansions,
            "expansions": [
                {
                    "text": item.text,
                    "normalized_text": item.normalized_text,
                    "language": item.language,
                    "kind": item.kind,
                    "source_terms": list(item.source_terms),
                    "concept_id": item.concept_id,
                }
                for item in expansions
            ],
        }
        return QueryExpansionResponse(
            original_text=request.text,
            query_language=request.language,
            detected_language=detected_language,
            expansion_version=QUERY_EXPANSION_VERSION,
            policy_version=request.policy.version,
            disabled=disabled,
            limited=limited,
            named_reference_preserved=named_reference_preserved,
            expansions=expansions,
            trace=trace,
        )


def _dedupe(items: list[QueryExpansionItem]) -> list[QueryExpansionItem]:
    seen: set[tuple[str, str, str]] = set()
    result: list[QueryExpansionItem] = []
    for item in items:
        key = (item.normalized_text.casefold(), item.language, item.kind)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _matched_concepts(text: str) -> list[str]:
    return [
        concept_id
        for concept_id, group in _TERM_GROUPS.items()
        if any(_contains(text, term) for terms in group.values() for term in terms)
    ]


def _contains(text: str, term: str) -> bool:
    return term.casefold() in text.casefold()


def _detect_language(text: str, fallback: ExpansionLanguage) -> ExpansionLanguage:
    has_thai = any("\u0e00" <= char <= "\u0e7f" for char in text)
    has_arabic = any("\u0600" <= char <= "\u06ff" or "\u0750" <= char <= "\u077f" for char in text)
    has_latin = any("a" <= char.casefold() <= "z" for char in text)
    count = sum((has_thai, has_arabic, has_latin))
    if count > 1:
        return "mixed"
    if has_thai:
        return "th"
    if has_arabic:
        return "ar"
    if has_latin:
        return "en"
    return fallback
