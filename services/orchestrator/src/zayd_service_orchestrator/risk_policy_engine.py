"""Risk policy engine with deterministic safety rules."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from .provider_sdk import ProviderSDKError
from .question_classification import ClassificationResult, RiskLevel

RISK_POLICY_VERSION = "risk-policy-v1"
RISK_POLICY_STATUS = "approved"
APPROVED_POLICY_STATUSES = frozenset({RISK_POLICY_STATUS})


class PolicyAction(StrEnum):
    """Policy action to take based on risk assessment."""

    ALLOW = "allow"
    ALLOW_WITH_WARNING = "allow_with_warning"
    REQUIRE_DISCLAIMER = "require_disclaimer"
    ESCALATE_TO_SCHOLAR = "escalate_to_scholar"
    RESTRICT = "restrict"


class PolicyStatus(StrEnum):
    """Governance status of the active policy table."""

    APPROVED = "approved"
    DRAFT = "draft"


class EscalationTarget(StrEnum):
    """Human or professional route required by policy."""

    NONE = "none"
    SCHOLAR = "scholar"
    MEDICAL_PROFESSIONAL = "medical_professional"
    LEGAL_OR_SAFETY_AUTHORITY = "legal_or_safety_authority"


class RestrictionReason(StrEnum):
    """Reason for restricting a question."""

    TAKFIR = "takfir"  # Declaring someone kafir/non-Muslim
    DIVORCE = "divorce"
    INHERITANCE = "inheritance"
    MARRIAGE_OR_FAMILY = "marriage_or_family"
    HEALTH_DANGER = "health_danger"  # Medical advice that could harm
    ILLEGAL_ACTIVITY = "illegal_activity"  # Promoting illegal acts
    PERSONAL_RULING_COMPLEX = "personal_ruling_complex"  # Complex personal fatwa
    FINANCIAL_OR_CONTRACT = "financial_or_contract"
    SELF_HARM = "self_harm"
    INSUFFICIENT_QUALIFICATION = "insufficient_qualification"  # Requires scholar
    VIOLENCE = "violence"  # Violence or terrorism
    NONE = "none"


@dataclass(frozen=True)
class RiskPolicyMatch:
    """Internal deterministic policy match.

    The match records only rule metadata. It never stores the full user question.
    """

    rule_id: str
    action: PolicyAction
    risk_level: RiskLevel
    restriction_reason: RestrictionReason
    escalation_target: EscalationTarget = EscalationTarget.NONE
    matched_sources: tuple[str, ...] = ()


@dataclass(frozen=True)
class PolicyDecision:
    """Risk policy decision with action and justification."""

    action: PolicyAction
    risk_level: RiskLevel
    restriction_reason: RestrictionReason
    policy_version: str = RISK_POLICY_VERSION
    policy_status: PolicyStatus = PolicyStatus.APPROVED
    decided_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    escalation_target: EscalationTarget = EscalationTarget.NONE
    warning_message: str | None = None
    disclaimer_message: str | None = None
    escalation_message: str | None = None
    user_facing_message: str | None = None
    trace: dict[str, object] = field(default_factory=dict)


class RiskPolicyEngine:
    """Enforce deterministic safety policies based on risk classification."""

    def __init__(
        self,
        policy_version: str = RISK_POLICY_VERSION,
        policy_status: PolicyStatus = PolicyStatus.APPROVED,
    ) -> None:
        """Initialize risk policy engine."""
        if not policy_version or not policy_version.strip():
            raise ProviderSDKError(
                "PROVIDER_CONFIG_INVALID",
                "Risk policy version is required",
                status_code=500,
            )
        if policy_status.value not in APPROVED_POLICY_STATUSES:
            raise ProviderSDKError(
                "PROVIDER_CONFIG_INVALID",
                "Risk policy changes require approval and regression tests before activation",
                status_code=500,
            )
        self.policy_version = policy_version
        self.policy_status = policy_status

    def evaluate(
        self,
        classification: ClassificationResult,
        *,
        question_text: str | None = None,
        actor: str = "system",
    ) -> PolicyDecision:
        """
        Evaluate classification result and return policy decision.

        This is a deterministic function: same classification always produces
        same decision. Model output cannot downgrade restrictions when rule
        patterns identify a stricter category.
        """
        if question_text is not None and not question_text.strip():
            raise ProviderSDKError(
                "PROVIDER_INPUT_INVALID",
                "Question text must not be empty when supplied",
                status_code=400,
            )

        match = self._deterministic_match(classification, question_text=question_text)
        if match is not None:
            return self._decision_from_match(classification, match, actor=actor)

        if classification.risk_level == RiskLevel.MEDIUM:
            return self._handle_medium_risk(classification, actor=actor)

        return self._handle_low_risk(classification, actor=actor)

    def _deterministic_match(
        self, classification: ClassificationResult, *, question_text: str | None
    ) -> RiskPolicyMatch | None:
        """Find the strongest deterministic rule match."""
        signals = self._policy_signals(classification, question_text=question_text)

        restricted_rules: tuple[tuple[str, RestrictionReason, tuple[str, ...]], ...] = (
            (
                "restricted-takfir-v1",
                RestrictionReason.TAKFIR,
                (
                    r"\btakfir\b",
                    r"\bkafir\b",
                    r"\bkufr\b",
                    r"\bapostate\b",
                    r"ตักฟีร",
                    r"กุฟร",
                    r"กาเฟร",
                    r"ออกจากศาสนา",
                    r"كافر",
                    r"تكفير",
                ),
            ),
            (
                "restricted-violence-v1",
                RestrictionReason.VIOLENCE,
                (
                    r"\bkill\b",
                    r"\bbomb\b",
                    r"\bterror\b",
                    r"\bweapon\b",
                    r"ฆ่า",
                    r"ระเบิด",
                    r"เทอร์เรอร์",
                    r"อาวุธ",
                ),
            ),
            (
                "restricted-self-harm-v1",
                RestrictionReason.SELF_HARM,
                (
                    r"\bsuicide\b",
                    r"\bself[- ]harm\b",
                    r"ฆ่าตัวตาย",
                    r"ทำร้ายตัวเอง",
                ),
            ),
            (
                "restricted-illegal-v1",
                RestrictionReason.ILLEGAL_ACTIVITY,
                (
                    r"\billegal\b",
                    r"\bevade\b",
                    r"\bfraud\b",
                    r"\bhack\b",
                    r"ผิดกฎหมาย",
                    r"หลบเลี่ยงกฎหมาย",
                    r"โกง",
                    r"แฮก",
                ),
            ),
            (
                "restricted-health-danger-v1",
                RestrictionReason.HEALTH_DANGER,
                (
                    r"\bstop (?:taking )?(?:medicine|medication|insulin)\b",
                    r"\bavoid (?:doctor|hospital)\b",
                    r"\bignore (?:doctor|medical)\b",
                    r"หยุดยา",
                    r"ไม่ต้องไปหาหมอ",
                    r"ไม่ต้องพบแพทย์",
                ),
            ),
        )

        for rule_id, reason, patterns in restricted_rules:
            matched = self._matched_sources(signals, patterns)
            if matched:
                target = (
                    EscalationTarget.MEDICAL_PROFESSIONAL
                    if reason in {RestrictionReason.HEALTH_DANGER, RestrictionReason.SELF_HARM}
                    else EscalationTarget.LEGAL_OR_SAFETY_AUTHORITY
                    if reason in {RestrictionReason.VIOLENCE, RestrictionReason.ILLEGAL_ACTIVITY}
                    else EscalationTarget.SCHOLAR
                )
                return RiskPolicyMatch(
                    rule_id=rule_id,
                    action=PolicyAction.RESTRICT,
                    risk_level=RiskLevel.RESTRICTED
                    if classification.risk_level == RiskLevel.RESTRICTED
                    else RiskLevel.HIGH,
                    restriction_reason=reason,
                    escalation_target=target,
                    matched_sources=matched,
                )

        high_risk_rules: tuple[tuple[str, RestrictionReason, tuple[str, ...]], ...] = (
            (
                "high-risk-divorce-v1",
                RestrictionReason.DIVORCE,
                (r"\bdivorce\b", r"\btalaq\b", r"หย่า", r"طلاق"),
            ),
            (
                "high-risk-inheritance-v1",
                RestrictionReason.INHERITANCE,
                (r"\binheritance\b", r"\bwill\b", r"\bestate\b", r"มรดก", r"وصية"),
            ),
            (
                "high-risk-family-v1",
                RestrictionReason.MARRIAGE_OR_FAMILY,
                (
                    r"\bmarriage\b",
                    r"\bnikah\b",
                    r"\bcustody\b",
                    r"\badoption\b",
                    r"แต่งงาน",
                    r"นิกะห์",
                    r"รับบุตร",
                    r"สิทธิเลี้ยงดู",
                ),
            ),
            (
                "high-risk-contract-v1",
                RestrictionReason.FINANCIAL_OR_CONTRACT,
                (
                    r"\bcontract\b",
                    r"\binvestment\b",
                    r"\bloan\b",
                    r"\bstock\b",
                    r"สัญญา",
                    r"ลงทุน",
                    r"หุ้น",
                    r"เงินกู้",
                ),
            ),
            (
                "high-risk-health-v1",
                RestrictionReason.HEALTH_DANGER,
                (
                    r"\bmedical\b",
                    r"\bsurgery\b",
                    r"\bdisease\b",
                    r"\bmedicine\b",
                    r"รักษา",
                    r"ผ่าตัด",
                    r"โรค",
                    r"ยา",
                ),
            ),
        )

        for rule_id, reason, patterns in high_risk_rules:
            matched = self._matched_sources(signals, patterns)
            if matched:
                if reason == RestrictionReason.HEALTH_DANGER:
                    return RiskPolicyMatch(
                        rule_id=rule_id,
                        action=PolicyAction.REQUIRE_DISCLAIMER,
                        risk_level=RiskLevel.HIGH,
                        restriction_reason=reason,
                        escalation_target=EscalationTarget.MEDICAL_PROFESSIONAL,
                        matched_sources=matched,
                    )
                if reason == RestrictionReason.FINANCIAL_OR_CONTRACT:
                    return RiskPolicyMatch(
                        rule_id=rule_id,
                        action=PolicyAction.REQUIRE_DISCLAIMER,
                        risk_level=RiskLevel.HIGH,
                        restriction_reason=RestrictionReason.INSUFFICIENT_QUALIFICATION,
                        escalation_target=EscalationTarget.SCHOLAR,
                        matched_sources=matched,
                    )
                return RiskPolicyMatch(
                    rule_id=rule_id,
                    action=PolicyAction.ESCALATE_TO_SCHOLAR,
                    risk_level=RiskLevel.HIGH,
                    restriction_reason=RestrictionReason.PERSONAL_RULING_COMPLEX,
                    escalation_target=EscalationTarget.SCHOLAR,
                    matched_sources=matched,
                )

        if classification.risk_level == RiskLevel.RESTRICTED:
            return RiskPolicyMatch(
                rule_id="classification-restricted-v1",
                action=PolicyAction.RESTRICT,
                risk_level=RiskLevel.RESTRICTED,
                restriction_reason=RestrictionReason.INSUFFICIENT_QUALIFICATION,
                escalation_target=EscalationTarget.SCHOLAR,
                matched_sources=("classification",),
            )

        if classification.risk_level == RiskLevel.HIGH:
            return RiskPolicyMatch(
                rule_id="classification-high-risk-v1",
                action=PolicyAction.REQUIRE_DISCLAIMER,
                risk_level=RiskLevel.HIGH,
                restriction_reason=RestrictionReason.INSUFFICIENT_QUALIFICATION,
                escalation_target=EscalationTarget.SCHOLAR,
                matched_sources=("classification",),
            )

        return None

    def _policy_signals(
        self, classification: ClassificationResult, *, question_text: str | None
    ) -> dict[str, str]:
        """Build sanitized signals for deterministic matching."""
        trace_signal_keys = (
            "intent_detected",
            "risk_detected",
            "matched_risk_terms",
            "matched_keywords",
        )
        signals = {
            "classification_intent": classification.intent.value,
            "classification_risk": classification.risk_level.value,
        }
        if question_text is not None:
            signals["question"] = question_text.strip().lower()
        for key in trace_signal_keys:
            value = classification.trace.get(key)
            if value is not None:
                signals[f"trace_{key}"] = str(value).lower()
        return signals

    def _matched_sources(
        self, signals: dict[str, str], patterns: tuple[str, ...]
    ) -> tuple[str, ...]:
        """Return signal names that matched at least one policy pattern."""
        matched = []
        for source, value in signals.items():
            if any(re.search(pattern, value, flags=re.IGNORECASE) for pattern in patterns):
                matched.append(source)
        return tuple(matched)

    def _decision_from_match(
        self,
        classification: ClassificationResult,
        match: RiskPolicyMatch,
        *,
        actor: str,
    ) -> PolicyDecision:
        """Convert a deterministic rule match to the public policy decision."""
        if match.action == PolicyAction.RESTRICT:
            return self._restricted_decision(classification, match, actor=actor)
        if match.action == PolicyAction.ESCALATE_TO_SCHOLAR:
            return self._scholar_escalation_decision(classification, match, actor=actor)
        if match.action == PolicyAction.REQUIRE_DISCLAIMER:
            return self._disclaimer_decision(classification, match, actor=actor)
        raise ProviderSDKError(
            "PROVIDER_RESPONSE_INVALID",
            f"Unsupported risk policy action: {match.action}",
            status_code=500,
        )

    def _restricted_decision(
        self,
        classification: ClassificationResult,
        match: RiskPolicyMatch,
        *,
        actor: str,
    ) -> PolicyDecision:
        """Handle restricted content that must not be answered automatically."""
        reason_messages = {
            RestrictionReason.TAKFIR: (
                "Zayd cannot make judgments about whether individuals are Muslim or "
                "non-Muslim. This serious matter must be referred to qualified scholars."
            ),
            RestrictionReason.HEALTH_DANGER: (
                "Zayd cannot provide guidance that may create health or safety harm. "
                "Please consult a qualified medical professional for health decisions."
            ),
            RestrictionReason.SELF_HARM: (
                "Zayd cannot provide instructions related to self-harm. Please contact "
                "local emergency or crisis support services if there is immediate danger."
            ),
            RestrictionReason.VIOLENCE: (
                "Zayd cannot provide guidance related to violence, weapons, or terrorism."
            ),
            RestrictionReason.ILLEGAL_ACTIVITY: (
                "Zayd cannot provide guidance for illegal activity or evading law and safety rules."
            ),
        }
        message = reason_messages.get(
            match.restriction_reason,
            "Zayd cannot provide automated guidance for this restricted topic.",
        )
        return PolicyDecision(
            action=PolicyAction.RESTRICT,
            risk_level=match.risk_level,
            restriction_reason=match.restriction_reason,
            policy_version=self.policy_version,
            policy_status=self.policy_status,
            escalation_target=match.escalation_target,
            user_facing_message=message,
            escalation_message=self._escalation_message(match),
            trace=self._trace(classification, match, actor=actor),
        )

    def _scholar_escalation_decision(
        self,
        classification: ClassificationResult,
        match: RiskPolicyMatch,
        *,
        actor: str,
    ) -> PolicyDecision:
        """Handle high-risk religious rulings that require a qualified scholar."""
        category = match.restriction_reason.value.replace("_", " ")
        if match.rule_id.startswith("high-risk-divorce"):
            category = "divorce"
        elif match.rule_id.startswith("high-risk-inheritance"):
            category = "inheritance"
        elif match.rule_id.startswith("high-risk-family"):
            category = "marriage or family rulings"
        return PolicyDecision(
            action=PolicyAction.ESCALATE_TO_SCHOLAR,
            risk_level=RiskLevel.HIGH,
            restriction_reason=match.restriction_reason,
            policy_version=self.policy_version,
            policy_status=self.policy_status,
            escalation_target=EscalationTarget.SCHOLAR,
            warning_message=(
                "This question involves a serious ruling where personal circumstances "
                "matter and requires consultation with a qualified scholar. Zayd can "
                "provide only general information and cannot issue a fatwa."
            ),
            escalation_message=self._escalation_message(match),
            user_facing_message=(
                "This topic requires consultation with a qualified scholar who can review "
                "the specific facts, madhhab context, and evidence. Zayd may provide general "
                f"background about {category}, but it must not decide your individual case."
            ),
            trace=self._trace(classification, match, actor=actor),
        )

    def _disclaimer_decision(
        self,
        classification: ClassificationResult,
        match: RiskPolicyMatch,
        *,
        actor: str,
    ) -> PolicyDecision:
        """Handle high-risk categories that require strong disclaimers."""
        if match.restriction_reason == RestrictionReason.HEALTH_DANGER:
            disclaimer = (
                "Medical disclaimer: Zayd provides Islamic knowledge context only. "
                "Consult qualified medical professionals for diagnosis, treatment, "
                "or safety decisions."
            )
        elif match.rule_id == "high-risk-contract-v1":
            disclaimer = (
                "Financial and contract disclaimer: Zayd provides general Islamic principles only. "
                "Consult qualified scholars and regulated professionals for specific decisions."
            )
        else:
            disclaimer = (
                "This topic may require a qualified scholar or professional. "
                "Zayd provides general information only."
            )
        return PolicyDecision(
            action=PolicyAction.REQUIRE_DISCLAIMER,
            risk_level=RiskLevel.HIGH,
            restriction_reason=match.restriction_reason,
            policy_version=self.policy_version,
            policy_status=self.policy_status,
            escalation_target=match.escalation_target,
            disclaimer_message=disclaimer,
            trace=self._trace(classification, match, actor=actor),
        )

    def _handle_medium_risk(
        self, classification: ClassificationResult, *, actor: str
    ) -> PolicyDecision:
        """Handle medium-risk content - allow with warnings."""
        from .question_classification import Intent

        intent = classification.intent

        # Fiqh questions: practical Islamic law
        if intent == Intent.FIQH:
            warning = (
                "Fiqh rulings may vary by madhhab and individual circumstances. "
                f"Answer based on {classification.madhhab.value} perspective when specified."
            )

        # Personal advice questions
        elif intent == Intent.PERSONAL_ADVICE:
            warning = (
                "This is general guidance based on Islamic principles. "
                "For personal matters, consider your specific circumstances and "
                "consult with someone knowledgeable about your situation."
            )

        else:
            warning = "Information provided is general guidance. Individual circumstances may vary."

        return PolicyDecision(
            action=PolicyAction.ALLOW_WITH_WARNING,
            risk_level=RiskLevel.MEDIUM,
            restriction_reason=RestrictionReason.NONE,
            policy_version=self.policy_version,
            policy_status=self.policy_status,
            warning_message=warning,
            trace=self._trace(classification, None, actor=actor),
        )

    def _handle_low_risk(
        self, classification: ClassificationResult, *, actor: str
    ) -> PolicyDecision:
        """Handle low-risk content - allow without warnings."""
        return PolicyDecision(
            action=PolicyAction.ALLOW,
            risk_level=RiskLevel.LOW,
            restriction_reason=RestrictionReason.NONE,
            policy_version=self.policy_version,
            policy_status=self.policy_status,
            trace=self._trace(classification, None, actor=actor),
        )

    def _trace(
        self,
        classification: ClassificationResult,
        match: RiskPolicyMatch | None,
        *,
        actor: str,
    ) -> dict[str, object]:
        """Build safe audit trace without storing the raw question or model text."""
        trace: dict[str, object] = {
            "actor": actor,
            "classification_schema_version": classification.schema_version,
            "classification_method": classification.method,
            "classification_confidence": classification.confidence,
            "classification_risk": classification.risk_level.value,
            "intent": classification.intent.value,
            "madhhab": classification.madhhab.value,
            "policy_version": self.policy_version,
            "policy_status": self.policy_status.value,
        }
        llm_suggested_risk = classification.trace.get("llm_suggested_risk")
        if llm_suggested_risk is not None:
            trace["llm_suggested_risk"] = str(llm_suggested_risk)
            trace["deterministic_policy_authoritative"] = True
        if match is not None:
            trace.update(
                {
                    "rule_id": match.rule_id,
                    "matched_sources": match.matched_sources,
                    "escalation_target": match.escalation_target.value,
                }
            )
            if match.restriction_reason == RestrictionReason.TAKFIR:
                trace["detected_takfir"] = True
            if match.restriction_reason == RestrictionReason.HEALTH_DANGER:
                trace["detected_medical"] = True
            if match.rule_id == "high-risk-contract-v1":
                trace["detected_financial"] = True
        return trace

    def _escalation_message(self, match: RiskPolicyMatch) -> str:
        """Return a sanitized internal routing note."""
        target = match.escalation_target.value.replace("_", " ")
        return (
            f"Risk policy rule {match.rule_id} selected action {match.action.value}; "
            f"route to {target} when that channel is enabled."
        )
