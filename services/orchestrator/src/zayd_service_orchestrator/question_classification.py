"""Question classification with rule-based detection and LLM fallback."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from .provider_sdk import LLMMessage, LLMProvider, LLMRequest, ProviderSDKError

CLASSIFICATION_SCHEMA_VERSION = "classification-v1"


class Language(StrEnum):
    """Detected language."""

    THAI = "th"
    ARABIC = "ar"
    ENGLISH = "en"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class Intent(StrEnum):
    """Question intent categories."""

    QURAN = "quran"
    HADITH = "hadith"
    FIQH = "fiqh"
    AQIDAH = "aqidah"
    HISTORY = "history"
    HALAL = "halal"
    PERSONAL_ADVICE = "personal_advice"
    HIGH_RISK_RULING = "high_risk_ruling"
    GENERAL = "general"


class Madhhab(StrEnum):
    """Islamic schools of jurisprudence."""

    SHAFII = "shafii"
    HANAFI = "hanafi"
    MALIKI = "maliki"
    HANBALI = "hanbali"
    UNSPECIFIED = "unspecified"


class RiskLevel(StrEnum):
    """Risk level for question classification."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    RESTRICTED = "restricted"


@dataclass(frozen=True)
class ClassificationResult:
    """Structured classification output."""

    language: Language
    intent: Intent
    madhhab: Madhhab
    risk_level: RiskLevel
    requires_current_info: bool
    requires_thai_specific: bool
    schema_version: str = CLASSIFICATION_SCHEMA_VERSION
    classified_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    method: Literal["rule", "llm", "hybrid"] = "rule"
    confidence: float = 1.0
    trace: dict[str, object] = field(default_factory=dict)


class QuestionClassifier:
    """Classify questions using rules first, LLM fallback when needed."""

    def __init__(self, llm_provider: LLMProvider | None = None) -> None:
        """Initialize classifier with optional LLM provider for fallback."""
        self.llm_provider = llm_provider

    async def classify(self, question: str) -> ClassificationResult:
        """Classify a question using rules first, then LLM fallback if needed."""
        if not question or not question.strip():
            raise ProviderSDKError(
                "PROVIDER_INPUT_INVALID",
                "Question text is required",
                status_code=400,
            )

        question = question.strip()

        # Stage 1: Deterministic rule-based classification
        rule_result = self._classify_with_rules(question)

        # If rules give high confidence, return immediately
        if rule_result.confidence >= 0.9:
            return rule_result

        # Stage 2: LLM fallback for ambiguous cases
        if self.llm_provider:
            try:
                llm_result = await self._classify_with_llm(question, rule_result)
                return llm_result
            except Exception:
                # LLM failed, return rule-based result
                return rule_result

        # No LLM available, return rule result
        return rule_result

    def _classify_with_rules(self, question: str) -> ClassificationResult:
        """Apply deterministic rules for classification."""
        q_lower = question.lower()

        # Detect language
        language = self._detect_language(question)

        # Detect intent using keyword patterns
        intent = self._detect_intent(q_lower)

        # Detect madhhab mention
        madhhab = self._detect_madhhab(q_lower)

        # Detect risk level (deterministic rules for critical cases)
        risk_level = self._detect_risk_level(q_lower, intent)

        # Detect current info requirement
        requires_current_info = self._requires_current_info(q_lower)

        # Detect Thailand-specific requirement
        requires_thai_specific = self._requires_thai_specific(q_lower)

        # Confidence based on rule matches
        confidence = self._calculate_rule_confidence(
            language, intent, madhhab, risk_level
        )

        return ClassificationResult(
            language=language,
            intent=intent,
            madhhab=madhhab,
            risk_level=risk_level,
            requires_current_info=requires_current_info,
            requires_thai_specific=requires_thai_specific,
            method="rule",
            confidence=confidence,
            trace={
                "language_detected": language.value,
                "intent_detected": intent.value,
                "madhhab_detected": madhhab.value,
                "risk_detected": risk_level.value,
            },
        )

    def _detect_language(self, text: str) -> Language:
        """Detect language using character ranges."""
        # Thai Unicode range: ฀-๿
        thai_chars = len(re.findall(r"[฀-๿]", text))

        # Arabic Unicode range: ؀-ۿ
        arabic_chars = len(re.findall(r"[؀-ۿ]", text))

        # English (basic Latin): a-z, A-Z
        english_chars = len(re.findall(r"[a-zA-Z]", text))

        total_chars = len(text)
        if total_chars == 0:
            return Language.UNKNOWN

        thai_ratio = thai_chars / total_chars
        arabic_ratio = arabic_chars / total_chars
        english_ratio = english_chars / total_chars

        # Mixed if multiple scripts are significant (lowered threshold)
        significant_scripts = sum(
            [thai_ratio > 0.1, arabic_ratio > 0.1, english_ratio > 0.1]
        )
        if significant_scripts > 1:
            return Language.MIXED

        # Primary language
        if thai_ratio > 0.3:
            return Language.THAI
        if arabic_ratio > 0.3:
            return Language.ARABIC
        if english_ratio > 0.3:
            return Language.ENGLISH

        return Language.UNKNOWN

    def _detect_intent(self, q_lower: str) -> Intent:
        """Detect intent using keyword patterns."""
        # High-risk ruling keywords (most specific first)
        high_risk_patterns = [
            r"طلاق",  # divorce (Arabic)
            r"(ทำ)?แท้ง",  # abortion
            r"หย่า",  # divorce
            r"มรดก",  # inheritance
            r"ผิดกฎหมาย",  # illegal
            r"ฆ่าตัวตาย",  # suicide
            r"รับบุตร",  # adoption
        ]

        for pattern in high_risk_patterns:
            if re.search(pattern, q_lower):
                return Intent.HIGH_RISK_RULING

        # Quran keywords (check before personal advice)
        if re.search(
            r"(quran|al-quran|กุรอาน|อัลกุรอาน|ซูเราะ|อายะ|سورة|آية)", q_lower
        ):
            return Intent.QURAN

        # Hadith keywords (check before personal advice)
        # Use word boundaries for English, but not for Thai/Arabic
        hadith_pattern = (
            r"(\bhadith\b|\bbukhari\b|\btirmidhi\b|"
            r"\babu dawud\b|\bibn majah\b|\bahmad\b|บุคอรี|حديث)"
        )
        if re.search(hadith_pattern, q_lower):
            return Intent.HADITH

        # Fiqh keywords (check before personal advice)
        if re.search(
            r"(ฟิกฮ์|ฟิกฮฺ|นมาซ|ศอลาต|โซกาต|ศอกาต|วุฎูอ์|รอมฎอน|หัจญ์|\bfiqh\b|\bsalah\b|\bzakat\b|\bwudu\b|\bhajj\b|صلاة|زكاة|حج)",
            q_lower,
        ):
            return Intent.FIQH

        # Aqidah keywords
        if re.search(
            r"(อะกีดะฮ์|อักกีดะห์|ตะวัคกุล|กะฎอ|กะดัร|อีมาน|\baqidah\b|\btawhid\b|\biman\b|عقيدة|توحيد|إيمان)",
            q_lower,
        ):
            return Intent.AQIDAH

        # Halal keywords
        if re.search(
            r"(\bhalal\b|\bharam\b|ฮาลาล|ฮารอม|อาหาร|เนื้อ|เครื่องดื่ม|حلال|حرام)",
            q_lower,
        ):
            return Intent.HALAL

        # History keywords
        if re.search(
            r"(\bprophet\b|ประวัติ|ท่านนบี|ศอฮาบะฮ์|สมัย|ยุค|\bsahaba\b|\bcompanion\b|النبي|الصحابة)",
            q_lower,
        ):
            return Intent.HISTORY

        # Personal advice indicators (check last, as it's more generic)
        if re.search(r"(ควร|ต้อง|จะ|ผม|ดิฉัน|ฉัน|ช่วย|\bi should\b|\bshould i\b)", q_lower):
            return Intent.PERSONAL_ADVICE

        return Intent.GENERAL

    def _detect_madhhab(self, q_lower: str) -> Madhhab:
        """Detect madhhab from explicit mentions."""
        if re.search(r"(\bshafii\b|\bshafi'i\b|ชาฟิอี|الشافعي)", q_lower):
            return Madhhab.SHAFII
        if re.search(r"(\bhanafi\b|ฮานาฟี|الحنفي)", q_lower):
            return Madhhab.HANAFI
        if re.search(r"(\bmaliki\b|มาลิกี|المالكي)", q_lower):
            return Madhhab.MALIKI
        if re.search(r"(\bhanbali\b|ฮันบะลี|الحنبلي)", q_lower):
            return Madhhab.HANBALI

        return Madhhab.UNSPECIFIED

    def _detect_risk_level(self, q_lower: str, intent: Intent) -> RiskLevel:
        """Detect risk level using deterministic rules."""
        # RESTRICTED: Questions about illegal activities
        if re.search(
            r"(ผิดกฎหมาย|ฆ่า|ระเบิด|เทอร์เรอร์|\billegal\b|\bkill\b|\bbomb\b|\bterror\b)", q_lower
        ):
            return RiskLevel.RESTRICTED

        # HIGH: High-risk rulings and critical decisions
        if intent == Intent.HIGH_RISK_RULING:
            return RiskLevel.HIGH

        # HIGH: Medical or financial fatwa
        if re.search(r"(รักษา|ผ่าตัด|โรค|ลงทุน|หุ้น|\bmedical\b|\bsurgery\b|\binvestment\b)", q_lower):
            return RiskLevel.HIGH

        # MEDIUM: Fiqh and personal advice
        if intent in [Intent.FIQH, Intent.PERSONAL_ADVICE]:
            return RiskLevel.MEDIUM

        # LOW: Informational queries
        return RiskLevel.LOW

    def _requires_current_info(self, q_lower: str) -> bool:
        """Check if question requires current information."""
        current_patterns = [
            r"(ตอนนี้|ปัจจุบัน|ปีนี้|\bnow\b|\bcurrent\b|\btoday\b|\blatest\b|\brecent\b)",
            r"\b(2026|2025|2024)\b",
            r"(covid|โควิด|\bpandemic\b|วัคซีน|\bvaccine\b)",
        ]

        return any(re.search(pattern, q_lower) for pattern in current_patterns)

    def _requires_thai_specific(self, q_lower: str) -> bool:
        """Check if question requires Thailand-specific information."""
        thai_patterns = [
            r"(ไทย|\bthailand\b|กทม|\bbangkok\b|กระทรวง|\bministry\b)",
            r"(กฎหมายไทย|\bthai law\b)",
            r"(halal thai|ฮาลาลไทย)",
        ]

        return any(re.search(pattern, q_lower) for pattern in thai_patterns)

    def _calculate_rule_confidence(
        self,
        language: Language,
        intent: Intent,
        madhhab: Madhhab,
        risk_level: RiskLevel,
    ) -> float:
        """Calculate confidence score for rule-based classification."""
        confidence = 0.5  # Base confidence

        # Language detection is generally reliable
        if language != Language.UNKNOWN:
            confidence += 0.2

        # Intent detection confidence
        if intent != Intent.GENERAL:
            confidence += 0.2

        # Risk level detection is critical and reliable
        if risk_level in [RiskLevel.HIGH, RiskLevel.RESTRICTED]:
            confidence = 1.0  # Full confidence for safety-critical rules

        return min(confidence, 1.0)

    async def _classify_with_llm(
        self, question: str, rule_result: ClassificationResult
    ) -> ClassificationResult:
        """Use LLM to refine ambiguous classifications."""
        if not self.llm_provider:
            return rule_result

        prompt = f"""Classify this Islamic knowledge question:

Question: {question}

Rule-based classification:
- Language: {rule_result.language.value}
- Intent: {rule_result.intent.value}
- Madhhab: {rule_result.madhhab.value}
- Risk: {rule_result.risk_level.value}

Refine the classification if the rules are incorrect. Output JSON:
{{
  "language": "th|ar|en|mixed|unknown",
  "intent": "quran|hadith|fiqh|aqidah|history|halal|personal_advice|high_risk_ruling|general",
  "madhhab": "shafii|hanafi|maliki|hanbali|unspecified",
  "risk_level": "low|medium|high|restricted",
  "confidence": 0.0-1.0
}}"""

        request = LLMRequest(
            messages=(
                LLMMessage(role="system", content="You are an Islamic knowledge classifier."),
                LLMMessage(role="user", content=prompt),
            ),
            temperature=0.0,
            max_output_tokens=200,
        )

        try:
            response = await self.llm_provider.generate(request)

            # Parse LLM response (simplified - production would use structured output)
            llm_trace = {
                "llm_text": response.text,
                "llm_provider": response.provider.name,
            }

            # For now, use rule result with LLM trace
            # Full implementation would parse JSON and merge results
            return ClassificationResult(
                language=rule_result.language,
                intent=rule_result.intent,
                madhhab=rule_result.madhhab,
                risk_level=rule_result.risk_level,
                requires_current_info=rule_result.requires_current_info,
                requires_thai_specific=rule_result.requires_thai_specific,
                method="hybrid",
                confidence=0.8,
                trace={**rule_result.trace, **llm_trace},
            )

        except Exception as e:
            # LLM failed, return rule result
            return ClassificationResult(
                language=rule_result.language,
                intent=rule_result.intent,
                madhhab=rule_result.madhhab,
                risk_level=rule_result.risk_level,
                requires_current_info=rule_result.requires_current_info,
                requires_thai_specific=rule_result.requires_thai_specific,
                method="rule",
                confidence=rule_result.confidence,
                trace={**rule_result.trace, "llm_error": str(e)},
            )
