"""Tests for question classification."""

from __future__ import annotations

import pytest
from zayd_service_orchestrator.provider_sdk import (
    LLMMessage,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    LLMUsage,
    ProviderIdentity,
    ProviderSDKError,
)
from zayd_service_orchestrator.question_classification import (
    Intent,
    Language,
    Madhhab,
    QuestionClassifier,
    RiskLevel,
)


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing."""

    def identity(self) -> ProviderIdentity:
        return ProviderIdentity(
            name="mock",
            kind="llm",
            version="1.0",
            model_id="mock-model",
        )

    async def generate(self, request: LLMRequest) -> LLMResponse:
        # Return mock classification
        return LLMResponse(
            text='{"language": "th", "intent": "fiqh", "madhhab": "shafii", "risk_level": "medium", "confidence": 0.85}',
            provider=self.identity(),
            usage=LLMUsage(input_tokens=10, output_tokens=20),
            finish_reason="stop",
        )


@pytest.mark.asyncio
async def test_classify_empty_question() -> None:
    """Test that empty questions raise validation error."""
    classifier = QuestionClassifier()

    with pytest.raises(ProviderSDKError) as exc_info:
        await classifier.classify("")

    assert exc_info.value.code == "PROVIDER_INPUT_INVALID"


@pytest.mark.asyncio
async def test_classify_thai_quran_question() -> None:
    """Test classification of Thai Quran question."""
    classifier = QuestionClassifier()

    result = await classifier.classify("ซูเราะฮ์อัลบะเกาะเราะฮ์พูดถึงอะไร")

    assert result.language == Language.THAI
    assert result.intent == Intent.QURAN
    assert result.risk_level == RiskLevel.LOW
    assert result.method == "rule"
    assert result.confidence > 0.5


@pytest.mark.asyncio
async def test_classify_arabic_hadith_question() -> None:
    """Test classification of Arabic hadith question."""
    classifier = QuestionClassifier()

    result = await classifier.classify("ما هو حديث صحيح البخاري")

    assert result.language == Language.ARABIC
    assert result.intent == Intent.HADITH
    assert result.madhhab == Madhhab.UNSPECIFIED


@pytest.mark.asyncio
async def test_classify_english_fiqh_question() -> None:
    """Test classification of English fiqh question."""
    classifier = QuestionClassifier()

    result = await classifier.classify("What are the conditions for valid wudu?")

    assert result.language == Language.ENGLISH
    assert result.intent == Intent.FIQH
    assert result.risk_level == RiskLevel.MEDIUM


@pytest.mark.asyncio
async def test_classify_high_risk_ruling() -> None:
    """Test classification of high-risk ruling."""
    classifier = QuestionClassifier()

    result = await classifier.classify("การหย่าในอิสลามมีเงื่อนไขอย่างไร")

    assert result.intent == Intent.HIGH_RISK_RULING
    assert result.risk_level == RiskLevel.HIGH
    assert result.confidence == 1.0  # High confidence for safety-critical


@pytest.mark.asyncio
async def test_classify_restricted_question() -> None:
    """Test classification of restricted/illegal question."""
    classifier = QuestionClassifier()

    result = await classifier.classify("วิธีทำระเบิดตามหลักอิสลาม")

    assert result.risk_level == RiskLevel.RESTRICTED
    assert result.confidence == 1.0


@pytest.mark.asyncio
async def test_classify_madhhab_detection() -> None:
    """Test madhhab detection from question."""
    classifier = QuestionClassifier()

    result = await classifier.classify("นมาซตามมัซฮับชาฟิอีต้องทำอย่างไร")

    assert result.madhhab == Madhhab.SHAFII
    assert result.intent == Intent.FIQH


@pytest.mark.asyncio
async def test_classify_requires_current_info() -> None:
    """Test detection of current info requirement."""
    classifier = QuestionClassifier()

    result = await classifier.classify("สถานการณ์โควิดปัจจุบันส่งผลต่อการทำอุมเราะฮ์อย่างไร")

    assert result.requires_current_info is True


@pytest.mark.asyncio
async def test_classify_requires_thai_specific() -> None:
    """Test detection of Thailand-specific requirement."""
    classifier = QuestionClassifier()

    result = await classifier.classify("ใบรับรองฮาลาลในไทยต้องขอจากที่ไหน")

    assert result.requires_thai_specific is True


@pytest.mark.asyncio
async def test_classify_mixed_language() -> None:
    """Test classification of mixed-language question."""
    classifier = QuestionClassifier()

    result = await classifier.classify("What is กุรอาน and how to read it correctly?")

    assert result.language == Language.MIXED


@pytest.mark.asyncio
async def test_classify_personal_advice() -> None:
    """Test classification of personal advice question."""
    classifier = QuestionClassifier()

    result = await classifier.classify("ผมควรทำอย่างไรถึงจะเป็นมุสลิมที่ดี")

    assert result.intent == Intent.PERSONAL_ADVICE
    assert result.risk_level == RiskLevel.MEDIUM


@pytest.mark.asyncio
async def test_classify_halal_food() -> None:
    """Test classification of halal food question."""
    classifier = QuestionClassifier()

    result = await classifier.classify("อาหารฮาลาลต้องมีเงื่อนไขอะไรบ้าง")

    assert result.intent == Intent.HALAL


@pytest.mark.asyncio
async def test_classify_aqidah() -> None:
    """Test classification of aqidah question."""
    classifier = QuestionClassifier()

    result = await classifier.classify("อะกีดะฮ์ในอิสลามคืออะไร")

    assert result.intent == Intent.AQIDAH


@pytest.mark.asyncio
async def test_classify_history() -> None:
    """Test classification of history question."""
    classifier = QuestionClassifier()

    result = await classifier.classify("ประวัติของท่านนบีมุฮัมมัด")

    assert result.intent == Intent.HISTORY
    assert result.risk_level == RiskLevel.LOW


@pytest.mark.asyncio
async def test_classify_with_llm_fallback() -> None:
    """Test classification with LLM fallback for ambiguous cases."""
    mock_llm = MockLLMProvider()
    classifier = QuestionClassifier(llm_provider=mock_llm)

    # Ambiguous question that rules can't classify with high confidence
    result = await classifier.classify("ช่วยอธิบายหน่อย")

    # Should attempt LLM fallback for low-confidence rule result
    assert result.method in ["rule", "hybrid"]


@pytest.mark.asyncio
async def test_classify_schema_version() -> None:
    """Test that classification result includes schema version."""
    classifier = QuestionClassifier()

    result = await classifier.classify("ซูเราะฮ์อัลฟาติหะฮ์")

    assert result.schema_version == "classification-v1"
    assert result.classified_at is not None


@pytest.mark.asyncio
async def test_classify_trace_metadata() -> None:
    """Test that classification includes trace metadata."""
    classifier = QuestionClassifier()

    result = await classifier.classify("นมาซวิตรต้องละหมาดกี่เราะกาะฮ์")

    assert "language_detected" in result.trace
    assert "intent_detected" in result.trace
    assert "madhhab_detected" in result.trace
    assert "risk_detected" in result.trace


@pytest.mark.asyncio
async def test_classify_unknown_language() -> None:
    """Test classification of question with unknown language."""
    classifier = QuestionClassifier()

    result = await classifier.classify("12345 !@#$%")

    assert result.language == Language.UNKNOWN


@pytest.mark.asyncio
async def test_classify_general_intent() -> None:
    """Test classification of general question without specific keywords."""
    classifier = QuestionClassifier()

    result = await classifier.classify("Tell me about Islam")

    assert result.intent == Intent.GENERAL
    assert result.language == Language.ENGLISH


@pytest.mark.asyncio
async def test_classify_hanafi_madhhab() -> None:
    """Test detection of Hanafi madhhab."""
    classifier = QuestionClassifier()

    result = await classifier.classify("มัซฮับฮานาฟีมีความเห็นอย่างไรเรื่องนี้")

    assert result.madhhab == Madhhab.HANAFI


@pytest.mark.asyncio
async def test_classify_medical_high_risk() -> None:
    """Test that medical questions are classified as high risk."""
    classifier = QuestionClassifier()

    result = await classifier.classify("การผ่าตัดเปลี่ยนเพศตามหลักอิสลาม")

    assert result.risk_level == RiskLevel.HIGH


@pytest.mark.asyncio
async def test_classification_golden_set() -> None:
    """Test classification golden set with known correct answers."""
    classifier = QuestionClassifier()

    golden_cases = [
        ("ซูเราะฮ์อัลบะเกาะเราะฮ์พูดถึงอะไร", Language.THAI, Intent.QURAN, RiskLevel.LOW),
        ("การหย่าในอิสลาม", Language.THAI, Intent.HIGH_RISK_RULING, RiskLevel.HIGH),
        ("What is wudu?", Language.ENGLISH, Intent.FIQH, RiskLevel.MEDIUM),
        ("ما هو حديث", Language.ARABIC, Intent.HADITH, RiskLevel.LOW),
        ("อาหารฮาลาล", Language.THAI, Intent.HALAL, RiskLevel.LOW),
    ]

    for question, expected_lang, expected_intent, expected_risk in golden_cases:
        result = await classifier.classify(question)
        assert result.language == expected_lang, f"Language mismatch for: {question}"
        assert result.intent == expected_intent, f"Intent mismatch for: {question}"
        assert result.risk_level == expected_risk, f"Risk mismatch for: {question}"
