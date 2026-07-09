# Question Classification Architecture

Question classification is the first stage of the Zayd orchestration pipeline. It analyzes incoming questions to determine language, intent, madhhab, risk level, and special requirements before retrieval begins.

## Design Principles

1. **Rules First, LLM Fallback**: Deterministic rules handle safety-critical decisions (risk level, restricted content). LLM is used only for ambiguous cases.

2. **Versioned Schema**: Classification results include a schema version for auditability and migration.

3. **Traceable Decisions**: Every classification records whether it used rules, LLM, or hybrid method with confidence scores.

4. **Fail-Safe**: When LLM is unavailable or fails, rules-based classification continues operation.

## Classification Schema v1

```python
@dataclass(frozen=True)
class ClassificationResult:
    language: Language              # th, ar, en, mixed, unknown
    intent: Intent                  # quran, hadith, fiqh, aqidah, history, halal, personal_advice, high_risk_ruling, general
    madhhab: Madhhab               # shafii, hanafi, maliki, hanbali, unspecified
    risk_level: RiskLevel          # low, medium, high, restricted
    requires_current_info: bool    # Does question need current/recent information?
    requires_thai_specific: bool   # Does question need Thailand-specific rules/law?
    schema_version: str            # "classification-v1"
    classified_at: datetime        # Timestamp
    method: Literal["rule", "llm", "hybrid"]
    confidence: float              # 0.0-1.0
    trace: dict[str, object]       # Trace metadata
```

## Language Detection

Uses Unicode character ranges to detect:

- **Thai**: `฀-๿` (U+0E00 to U+0E7F)
- **Arabic**: `؀-ۿ` (U+0600 to U+06FF)
- **English**: `a-z, A-Z` (Basic Latin)

**Mixed language** is detected when multiple scripts exceed 10% of total characters.

## Intent Classification

Intent categories are checked in priority order:

### 1. High-Risk Ruling (Tier S)

Deterministic patterns for critical religious rulings:

- **Divorce** (طلاق, หย่า)
- **Abortion** (แท้ง)
- **Inheritance** (มรดก)
- **Adoption** (รับบุตร)
- **Suicide** (ฆ่าตัวตาย)

These always return `confidence=1.0` because safety is critical.

### 2. Quran

Keywords: quran, al-quran, กุรอาน, ซูเราะ (surah), อายะ (ayah), سورة, آية

### 3. Hadith

Keywords: hadith, bukhari, muslim, tirmidhi, abu dawud, ibn majah, ahmad, บุคอรี, حديث

**Note**: Word boundaries prevent false positives (e.g., "มุสลิม" as "Muslim" vs. "muslim" the hadith collector).

### 4. Fiqh

Keywords: ฟิกฮ์, นมาซ (salah), วุฎูอ์ (wudu), โซกาต (zakat), รอมฎอน (Ramadan), หัจญ์ (hajj), صلاة, زكاة, حج

### 5. Aqidah

Keywords: อะกีดะฮ์, ตะวัคกุล (tawakkul), อีมาน (iman), عقيدة, توحيد, إيمان

### 6. Halal

Keywords: halal, haram, ฮาลาล, ฮารอม, อาหาร, เนื้อ, حلال, حرام

### 7. History

Keywords: prophet, ประวัติ (history), ท่านนบี, ศอฮาบะฮ์ (sahaba), النبي, الصحابة

### 8. Personal Advice

Generic indicators: ควร (should), ต้อง (must), ผม/ดิฉัน/ฉัน (I), ช่วย (help), "i should", "should i"

**Note**: Checked last because it's the most generic pattern.

### 9. General

Fallback when no specific intent is detected.

## Madhhab Detection

Detects explicit madhhab mentions:

- **Shafii**: shafii, shafi'i, ชาฟิอี, الشافعي
- **Hanafi**: hanafi, ฮานาฟี, الحنفي
- **Maliki**: maliki, มาลิกี, المالكي
- **Hanbali**: hanbali, ฮันบะลี, الحنبلي

Returns `unspecified` when no madhhab is mentioned (system will use user preference).

## Risk Level Classification

### Restricted (Always Rules-Based)

Questions about illegal activities:

- Illegal acts (ผิดกฎหมาย, illegal)
- Violence (ฆ่า, kill)
- Terrorism (ระเบิด, เทอร์เรอร์, bomb, terror)

Returns `confidence=1.0` for safety-critical detection.

### High

- High-risk rulings (divorce, abortion, inheritance)
- Medical questions (รักษา, ผ่าตัด, surgery)
- Financial questions (ลงทุน, หุ้น, investment)

### Medium

- Fiqh questions (ritual practice)
- Personal advice questions

### Low

- Informational queries (Quran, Hadith, history, aqidah)

## Special Requirements

### Requires Current Information

Detects temporal indicators:

- Time references: ตอนนี้ (now), ปัจจุบัน (current), ปีนี้ (this year), recent, latest
- Specific years: 2024, 2025, 2026
- Current events: covid, โควิด, pandemic, วัคซีน (vaccine)

When `true`, orchestrator should consider external knowledge sources or return a disclaimer about information currency.

### Requires Thailand-Specific Information

Detects location-specific indicators:

- ไทย, Thailand, กทม (Bangkok), bangkok
- กฎหมายไทย (Thai law), thai law
- กระทรวง (ministry)
- halal thai, ฮาลาลไทย

When `true`, orchestrator should prioritize Thailand-specific sources or mention jurisdiction limitations.

## LLM Fallback Strategy

LLM fallback is used only when rule-based confidence is below 0.9 (ambiguous cases).

### When LLM is Used

- Generic questions without clear keywords
- Mixed-language questions with ambiguous intent
- Questions where multiple intents could apply

### When LLM is Skipped

- High-risk or restricted content (rules are deterministic)
- Clear keyword matches with high confidence
- LLM provider unavailable (fail-safe to rules)

### LLM Prompt Structure

```
Classify this Islamic knowledge question:

Question: {question}

Rule-based classification:
- Language: {rule_language}
- Intent: {rule_intent}
- Madhhab: {rule_madhhab}
- Risk: {rule_risk}

Refine the classification if the rules are incorrect. Output JSON:
{
  "language": "th|ar|en|mixed|unknown",
  "intent": "quran|hadith|fiqh|...",
  "madhhab": "shafii|hanafi|maliki|hanbali|unspecified",
  "risk_level": "low|medium|high|restricted",
  "confidence": 0.0-1.0
}
```

**Note**: Current implementation returns hybrid result with rule data and LLM trace. Future enhancement: parse LLM JSON and merge intelligently.

## Confidence Scoring

Rule-based confidence calculation:

- **Base**: 0.5
- **+0.2**: Language detected (not unknown)
- **+0.2**: Intent detected (not general)
- **Override to 1.0**: Risk level is HIGH or RESTRICTED (safety-critical)

LLM-enhanced confidence is typically 0.8 (indicating LLM assisted with ambiguous case).

## Integration with Orchestration Pipeline

```python
from zayd_service_orchestrator import QuestionClassifier, OllamaLLMAdapter

# Initialize with optional LLM fallback
llm = OllamaLLMAdapter(model_id="llama2")
classifier = QuestionClassifier(llm_provider=llm)

# Classify question
result = await classifier.classify("ซูเราะฮ์อัลบะเกาะเราะฮ์พูดถึงอะไร")

# Use classification results
if result.risk_level == RiskLevel.RESTRICTED:
    return "Question violates policy"

if result.language == Language.THAI:
    query_expansion = expand_thai_query(question)

if result.intent == Intent.QURAN:
    retrieval_strategy = QuranRetrievalStrategy()

if result.requires_current_info:
    return "Question requires current information beyond knowledge cutoff"
```

## Traceability

Every classification includes trace metadata:

```python
result.trace = {
    "language_detected": "th",
    "intent_detected": "quran",
    "madhhab_detected": "unspecified",
    "risk_detected": "low",
    "llm_text": "...",  # LLM response if used
    "llm_provider": "ollama",  # LLM provider if used
    "llm_error": "...",  # Error if LLM failed
}
```

This enables:

- Audit logs for safety-critical decisions
- Debugging classification errors
- Regression testing with golden sets
- Reviewer correction workflow

## Security Considerations

1. **Deterministic Safety**: Risk level detection uses only deterministic rules, never LLM judgment alone.

2. **Fail-Safe**: Classification continues with rules-based results when LLM is unavailable.

3. **No Prompt Injection**: Classification treats question text as data, not instructions.

4. **Versioned Schema**: Schema version allows migration and validation of stored classifications.

5. **Audit Trail**: All decisions are traceable through trace metadata.

## Testing Strategy

### Golden Set Testing

`test_classification_golden_set()` validates known-correct classifications:

```python
golden_cases = [
    ("ซูเราะฮ์อัลบะเกาะเราะฮ์พูดถึงอะไร", Language.THAI, Intent.QURAN, RiskLevel.LOW),
    ("การหย่าในอิสลาม", Language.THAI, Intent.HIGH_RISK_RULING, RiskLevel.HIGH),
    ("What is wudu?", Language.ENGLISH, Intent.FIQH, RiskLevel.MEDIUM),
    ("ما هو حديث", Language.ARABIC, Intent.HADITH, RiskLevel.LOW),
    ("อาหารฮาลาล", Language.THAI, Intent.HALAL, RiskLevel.LOW),
]
```

### Rule vs. LLM Coverage

Tests verify:

- Rules handle safety-critical cases with `confidence=1.0`
- LLM fallback triggers for ambiguous cases
- LLM failure doesn't break classification

### Regression Prevention

When reviewers correct classifications:

1. Add corrected case to golden set
2. Update rules if pattern is generalizable
3. Re-run full test suite

## Future Enhancements

1. **Structured LLM Output**: Use LLM response_format="json" for reliable parsing.

2. **Multi-madhhab Detection**: Detect when question explicitly asks for multiple madhhab views.

3. **Confidence Thresholds**: Tune thresholds for LLM fallback based on production data.

4. **Language-Specific Rules**: More comprehensive Thai and Arabic keyword coverage.

5. **Reviewer Feedback Loop**: Incorporate reviewer corrections to improve rule patterns.

## References

- SRS §13: Functional Requirements — Question Classification
- FR-CLASS-001 to FR-CLASS-008
- Provider SDK: `services/orchestrator/src/zayd_service_orchestrator/provider_sdk.py`
- Implementation: `services/orchestrator/src/zayd_service_orchestrator/question_classification.py`
- Tests: `services/orchestrator/tests/test_question_classification.py`
