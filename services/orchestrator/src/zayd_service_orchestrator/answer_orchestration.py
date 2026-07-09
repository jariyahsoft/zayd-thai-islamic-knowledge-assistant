"""Traceable answer orchestration state machine."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID, uuid4

from zayd_common.enums import EvidenceStatus
from zayd_service_retrieval.evidence_sufficiency import (
    EvidenceCandidate,
    EvidenceSufficiencyDecision,
    EvidenceSufficiencyRequest,
    EvidenceSufficiencyService,
)
from zayd_common.prompt_registry import PromptDefinition, prompt_body_only

from .provider_sdk import LLMMessage, LLMProvider, LLMRequest, ProviderSDKError
from .question_classification import ClassificationResult, QuestionClassifier
from .risk_policy_engine import PolicyAction, PolicyDecision, RiskPolicyEngine

ANSWER_ORCHESTRATOR_VERSION = "answer-orchestrator-v1"
ANSWER_SCHEMA_VERSION = "answer-response-v1"
DEFAULT_PROMPT_VERSION = "answer-generation-prompt-v1"


class AnswerOrchestrationStatus(StrEnum):
    """Terminal state of the answer workflow."""

    COMPLETED = "completed"
    ABSTAINED = "abstained"
    ESCALATED = "escalated"
    RESTRICTED = "restricted"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OrchestrationStepName(StrEnum):
    """State-machine step names."""

    VALIDATE = "validate"
    IDEMPOTENCY = "idempotency"
    CLASSIFY = "classify"
    POLICY = "policy"
    RETRIEVE = "retrieve"
    EVIDENCE = "evidence"
    EXPAND_RETRIEVE = "expand_retrieve"
    GENERATE = "generate"
    VERIFY = "verify"
    REVISE = "revise"
    RETURN = "return"


class OrchestrationStepStatus(StrEnum):
    """State-machine step status."""

    PENDING = "pending"
    STARTED = "started"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ConfidenceLevel(StrEnum):
    """Public confidence levels for structured answers."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AnswerVerificationStatus(StrEnum):
    """Deterministic verification result for the generated answer."""

    VERIFIED = "verified"
    NEEDS_REVISION = "needs_revision"
    FAILED = "failed"


@dataclass(frozen=True)
class OrchestrationStepTrace:
    """Safe trace record for one state-machine step."""

    name: OrchestrationStepName
    status: OrchestrationStepStatus
    started_at: datetime
    completed_at: datetime | None = None
    trace: dict[str, object] = field(default_factory=dict)
    error_code: str | None = None


@dataclass(frozen=True)
class AnswerCitation:
    """Citation handle exposed in the structured answer."""

    citation_id: str
    display: str
    source_type: str
    verification_status: str


@dataclass(frozen=True)
class StructuredAnswer:
    """SRS §26 compatible structured answer payload."""

    answer_id: str
    summary: str
    answer_th: str
    madhhab: str
    risk_level: str
    evidence_sufficient: bool
    confidence: ConfidenceLevel
    citations: tuple[AnswerCitation, ...]
    differences_of_opinion: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    warning: str | None = None
    requires_scholar: bool = False
    trace_id: str | None = None
    schema_version: str = ANSWER_SCHEMA_VERSION


@dataclass(frozen=True)
class AnswerGenerationContext:
    """Input supplied to an answer generator."""

    question: str
    classification: ClassificationResult
    policy_decision: PolicyDecision
    evidence_decision: EvidenceSufficiencyDecision
    candidates: tuple[EvidenceCandidate, ...]
    trace_id: str
    prompt_version: str


@dataclass(frozen=True)
class GeneratedAnswerDraft:
    """Draft answer produced before deterministic verification."""

    summary: str
    answer_th: str
    citations: tuple[AnswerCitation, ...]
    differences_of_opinion: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    trace: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class AnswerVerificationResult:
    """Verification output for a draft answer."""

    status: AnswerVerificationStatus
    reason_codes: tuple[str, ...]
    trace: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class AnswerOrchestrationRequest:
    """Request for the answer state machine."""

    question: str
    actor: str = "system"
    idempotency_key: str | None = None
    trace_id: str | None = None
    requested_madhhab: str | None = None
    timeout_seconds: float = 30.0
    max_retries: int = 1
    max_revision_attempts: int = 1


@dataclass(frozen=True)
class AnswerOrchestrationResult:
    """Terminal output from the answer workflow."""

    status: AnswerOrchestrationStatus
    answer: StructuredAnswer | None
    trace_id: str
    request_id: str
    idempotency_key: str | None
    orchestrator_version: str
    classification: ClassificationResult | None
    policy_decision: PolicyDecision | None
    evidence_decision: EvidenceSufficiencyDecision | None
    steps: tuple[OrchestrationStepTrace, ...]
    error_code: str | None = None
    trace: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievalResponse:
    """Retrieval response consumed by orchestration."""

    candidates: tuple[EvidenceCandidate, ...]
    retriever_version: str
    retrieval_run_id: object | None = None
    trace: dict[str, object] = field(default_factory=dict)


class AnswerOrchestrationStore(Protocol):
    """Idempotency store for terminal orchestration results."""

    def get(self, idempotency_key: str) -> AnswerOrchestrationResult | None: ...

    def put(self, idempotency_key: str, result: AnswerOrchestrationResult) -> None: ...


class InMemoryAnswerOrchestrationStore:
    """Small deterministic store used for tests and local orchestration."""

    def __init__(self) -> None:
        self._results: dict[str, AnswerOrchestrationResult] = {}

    def get(self, idempotency_key: str) -> AnswerOrchestrationResult | None:
        return self._results.get(idempotency_key)

    def put(self, idempotency_key: str, result: AnswerOrchestrationResult) -> None:
        self._results.setdefault(idempotency_key, result)


class AnswerRetriever(Protocol):
    """Retrieval port used by the answer state machine."""

    async def retrieve(
        self,
        question: str,
        *,
        classification: ClassificationResult,
        trace_id: str,
        expanded: bool = False,
    ) -> RetrievalResponse: ...


class AnswerGenerator(Protocol):
    """Generation port used by the answer state machine."""

    async def generate(self, context: AnswerGenerationContext) -> GeneratedAnswerDraft: ...


class AnswerVerifier(Protocol):
    """Deterministic answer verifier."""

    def verify(
        self,
        draft: GeneratedAnswerDraft,
        context: AnswerGenerationContext,
    ) -> AnswerVerificationResult: ...


class StaticAnswerRetriever:
    """Simple retriever fixture for deterministic local orchestration."""

    def __init__(
        self,
        candidates: tuple[EvidenceCandidate, ...],
        *,
        expanded_candidates: tuple[EvidenceCandidate, ...] | None = None,
        retriever_version: str = "static-answer-retriever-v1",
    ) -> None:
        self.candidates = candidates
        self.expanded_candidates = expanded_candidates
        self.retriever_version = retriever_version
        self.calls = 0
        self.cancelled = False

    async def retrieve(
        self,
        question: str,
        *,
        classification: ClassificationResult,
        trace_id: str,
        expanded: bool = False,
    ) -> RetrievalResponse:
        self.calls += 1
        await asyncio.sleep(0)
        candidates = (
            self.expanded_candidates if expanded and self.expanded_candidates else self.candidates
        )
        return RetrievalResponse(
            candidates=tuple(candidates),
            retriever_version=self.retriever_version,
            trace={
                "candidate_count": len(candidates),
                "expanded": expanded,
                "classification_risk": classification.risk_level.value,
            },
        )


class LLMAnswerGenerator:
    """Structured answer generator backed by the provider SDK."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        *,
        prompt_record: PromptDefinition | None = None,
        prompt_version: str = DEFAULT_PROMPT_VERSION,
    ) -> None:
        self.llm_provider = llm_provider
        self.prompt_record = prompt_record
        self.prompt_version = prompt_record.version if prompt_record else prompt_version

    async def generate(self, context: AnswerGenerationContext) -> GeneratedAnswerDraft:
        evidence_summary = "\n".join(
            f"- {candidate.canonical_reference}: {candidate.source_type}"
            for candidate in context.candidates[:5]
        )
        system_prompt = (
            prompt_body_only(self.prompt_record.prompt_body)
            if self.prompt_record
            else (
                "Create a concise Thai Islamic knowledge answer using only the "
                "provided evidence handles. Do not issue a fatwa."
            )
        )
        request = LLMRequest(
            messages=(
                LLMMessage(
                    role="system",
                    content=system_prompt,
                ),
                LLMMessage(
                    role="user",
                    content=(
                        f"Question: {context.question}\n"
                        f"Risk: {context.policy_decision.risk_level.value}\n"
                        f"Evidence:\n{evidence_summary}"
                    ),
                ),
            ),
            trace_id=context.trace_id,
            temperature=0.0,
            max_output_tokens=512,
            safety_context={
                "policy_version": context.policy_decision.policy_version,
                "evidence_rules_version": context.evidence_decision.rules_version,
                "prompt_version": context.prompt_version,
            },
        )
        response = await self.llm_provider.generate(request)
        citations = tuple(_citation_from_candidate(candidate) for candidate in context.candidates)
        return GeneratedAnswerDraft(
            summary="คำตอบโดยสรุปจากหลักฐานที่ค้นได้",
            answer_th=response.text,
            citations=citations,
            limitations=("นี่ไม่ใช่ฟัตวา",),
            trace={
                "provider": response.provider.name,
                "finish_reason": response.finish_reason,
                "usage_total_tokens": response.usage.total_tokens,
            },
        )


class TemplateAnswerGenerator:
    """Deterministic local generator for tests and offline mode."""

    def __init__(self, *, fail_first_attempt: bool = False) -> None:
        self.calls = 0
        self.fail_first_attempt = fail_first_attempt

    async def generate(self, context: AnswerGenerationContext) -> GeneratedAnswerDraft:
        self.calls += 1
        await asyncio.sleep(0)
        if self.fail_first_attempt and self.calls == 1:
            return GeneratedAnswerDraft(
                summary="needs revision",
                answer_th="ยังไม่ได้ใส่ citation",
                citations=(),
                limitations=("นี่ไม่ใช่ฟัตวา",),
                trace={"generator": "template", "attempt": self.calls},
            )
        citations = tuple(_citation_from_candidate(candidate) for candidate in context.candidates)
        return GeneratedAnswerDraft(
            summary="คำตอบโดยสรุปจากหลักฐานที่ค้นได้",
            answer_th=(
                "คำตอบนี้สรุปจากหลักฐานที่ค้นได้เท่านั้น และไม่ใช่คำวินิจฉัยทางศาสนา โปรดตรวจรายละเอียดจาก citation"
            ),
            citations=citations,
            limitations=("นี่ไม่ใช่ฟัตวา",),
            trace={"generator": "template", "attempt": self.calls},
        )


class DeterministicAnswerVerifier:
    """Verify basic citation and safety constraints without using an LLM."""

    def verify(
        self,
        draft: GeneratedAnswerDraft,
        context: AnswerGenerationContext,
    ) -> AnswerVerificationResult:
        allowed_citation_ids = {
            _citation_from_candidate(candidate).citation_id for candidate in context.candidates
        }
        draft_citation_ids = {citation.citation_id for citation in draft.citations}
        reason_codes: list[str] = []
        if not draft.summary.strip() or not draft.answer_th.strip():
            reason_codes.append("ANSWER_TEXT_REQUIRED")
        if not draft_citation_ids:
            reason_codes.append("CITATION_REQUIRED")
        if not draft_citation_ids.issubset(allowed_citation_ids):
            reason_codes.append("CITATION_NOT_ALLOWED")
        if "fatwa ที่ผูกพัน" in draft.answer_th or "ฟัตวาที่ผูกพัน" in draft.answer_th:
            reason_codes.append("PROHIBITED_FATWA_CLAIM")
        if context.evidence_decision.status != EvidenceStatus.SUFFICIENT:
            reason_codes.append("EVIDENCE_NOT_SUFFICIENT_FOR_GENERATED_ANSWER")
        status = (
            AnswerVerificationStatus.VERIFIED
            if not reason_codes
            else AnswerVerificationStatus.NEEDS_REVISION
        )
        return AnswerVerificationResult(
            status=status,
            reason_codes=tuple(reason_codes or ("VERIFIED",)),
            trace={
                "allowed_citation_count": len(allowed_citation_ids),
                "draft_citation_count": len(draft_citation_ids),
            },
        )


class AnswerOrchestrator:
    """Run the answer workflow as a traceable state machine."""

    def __init__(
        self,
        *,
        classifier: QuestionClassifier,
        risk_policy_engine: RiskPolicyEngine,
        retriever: AnswerRetriever,
        evidence_service: EvidenceSufficiencyService,
        generator: AnswerGenerator,
        verifier: AnswerVerifier | None = None,
        store: AnswerOrchestrationStore | None = None,
        prompt_version: str = DEFAULT_PROMPT_VERSION,
        prompt_version_id: UUID | None = None,
        policy_version_id: UUID | None = None,
        model_configuration_id: UUID | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.classifier = classifier
        self.risk_policy_engine = risk_policy_engine
        self.retriever = retriever
        self.evidence_service = evidence_service
        self.generator = generator
        self.verifier = verifier or DeterministicAnswerVerifier()
        self.store = store or InMemoryAnswerOrchestrationStore()
        self.prompt_version = prompt_version
        self.prompt_version_id = prompt_version_id
        self.policy_version_id = policy_version_id
        self.model_configuration_id = model_configuration_id
        self.clock = clock or (lambda: datetime.now(UTC))

    async def answer(self, request: AnswerOrchestrationRequest) -> AnswerOrchestrationResult:
        request_id = f"answer-{uuid4()}"
        trace_id = request.trace_id or request_id
        steps: list[OrchestrationStepTrace] = []
        classification: ClassificationResult | None = None
        policy_decision: PolicyDecision | None = None
        evidence_decision: EvidenceSufficiencyDecision | None = None

        try:
            self._validate_request(request)
            self._record_step(
                steps,
                OrchestrationStepName.VALIDATE,
                OrchestrationStepStatus.COMPLETED,
                {"question_present": True, "actor": request.actor},
            )

            if request.idempotency_key:
                cached = self.store.get(request.idempotency_key)
                if cached is not None:
                    self._record_step(
                        steps,
                        OrchestrationStepName.IDEMPOTENCY,
                        OrchestrationStepStatus.COMPLETED,
                        {"cache_hit": True},
                    )
                    return cached
                self._record_step(
                    steps,
                    OrchestrationStepName.IDEMPOTENCY,
                    OrchestrationStepStatus.COMPLETED,
                    {"cache_hit": False},
                )

            result = await asyncio.wait_for(
                self._run(
                    request=request,
                    request_id=request_id,
                    trace_id=trace_id,
                    steps=steps,
                ),
                timeout=request.timeout_seconds,
            )
            if request.idempotency_key:
                self.store.put(request.idempotency_key, result)
            return result
        except TimeoutError:
            return self._failure_result(
                request=request,
                request_id=request_id,
                trace_id=trace_id,
                steps=steps,
                status=AnswerOrchestrationStatus.FAILED,
                error_code="ANSWER_TIMEOUT",
                classification=classification,
                policy_decision=policy_decision,
                evidence_decision=evidence_decision,
            )
        except asyncio.CancelledError:
            self._record_step(
                steps,
                OrchestrationStepName.RETURN,
                OrchestrationStepStatus.CANCELLED,
                {"cancelled": True},
            )
            raise
        except ProviderSDKError as error:
            return self._failure_result(
                request=request,
                request_id=request_id,
                trace_id=trace_id,
                steps=steps,
                status=AnswerOrchestrationStatus.FAILED,
                error_code=error.code,
                classification=classification,
                policy_decision=policy_decision,
                evidence_decision=evidence_decision,
            )

    async def _run(
        self,
        *,
        request: AnswerOrchestrationRequest,
        request_id: str,
        trace_id: str,
        steps: list[OrchestrationStepTrace],
    ) -> AnswerOrchestrationResult:
        classification = await self.classifier.classify(request.question)
        self._record_step(
            steps,
            OrchestrationStepName.CLASSIFY,
            OrchestrationStepStatus.COMPLETED,
            {
                "schema_version": classification.schema_version,
                "method": classification.method,
                "risk_level": classification.risk_level.value,
                "intent": classification.intent.value,
                "madhhab": classification.madhhab.value,
            },
        )

        policy_decision = self.risk_policy_engine.evaluate(
            classification,
            question_text=request.question,
            actor=request.actor,
        )
        self._record_step(
            steps,
            OrchestrationStepName.POLICY,
            OrchestrationStepStatus.COMPLETED,
            {
                "action": policy_decision.action.value,
                "risk_level": policy_decision.risk_level.value,
                "policy_version": policy_decision.policy_version,
                "policy_status": policy_decision.policy_status.value,
                "escalation_target": policy_decision.escalation_target.value,
            },
        )

        if policy_decision.action == PolicyAction.RESTRICT:
            result = self._policy_terminal_result(
                request=request,
                request_id=request_id,
                trace_id=trace_id,
                steps=steps,
                classification=classification,
                policy_decision=policy_decision,
                status=AnswerOrchestrationStatus.RESTRICTED,
            )
            self._record_step(
                steps,
                OrchestrationStepName.RETURN,
                OrchestrationStepStatus.COMPLETED,
                {"status": result.status.value},
            )
            return _replace_steps(result, steps)

        retrieval = await self._retry_retrieve(
            request,
            classification=classification,
            trace_id=trace_id,
            expanded=False,
        )
        self._record_step(
            steps,
            OrchestrationStepName.RETRIEVE,
            OrchestrationStepStatus.COMPLETED,
            {
                "candidate_count": len(retrieval.candidates),
                "retriever_version": retrieval.retriever_version,
            },
        )

        evidence_decision = self._evaluate_evidence(
            request=request,
            retrieval=retrieval,
            classification=classification,
            trace_id=trace_id,
        )
        self._record_evidence_step(steps, evidence_decision)

        if evidence_decision.should_search_more:
            expanded_retrieval = await self._retry_retrieve(
                request,
                classification=classification,
                trace_id=trace_id,
                expanded=True,
            )
            self._record_step(
                steps,
                OrchestrationStepName.EXPAND_RETRIEVE,
                OrchestrationStepStatus.COMPLETED,
                {
                    "candidate_count": len(expanded_retrieval.candidates),
                    "retriever_version": expanded_retrieval.retriever_version,
                },
            )
            expanded_evidence = self._evaluate_evidence(
                request=request,
                retrieval=expanded_retrieval,
                classification=classification,
                trace_id=trace_id,
            )
            self._record_evidence_step(steps, expanded_evidence)
            if _evidence_rank(expanded_evidence.status) > _evidence_rank(evidence_decision.status):
                retrieval = expanded_retrieval
                evidence_decision = expanded_evidence

        if evidence_decision.status == EvidenceStatus.INSUFFICIENT:
            result = self._abstain_result(
                request=request,
                request_id=request_id,
                trace_id=trace_id,
                steps=steps,
                classification=classification,
                policy_decision=policy_decision,
                evidence_decision=evidence_decision,
            )
            self._record_step(
                steps,
                OrchestrationStepName.RETURN,
                OrchestrationStepStatus.COMPLETED,
                {"status": result.status.value},
            )
            return _replace_steps(result, steps)

        if evidence_decision.status == EvidenceStatus.CONFLICTING:
            result = self._conflicting_result(
                request=request,
                request_id=request_id,
                trace_id=trace_id,
                steps=steps,
                classification=classification,
                policy_decision=policy_decision,
                evidence_decision=evidence_decision,
            )
            self._record_step(
                steps,
                OrchestrationStepName.RETURN,
                OrchestrationStepStatus.COMPLETED,
                {"status": result.status.value},
            )
            return _replace_steps(result, steps)

        if policy_decision.action == PolicyAction.ESCALATE_TO_SCHOLAR:
            result = self._policy_terminal_result(
                request=request,
                request_id=request_id,
                trace_id=trace_id,
                steps=steps,
                classification=classification,
                policy_decision=policy_decision,
                evidence_decision=evidence_decision,
                status=AnswerOrchestrationStatus.ESCALATED,
            )
            self._record_step(
                steps,
                OrchestrationStepName.RETURN,
                OrchestrationStepStatus.COMPLETED,
                {"status": result.status.value},
            )
            return _replace_steps(result, steps)

        context = AnswerGenerationContext(
            question=request.question,
            classification=classification,
            policy_decision=policy_decision,
            evidence_decision=evidence_decision,
            candidates=retrieval.candidates,
            trace_id=trace_id,
            prompt_version=self.prompt_version,
        )
        draft = await self.generator.generate(context)
        self._record_step(
            steps,
            OrchestrationStepName.GENERATE,
            OrchestrationStepStatus.COMPLETED,
            {
                "prompt_version": self.prompt_version,
                "citation_count": len(draft.citations),
                "generator_trace": _safe_trace(draft.trace),
            },
        )

        verification = self.verifier.verify(draft, context)
        self._record_step(
            steps,
            OrchestrationStepName.VERIFY,
            OrchestrationStepStatus.COMPLETED,
            {
                "status": verification.status.value,
                "reason_codes": verification.reason_codes,
                "verification_trace": _safe_trace(verification.trace),
            },
        )
        for attempt in range(1, request.max_revision_attempts + 1):
            if verification.status == AnswerVerificationStatus.VERIFIED:
                break
            draft = await self.generator.generate(context)
            self._record_step(
                steps,
                OrchestrationStepName.REVISE,
                OrchestrationStepStatus.COMPLETED,
                {"attempt": attempt, "citation_count": len(draft.citations)},
            )
            verification = self.verifier.verify(draft, context)
            self._record_step(
                steps,
                OrchestrationStepName.VERIFY,
                OrchestrationStepStatus.COMPLETED,
                {"status": verification.status.value, "reason_codes": verification.reason_codes},
            )

        if verification.status != AnswerVerificationStatus.VERIFIED:
            result = self._abstain_result(
                request=request,
                request_id=request_id,
                trace_id=trace_id,
                steps=steps,
                classification=classification,
                policy_decision=policy_decision,
                evidence_decision=evidence_decision,
                reason_codes=verification.reason_codes,
            )
            self._record_step(
                steps,
                OrchestrationStepName.RETURN,
                OrchestrationStepStatus.COMPLETED,
                {"status": result.status.value},
            )
            return _replace_steps(result, steps)

        answer = _structured_answer(
            draft=draft,
            classification=classification,
            policy_decision=policy_decision,
            evidence_decision=evidence_decision,
            trace_id=trace_id,
            confidence=ConfidenceLevel.HIGH
            if evidence_decision.allow_high_confidence_answer
            else ConfidenceLevel.LOW,
        )
        result = AnswerOrchestrationResult(
            status=AnswerOrchestrationStatus.COMPLETED,
            answer=answer,
            trace_id=trace_id,
            request_id=request_id,
            idempotency_key=request.idempotency_key,
            orchestrator_version=ANSWER_ORCHESTRATOR_VERSION,
            classification=classification,
            policy_decision=policy_decision,
            evidence_decision=evidence_decision,
            steps=tuple(steps),
            trace=self._result_trace(classification, policy_decision, evidence_decision),
        )
        self._record_step(
            steps,
            OrchestrationStepName.RETURN,
            OrchestrationStepStatus.COMPLETED,
            {"status": result.status.value},
        )
        return _replace_steps(result, steps)

    async def _retry_retrieve(
        self,
        request: AnswerOrchestrationRequest,
        *,
        classification: ClassificationResult,
        trace_id: str,
        expanded: bool,
    ) -> RetrievalResponse:
        last_error: Exception | None = None
        for _ in range(request.max_retries + 1):
            try:
                return await self.retriever.retrieve(
                    request.question,
                    classification=classification,
                    trace_id=trace_id,
                    expanded=expanded,
                )
            except asyncio.CancelledError:
                raise
            except Exception as error:
                last_error = error
        raise ProviderSDKError(
            "PROVIDER_RESPONSE_INVALID",
            f"Retrieval failed after retries: {type(last_error).__name__}",
            status_code=502,
        )

    def _evaluate_evidence(
        self,
        *,
        request: AnswerOrchestrationRequest,
        retrieval: RetrievalResponse,
        classification: ClassificationResult,
        trace_id: str,
    ) -> EvidenceSufficiencyDecision:
        return self.evidence_service.evaluate(
            EvidenceSufficiencyRequest(
                query=request.question,
                candidates=retrieval.candidates,
                requested_madhhab=request.requested_madhhab or _requested_madhhab(classification),
                retrieval_run_id=None,
                trace_id=trace_id,
            )
        )

    def _record_step(
        self,
        steps: list[OrchestrationStepTrace],
        name: OrchestrationStepName,
        status: OrchestrationStepStatus,
        trace: dict[str, object] | None = None,
        error_code: str | None = None,
    ) -> None:
        now = self.clock()
        steps.append(
            OrchestrationStepTrace(
                name=name,
                status=status,
                started_at=now,
                completed_at=now,
                trace=_safe_trace(trace or {}),
                error_code=error_code,
            )
        )

    def _record_evidence_step(
        self,
        steps: list[OrchestrationStepTrace],
        evidence_decision: EvidenceSufficiencyDecision,
    ) -> None:
        self._record_step(
            steps,
            OrchestrationStepName.EVIDENCE,
            OrchestrationStepStatus.COMPLETED,
            {
                "status": evidence_decision.status.value,
                "reason_codes": evidence_decision.reason_codes,
                "rules_version": evidence_decision.rules_version,
                "allow_high_confidence_answer": evidence_decision.allow_high_confidence_answer,
                "should_search_more": evidence_decision.should_search_more,
                "should_abstain": evidence_decision.should_abstain,
            },
        )

    def _validate_request(self, request: AnswerOrchestrationRequest) -> None:
        if not request.question.strip():
            raise ProviderSDKError(
                "PROVIDER_INPUT_INVALID",
                "Question text is required.",
                status_code=400,
            )
        if request.timeout_seconds <= 0:
            raise ProviderSDKError(
                "PROVIDER_CONFIG_INVALID",
                "timeout_seconds must be positive.",
                status_code=400,
            )
        if request.max_retries < 0 or request.max_retries > 5:
            raise ProviderSDKError(
                "PROVIDER_CONFIG_INVALID",
                "max_retries must be between 0 and 5.",
                status_code=400,
            )

    def _policy_terminal_result(
        self,
        *,
        request: AnswerOrchestrationRequest,
        request_id: str,
        trace_id: str,
        steps: list[OrchestrationStepTrace],
        classification: ClassificationResult,
        policy_decision: PolicyDecision,
        status: AnswerOrchestrationStatus,
        evidence_decision: EvidenceSufficiencyDecision | None = None,
    ) -> AnswerOrchestrationResult:
        answer = StructuredAnswer(
            answer_id=f"ans-{uuid4()}",
            summary="ไม่สามารถตอบเป็นคำวินิจฉัยเฉพาะกรณีได้",
            answer_th=policy_decision.user_facing_message
            or policy_decision.warning_message
            or policy_decision.disclaimer_message
            or "คำถามนี้ต้องจำกัดคำตอบตามนโยบายความปลอดภัย",
            madhhab=classification.madhhab.value,
            risk_level=policy_decision.risk_level.value,
            evidence_sufficient=evidence_decision is not None
            and evidence_decision.status == EvidenceStatus.SUFFICIENT,
            confidence=ConfidenceLevel.LOW,
            citations=(),
            limitations=("นี่ไม่ใช่ฟัตวา",),
            warning=policy_decision.warning_message or policy_decision.disclaimer_message,
            requires_scholar=policy_decision.action == PolicyAction.ESCALATE_TO_SCHOLAR,
            trace_id=trace_id,
        )
        return AnswerOrchestrationResult(
            status=status,
            answer=answer,
            trace_id=trace_id,
            request_id=request_id,
            idempotency_key=request.idempotency_key,
            orchestrator_version=ANSWER_ORCHESTRATOR_VERSION,
            classification=classification,
            policy_decision=policy_decision,
            evidence_decision=evidence_decision,
            steps=tuple(steps),
            trace=self._result_trace(classification, policy_decision, evidence_decision),
        )

    def _abstain_result(
        self,
        *,
        request: AnswerOrchestrationRequest,
        request_id: str,
        trace_id: str,
        steps: list[OrchestrationStepTrace],
        classification: ClassificationResult,
        policy_decision: PolicyDecision,
        evidence_decision: EvidenceSufficiencyDecision,
        reason_codes: tuple[str, ...] | None = None,
    ) -> AnswerOrchestrationResult:
        reasons = reason_codes or evidence_decision.reason_codes
        answer = StructuredAnswer(
            answer_id=f"ans-{uuid4()}",
            summary="ยังไม่พบหลักฐานเพียงพอ",
            answer_th="ยังไม่พบหลักฐานที่เพียงพอสำหรับตอบคำถามนี้อย่างน่าเชื่อถือ",
            madhhab=classification.madhhab.value,
            risk_level=policy_decision.risk_level.value,
            evidence_sufficient=False,
            confidence=ConfidenceLevel.LOW,
            citations=(),
            limitations=("นี่ไม่ใช่ฟัตวา", *reasons),
            warning=policy_decision.warning_message or policy_decision.disclaimer_message,
            requires_scholar=policy_decision.action == PolicyAction.ESCALATE_TO_SCHOLAR,
            trace_id=trace_id,
        )
        return AnswerOrchestrationResult(
            status=AnswerOrchestrationStatus.ABSTAINED,
            answer=answer,
            trace_id=trace_id,
            request_id=request_id,
            idempotency_key=request.idempotency_key,
            orchestrator_version=ANSWER_ORCHESTRATOR_VERSION,
            classification=classification,
            policy_decision=policy_decision,
            evidence_decision=evidence_decision,
            steps=tuple(steps),
            trace=self._result_trace(classification, policy_decision, evidence_decision),
        )

    def _conflicting_result(
        self,
        *,
        request: AnswerOrchestrationRequest,
        request_id: str,
        trace_id: str,
        steps: list[OrchestrationStepTrace],
        classification: ClassificationResult,
        policy_decision: PolicyDecision,
        evidence_decision: EvidenceSufficiencyDecision,
    ) -> AnswerOrchestrationResult:
        answer = StructuredAnswer(
            answer_id=f"ans-{uuid4()}",
            summary="พบหลักฐานที่ขัดแย้งกัน",
            answer_th=("พบหลักฐานหรือทัศนะที่ขัดแย้งกัน จึงไม่ควรสรุปเป็นคำตอบเดียว โปรดตรวจสอบกับผู้รู้ที่เหมาะสม"),
            madhhab=classification.madhhab.value,
            risk_level=policy_decision.risk_level.value,
            evidence_sufficient=False,
            confidence=ConfidenceLevel.LOW,
            citations=(),
            differences_of_opinion=evidence_decision.reason_codes,
            limitations=("นี่ไม่ใช่ฟัตวา",),
            warning=policy_decision.warning_message or policy_decision.disclaimer_message,
            requires_scholar=True,
            trace_id=trace_id,
        )
        return AnswerOrchestrationResult(
            status=AnswerOrchestrationStatus.ESCALATED,
            answer=answer,
            trace_id=trace_id,
            request_id=request_id,
            idempotency_key=request.idempotency_key,
            orchestrator_version=ANSWER_ORCHESTRATOR_VERSION,
            classification=classification,
            policy_decision=policy_decision,
            evidence_decision=evidence_decision,
            steps=tuple(steps),
            trace=self._result_trace(classification, policy_decision, evidence_decision),
        )

    def _failure_result(
        self,
        *,
        request: AnswerOrchestrationRequest,
        request_id: str,
        trace_id: str,
        steps: list[OrchestrationStepTrace],
        status: AnswerOrchestrationStatus,
        error_code: str,
        classification: ClassificationResult | None,
        policy_decision: PolicyDecision | None,
        evidence_decision: EvidenceSufficiencyDecision | None,
    ) -> AnswerOrchestrationResult:
        self._record_step(
            steps,
            OrchestrationStepName.RETURN,
            OrchestrationStepStatus.FAILED,
            {"status": status.value},
            error_code=error_code,
        )
        return AnswerOrchestrationResult(
            status=status,
            answer=None,
            trace_id=trace_id,
            request_id=request_id,
            idempotency_key=request.idempotency_key,
            orchestrator_version=ANSWER_ORCHESTRATOR_VERSION,
            classification=classification,
            policy_decision=policy_decision,
            evidence_decision=evidence_decision,
            steps=tuple(steps),
            error_code=error_code,
            trace={
                "orchestrator_version": ANSWER_ORCHESTRATOR_VERSION,
                "error_code": error_code,
            },
        )

    def _result_trace(
        self,
        classification: ClassificationResult,
        policy_decision: PolicyDecision,
        evidence_decision: EvidenceSufficiencyDecision | None,
    ) -> dict[str, object]:
        trace: dict[str, object] = {
            "orchestrator_version": ANSWER_ORCHESTRATOR_VERSION,
            "classification_schema_version": classification.schema_version,
            "policy_version": policy_decision.policy_version,
            "policy_action": policy_decision.action.value,
            "risk_level": policy_decision.risk_level.value,
            "prompt_version": self.prompt_version,
            "prompt_version_id": str(self.prompt_version_id) if self.prompt_version_id else None,
            "policy_version_id": str(self.policy_version_id) if self.policy_version_id else None,
            "model_configuration_id": (
                str(self.model_configuration_id) if self.model_configuration_id else None
            ),
        }
        if evidence_decision is not None:
            trace.update(
                {
                    "evidence_status": evidence_decision.status.value,
                    "evidence_rules_version": evidence_decision.rules_version,
                    "evidence_reason_codes": evidence_decision.reason_codes,
                }
            )
        return trace


def _requested_madhhab(classification: ClassificationResult) -> str | None:
    if classification.madhhab.value == "unspecified":
        return None
    return classification.madhhab.value


def _citation_from_candidate(candidate: EvidenceCandidate) -> AnswerCitation:
    return AnswerCitation(
        citation_id=f"CIT-{str(candidate.chunk_id)[:8]}",
        display=candidate.canonical_reference,
        source_type=candidate.source_type,
        verification_status="verified",
    )


def _structured_answer(
    *,
    draft: GeneratedAnswerDraft,
    classification: ClassificationResult,
    policy_decision: PolicyDecision,
    evidence_decision: EvidenceSufficiencyDecision,
    trace_id: str,
    confidence: ConfidenceLevel,
) -> StructuredAnswer:
    limitations = tuple(
        dict.fromkeys(
            (
                *draft.limitations,
                *(("นี่ไม่ใช่ฟัตวา",) if "นี่ไม่ใช่ฟัตวา" not in draft.limitations else ()),
            )
        )
    )
    return StructuredAnswer(
        answer_id=f"ans-{uuid4()}",
        summary=draft.summary,
        answer_th=draft.answer_th,
        madhhab=classification.madhhab.value,
        risk_level=policy_decision.risk_level.value,
        evidence_sufficient=evidence_decision.status == EvidenceStatus.SUFFICIENT,
        confidence=confidence,
        citations=draft.citations,
        differences_of_opinion=draft.differences_of_opinion,
        limitations=limitations,
        warning=policy_decision.warning_message or policy_decision.disclaimer_message,
        requires_scholar=policy_decision.action == PolicyAction.ESCALATE_TO_SCHOLAR,
        trace_id=trace_id,
    )


def _replace_steps(
    result: AnswerOrchestrationResult,
    steps: list[OrchestrationStepTrace],
) -> AnswerOrchestrationResult:
    return AnswerOrchestrationResult(
        status=result.status,
        answer=result.answer,
        trace_id=result.trace_id,
        request_id=result.request_id,
        idempotency_key=result.idempotency_key,
        orchestrator_version=result.orchestrator_version,
        classification=result.classification,
        policy_decision=result.policy_decision,
        evidence_decision=result.evidence_decision,
        steps=tuple(steps),
        error_code=result.error_code,
        trace=result.trace,
    )


def _evidence_rank(status: EvidenceStatus) -> int:
    return {
        EvidenceStatus.INSUFFICIENT: 0,
        EvidenceStatus.CONFLICTING: 1,
        EvidenceStatus.PARTIALLY_SUFFICIENT: 2,
        EvidenceStatus.SUFFICIENT: 3,
    }[status]


def _safe_trace(trace: dict[str, object]) -> dict[str, object]:
    forbidden = ("question", "raw_text", "prompt", "messages", "answer_text", "secret", "token")
    return {
        key: value
        for key, value in trace.items()
        if not any(fragment in key.lower() for fragment in forbidden)
    }
