"""Tests for citation-verification-v1."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from zayd_common.database.models import (
    Base,
    Document,
    DocumentChunk,
    DocumentVersion,
    Source,
    SourceLicense,
    User,
)
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.enums import EvidenceStatus
from zayd_service_orchestrator.answer_orchestration import (
    AnswerCitation,
    AnswerGenerationContext,
    AnswerOrchestrationRequest,
    AnswerOrchestrationStatus,
    AnswerOrchestrator,
    GeneratedAnswerDraft,
    StaticAnswerRetriever,
)
from zayd_service_orchestrator.citation_registry import (
    CitationRegistrationRequest,
    CitationRegistryService,
    CitationType,
    citation_token,
)
from zayd_service_orchestrator.citation_verification import (
    CITATION_VERIFICATION_VERSION,
    CitationVerificationAnswerVerifier,
    CitationVerificationEngine,
    CitationVerificationError,
    CitationVerificationRequest,
    CitedClaimInput,
    ClaimSupportStatus,
    OverallVerificationStatus,
    VerificationEvidencePack,
    evidence_from_candidate_metadata,
    load_evidence_packs,
)
from zayd_service_orchestrator.question_classification import (
    ClassificationResult,
    Intent,
    Language,
    Madhhab,
    QuestionClassifier,
    RiskLevel,
)
from zayd_service_orchestrator.risk_policy_engine import (
    EscalationTarget,
    PolicyAction,
    PolicyDecision,
    RestrictionReason,
    RiskPolicyEngine,
)
from zayd_service_retrieval.evidence_sufficiency import (
    EvidenceCandidate,
    EvidenceSufficiencyDecision,
    EvidenceSufficiencyService,
)


@dataclass(frozen=True)
class RegistryFixture:
    session_factory: sessionmaker[Any]
    actor_id: UUID
    version_id: UUID
    chunk_id: UUID
    chunk_content: str

    @property
    def registry(self) -> CitationRegistryService:
        return CitationRegistryService(SQLAlchemyUnitOfWork(self.session_factory))

    @property
    def uow(self) -> SQLAlchemyUnitOfWork:
        return SQLAlchemyUnitOfWork(self.session_factory)


@pytest.fixture
def registry_fixture() -> RegistryFixture:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    actor_id = uuid4()
    source_id = uuid4()
    license_id = uuid4()
    document_id = uuid4()
    version_id = uuid4()
    chunk_id = uuid4()
    chunk_content = "การละหมาดห้าเวลาเป็นหน้าที่ของมุสลิมทุกคน และต้องรักษาความสะอาดก่อนเข้าสู่การละหมาด"

    with session_factory() as session:
        session.add(
            User(
                id=actor_id,
                email="reviewer@example.test",
                display_name="Reviewer",
            )
        )
        session.add(
            Source(
                id=source_id,
                name="Reviewed Source",
                source_type="fiqh",
                language="th",
                reliability_level=5,
                created_by=actor_id,
            )
        )
        session.add(
            SourceLicense(
                id=license_id,
                source_id=source_id,
                license_name="Reviewed License",
                status="persistent_redistributable",
                storage_permission="allowed",
                embedding_permission="allowed",
                commercial_use="allowed",
                redistribution="allowed",
                created_by=actor_id,
            )
        )
        session.add(
            Document(
                id=document_id,
                source_id=source_id,
                source_license_id=license_id,
                canonical_id="doc:prayer",
                document_type="book",
                title="Fiqh of Prayer",
                language="th",
                review_status="approved",
                created_by=actor_id,
            )
        )
        session.add(
            DocumentVersion(
                id=version_id,
                document_id=document_id,
                version_number=1,
                status="published",
                content_hash="version-hash",
                metadata_json={},
                created_by=actor_id,
            )
        )
        session.add(
            DocumentChunk(
                id=chunk_id,
                document_version_id=version_id,
                chunk_index=0,
                content=chunk_content,
                content_normalized=chunk_content,
                token_count=20,
                reference="book:prayer:1:10",
                metadata_json={
                    "citation": {"canonical_reference": "book:prayer:1:10", "page": "10"},
                    "madhhab": "shafii",
                },
                is_published=True,
                chunking_strategy_version="test-v1",
                content_hash="chunk-hash-0",
            )
        )
        session.commit()

    return RegistryFixture(
        session_factory=session_factory,
        actor_id=actor_id,
        version_id=version_id,
        chunk_id=chunk_id,
        chunk_content=chunk_content,
    )


def _pack(
    *,
    token: str | None = None,
    citation_id: UUID | None = None,
    content: str = "การละหมาดห้าเวลาเป็นหน้าที่ของมุสลิม",
    canonical_reference: str = "book:prayer:1:10",
    madhhab: str | None = "shafii",
    is_published: bool = True,
    citation_active: bool = True,
    is_registered: bool = True,
    version_status: str = "published",
    arabic_text: str | None = None,
    thai_translation: str | None = None,
) -> VerificationEvidencePack:
    citation_uuid = citation_id or uuid4()
    return evidence_from_candidate_metadata(
        citation_token_value=token or citation_token(citation_uuid),
        citation_id=citation_uuid,
        canonical_reference=canonical_reference,
        citation_type="book",
        display_title="Fiqh of Prayer, vol. 1, p. 10",
        chunk_id=uuid4(),
        document_version_id=uuid4(),
        chunk_content=content,
        madhhab=madhhab,
        arabic_text=arabic_text,
        thai_translation=thai_translation,
        is_published=is_published,
        citation_active=citation_active,
        version_status=version_status,
    )


def test_supported_claim_with_exact_quote_and_reference() -> None:
    pack = _pack(
        content="ผู้ latent ต้องชำระซะกาตเมื่อครบนิษาบ",
        thai_translation="ผู้ latent ต้องชำระซะกาตเมื่อครบนิษาบ",
    )
    claim = CitedClaimInput(
        claim_id="c1",
        claim_text="ผู้ latent ต้องชำระซะกาตเมื่อครบนิษาบตามหลักฟิกห์",
        citation_tokens=(pack.citation_token,),
        quoted_text="ต้องชำระซะกาตเมื่อครบนิษาบ",
        declared_reference="book:prayer:1:10",
        declared_madhhab="shafii",
    )
    decision = CitationVerificationEngine().verify(
        CitationVerificationRequest(
            claims=(claim,),
            evidence=(pack,),
            allowed_tokens=(pack.citation_token,),
            requested_madhhab="shafii",
            trace_id="trace-ok",
        )
    )

    assert decision.status == OverallVerificationStatus.VERIFIED
    assert decision.version == CITATION_VERIFICATION_VERSION
    assert decision.requires_revision is False
    assert decision.claim_results[0].support_status == ClaimSupportStatus.SUPPORTED
    machine = decision.claim_results_machine_readable()
    assert machine[0]["claim_id"] == "c1"
    assert machine[0]["support_status"] == "supported"
    checks = machine[0]["checks"]
    assert isinstance(checks, list)
    assert any(
        isinstance(check, dict) and check.get("name") == "quote_fidelity" for check in checks
    )


def test_quote_fidelity_fails_when_quote_not_in_source() -> None:
    pack = _pack(content="ข้อความต้นฉบับเกี่ยวกับการละหมาด")
    claim = CitedClaimInput(
        claim_id="c1",
        claim_text="ข้อความต้นฉบับเกี่ยวกับการละหมาดมีความสำคัญ",
        citation_tokens=(pack.citation_token,),
        quoted_text="ข้อความที่ไม่มีอยู่ในต้นฉบับเลย",
    )
    decision = CitationVerificationEngine().verify(
        CitationVerificationRequest(
            claims=(claim,),
            evidence=(pack,),
            allowed_tokens=(pack.citation_token,),
        )
    )

    assert decision.status == OverallVerificationStatus.NEEDS_REVISION
    assert decision.requires_revision is True
    assert "QUOTE_FIDELITY_FAILED" in decision.reason_codes
    assert decision.claim_results[0].support_status == ClaimSupportStatus.UNSUPPORTED


def test_arabic_quote_fidelity_ignores_diacritics() -> None:
    pack = _pack(
        content="بسم الله الرحمن الرحيم",
        arabic_text="بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ",
        canonical_reference="quran:1:1",
    )
    claim = CitedClaimInput(
        claim_id="c1",
        claim_text="อายะฮ์เปิดด้วย بسم الله الرحمن الرحيم",
        citation_tokens=(pack.citation_token,),
        quoted_text="بسم الله الرحمن الرحيم",
    )
    decision = CitationVerificationEngine().verify(
        CitationVerificationRequest(
            claims=(claim,),
            evidence=(pack,),
            allowed_tokens=(pack.citation_token,),
        )
    )
    assert decision.status == OverallVerificationStatus.VERIFIED


def test_unregistered_token_is_invalid() -> None:
    pack = _pack()
    fake_token = citation_token(uuid4())
    claim = CitedClaimInput(
        claim_id="c1",
        claim_text="ข้อความที่ไม่สามารถยืนยันได้",
        citation_tokens=(fake_token,),
    )
    decision = CitationVerificationEngine().verify(
        CitationVerificationRequest(
            claims=(claim,),
            evidence=(pack,),
            allowed_tokens=(fake_token,),
        )
    )
    assert decision.claim_results[0].support_status == ClaimSupportStatus.INVALID_CITATION
    assert "CITATION_NOT_REGISTERED" in decision.reason_codes
    assert decision.requires_revision is True


def test_not_allowed_token_fails_closed() -> None:
    pack = _pack()
    claim = CitedClaimInput(
        claim_id="c1",
        claim_text="การละหมาดห้าเวลาเป็นหน้าที่ของมุสลิม",
        citation_tokens=(pack.citation_token,),
    )
    decision = CitationVerificationEngine().verify(
        CitationVerificationRequest(
            claims=(claim,),
            evidence=(pack,),
            allowed_tokens=(),
        )
    )
    assert decision.claim_results[0].support_status == ClaimSupportStatus.INVALID_CITATION
    assert "CITATION_NOT_ALLOWED" in decision.reason_codes


def test_invalidated_and_unpublished_citations_are_not_valid() -> None:
    inactive = _pack(citation_active=False, content="หลักฐานถูกลบออกจากการเผยแพร่")
    unpublished = _pack(
        is_published=False,
        content="หลักฐานยังไม่ผ่านการเผยแพร่",
        version_status="approved",
    )
    engine = CitationVerificationEngine()

    inactive_decision = engine.verify(
        CitationVerificationRequest(
            claims=(
                CitedClaimInput(
                    claim_id="inactive",
                    claim_text="หลักฐานถูกลบออกจากการเผยแพร่แล้ว",
                    citation_tokens=(inactive.citation_token,),
                ),
            ),
            evidence=(inactive,),
            allowed_tokens=(inactive.citation_token,),
        )
    )
    unpublished_decision = engine.verify(
        CitationVerificationRequest(
            claims=(
                CitedClaimInput(
                    claim_id="unpublished",
                    claim_text="หลักฐานยังไม่ผ่านการเผยแพร่",
                    citation_tokens=(unpublished.citation_token,),
                ),
            ),
            evidence=(unpublished,),
            allowed_tokens=(unpublished.citation_token,),
        )
    )

    assert inactive_decision.claim_results[0].support_status == ClaimSupportStatus.INVALID_CITATION
    assert "CITATION_INACTIVE" in inactive_decision.reason_codes
    assert (
        unpublished_decision.claim_results[0].support_status == ClaimSupportStatus.INVALID_CITATION
    )
    assert "CITATION_NOT_PUBLISHED" in unpublished_decision.reason_codes


def test_claim_support_fixture_partial_and_unsupported() -> None:
    pack = _pack(content="การละหมาดในมัสยิดมีคุณค่าสูง")
    engine = CitationVerificationEngine()

    partial = engine.verify(
        CitationVerificationRequest(
            claims=(
                CitedClaimInput(
                    claim_id="partial",
                    claim_text="การละหมาดในมัสยิดและการบริจาคซะกาตมีความสำคัญ",
                    citation_tokens=(pack.citation_token,),
                ),
            ),
            evidence=(pack,),
            allowed_tokens=(pack.citation_token,),
            min_supported_overlap=0.85,
            min_partial_overlap=0.15,
        )
    )
    unsupported = engine.verify(
        CitationVerificationRequest(
            claims=(
                CitedClaimInput(
                    claim_id="unsupported",
                    claim_text="การลงทุนในตลาดหุ้นต้องหลีกเลี่ยงดอกเบี้ย",
                    citation_tokens=(pack.citation_token,),
                ),
            ),
            evidence=(pack,),
            allowed_tokens=(pack.citation_token,),
        )
    )

    # With a high supported threshold this claim should not fully pass.
    assert partial.claim_results[0].support_status == ClaimSupportStatus.PARTIAL
    assert partial.status == OverallVerificationStatus.NEEDS_REVISION
    assert unsupported.claim_results[0].support_status == ClaimSupportStatus.UNSUPPORTED
    assert "CLAIM_UNSUPPORTED" in unsupported.reason_codes


def test_madhhab_mismatch_triggers_revision() -> None:
    pack = _pack(madhhab="hanafi", content="รายละเอียดการละหมาดตามทัศนะหนึ่ง")
    decision = CitationVerificationEngine().verify(
        CitationVerificationRequest(
            claims=(
                CitedClaimInput(
                    claim_id="c1",
                    claim_text="รายละเอียดการละหมาดตามทัศนะหนึ่ง",
                    citation_tokens=(pack.citation_token,),
                    declared_madhhab="shafii",
                ),
            ),
            evidence=(pack,),
            allowed_tokens=(pack.citation_token,),
            requested_madhhab="shafii",
        )
    )
    assert decision.status == OverallVerificationStatus.NEEDS_REVISION
    assert "MADHHAB_MISMATCH" in decision.reason_codes


def test_reference_mismatch_fails() -> None:
    pack = _pack(canonical_reference="book:prayer:1:10")
    decision = CitationVerificationEngine().verify(
        CitationVerificationRequest(
            claims=(
                CitedClaimInput(
                    claim_id="c1",
                    claim_text="การละหมาดห้าเวลาเป็นหน้าที่ของมุสลิม",
                    citation_tokens=(pack.citation_token,),
                    declared_reference="quran:2:43",
                ),
            ),
            evidence=(pack,),
            allowed_tokens=(pack.citation_token,),
        )
    )
    assert decision.claim_results[0].support_status == ClaimSupportStatus.INVALID_CITATION
    assert "REFERENCE_MISMATCH" in decision.reason_codes


def test_invalid_thresholds_raise() -> None:
    pack = _pack()
    with pytest.raises(CitationVerificationError) as exc_info:
        CitationVerificationEngine().verify(
            CitationVerificationRequest(
                claims=(
                    CitedClaimInput(
                        claim_id="c1",
                        claim_text="การละหมาด",
                        citation_tokens=(pack.citation_token,),
                    ),
                ),
                evidence=(pack,),
                allowed_tokens=(pack.citation_token,),
                min_supported_overlap=0.1,
                min_partial_overlap=0.2,
            )
        )
    assert exc_info.value.code == "CITATION_VERIFICATION_THRESHOLD_INVALID"


def test_load_evidence_packs_from_registry(registry_fixture: RegistryFixture) -> None:
    registered = registry_fixture.registry.register_citation(
        CitationRegistrationRequest(
            document_version_id=registry_fixture.version_id,
            chunk_id=registry_fixture.chunk_id,
            citation_type=CitationType.BOOK,
            canonical_reference="book:prayer:1:10",
            display_title="Fiqh of Prayer",
            actor_user_id=registry_fixture.actor_id,
            volume="1",
            page="10",
        )
    )
    packs = load_evidence_packs(registry_fixture.uow, (registered.citation.token,))
    assert len(packs) == 1
    assert packs[0].citation_token == registered.citation.token
    assert packs[0].citation_active is True
    assert packs[0].is_published is True
    assert "ละหมาด" in packs[0].chunk_content

    registry_fixture.registry.invalidate_citation(
        citation_id=registered.citation.id,
        reason="source correction",
        actor_user_id=registry_fixture.actor_id,
    )
    inactive_packs = load_evidence_packs(registry_fixture.uow, (registered.citation.token,))
    assert inactive_packs[0].citation_active is False

    decision = CitationVerificationEngine().verify(
        CitationVerificationRequest(
            claims=(
                CitedClaimInput(
                    claim_id="c1",
                    claim_text=registry_fixture.chunk_content,
                    citation_tokens=(registered.citation.token,),
                ),
            ),
            evidence=inactive_packs,
            allowed_tokens=(registered.citation.token,),
        )
    )
    assert decision.claim_results[0].support_status == ClaimSupportStatus.INVALID_CITATION


class _FlakyGenerator:
    """First draft fails citation verification; second draft recovers."""

    def __init__(self, bad: GeneratedAnswerDraft, good: GeneratedAnswerDraft) -> None:
        self.bad = bad
        self.good = good
        self.calls = 0

    async def generate(self, context: AnswerGenerationContext) -> GeneratedAnswerDraft:
        self.calls += 1
        return self.bad if self.calls == 1 else self.good


class _AlwaysBadGenerator:
    def __init__(self, draft: GeneratedAnswerDraft) -> None:
        self.draft = draft
        self.calls = 0

    async def generate(self, context: AnswerGenerationContext) -> GeneratedAnswerDraft:
        self.calls += 1
        return self.draft


def _context_candidate(
    pack: VerificationEvidencePack,
    *,
    score: float = 0.9,
    rank: int = 1,
) -> EvidenceCandidate:
    return EvidenceCandidate(
        chunk_id=pack.chunk_id,
        document_version_id=pack.document_version_id,
        source_id=uuid4(),
        canonical_reference=pack.canonical_reference,
        madhhab=pack.madhhab or "shafii",
        source_type="fiqh",
        license_status="persistent_redistributable",
        score_final=score,
        score_reranker=score,
        score_reliability=1.0,
        rank=rank,
        metadata={
            "citation_token": pack.citation_token,
            "citation_id": str(pack.citation_id),
            "chunk_content": pack.chunk_content,
            "citation_type": pack.citation_type,
            "display_title": pack.display_title,
            "is_published": pack.is_published,
            "citation_active": pack.citation_active,
            "version_status": pack.version_status,
        },
    )


def _classification() -> ClassificationResult:
    return ClassificationResult(
        language=Language.THAI,
        intent=Intent.FIQH,
        madhhab=Madhhab.SHAFII,
        risk_level=RiskLevel.LOW,
        requires_current_info=False,
        requires_thai_specific=True,
        confidence=0.95,
        trace={"source": "test"},
    )


@pytest.mark.asyncio
async def test_revision_path_recovers_after_failed_verification() -> None:
    pack = _pack(content="การละหมาดห้าเวลาเป็นหน้าที่ของมุสลิมทุกคน")
    candidate = _context_candidate(pack)
    good_citation = AnswerCitation(
        citation_id=pack.citation_token,
        display=pack.display_title,
        source_type="book",
        verification_status="pending",
    )
    bad_draft = GeneratedAnswerDraft(
        summary="สรุปผิด",
        answer_th="คำตอบที่อ้าง citation ที่ไม่อนุญาต",
        citations=(
            AnswerCitation(
                citation_id=citation_token(uuid4()),
                display="fabricated",
                source_type="book",
                verification_status="pending",
            ),
        ),
        trace={
            "claims": [
                {
                    "claim_id": "c1",
                    "claim_text": "คำตอบที่อ้าง citation ที่ไม่อนุญาต",
                    "citation_tokens": [citation_token(uuid4())],
                }
            ]
        },
    )
    good_draft = GeneratedAnswerDraft(
        summary="สรุปถูกต้อง",
        answer_th="การละหมาดห้าเวลาเป็นหน้าที่ของมุสลิมทุกคน",
        citations=(good_citation,),
        limitations=("นี่ไม่ใช่ฟัตวา",),
        trace={
            "claims": [
                {
                    "claim_id": "c1",
                    "claim_text": "การละหมาดห้าเวลาเป็นหน้าที่ของมุสลิมทุกคน",
                    "citation_tokens": [pack.citation_token],
                    "quoted_text": "การละหมาดห้าเวลาเป็นหน้าที่ของมุสลิม",
                }
            ]
        },
    )
    generator = _FlakyGenerator(bad_draft, good_draft)
    orchestrator = AnswerOrchestrator(
        classifier=QuestionClassifier(),
        risk_policy_engine=RiskPolicyEngine(),
        retriever=StaticAnswerRetriever((candidate, _context_candidate(_pack(), rank=2))),
        evidence_service=EvidenceSufficiencyService(),
        generator=generator,
        verifier=CitationVerificationAnswerVerifier(),
    )
    result = await orchestrator.answer(
        AnswerOrchestrationRequest(
            question="การละหมาดห้าเวลาจำเป็นหรือไม่",
            max_revision_attempts=1,
        )
    )
    assert result.status == AnswerOrchestrationStatus.COMPLETED
    assert result.answer is not None
    assert generator.calls == 2
    assert any(step.name.value == "revise" for step in result.steps)


@pytest.mark.asyncio
async def test_failed_verification_abstains_when_unrecovered() -> None:
    pack = _pack(content="การละหมาดห้าเวลาเป็นหน้าที่ของมุสลิมทุกคน")
    candidate = _context_candidate(pack)
    bad_token = citation_token(uuid4())
    draft = GeneratedAnswerDraft(
        summary="สรุป",
        answer_th="คำตอบที่ไม่มีหลักฐานรองรับจริง",
        citations=(
            AnswerCitation(
                citation_id=bad_token,
                display="fabricated",
                source_type="book",
                verification_status="pending",
            ),
        ),
        trace={
            "claims": [
                {
                    "claim_id": "c1",
                    "claim_text": "คำตอบที่ไม่มีหลักฐานรองรับจริง",
                    "citation_tokens": [bad_token],
                }
            ]
        },
    )
    generator = _AlwaysBadGenerator(draft)
    orchestrator = AnswerOrchestrator(
        classifier=QuestionClassifier(),
        risk_policy_engine=RiskPolicyEngine(),
        retriever=StaticAnswerRetriever((candidate, _context_candidate(_pack(), rank=2))),
        evidence_service=EvidenceSufficiencyService(),
        generator=generator,
        verifier=CitationVerificationAnswerVerifier(),
    )
    result = await orchestrator.answer(
        AnswerOrchestrationRequest(
            question="การละหมาดห้าเวลาจำเป็นหรือไม่",
            max_revision_attempts=1,
        )
    )
    assert result.status == AnswerOrchestrationStatus.ABSTAINED
    assert result.answer is not None
    assert "หลักฐาน" in result.answer.answer_th or "ไม่" in result.answer.summary
    assert generator.calls == 2


def test_answer_verifier_emits_machine_readable_claim_results() -> None:
    pack = _pack(content="การละหมาดห้าเวลาเป็นหน้าที่ของมุสลิมทุกคน")
    candidate = _context_candidate(pack)
    context = AnswerGenerationContext(
        question="q",
        classification=_classification(),
        policy_decision=PolicyDecision(
            action=PolicyAction.ALLOW,
            risk_level=RiskLevel.LOW,
            restriction_reason=RestrictionReason.NONE,
            escalation_target=EscalationTarget.NONE,
        ),
        evidence_decision=EvidenceSufficiencyDecision(
            status=EvidenceStatus.SUFFICIENT,
            reason_codes=("OK",),
            rules_version="evidence-sufficiency-rules-v1",
            allow_high_confidence_answer=True,
            should_search_more=False,
            should_abstain=False,
            candidate_count=1,
            distinct_source_count=1,
            top_score=0.9,
            average_score=0.9,
            trace={},
        ),
        candidates=(candidate,),
        trace_id="trace-verifier",
        prompt_version="answer-generation-prompt-v1",
    )
    draft = GeneratedAnswerDraft(
        summary="สรุป",
        answer_th="การละหมาดห้าเวลาเป็นหน้าที่ของมุสลิมทุกคน",
        citations=(
            AnswerCitation(
                citation_id=pack.citation_token,
                display=pack.display_title,
                source_type="book",
                verification_status="pending",
            ),
        ),
        trace={
            "claims": [
                {
                    "claim_id": "c1",
                    "claim_text": "การละหมาดห้าเวลาเป็นหน้าที่ของมุสลิมทุกคน",
                    "citation_tokens": [pack.citation_token],
                }
            ]
        },
    )
    result = CitationVerificationAnswerVerifier().verify(draft, context)
    assert result.status.value == "verified"
    claim_results = result.trace["claim_results"]
    assert isinstance(claim_results, list)
    first = claim_results[0]
    assert isinstance(first, dict)
    assert first["support_status"] == "supported"
    assert first["claim_id"] == "c1"
