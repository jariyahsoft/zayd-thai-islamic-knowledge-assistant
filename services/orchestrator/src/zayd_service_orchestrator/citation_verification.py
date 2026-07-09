"""Deterministic citation verification for claim support and quote fidelity.

Policy order is always deterministic checks first. Optional model evaluator
signals are non-authoritative and cannot override a hard deterministic failure
such as an unregistered, unpublished, or invalidated citation.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol
from uuid import UUID

from zayd_common.database.models import Citation, DocumentChunk, DocumentVersion
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.normalization import normalize_text

from .answer_orchestration import (
    AnswerGenerationContext,
    AnswerVerificationResult,
    AnswerVerificationStatus,
    GeneratedAnswerDraft,
)
from .citation_registry import (
    CitationRegistryError,
    citation_id_from_token,
    citation_token,
)

CITATION_VERIFICATION_VERSION = "citation-verification-v1"

# Conservative defaults for deterministic claim-support scoring.
DEFAULT_MIN_SUPPORTED_OVERLAP = 0.25
DEFAULT_MIN_PARTIAL_OVERLAP = 0.12

_TOKEN_RE = re.compile(r"[\w\u0E00-\u0E7F\u0600-\u06FF]+", re.UNICODE)
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "this",
        "to",
        "with",
        "และ",
        "หรือ",
        "ที่",
        "ของ",
        "ใน",
        "เป็น",
        "ได้",
        "ไม่",
        "มี",
        "ว่า",
        "จาก",
        "ตาม",
        "ให้",
        "กับ",
        "โดย",
        "ซึ่ง",
        "คือ",
    }
)
_GENERAL_MADHHABS = frozenset(
    {
        "",
        "unknown",
        "unspecified",
        "general",
        "all",
        "multi",
        "multiple",
        "none",
    }
)


class CheckName(StrEnum):
    """Named deterministic checks applied to each claim citation."""

    EXISTENCE = "existence"
    ALLOWED_TOKEN = "allowed_token"
    ACTIVE_STATUS = "active_status"
    PUBLICATION_STATUS = "publication_status"
    REFERENCE_CORRECTNESS = "reference_correctness"
    QUOTE_FIDELITY = "quote_fidelity"
    CLAIM_SUPPORT = "claim_support"
    MADHHAB_CONSISTENCY = "madhhab_consistency"


class CheckOutcome(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    WARN = "warn"


class ClaimSupportStatus(StrEnum):
    """Machine-readable claim-level verification outcome."""

    SUPPORTED = "supported"
    PARTIAL = "partial"
    UNSUPPORTED = "unsupported"
    INVALID_CITATION = "invalid_citation"
    UNVERIFIABLE = "unverifiable"


class OverallVerificationStatus(StrEnum):
    VERIFIED = "verified"
    NEEDS_REVISION = "needs_revision"
    FAILED = "failed"


CitationVerificationErrorCode = str


class CitationVerificationError(Exception):
    """Stable citation verification error for invalid inputs."""

    def __init__(
        self,
        code: CitationVerificationErrorCode,
        message: str,
        *,
        status_code: int = 400,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class VerificationEvidencePack:
    """Evidence the verifier is allowed to treat as valid source material."""

    citation_token: str
    citation_id: UUID
    canonical_reference: str
    citation_type: str
    display_title: str
    chunk_id: UUID
    document_version_id: UUID
    chunk_content: str
    chunk_content_normalized: str | None = None
    arabic_text: str | None = None
    thai_translation: str | None = None
    madhhab: str | None = None
    is_published: bool = True
    citation_active: bool = True
    is_registered: bool = True
    version_status: str | None = None


@dataclass(frozen=True)
class CitedClaimInput:
    """One claim that must be supported by one or more citation tokens."""

    claim_id: str
    claim_text: str
    citation_tokens: tuple[str, ...]
    quoted_text: str | None = None
    declared_madhhab: str | None = None
    declared_reference: str | None = None


@dataclass(frozen=True)
class CheckResult:
    """Result of one deterministic check."""

    name: CheckName
    outcome: CheckOutcome
    reason_code: str | None = None
    detail: dict[str, object] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "name": self.name.value,
            "outcome": self.outcome.value,
        }
        if self.reason_code is not None:
            payload["reason_code"] = self.reason_code
        if self.detail:
            payload["detail"] = dict(self.detail)
        return payload


@dataclass(frozen=True)
class ClaimVerificationResult:
    """Machine-readable verification result for one claim."""

    claim_id: str
    claim_text_hash: str
    citation_tokens: tuple[str, ...]
    support_status: ClaimSupportStatus
    checks: tuple[CheckResult, ...]
    reason_codes: tuple[str, ...]
    claim_support_score: float | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "claim_id": self.claim_id,
            "claim_text_hash": self.claim_text_hash,
            "citation_tokens": list(self.citation_tokens),
            "support_status": self.support_status.value,
            "reason_codes": list(self.reason_codes),
            "claim_support_score": self.claim_support_score,
            "checks": [check.as_dict() for check in self.checks],
            "verification_version": CITATION_VERIFICATION_VERSION,
        }


@dataclass(frozen=True)
class CitationVerificationRequest:
    """Input for claim-level citation verification."""

    claims: tuple[CitedClaimInput, ...]
    evidence: tuple[VerificationEvidencePack, ...]
    allowed_tokens: tuple[str, ...]
    requested_madhhab: str | None = None
    min_supported_overlap: float = DEFAULT_MIN_SUPPORTED_OVERLAP
    min_partial_overlap: float = DEFAULT_MIN_PARTIAL_OVERLAP
    require_all_claims_supported: bool = True
    optional_llm_signal: dict[str, object] | None = None
    trace_id: str | None = None


@dataclass(frozen=True)
class CitationVerificationDecision:
    """Overall verification decision with per-claim machine-readable results."""

    status: OverallVerificationStatus
    claim_results: tuple[ClaimVerificationResult, ...]
    reason_codes: tuple[str, ...]
    requires_revision: bool
    requires_abstention: bool
    version: str
    trace: dict[str, object]

    def claim_results_machine_readable(self) -> list[dict[str, object]]:
        return [result.as_dict() for result in self.claim_results]


class OptionalClaimSupportEvaluator(Protocol):
    """Optional non-authoritative model evaluator for claim support."""

    def evaluate(
        self,
        *,
        claim_text: str,
        evidence_texts: Sequence[str],
        claimed_tokens: Sequence[str],
    ) -> dict[str, object]: ...


class CitationVerificationEngine:
    """Run deterministic citation and claim-support checks."""

    def __init__(
        self,
        *,
        llm_evaluator: OptionalClaimSupportEvaluator | None = None,
    ) -> None:
        self.llm_evaluator = llm_evaluator

    def verify(self, request: CitationVerificationRequest) -> CitationVerificationDecision:
        self._validate_request(request)
        evidence_by_token = {item.citation_token: item for item in request.evidence}
        allowed = set(request.allowed_tokens)
        claim_results: list[ClaimVerificationResult] = []

        for claim in request.claims:
            claim_results.append(
                self._verify_claim(
                    claim,
                    evidence_by_token=evidence_by_token,
                    allowed_tokens=allowed,
                    request=request,
                )
            )

        reason_codes = _unique_reason_codes(
            [code for result in claim_results for code in result.reason_codes]
        )
        if not claim_results:
            reason_codes = ("CLAIM_REQUIRED",)
            status = OverallVerificationStatus.FAILED
        else:
            status = _overall_status(claim_results, request.require_all_claims_supported)

        # Optional model signals never upgrade an invalid citation.
        llm_signal = request.optional_llm_signal
        if self.llm_evaluator is not None and llm_signal is None:
            llm_signal = {
                "note": "llm_evaluator_available_but_not_used_for_authoritative_decision",
                "authoritative": False,
            }
        if llm_signal is not None and status == OverallVerificationStatus.VERIFIED:
            # Model may only add non-authoritative notes, never change pass/fail.
            pass

        requires_revision = status == OverallVerificationStatus.NEEDS_REVISION
        requires_abstention = status == OverallVerificationStatus.FAILED or (
            status == OverallVerificationStatus.NEEDS_REVISION
            and any(
                result.support_status == ClaimSupportStatus.INVALID_CITATION
                for result in claim_results
            )
        )
        # Hard invalid citations should force abstention if unrecovered.
        if any(
            result.support_status == ClaimSupportStatus.INVALID_CITATION for result in claim_results
        ):
            requires_revision = True
            if status == OverallVerificationStatus.FAILED:
                requires_abstention = True

        if status == OverallVerificationStatus.VERIFIED:
            reason_codes = ("VERIFIED",)

        return CitationVerificationDecision(
            status=status,
            claim_results=tuple(claim_results),
            reason_codes=reason_codes,
            requires_revision=requires_revision,
            requires_abstention=requires_abstention
            if status != OverallVerificationStatus.VERIFIED
            else False,
            version=CITATION_VERIFICATION_VERSION,
            trace={
                "verification_version": CITATION_VERIFICATION_VERSION,
                "claim_count": len(claim_results),
                "allowed_token_count": len(request.allowed_tokens),
                "evidence_count": len(request.evidence),
                "status": status.value,
                "reason_codes": list(reason_codes),
                "requires_revision": requires_revision
                if status != OverallVerificationStatus.VERIFIED
                else False,
                "requires_abstention": requires_abstention
                if status != OverallVerificationStatus.VERIFIED
                else False,
                "claim_results": [result.as_dict() for result in claim_results],
                "trace_id": request.trace_id,
                "llm_signal_authoritative": False,
                "llm_signal_present": llm_signal is not None,
            },
        )

    def _validate_request(self, request: CitationVerificationRequest) -> None:
        if request.min_supported_overlap < request.min_partial_overlap:
            raise CitationVerificationError(
                "CITATION_VERIFICATION_THRESHOLD_INVALID",
                "min_supported_overlap must be >= min_partial_overlap.",
            )
        if not 0.0 <= request.min_partial_overlap <= 1.0:
            raise CitationVerificationError(
                "CITATION_VERIFICATION_THRESHOLD_INVALID",
                "min_partial_overlap must be between 0 and 1.",
            )
        if not 0.0 <= request.min_supported_overlap <= 1.0:
            raise CitationVerificationError(
                "CITATION_VERIFICATION_THRESHOLD_INVALID",
                "min_supported_overlap must be between 0 and 1.",
            )
        seen_claim_ids: set[str] = set()
        for claim in request.claims:
            if not claim.claim_id.strip():
                raise CitationVerificationError(
                    "CITATION_VERIFICATION_INPUT_INVALID",
                    "claim_id is required.",
                )
            if claim.claim_id in seen_claim_ids:
                raise CitationVerificationError(
                    "CITATION_VERIFICATION_INPUT_INVALID",
                    "claim_id values must be unique.",
                )
            seen_claim_ids.add(claim.claim_id)
            if not claim.claim_text.strip():
                raise CitationVerificationError(
                    "CITATION_VERIFICATION_INPUT_INVALID",
                    "claim_text is required.",
                )
        seen_tokens: set[str] = set()
        for pack in request.evidence:
            if pack.citation_token in seen_tokens:
                raise CitationVerificationError(
                    "CITATION_VERIFICATION_INPUT_INVALID",
                    "evidence citation tokens must be unique.",
                )
            seen_tokens.add(pack.citation_token)

    def _verify_claim(
        self,
        claim: CitedClaimInput,
        *,
        evidence_by_token: Mapping[str, VerificationEvidencePack],
        allowed_tokens: set[str],
        request: CitationVerificationRequest,
    ) -> ClaimVerificationResult:
        checks: list[CheckResult] = []
        reason_codes: list[str] = []
        tokens = tuple(token.strip() for token in claim.citation_tokens if token.strip())

        if not tokens:
            checks.append(
                CheckResult(
                    name=CheckName.EXISTENCE,
                    outcome=CheckOutcome.FAIL,
                    reason_code="CITATION_REQUIRED",
                )
            )
            return ClaimVerificationResult(
                claim_id=claim.claim_id,
                claim_text_hash=_hash_text(claim.claim_text),
                citation_tokens=(),
                support_status=ClaimSupportStatus.UNVERIFIABLE,
                checks=tuple(checks),
                reason_codes=("CITATION_REQUIRED",),
            )

        packs: list[VerificationEvidencePack] = []
        invalid = False
        for token in tokens:
            token_checks, pack, token_invalid = self._verify_token(
                token,
                claim=claim,
                evidence_by_token=evidence_by_token,
                allowed_tokens=allowed_tokens,
            )
            checks.extend(token_checks)
            if token_invalid:
                invalid = True
            elif pack is not None:
                packs.append(pack)

        if invalid or not packs:
            status = ClaimSupportStatus.INVALID_CITATION
            reason_codes.extend(
                check.reason_code
                for check in checks
                if check.outcome == CheckOutcome.FAIL and check.reason_code
            )
            return ClaimVerificationResult(
                claim_id=claim.claim_id,
                claim_text_hash=_hash_text(claim.claim_text),
                citation_tokens=tokens,
                support_status=status,
                checks=tuple(checks),
                reason_codes=_unique_reason_codes(reason_codes or ("CITATION_INVALID",)),
            )

        quote_check = self._check_quote_fidelity(claim.quoted_text, packs)
        checks.append(quote_check)
        if quote_check.outcome == CheckOutcome.FAIL:
            reason_codes.append(quote_check.reason_code or "QUOTE_FIDELITY_FAILED")

        support_check, support_score, support_status = self._check_claim_support(
            claim.claim_text,
            packs,
            min_supported=request.min_supported_overlap,
            min_partial=request.min_partial_overlap,
        )
        checks.append(support_check)
        if support_check.outcome == CheckOutcome.FAIL:
            reason_codes.append(support_check.reason_code or "CLAIM_UNSUPPORTED")
        elif support_check.outcome == CheckOutcome.WARN:
            reason_codes.append(support_check.reason_code or "CLAIM_PARTIAL_SUPPORT")

        madhhab_check = self._check_madhhab(
            claim=claim,
            packs=packs,
            requested_madhhab=request.requested_madhhab,
        )
        checks.append(madhhab_check)
        if madhhab_check.outcome == CheckOutcome.FAIL:
            reason_codes.append(madhhab_check.reason_code or "MADHHAB_MISMATCH")
            # Madhhab mismatch is a hard failure for claim support when declared.
            if support_status == ClaimSupportStatus.SUPPORTED:
                support_status = ClaimSupportStatus.UNSUPPORTED

        if quote_check.outcome == CheckOutcome.FAIL:
            support_status = ClaimSupportStatus.UNSUPPORTED

        if support_status == ClaimSupportStatus.SUPPORTED and not reason_codes:
            reason_codes = ["CLAIM_SUPPORTED"]

        return ClaimVerificationResult(
            claim_id=claim.claim_id,
            claim_text_hash=_hash_text(claim.claim_text),
            citation_tokens=tokens,
            support_status=support_status,
            checks=tuple(checks),
            reason_codes=_unique_reason_codes(reason_codes),
            claim_support_score=support_score,
        )

    def _verify_token(
        self,
        token: str,
        *,
        claim: CitedClaimInput,
        evidence_by_token: Mapping[str, VerificationEvidencePack],
        allowed_tokens: set[str],
    ) -> tuple[list[CheckResult], VerificationEvidencePack | None, bool]:
        checks: list[CheckResult] = []

        if token not in allowed_tokens:
            checks.append(
                CheckResult(
                    name=CheckName.ALLOWED_TOKEN,
                    outcome=CheckOutcome.FAIL,
                    reason_code="CITATION_NOT_ALLOWED",
                    detail={"citation_token": token},
                )
            )
            return checks, None, True
        checks.append(
            CheckResult(
                name=CheckName.ALLOWED_TOKEN,
                outcome=CheckOutcome.PASS,
                detail={"citation_token": token},
            )
        )

        pack = evidence_by_token.get(token)
        if pack is None or not pack.is_registered:
            checks.append(
                CheckResult(
                    name=CheckName.EXISTENCE,
                    outcome=CheckOutcome.FAIL,
                    reason_code="CITATION_NOT_REGISTERED",
                    detail={"citation_token": token},
                )
            )
            return checks, None, True
        checks.append(
            CheckResult(
                name=CheckName.EXISTENCE,
                outcome=CheckOutcome.PASS,
                detail={
                    "citation_token": token,
                    "citation_id": str(pack.citation_id),
                },
            )
        )

        if not pack.citation_active:
            checks.append(
                CheckResult(
                    name=CheckName.ACTIVE_STATUS,
                    outcome=CheckOutcome.FAIL,
                    reason_code="CITATION_INACTIVE",
                    detail={"citation_token": token},
                )
            )
            return checks, None, True
        checks.append(
            CheckResult(
                name=CheckName.ACTIVE_STATUS,
                outcome=CheckOutcome.PASS,
                detail={"citation_token": token},
            )
        )

        published = pack.is_published and (
            pack.version_status is None or pack.version_status == "published"
        )
        if not published:
            checks.append(
                CheckResult(
                    name=CheckName.PUBLICATION_STATUS,
                    outcome=CheckOutcome.FAIL,
                    reason_code="CITATION_NOT_PUBLISHED",
                    detail={
                        "citation_token": token,
                        "is_published": pack.is_published,
                        "version_status": pack.version_status,
                    },
                )
            )
            return checks, None, True
        checks.append(
            CheckResult(
                name=CheckName.PUBLICATION_STATUS,
                outcome=CheckOutcome.PASS,
                detail={"citation_token": token},
            )
        )

        ref_check = self._check_reference(claim.declared_reference, pack)
        checks.append(ref_check)
        if ref_check.outcome == CheckOutcome.FAIL:
            return checks, None, True

        return checks, pack, False

    def _check_reference(
        self,
        declared_reference: str | None,
        pack: VerificationEvidencePack,
    ) -> CheckResult:
        canonical = (pack.canonical_reference or "").strip()
        if not canonical:
            return CheckResult(
                name=CheckName.REFERENCE_CORRECTNESS,
                outcome=CheckOutcome.FAIL,
                reason_code="REFERENCE_MISSING",
                detail={"citation_token": pack.citation_token},
            )
        if declared_reference is None or not declared_reference.strip():
            return CheckResult(
                name=CheckName.REFERENCE_CORRECTNESS,
                outcome=CheckOutcome.PASS,
                detail={
                    "citation_token": pack.citation_token,
                    "canonical_reference": canonical,
                    "mode": "canonical_present",
                },
            )
        declared = declared_reference.strip()
        if _normalize_simple(declared) == _normalize_simple(canonical):
            return CheckResult(
                name=CheckName.REFERENCE_CORRECTNESS,
                outcome=CheckOutcome.PASS,
                detail={
                    "citation_token": pack.citation_token,
                    "mode": "exact_match",
                },
            )
        if _normalize_simple(declared) in _normalize_simple(canonical) or _normalize_simple(
            canonical
        ) in _normalize_simple(declared):
            return CheckResult(
                name=CheckName.REFERENCE_CORRECTNESS,
                outcome=CheckOutcome.PASS,
                detail={
                    "citation_token": pack.citation_token,
                    "mode": "compatible_match",
                },
            )
        return CheckResult(
            name=CheckName.REFERENCE_CORRECTNESS,
            outcome=CheckOutcome.FAIL,
            reason_code="REFERENCE_MISMATCH",
            detail={"citation_token": pack.citation_token},
        )

    def _check_quote_fidelity(
        self,
        quoted_text: str | None,
        packs: Sequence[VerificationEvidencePack],
    ) -> CheckResult:
        if quoted_text is None or not quoted_text.strip():
            return CheckResult(
                name=CheckName.QUOTE_FIDELITY,
                outcome=CheckOutcome.SKIP,
                reason_code="QUOTE_NOT_PROVIDED",
            )
        source_texts: list[str] = []
        for pack in packs:
            source_texts.extend(
                text
                for text in (
                    pack.chunk_content,
                    pack.chunk_content_normalized,
                    pack.arabic_text,
                    pack.thai_translation,
                )
                if text
            )
        if _quote_matches_sources(quoted_text, source_texts):
            return CheckResult(
                name=CheckName.QUOTE_FIDELITY,
                outcome=CheckOutcome.PASS,
                detail={"source_count": len(source_texts)},
            )
        return CheckResult(
            name=CheckName.QUOTE_FIDELITY,
            outcome=CheckOutcome.FAIL,
            reason_code="QUOTE_FIDELITY_FAILED",
            detail={"source_count": len(source_texts)},
        )

    def _check_claim_support(
        self,
        claim_text: str,
        packs: Sequence[VerificationEvidencePack],
        *,
        min_supported: float,
        min_partial: float,
    ) -> tuple[CheckResult, float, ClaimSupportStatus]:
        evidence_text = "\n".join(
            text
            for pack in packs
            for text in (
                pack.chunk_content,
                pack.chunk_content_normalized,
                pack.arabic_text,
                pack.thai_translation,
                pack.display_title,
                pack.canonical_reference,
            )
            if text
        )
        score = _claim_support_overlap(claim_text, evidence_text)
        detail: dict[str, object] = {"overlap": round(score, 4)}
        if score >= min_supported:
            return (
                CheckResult(
                    name=CheckName.CLAIM_SUPPORT,
                    outcome=CheckOutcome.PASS,
                    reason_code="CLAIM_SUPPORTED",
                    detail=detail,
                ),
                score,
                ClaimSupportStatus.SUPPORTED,
            )
        if score >= min_partial:
            return (
                CheckResult(
                    name=CheckName.CLAIM_SUPPORT,
                    outcome=CheckOutcome.WARN,
                    reason_code="CLAIM_PARTIAL_SUPPORT",
                    detail=detail,
                ),
                score,
                ClaimSupportStatus.PARTIAL,
            )
        return (
            CheckResult(
                name=CheckName.CLAIM_SUPPORT,
                outcome=CheckOutcome.FAIL,
                reason_code="CLAIM_UNSUPPORTED",
                detail=detail,
            ),
            score,
            ClaimSupportStatus.UNSUPPORTED,
        )

    def _check_madhhab(
        self,
        *,
        claim: CitedClaimInput,
        packs: Sequence[VerificationEvidencePack],
        requested_madhhab: str | None,
    ) -> CheckResult:
        target = (claim.declared_madhhab or requested_madhhab or "").strip().lower()
        if target in _GENERAL_MADHHABS:
            return CheckResult(
                name=CheckName.MADHHAB_CONSISTENCY,
                outcome=CheckOutcome.SKIP,
                reason_code="MADHHAB_NOT_REQUESTED",
            )
        evidence_madhhabs = {
            (pack.madhhab or "").strip().lower() for pack in packs if (pack.madhhab or "").strip()
        }
        if not evidence_madhhabs or evidence_madhhabs <= _GENERAL_MADHHABS:
            return CheckResult(
                name=CheckName.MADHHAB_CONSISTENCY,
                outcome=CheckOutcome.PASS,
                reason_code="MADHHAB_UNSPECIFIED_IN_EVIDENCE",
                detail={"requested_madhhab": target},
            )
        if target in evidence_madhhabs:
            return CheckResult(
                name=CheckName.MADHHAB_CONSISTENCY,
                outcome=CheckOutcome.PASS,
                detail={
                    "requested_madhhab": target,
                    "evidence_madhhabs": sorted(evidence_madhhabs),
                },
            )
        if evidence_madhhabs & _GENERAL_MADHHABS:
            return CheckResult(
                name=CheckName.MADHHAB_CONSISTENCY,
                outcome=CheckOutcome.PASS,
                reason_code="MADHHAB_GENERAL_EVIDENCE",
                detail={"requested_madhhab": target},
            )
        return CheckResult(
            name=CheckName.MADHHAB_CONSISTENCY,
            outcome=CheckOutcome.FAIL,
            reason_code="MADHHAB_MISMATCH",
            detail={
                "requested_madhhab": target,
                "evidence_madhhabs": sorted(evidence_madhhabs - _GENERAL_MADHHABS),
            },
        )


def load_evidence_packs(
    uow: SQLAlchemyUnitOfWork,
    tokens: Sequence[str],
) -> tuple[VerificationEvidencePack, ...]:
    """Load published/active evidence packs for registered citation tokens.

    Unpublished chunks, non-published document versions, and inactive
    citations are still returned with status flags so the verifier can fail
    closed rather than silently inventing support.
    """
    packs: list[VerificationEvidencePack] = []
    with uow:
        session = uow.session
        if session is None:
            raise RuntimeError("Database session not initialised in UoW.")
        for token in tokens:
            try:
                citation_id = citation_id_from_token(token)
            except CitationRegistryError:
                continue
            citation = session.get(Citation, citation_id)
            if citation is None:
                continue
            chunk = session.get(DocumentChunk, citation.chunk_id)
            version = session.get(DocumentVersion, citation.document_version_id)
            if chunk is None or version is None:
                continue
            metadata = dict(chunk.metadata_json or {})
            madhhab = metadata.get("madhhab")
            packs.append(
                VerificationEvidencePack(
                    citation_token=citation_token(citation.id),
                    citation_id=citation.id,
                    canonical_reference=citation.canonical_reference,
                    citation_type=citation.citation_type,
                    display_title=citation.display_title,
                    chunk_id=chunk.id,
                    document_version_id=version.id,
                    chunk_content=chunk.content,
                    chunk_content_normalized=chunk.content_normalized,
                    arabic_text=citation.arabic_text,
                    thai_translation=citation.thai_translation,
                    madhhab=str(madhhab) if madhhab is not None else None,
                    is_published=bool(chunk.is_published),
                    citation_active=bool(citation.verified and citation.invalidated_at is None),
                    is_registered=True,
                    version_status=version.status,
                )
            )
        uow.commit()
    return tuple(packs)


def evidence_from_candidate_metadata(
    *,
    citation_token_value: str,
    citation_id: UUID,
    canonical_reference: str,
    citation_type: str,
    display_title: str,
    chunk_id: UUID,
    document_version_id: UUID,
    chunk_content: str,
    madhhab: str | None = None,
    arabic_text: str | None = None,
    thai_translation: str | None = None,
    is_published: bool = True,
    citation_active: bool = True,
    version_status: str = "published",
) -> VerificationEvidencePack:
    """Helper for tests and orchestration adapters."""
    return VerificationEvidencePack(
        citation_token=citation_token_value,
        citation_id=citation_id,
        canonical_reference=canonical_reference,
        citation_type=citation_type,
        display_title=display_title,
        chunk_id=chunk_id,
        document_version_id=document_version_id,
        chunk_content=chunk_content,
        chunk_content_normalized=_normalize_simple(chunk_content),
        arabic_text=arabic_text,
        thai_translation=thai_translation,
        madhhab=madhhab,
        is_published=is_published,
        citation_active=citation_active,
        is_registered=True,
        version_status=version_status,
    )


def claims_from_draft(
    draft: GeneratedAnswerDraft,
    *,
    fallback_claim_id: str = "claim-1",
) -> tuple[CitedClaimInput, ...]:
    """Build claim inputs from structured draft.trace claims or a single fallback claim."""
    raw_claims = draft.trace.get("claims") if isinstance(draft.trace, Mapping) else None
    if isinstance(raw_claims, Sequence) and not isinstance(raw_claims, (str, bytes)):
        parsed: list[CitedClaimInput] = []
        for index, item in enumerate(raw_claims, start=1):
            if not isinstance(item, Mapping):
                continue
            tokens_raw = item.get("citation_tokens") or item.get("citations") or ()
            tokens = tuple(str(token) for token in tokens_raw)
            claim_text = str(item.get("claim_text") or item.get("text") or "").strip()
            if not claim_text:
                continue
            parsed.append(
                CitedClaimInput(
                    claim_id=str(item.get("claim_id") or f"claim-{index}"),
                    claim_text=claim_text,
                    citation_tokens=tokens,
                    quoted_text=_optional_str(item.get("quoted_text")),
                    declared_madhhab=_optional_str(item.get("madhhab")),
                    declared_reference=_optional_str(item.get("declared_reference")),
                )
            )
        if parsed:
            return tuple(parsed)

    tokens = tuple(citation.citation_id for citation in draft.citations)
    return (
        CitedClaimInput(
            claim_id=fallback_claim_id,
            claim_text=draft.answer_th or draft.summary,
            citation_tokens=tokens,
            quoted_text=_optional_str(draft.trace.get("quoted_text"))
            if isinstance(draft.trace, Mapping)
            else None,
        ),
    )


class CitationVerificationAnswerVerifier:
    """AnswerVerifier adapter that applies claim-level citation verification.

    When candidate metadata lacks usable evidence packs, the adapter falls back
    to the basic allowed-token subset check so orchestration remains usable in
    lightweight unit fixtures.
    """

    def __init__(
        self,
        engine: CitationVerificationEngine | None = None,
        *,
        require_evidence_packs: bool = False,
    ) -> None:
        self.engine = engine or CitationVerificationEngine()
        self.require_evidence_packs = require_evidence_packs

    def verify(
        self,
        draft: GeneratedAnswerDraft,
        context: AnswerGenerationContext,
    ) -> AnswerVerificationResult:
        reason_codes: list[str] = []
        if not draft.summary.strip() or not draft.answer_th.strip():
            reason_codes.append("ANSWER_TEXT_REQUIRED")
        if "fatwa ที่ผูกพัน" in draft.answer_th or "ฟัตวาที่ผูกพัน" in draft.answer_th:
            reason_codes.append("PROHIBITED_FATWA_CLAIM")

        allowed_tokens, evidence_packs = _allowed_and_evidence_from_context(context)
        draft_tokens = tuple(citation.citation_id for citation in draft.citations)
        if not draft_tokens:
            reason_codes.append("CITATION_REQUIRED")

        if not evidence_packs:
            if self.require_evidence_packs:
                reason_codes.append("CITATION_EVIDENCE_UNAVAILABLE")
            else:
                # Lightweight fallback used by existing orchestration fixtures.
                if draft_tokens and not set(draft_tokens).issubset(set(allowed_tokens)):
                    reason_codes.append("CITATION_NOT_ALLOWED")
                if reason_codes:
                    return AnswerVerificationResult(
                        status=AnswerVerificationStatus.NEEDS_REVISION,
                        reason_codes=tuple(reason_codes),
                        trace={
                            "mode": "fallback_allowed_token_check",
                            "allowed_citation_count": len(allowed_tokens),
                            "draft_citation_count": len(draft_tokens),
                        },
                    )
                return AnswerVerificationResult(
                    status=AnswerVerificationStatus.VERIFIED,
                    reason_codes=("VERIFIED",),
                    trace={
                        "mode": "fallback_allowed_token_check",
                        "allowed_citation_count": len(allowed_tokens),
                        "draft_citation_count": len(draft_tokens),
                    },
                )

        claims = claims_from_draft(draft)
        decision = self.engine.verify(
            CitationVerificationRequest(
                claims=claims,
                evidence=evidence_packs,
                allowed_tokens=allowed_tokens,
                requested_madhhab=_requested_madhhab_from_context(context),
                trace_id=context.trace_id,
            )
        )
        if decision.status != OverallVerificationStatus.VERIFIED:
            reason_codes.extend(code for code in decision.reason_codes if code != "VERIFIED")
        if reason_codes:
            status = (
                AnswerVerificationStatus.FAILED
                if decision.status == OverallVerificationStatus.FAILED
                else AnswerVerificationStatus.NEEDS_REVISION
            )
            return AnswerVerificationResult(
                status=status,
                reason_codes=tuple(_unique_reason_codes(reason_codes)),
                trace={
                    "mode": "citation_verification_engine",
                    "verification_version": decision.version,
                    "requires_revision": decision.requires_revision,
                    "requires_abstention": decision.requires_abstention,
                    "claim_results": decision.claim_results_machine_readable(),
                    "engine_status": decision.status.value,
                },
            )
        return AnswerVerificationResult(
            status=AnswerVerificationStatus.VERIFIED,
            reason_codes=("VERIFIED",),
            trace={
                "mode": "citation_verification_engine",
                "verification_version": decision.version,
                "claim_results": decision.claim_results_machine_readable(),
                "engine_status": decision.status.value,
            },
        )


def _allowed_and_evidence_from_context(
    context: AnswerGenerationContext,
) -> tuple[tuple[str, ...], tuple[VerificationEvidencePack, ...]]:
    tokens: list[str] = []
    packs: list[VerificationEvidencePack] = []
    for candidate in context.candidates:
        metadata = dict(candidate.metadata or {})
        token = metadata.get("citation_token")
        if not isinstance(token, str) or not token.strip():
            # Preserve legacy short tokens used by the template generator path.
            token = f"CIT-{str(candidate.chunk_id)[:8]}"
        tokens.append(token)
        content = metadata.get("chunk_content") or metadata.get("content")
        citation_id_raw = metadata.get("citation_id")
        if content is None or citation_id_raw is None:
            continue
        try:
            citation_id = (
                citation_id_raw if isinstance(citation_id_raw, UUID) else UUID(str(citation_id_raw))
            )
        except ValueError:
            continue
        packs.append(
            VerificationEvidencePack(
                citation_token=token,
                citation_id=citation_id,
                canonical_reference=candidate.canonical_reference,
                citation_type=str(metadata.get("citation_type") or candidate.source_type),
                display_title=str(metadata.get("display_title") or candidate.canonical_reference),
                chunk_id=candidate.chunk_id,
                document_version_id=candidate.document_version_id,
                chunk_content=str(content),
                chunk_content_normalized=_optional_str(metadata.get("content_normalized")),
                arabic_text=_optional_str(metadata.get("arabic_text")),
                thai_translation=_optional_str(metadata.get("thai_translation")),
                madhhab=candidate.madhhab,
                is_published=bool(metadata.get("is_published", True)),
                citation_active=bool(metadata.get("citation_active", True)),
                is_registered=bool(metadata.get("is_registered", True)),
                version_status=_optional_str(metadata.get("version_status")) or "published",
            )
        )
    return tuple(tokens), tuple(packs)


def _requested_madhhab_from_context(context: AnswerGenerationContext) -> str | None:
    value = context.classification.madhhab.value
    if value in _GENERAL_MADHHABS:
        return None
    return value


def _overall_status(
    claim_results: Sequence[ClaimVerificationResult],
    require_all_supported: bool,
) -> OverallVerificationStatus:
    statuses = {result.support_status for result in claim_results}
    if ClaimSupportStatus.INVALID_CITATION in statuses:
        return OverallVerificationStatus.NEEDS_REVISION
    if ClaimSupportStatus.UNVERIFIABLE in statuses:
        return OverallVerificationStatus.NEEDS_REVISION
    if ClaimSupportStatus.UNSUPPORTED in statuses:
        return OverallVerificationStatus.NEEDS_REVISION
    if ClaimSupportStatus.PARTIAL in statuses and require_all_supported:
        return OverallVerificationStatus.NEEDS_REVISION
    if statuses and statuses <= {ClaimSupportStatus.SUPPORTED}:
        return OverallVerificationStatus.VERIFIED
    if ClaimSupportStatus.PARTIAL in statuses:
        return OverallVerificationStatus.NEEDS_REVISION
    return OverallVerificationStatus.FAILED


def _quote_matches_sources(quote: str, sources: Sequence[str]) -> bool:
    quote_variants = {
        _normalize_for_match(quote, language)
        for language in ("ar", "th", "en")
        if _normalize_for_match(quote, language)
    }
    for source in sources:
        source_variants = {
            _normalize_for_match(source, language)
            for language in ("ar", "th", "en")
            if _normalize_for_match(source, language)
        }
        for quote_norm in quote_variants:
            for source_norm in source_variants:
                if quote_norm and quote_norm in source_norm:
                    return True
    return False


def _claim_support_overlap(claim_text: str, evidence_text: str) -> float:
    claim_tokens = _meaningful_tokens(claim_text)
    if not claim_tokens:
        return 0.0
    evidence_tokens = _meaningful_tokens(evidence_text)
    if not evidence_tokens:
        return 0.0
    overlap = claim_tokens & evidence_tokens
    return len(overlap) / len(claim_tokens)


def _meaningful_tokens(text: str) -> set[str]:
    """Extract comparable tokens for claim-support scoring.

    Space-delimited languages use word tokens. Thai and Arabic segments that
    do not split cleanly on whitespace also contribute character n-grams so
    deterministic support checks remain useful without an external tokenizer.
    """
    normalized = _normalize_simple(text)
    tokens = {
        token.lower()
        for token in _TOKEN_RE.findall(normalized)
        if token.lower() not in _STOPWORDS and len(token) > 1
    }
    compact = re.sub(r"\s+", "", normalized)
    if _contains_thai_or_arabic(compact):
        tokens.update(_character_ngrams(compact, size=3))
        tokens.update(_character_ngrams(compact, size=4))
    return tokens


def _contains_thai_or_arabic(text: str) -> bool:
    return any("\u0e00" <= ch <= "\u0e7f" or "\u0600" <= ch <= "\u06ff" for ch in text)


def _character_ngrams(text: str, *, size: int) -> set[str]:
    if len(text) < size:
        return {text} if text else set()
    return {text[index : index + size] for index in range(0, len(text) - size + 1)}


def _normalize_for_match(text: str, language: str) -> str:
    if language in {"ar", "th"}:
        return normalize_text(text, language=language).normalized.lower()
    return _normalize_simple(text)


def _normalize_simple(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).split()).lower()


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _unique_reason_codes(codes: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(code for code in codes if code))
