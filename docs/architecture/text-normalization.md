# Text Normalization Architecture

## Overview

Zayd uses **separate, versioned normalization pipelines** for Thai and Arabic text. Normalization produces search-optimized text while preserving the original byte-for-byte.

```
Parser Output (original text) → Normalization → Search Index
                             ↘ Original preserved in storage
```

## Core Principle: Original Text Preservation

**The original text is never mutated.** Every normalization function returns a `NormalizationResult` containing both:

- `original` — the exact input text, preserved byte-for-byte
- `normalized` — the search-optimized form

This ensures auditable, reversible normalization and allows re-normalization when the pipeline version changes.

## Normalization Pipelines

### Thai Pipeline (`thai-norm-v1`)

| Step | Description |
|---|---|
| Unicode NFC | Compose decomposed characters (e.g., Sara AM) |
| Zero-width removal | Strip ZWSP, ZWJ, ZWNJ, BOM, soft hyphen, etc. |
| Whitespace collapse | Multiple spaces → single space, trim edges |

**Why these steps?**

- Thai text frequently uses zero-width space (ZWSP U+200B) for word boundaries in digital text. These are invisible but cause search mismatches.
- Thai combining marks (tone marks, vowels like sara-am) appear in both composed and decomposed Unicode forms. NFC ensures consistent representation.
- Soft hyphens and other invisible formatting characters interfere with search indexing.

**What is preserved:**

- Thai combining marks (tone marks, vowels, consonant clusters)
- Arabic loanwords embedded in Thai text
- Digits and punctuation

### Arabic Pipeline (`arabic-norm-v1`)

| Step | Description |
|---|---|
| Unicode NFC | Compose decomposed characters |
| Diacritic removal | Strip all tashkeel/harakat marks |
| Tatweel removal | Remove kashida stretching character |
| Alef normalization | آ أ إ ٱ → ا |
| Teh marbuta → heh | ة → ه |
| Alef maksura → yeh | ى → ي |
| Whitespace collapse | Multiple spaces → single space, trim edges |

**Why these steps?**

- **Diacritics (tashkeel):** Arabic text with full diacritics (e.g., Quran text) must match queries without diacritics. Searching `بسم` should find `بِسْمِ`.
- **Tatweel (kashida):** Purely decorative stretching char (ـ) used in typography. Breaks exact search.
- **Alef variants:** Arabic has multiple alef forms (with hamza above/below, with madda, wasla). Users typically search with bare alef (ا).
- **Teh marbuta/heh:** In informal Arabic and many search queries, ة and ه are used interchangeably.
- **Alef maksura/yeh:** Similarly, ى and ي are often interchanged by users.

**What is preserved:**

- All base consonants and vowels
- Latin numerals and punctuation
- Non-Arabic script embedded in Arabic text

### Generic Fallback

Languages not explicitly supported receive NFC normalization only.

## API Usage

```python
from zayd_common.normalization import normalize_text

# Thai
result = normalize_text("สวัสดี​ครับ", language="th")
assert result.original == "สวัสดี​ครับ"    # ZWSP preserved in original
assert result.normalized == "สวัสดีครับ"    # ZWSP removed for search

# Arabic
result = normalize_text("بِسْمِ اللَّهِ", language="ar")
assert result.original == "بِسْمِ اللَّهِ"  # diacritics preserved
assert result.normalized == "بسم الله"      # diacritics stripped

# Language-specific
from zayd_common.normalization import normalize_thai, normalize_arabic
thai_result = normalize_thai("ทดสอบ")
arabic_result = normalize_arabic("القرآن")
```

## NormalizationResult

```python
@dataclass(frozen=True)
class NormalizationResult:
    original: str           # Input preserved byte-for-byte
    normalized: str         # Search-optimized form
    language: str           # Language code
    normalizer_version: str # Pipeline version (e.g., "thai-norm-v1")
    framework_version: str  # Framework version (e.g., "text-norm-v1")
    steps_applied: list[str]  # Which steps actually changed the text
```

The `steps_applied` field records only steps that modified the text, enabling audit and debugging.

## Versioning Strategy

Each pipeline has an independent version string:

- `thai-norm-v1` — Thai normalizer
- `arabic-norm-v1` — Arabic normalizer
- `generic-norm-v1` — Fallback (NFC only)
- `text-norm-v1` — Framework version

When a pipeline changes (e.g., adding new steps or modifying existing ones), bump the version. This allows re-normalization of previously processed documents when the pipeline improves.

## Islamic Religious Terminology

### Thai Islamic Terms

Thai transliterations of Arabic Islamic terms are preserved as-is:

| Thai | Arabic Origin | Meaning |
|---|---|---|
| อัลกุรอาน | القرآن | The Quran |
| ฮะดีษ | الحديث | Hadith |
| ซอลาต | الصلاة | Salat (prayer) |
| ซะกาต | الزكاة | Zakat |
| เราะมะฎอน | رمضان | Ramadan |
| มัสยิด | المسجد | Mosque |

### Arabic Islamic Terms

Core Islamic terms with diacritics normalize to their base forms for search:

| With Diacritics | Normalized | Meaning |
|---|---|---|
| بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ | بسم الله الرحمن الرحيم | Bismillah |
| القُرْآنُ | القران | The Quran |
| الْحَمْدُ لِلَّهِ | الحمد لله | Al-Hamdu Lillah |

## Security Considerations

- Normalization operates on in-memory strings only; no filesystem access.
- Input text is treated as untrusted; the normalizer does not execute or interpret content.
- Original text preservation ensures no data loss from normalization.
- No external dependencies — pure Python `unicodedata` module only.
