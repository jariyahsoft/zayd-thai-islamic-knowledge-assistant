"""Test risk policy engine."""

from __future__ import annotations

import pytest
from zayd_service_orchestrator.provider_sdk import ProviderSDKError
from zayd_service_orchestrator.question_classification import (
    ClassificationResult,
    Intent,
    Language,
    Madhhab,
    RiskLevel,
)
from zayd_service_orchestrator.risk_policy_engine import (
    RISK_POLICY_VERSION,
    EscalationTarget,
    PolicyAction,
    PolicyStatus,
    RestrictionReason,
    RiskPolicyEngine,
)


@pytest.fixture
def engine() -> RiskPolicyEngine:
    """Create risk policy engine."""
    return RiskPolicyEngine()


# ============================================================================
# Golden Set: Expected Policy Decisions
# ============================================================================


def test_restricted_illegal_activity(engine: RiskPolicyEngine) -> None:
    """Restricted content (illegal activity) must be blocked."""
    classification = ClassificationResult(
        language=Language.THAI,
        intent=Intent.GENERAL,
        madhhab=Madhhab.UNSPECIFIED,
        risk_level=RiskLevel.RESTRICTED,
        requires_current_info=False,
        requires_thai_specific=False,
        method="rule",
        confidence=1.0,
        trace={"intent_detected": "illegal activity"},
    )

    decision = engine.evaluate(classification)

    assert decision.action == PolicyAction.RESTRICT
    assert decision.risk_level == RiskLevel.RESTRICTED
    assert decision.restriction_reason == RestrictionReason.ILLEGAL_ACTIVITY
    assert decision.policy_version == RISK_POLICY_VERSION
    assert decision.user_facing_message is not None
    assert "illegal" in decision.user_facing_message.lower()
    assert "cannot provide" in decision.user_facing_message.lower()


def test_restricted_violence(engine: RiskPolicyEngine) -> None:
    """Restricted content (violence/terrorism) must be blocked."""
    classification = ClassificationResult(
        language=Language.THAI,
        intent=Intent.GENERAL,
        madhhab=Madhhab.UNSPECIFIED,
        risk_level=RiskLevel.RESTRICTED,
        requires_current_info=False,
        requires_thai_specific=False,
        method="rule",
        confidence=1.0,
        trace={"intent_detected": "bomb terror"},
    )

    decision = engine.evaluate(classification)

    assert decision.action == PolicyAction.RESTRICT
    assert decision.restriction_reason == RestrictionReason.VIOLENCE
    assert decision.user_facing_message is not None
    assert "violence" in decision.user_facing_message.lower()


def test_high_risk_takfir_restriction(engine: RiskPolicyEngine) -> None:
    """Takfir questions must be restricted (FR-SAFE-003)."""
    classification = ClassificationResult(
        language=Language.THAI,
        intent=Intent.HIGH_RISK_RULING,
        madhhab=Madhhab.UNSPECIFIED,
        risk_level=RiskLevel.HIGH,
        requires_current_info=False,
        requires_thai_specific=False,
        method="rule",
        confidence=1.0,
        trace={"intent_detected": "takfir kafir declaration"},
    )

    decision = engine.evaluate(classification)

    assert decision.action == PolicyAction.RESTRICT
    assert decision.restriction_reason == RestrictionReason.TAKFIR
    assert decision.user_facing_message is not None
    assert "cannot make judgments" in decision.user_facing_message.lower()
    assert "muslim or non-muslim" in decision.user_facing_message.lower()
    assert decision.trace["detected_takfir"] is True


def test_high_risk_takfir_thai(engine: RiskPolicyEngine) -> None:
    """Thai takfir keywords must be detected and restricted."""
    classification = ClassificationResult(
        language=Language.THAI,
        intent=Intent.HIGH_RISK_RULING,
        madhhab=Madhhab.UNSPECIFIED,
        risk_level=RiskLevel.HIGH,
        requires_current_info=False,
        requires_thai_specific=False,
        method="rule",
        confidence=1.0,
        trace={"intent_detected": "กุฟรฺ ตักฟีรฺ"},
    )

    decision = engine.evaluate(classification)

    assert decision.action == PolicyAction.RESTRICT
    assert decision.restriction_reason == RestrictionReason.TAKFIR


def test_high_risk_divorce_escalation(engine: RiskPolicyEngine) -> None:
    """Divorce questions must escalate to scholar."""
    classification = ClassificationResult(
        language=Language.THAI,
        intent=Intent.HIGH_RISK_RULING,
        madhhab=Madhhab.SHAFII,
        risk_level=RiskLevel.HIGH,
        requires_current_info=False,
        requires_thai_specific=False,
        method="rule",
        confidence=1.0,
        trace={"intent_detected": "divorce"},
    )

    decision = engine.evaluate(classification)

    assert decision.action == PolicyAction.ESCALATE_TO_SCHOLAR
    assert decision.restriction_reason == RestrictionReason.PERSONAL_RULING_COMPLEX
    assert decision.warning_message is not None
    assert "qualified scholar" in decision.warning_message.lower()
    assert decision.escalation_message is not None
    assert decision.user_facing_message is not None
    assert "divorce" in decision.user_facing_message.lower()
    assert "scholar" in decision.user_facing_message.lower()


def test_high_risk_inheritance_escalation(engine: RiskPolicyEngine) -> None:
    """Inheritance questions must escalate to scholar."""
    classification = ClassificationResult(
        language=Language.THAI,
        intent=Intent.HIGH_RISK_RULING,
        madhhab=Madhhab.UNSPECIFIED,
        risk_level=RiskLevel.HIGH,
        requires_current_info=False,
        requires_thai_specific=False,
        method="rule",
        confidence=1.0,
        trace={"intent_detected": "inheritance"},
    )

    decision = engine.evaluate(classification)

    assert decision.action == PolicyAction.ESCALATE_TO_SCHOLAR
    assert decision.restriction_reason == RestrictionReason.PERSONAL_RULING_COMPLEX


def test_high_risk_medical_disclaimer(engine: RiskPolicyEngine) -> None:
    """Medical questions must show health disclaimer (FR-SAFE-004)."""
    classification = ClassificationResult(
        language=Language.ENGLISH,
        intent=Intent.PERSONAL_ADVICE,
        madhhab=Madhhab.UNSPECIFIED,
        risk_level=RiskLevel.HIGH,
        requires_current_info=False,
        requires_thai_specific=False,
        method="rule",
        confidence=0.9,
        trace={"risk_detected": "medical surgery question"},
    )

    decision = engine.evaluate(classification)

    assert decision.action == PolicyAction.REQUIRE_DISCLAIMER
    assert decision.restriction_reason == RestrictionReason.HEALTH_DANGER
    assert decision.disclaimer_message is not None
    assert "medical" in decision.disclaimer_message.lower()
    assert "consult" in decision.disclaimer_message.lower()
    assert decision.trace["detected_medical"] is True


def test_high_risk_medical_thai(engine: RiskPolicyEngine) -> None:
    """Thai medical keywords must trigger disclaimer."""
    classification = ClassificationResult(
        language=Language.THAI,
        intent=Intent.PERSONAL_ADVICE,
        madhhab=Madhhab.UNSPECIFIED,
        risk_level=RiskLevel.HIGH,
        requires_current_info=False,
        requires_thai_specific=False,
        method="rule",
        confidence=0.9,
        trace={"risk_detected": "รักษา ผ่าตัด"},
    )

    decision = engine.evaluate(classification)

    assert decision.action == PolicyAction.REQUIRE_DISCLAIMER
    assert decision.restriction_reason == RestrictionReason.HEALTH_DANGER


def test_high_risk_financial_disclaimer(engine: RiskPolicyEngine) -> None:
    """Financial questions must show disclaimer."""
    classification = ClassificationResult(
        language=Language.THAI,
        intent=Intent.PERSONAL_ADVICE,
        madhhab=Madhhab.UNSPECIFIED,
        risk_level=RiskLevel.HIGH,
        requires_current_info=False,
        requires_thai_specific=False,
        method="rule",
        confidence=0.9,
        trace={"risk_detected": "investment ลงทุน หุ้น"},
    )

    decision = engine.evaluate(classification)

    assert decision.action == PolicyAction.REQUIRE_DISCLAIMER
    assert decision.restriction_reason == RestrictionReason.INSUFFICIENT_QUALIFICATION
    assert decision.disclaimer_message is not None
    assert "financial" in decision.disclaimer_message.lower()
    assert decision.trace["detected_financial"] is True


def test_high_risk_generic_disclaimer(engine: RiskPolicyEngine) -> None:
    """Generic high-risk questions require disclaimer."""
    classification = ClassificationResult(
        language=Language.ENGLISH,
        intent=Intent.PERSONAL_ADVICE,
        madhhab=Madhhab.UNSPECIFIED,
        risk_level=RiskLevel.HIGH,
        requires_current_info=False,
        requires_thai_specific=False,
        method="rule",
        confidence=0.8,
        trace={"risk_detected": "generic high risk"},
    )

    decision = engine.evaluate(classification)

    assert decision.action == PolicyAction.REQUIRE_DISCLAIMER
    assert decision.restriction_reason == RestrictionReason.INSUFFICIENT_QUALIFICATION
    assert decision.disclaimer_message is not None


def test_medium_risk_fiqh_warning(engine: RiskPolicyEngine) -> None:
    """Fiqh questions get warning about madhhab variation."""
    classification = ClassificationResult(
        language=Language.THAI,
        intent=Intent.FIQH,
        madhhab=Madhhab.SHAFII,
        risk_level=RiskLevel.MEDIUM,
        requires_current_info=False,
        requires_thai_specific=False,
        method="rule",
        confidence=0.9,
        trace={"intent_detected": "fiqh"},
    )

    decision = engine.evaluate(classification)

    assert decision.action == PolicyAction.ALLOW_WITH_WARNING
    assert decision.restriction_reason == RestrictionReason.NONE
    assert decision.warning_message is not None
    assert "madhhab" in decision.warning_message.lower()
    assert "shafii" in decision.warning_message.lower()


def test_medium_risk_personal_advice_warning(engine: RiskPolicyEngine) -> None:
    """Personal advice questions get warning about circumstances."""
    classification = ClassificationResult(
        language=Language.THAI,
        intent=Intent.PERSONAL_ADVICE,
        madhhab=Madhhab.UNSPECIFIED,
        risk_level=RiskLevel.MEDIUM,
        requires_current_info=False,
        requires_thai_specific=False,
        method="rule",
        confidence=0.8,
        trace={"intent_detected": "personal_advice"},
    )

    decision = engine.evaluate(classification)

    assert decision.action == PolicyAction.ALLOW_WITH_WARNING
    assert decision.warning_message is not None
    assert "circumstances" in decision.warning_message.lower()


def test_low_risk_allow(engine: RiskPolicyEngine) -> None:
    """Low-risk questions are allowed without warnings."""
    classification = ClassificationResult(
        language=Language.THAI,
        intent=Intent.QURAN,
        madhhab=Madhhab.UNSPECIFIED,
        risk_level=RiskLevel.LOW,
        requires_current_info=False,
        requires_thai_specific=False,
        method="rule",
        confidence=0.9,
        trace={"intent_detected": "quran"},
    )

    decision = engine.evaluate(classification)

    assert decision.action == PolicyAction.ALLOW
    assert decision.risk_level == RiskLevel.LOW
    assert decision.restriction_reason == RestrictionReason.NONE
    assert decision.warning_message is None
    assert decision.disclaimer_message is None
    assert decision.escalation_message is None
    assert decision.user_facing_message is None


# ============================================================================
# Determinism Tests
# ============================================================================


def test_deterministic_same_input_same_output(engine: RiskPolicyEngine) -> None:
    """Same classification always produces same decision."""
    classification = ClassificationResult(
        language=Language.THAI,
        intent=Intent.HIGH_RISK_RULING,
        madhhab=Madhhab.UNSPECIFIED,
        risk_level=RiskLevel.HIGH,
        requires_current_info=False,
        requires_thai_specific=False,
        method="rule",
        confidence=1.0,
        trace={"intent_detected": "divorce"},
    )

    decision1 = engine.evaluate(classification)
    decision2 = engine.evaluate(classification)

    assert decision1.action == decision2.action
    assert decision1.restriction_reason == decision2.restriction_reason
    assert decision1.warning_message == decision2.warning_message


def test_model_cannot_downgrade_restrictions(engine: RiskPolicyEngine) -> None:
    """Model-based classification cannot downgrade restrictions.

    Even if LLM classifies as low risk, deterministic rules enforce
    restrictions based on detected patterns.
    """
    # Simulate: LLM says "low risk" but rules detect takfir keywords
    classification = ClassificationResult(
        language=Language.THAI,
        intent=Intent.HIGH_RISK_RULING,
        madhhab=Madhhab.UNSPECIFIED,
        risk_level=RiskLevel.HIGH,
        requires_current_info=False,
        requires_thai_specific=False,
        method="hybrid",  # LLM was involved
        confidence=0.6,  # LLM not confident
        trace={
            "intent_detected": "takfir",
            "llm_suggested_risk": "low",  # LLM was wrong
        },
    )

    decision = engine.evaluate(classification)

    # Policy engine enforces restriction regardless of LLM output
    assert decision.action == PolicyAction.RESTRICT
    assert decision.restriction_reason == RestrictionReason.TAKFIR
    assert decision.trace["deterministic_policy_authoritative"] is True


def test_question_text_overrides_model_downgrade_for_takfir(engine: RiskPolicyEngine) -> None:
    """Question text rules override an LLM downgrade to low risk."""
    classification = ClassificationResult(
        language=Language.ENGLISH,
        intent=Intent.GENERAL,
        madhhab=Madhhab.UNSPECIFIED,
        risk_level=RiskLevel.LOW,
        requires_current_info=False,
        requires_thai_specific=False,
        method="hybrid",
        confidence=0.95,
        trace={"llm_suggested_risk": "low"},
    )

    decision = engine.evaluate(
        classification,
        question_text="Is this named person a kafir if he did that?",
        actor="answer_orchestrator",
    )

    assert decision.action == PolicyAction.RESTRICT
    assert decision.restriction_reason == RestrictionReason.TAKFIR
    assert decision.escalation_target == EscalationTarget.SCHOLAR
    assert decision.trace["rule_id"] == "restricted-takfir-v1"
    matched_sources = decision.trace["matched_sources"]
    assert isinstance(matched_sources, tuple)
    assert "question" in matched_sources
    assert decision.trace["actor"] == "answer_orchestrator"


def test_question_text_routes_divorce_even_when_classification_is_low(
    engine: RiskPolicyEngine,
) -> None:
    """High-risk personal ruling phrases route before model judgement."""
    classification = ClassificationResult(
        language=Language.THAI,
        intent=Intent.GENERAL,
        madhhab=Madhhab.UNSPECIFIED,
        risk_level=RiskLevel.LOW,
        requires_current_info=False,
        requires_thai_specific=False,
        method="llm",
        confidence=0.92,
        trace={"llm_suggested_risk": "low"},
    )

    decision = engine.evaluate(classification, question_text="ผมหย่าภรรยาแบบนี้ถือว่าขาดไหม")

    assert decision.action == PolicyAction.ESCALATE_TO_SCHOLAR
    assert decision.risk_level == RiskLevel.HIGH
    assert decision.restriction_reason == RestrictionReason.PERSONAL_RULING_COMPLEX
    assert decision.trace["rule_id"] == "high-risk-divorce-v1"


def test_restricted_health_danger_blocks_unsafe_medical_instruction(
    engine: RiskPolicyEngine,
) -> None:
    """Dangerous health instructions are restricted, not merely disclaimed."""
    classification = ClassificationResult(
        language=Language.THAI,
        intent=Intent.PERSONAL_ADVICE,
        madhhab=Madhhab.UNSPECIFIED,
        risk_level=RiskLevel.LOW,
        requires_current_info=False,
        requires_thai_specific=False,
        method="hybrid",
        confidence=0.8,
    )

    decision = engine.evaluate(classification, question_text="ถ้าหยุดยาแล้วใช้ดุอาแทนได้ไหม")

    assert decision.action == PolicyAction.RESTRICT
    assert decision.risk_level == RiskLevel.HIGH
    assert decision.restriction_reason == RestrictionReason.HEALTH_DANGER
    assert decision.escalation_target == EscalationTarget.MEDICAL_PROFESSIONAL
    assert decision.trace["detected_medical"] is True


def test_draft_policy_version_cannot_be_activated_without_approval() -> None:
    """Policy changes require approval before activation."""
    with pytest.raises(ProviderSDKError) as exc_info:
        RiskPolicyEngine(policy_version="risk-policy-v2-draft", policy_status=PolicyStatus.DRAFT)

    error = exc_info.value
    assert error.code == "PROVIDER_CONFIG_INVALID"
    assert "approval" in str(error).lower()


def test_empty_question_text_is_stable_invalid_input(engine: RiskPolicyEngine) -> None:
    """Invalid input receives a stable provider error."""
    classification = ClassificationResult(
        language=Language.ENGLISH,
        intent=Intent.GENERAL,
        madhhab=Madhhab.UNSPECIFIED,
        risk_level=RiskLevel.LOW,
        requires_current_info=False,
        requires_thai_specific=False,
    )

    with pytest.raises(ProviderSDKError) as exc_info:
        engine.evaluate(classification, question_text=" ")

    assert exc_info.value.code == "PROVIDER_INPUT_INVALID"


# ============================================================================
# Metadata and Auditability
# ============================================================================


def test_policy_version_recorded(engine: RiskPolicyEngine) -> None:
    """Every decision records policy version for auditability."""
    classification = ClassificationResult(
        language=Language.ENGLISH,
        intent=Intent.QURAN,
        madhhab=Madhhab.UNSPECIFIED,
        risk_level=RiskLevel.LOW,
        requires_current_info=False,
        requires_thai_specific=False,
    )

    decision = engine.evaluate(classification)

    assert decision.policy_version == RISK_POLICY_VERSION
    assert decision.decided_at is not None


def test_trace_includes_classification_metadata(engine: RiskPolicyEngine) -> None:
    """Decision trace includes classification metadata."""
    classification = ClassificationResult(
        language=Language.THAI,
        intent=Intent.FIQH,
        madhhab=Madhhab.SHAFII,
        risk_level=RiskLevel.MEDIUM,
        requires_current_info=False,
        requires_thai_specific=False,
        method="hybrid",
        confidence=0.8,
    )

    decision = engine.evaluate(classification)

    assert decision.trace["classification_method"] == "hybrid"
    assert decision.trace["intent"] == Intent.FIQH.value
    assert decision.trace["madhhab"] == Madhhab.SHAFII.value


def test_custom_policy_version(engine: RiskPolicyEngine) -> None:
    """Engine can use custom policy version."""
    custom_engine = RiskPolicyEngine(policy_version="risk-policy-v2-beta")

    classification = ClassificationResult(
        language=Language.ENGLISH,
        intent=Intent.GENERAL,
        madhhab=Madhhab.UNSPECIFIED,
        risk_level=RiskLevel.LOW,
        requires_current_info=False,
        requires_thai_specific=False,
    )

    decision = custom_engine.evaluate(classification)

    assert decision.policy_version == "risk-policy-v2-beta"


# ============================================================================
# Adversarial and Edge Cases
# ============================================================================


def test_adversarial_mixed_takfir_and_fiqh(engine: RiskPolicyEngine) -> None:
    """Takfir mixed with legitimate fiqh still triggers restriction."""
    classification = ClassificationResult(
        language=Language.THAI,
        intent=Intent.HIGH_RISK_RULING,
        madhhab=Madhhab.UNSPECIFIED,
        risk_level=RiskLevel.HIGH,
        requires_current_info=False,
        requires_thai_specific=False,
        method="rule",
        confidence=1.0,
        trace={"intent_detected": "fiqh question with takfir declaration kafir"},
    )

    decision = engine.evaluate(classification)

    # Takfir detection takes priority
    assert decision.action == PolicyAction.RESTRICT
    assert decision.restriction_reason == RestrictionReason.TAKFIR


def test_adversarial_indirect_medical_advice(engine: RiskPolicyEngine) -> None:
    """Indirect medical questions still trigger disclaimer."""
    classification = ClassificationResult(
        language=Language.ENGLISH,
        intent=Intent.FIQH,
        madhhab=Madhhab.UNSPECIFIED,
        risk_level=RiskLevel.HIGH,
        requires_current_info=False,
        requires_thai_specific=False,
        method="rule",
        confidence=0.9,
        trace={"risk_detected": "asking about halal surgery options"},
    )

    decision = engine.evaluate(classification)

    assert decision.action == PolicyAction.REQUIRE_DISCLAIMER
    assert decision.restriction_reason == RestrictionReason.HEALTH_DANGER


def test_all_policy_actions_covered() -> None:
    """Verify all policy actions are reachable."""
    engine = RiskPolicyEngine()

    # RESTRICT
    restricted = engine.evaluate(
        ClassificationResult(
            language=Language.THAI,
            intent=Intent.GENERAL,
            madhhab=Madhhab.UNSPECIFIED,
            risk_level=RiskLevel.RESTRICTED,
            requires_current_info=False,
            requires_thai_specific=False,
            trace={"intent_detected": "illegal"},
        )
    )
    assert restricted.action == PolicyAction.RESTRICT

    # ESCALATE_TO_SCHOLAR
    escalate = engine.evaluate(
        ClassificationResult(
            language=Language.THAI,
            intent=Intent.HIGH_RISK_RULING,
            madhhab=Madhhab.UNSPECIFIED,
            risk_level=RiskLevel.HIGH,
            requires_current_info=False,
            requires_thai_specific=False,
            trace={"intent_detected": "divorce"},
        )
    )
    assert escalate.action == PolicyAction.ESCALATE_TO_SCHOLAR

    # REQUIRE_DISCLAIMER
    disclaimer = engine.evaluate(
        ClassificationResult(
            language=Language.ENGLISH,
            intent=Intent.PERSONAL_ADVICE,
            madhhab=Madhhab.UNSPECIFIED,
            risk_level=RiskLevel.HIGH,
            requires_current_info=False,
            requires_thai_specific=False,
            trace={"risk_detected": "medical"},
        )
    )
    assert disclaimer.action == PolicyAction.REQUIRE_DISCLAIMER

    # ALLOW_WITH_WARNING
    warning = engine.evaluate(
        ClassificationResult(
            language=Language.THAI,
            intent=Intent.FIQH,
            madhhab=Madhhab.SHAFII,
            risk_level=RiskLevel.MEDIUM,
            requires_current_info=False,
            requires_thai_specific=False,
        )
    )
    assert warning.action == PolicyAction.ALLOW_WITH_WARNING

    # ALLOW
    allow = engine.evaluate(
        ClassificationResult(
            language=Language.ENGLISH,
            intent=Intent.QURAN,
            madhhab=Madhhab.UNSPECIFIED,
            risk_level=RiskLevel.LOW,
            requires_current_info=False,
            requires_thai_specific=False,
        )
    )
    assert allow.action == PolicyAction.ALLOW
