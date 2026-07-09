"""Factory helpers for prompt-governed orchestrator composition."""

from __future__ import annotations

from typing import Callable

from zayd_common.prompt_registry import (
    DEFAULT_ANSWER_PROMPT_NAME,
    PromptRegistryService,
)

from .answer_orchestration import (
    AnswerGenerator,
    AnswerOrchestrator,
    AnswerRetriever,
    AnswerVerifier,
    LLMAnswerGenerator,
)
from .provider_sdk import LLMProvider
from .question_classification import QuestionClassifier
from .risk_policy_engine import RiskPolicyEngine
from zayd_service_retrieval.evidence_sufficiency import EvidenceSufficiencyService


def build_managed_answer_orchestrator(
    *,
    prompt_registry: PromptRegistryService,
    retriever: AnswerRetriever,
    llm_provider: LLMProvider | None = None,
    generator: AnswerGenerator | None = None,
    verifier: AnswerVerifier | None = None,
    classifier: QuestionClassifier | None = None,
    risk_policy_engine: RiskPolicyEngine | None = None,
    evidence_service: EvidenceSufficiencyService | None = None,
) -> AnswerOrchestrator:
    """Build an orchestrator bound to approved prompt/policy/model records."""
    prompt, policy_version_id, model_configuration_id = prompt_registry.resolve_answer_dependencies(
        prompt_name=DEFAULT_ANSWER_PROMPT_NAME,
        policy_name="answer-safety",
    )
    if generator is None:
        if llm_provider is None:
            raise ValueError("llm_provider is required when generator is not supplied")
        generator = LLMAnswerGenerator(llm_provider, prompt_record=prompt)
    return AnswerOrchestrator(
        classifier=classifier or QuestionClassifier(),
        risk_policy_engine=risk_policy_engine or RiskPolicyEngine(),
        retriever=retriever,
        evidence_service=evidence_service or EvidenceSufficiencyService(),
        generator=generator,
        verifier=verifier,
        prompt_version=prompt.version,
        prompt_version_id=prompt.id,
        policy_version_id=policy_version_id,
        model_configuration_id=model_configuration_id,
    )
