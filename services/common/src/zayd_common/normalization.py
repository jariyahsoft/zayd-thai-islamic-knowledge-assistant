"""Thai and Arabic text normalization pipelines.

Provides separate, versioned normalization pipelines for Thai and Arabic
search text.  The original text is **never mutated** — normalization always
produces a new string alongside the preserved original.

Thai normalization handles:
- Unicode NFC normalization
- Zero-width character removal (ZWSP, ZWJ, ZWNJ, FEFF, soft-hyphen)
- Thai whitespace conventions (trailing/leading whitespace collapse)
- Thai combining character ordering

Arabic normalization handles:
- Unicode NFC normalization
- Diacritic (tashkeel/harakat) removal for search
- Tatweel (kashida) removal
- Alef variants → bare alef
- Teh marbuta → heh
- Final yeh variants → yeh

Both pipelines are deterministic, idempotent, and versioned.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Version constants
# ---------------------------------------------------------------------------

THAI_NORMALIZER_VERSION = "thai-norm-v1"
ARABIC_NORMALIZER_VERSION = "arabic-norm-v1"
NORMALIZATION_FRAMEWORK_VERSION = "text-norm-v1"

# ---------------------------------------------------------------------------
# Thai normalization tables
# ---------------------------------------------------------------------------

#: Zero-width and invisible characters to strip from Thai text.
_THAI_STRIP_CHARS = frozenset({
    "​",  # Zero-Width Space (ZWSP)
    "‌",  # Zero-Width Non-Joiner (ZWNJ)
    "‍",  # Zero-Width Joiner (ZWJ)
    "⁠",  # Word Joiner
    "﻿",  # BOM / Zero-Width No-Break Space
    "­",  # Soft Hyphen
    "͏",  # Combining Grapheme Joiner
})

# ---------------------------------------------------------------------------
# Arabic normalization tables
# ---------------------------------------------------------------------------

#: Arabic diacritical marks (tashkeel/harakat) to remove for search.
_ARABIC_DIACRITICS = frozenset({
    "ؐ",  # ARABIC SIGN SALLALLAHOU ALAYHE WASSALLAM
    "ؑ",  # ARABIC SIGN ALAYHE ASSALLAM
    "ؒ",  # ARABIC SIGN RAHMATULLAH ALAYHE
    "ؓ",  # ARABIC SIGN RADI ALLAHOU ANHU
    "ؔ",  # ARABIC SIGN TAKHALLUS
    "ؕ",  # ARABIC SMALL HIGH TAH
    "ؖ",  # ARABIC SMALL HIGH LIGATURE ALEF WITH LAM WITH YEH
    "ؗ",  # ARABIC SMALL HIGH ZAIN
    "ؘ",  # ARABIC SMALL FATHAH
    "ؙ",  # ARABIC SMALL DAMMAH
    "ؚ",  # ARABIC SMALL KASRAH
    "ً",  # ARABIC FATHATAN (tanween fatha)
    "ٌ",  # ARABIC DAMMATAN (tanween damma)
    "ٍ",  # ARABIC KASRATAN (tanween kasra)
    "َ",  # ARABIC FATHAH
    "ُ",  # ARABIC DAMMAH
    "ِ",  # ARABIC KASRAH
    "ّ",  # ARABIC SHADDAH
    "ْ",  # ARABIC SUKUN
    "ٓ",  # ARABIC MADDAH ABOVE
    "ٔ",  # ARABIC HAMZAH ABOVE
    "ٕ",  # ARABIC HAMZAH BELOW
    "ٖ",  # ARABIC SUBSCRIPT ALEF
    "ٗ",  # ARABIC INVERTED DAMMA
    "٘",  # ARABIC MARK NOON GHUNNA
    "ٙ",  # ARABIC ZWARAKAY
    "ٚ",  # ARABIC VOWEL SIGN SMALL V ABOVE
    "ٛ",  # ARABIC VOWEL SIGN INVERTED SMALL V ABOVE
    "ٜ",  # ARABIC VOWEL SIGN DOT BELOW
    "ٝ",  # ARABIC REVERSED DAMMA
    "ٞ",  # ARABIC FATHA WITH TWO DOTS
    "ٟ",  # ARABIC WAVY HAMZA BELOW
    "ٰ",  # ARABIC LETTER SUPERSCRIPT ALEF
    "ۖ",  # ARABIC SMALL HIGH LIGATURE SAD WITH LAM WITH ALEF MAKSURA
    "ۗ",  # ARABIC SMALL HIGH LIGATURE QAF WITH LAM WITH ALEF MAKSURA
    "ۘ",  # ARABIC SMALL HIGH MEEM INITIAL FORM
    "ۙ",  # ARABIC SMALL HIGH LAM ALEF
    "ۚ",  # ARABIC SMALL HIGH JEEM
    "ۛ",  # ARABIC SMALL HIGH THREE DOTS
    "ۜ",  # ARABIC SMALL HIGH SEEN
    "۟",  # ARABIC SMALL HIGH ROUNDED ZERO
    "۠",  # ARABIC SMALL HIGH UPRIGHT RECTANGULAR ZERO
    "ۡ",  # ARABIC SMALL HIGH DOTLESS HEAD OF KHAH
    "ۢ",  # ARABIC SMALL HIGH MEEM ISOLATED FORM
    "ۣ",  # ARABIC SMALL LOW SEEN
    "ۤ",  # ARABIC SMALL HIGH MADDA
    "ۧ",  # ARABIC SMALL HIGH YEH
    "ۨ",  # ARABIC SMALL HIGH NOON
    "۪",  # ARABIC EMPTY CENTRE LOW STOP
    "۫",  # ARABIC EMPTY CENTRE HIGH STOP
    "۬",  # ARABIC ROUNDED HIGH STOP WITH FILLED CENTRE
    "ۭ",  # ARABIC SMALL LOW MEEM
})

#: Tatweel (kashida) character — used for typographic stretching.
_ARABIC_TATWEEL = "ـ"

#: Alef variant → bare alef mapping for search normalization.
_ARABIC_ALEF_VARIANTS: dict[str, str] = {
    "آ": "ا",  # ALEF WITH MADDA ABOVE → ALEF
    "أ": "ا",  # ALEF WITH HAMZA ABOVE → ALEF
    "إ": "ا",  # ALEF WITH HAMZA BELOW → ALEF
    "ٱ": "ا",  # ALEF WASLA → ALEF
    "ٲ": "ا",  # ALEF WITH WAVY HAMZA ABOVE → ALEF
    "ٳ": "ا",  # ALEF WITH WAVY HAMZA BELOW → ALEF
}

#: Teh marbuta → heh for search.
_ARABIC_TEH_MARBUTA = "ة"
_ARABIC_HEH = "ه"

#: Alef maksura → yeh for search.
_ARABIC_ALEF_MAKSURA = "ى"
_ARABIC_YEH = "ي"


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class NormalizationResult:
    """Result of text normalization.

    ``original`` is always preserved byte-for-byte.
    ``normalized`` is the search-optimized form.
    """

    original: str
    normalized: str
    language: str
    normalizer_version: str
    framework_version: str = NORMALIZATION_FRAMEWORK_VERSION
    steps_applied: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Thai normalizer
# ---------------------------------------------------------------------------

def normalize_thai(text: str) -> NormalizationResult:
    """Normalize Thai text for search while preserving the original.

    Steps applied:
    1. Unicode NFC normalization
    2. Zero-width character removal
    3. Whitespace collapsing (multiple spaces → single space, strip)
    """
    original = text
    steps: list[str] = []

    # Step 1: Unicode NFC
    result = unicodedata.normalize("NFC", text)
    if result != text:
        steps.append("unicode_nfc")

    # Step 2: Remove zero-width characters
    before = result
    result = "".join(ch for ch in result if ch not in _THAI_STRIP_CHARS)
    if result != before:
        steps.append("strip_zero_width")

    # Step 3: Whitespace collapsing
    before = result
    result = " ".join(result.split())
    if result != before:
        steps.append("collapse_whitespace")

    return NormalizationResult(
        original=original,
        normalized=result,
        language="th",
        normalizer_version=THAI_NORMALIZER_VERSION,
        steps_applied=steps,
    )


# ---------------------------------------------------------------------------
# Arabic normalizer
# ---------------------------------------------------------------------------

def normalize_arabic(text: str) -> NormalizationResult:
    """Normalize Arabic text for search while preserving the original.

    Steps applied:
    1. Unicode NFC normalization
    2. Diacritic (tashkeel) removal
    3. Tatweel (kashida) removal
    4. Alef variant normalization
    5. Teh marbuta → heh
    6. Alef maksura → yeh
    7. Whitespace collapsing
    """
    original = text
    steps: list[str] = []

    # Step 1: Unicode NFC
    result = unicodedata.normalize("NFC", text)
    if result != text:
        steps.append("unicode_nfc")

    # Step 2: Remove diacritics
    before = result
    result = "".join(ch for ch in result if ch not in _ARABIC_DIACRITICS)
    if result != before:
        steps.append("strip_diacritics")

    # Step 3: Remove tatweel
    before = result
    result = result.replace(_ARABIC_TATWEEL, "")
    if result != before:
        steps.append("strip_tatweel")

    # Step 4: Alef variant normalization
    before = result
    for variant, replacement in _ARABIC_ALEF_VARIANTS.items():
        result = result.replace(variant, replacement)
    if result != before:
        steps.append("normalize_alef")

    # Step 5: Teh marbuta → heh
    before = result
    result = result.replace(_ARABIC_TEH_MARBUTA, _ARABIC_HEH)
    if result != before:
        steps.append("teh_marbuta_to_heh")

    # Step 6: Alef maksura → yeh
    before = result
    result = result.replace(_ARABIC_ALEF_MAKSURA, _ARABIC_YEH)
    if result != before:
        steps.append("alef_maksura_to_yeh")

    # Step 7: Whitespace collapsing
    before = result
    result = " ".join(result.split())
    if result != before:
        steps.append("collapse_whitespace")

    return NormalizationResult(
        original=original,
        normalized=result,
        language="ar",
        normalizer_version=ARABIC_NORMALIZER_VERSION,
        steps_applied=steps,
    )


# ---------------------------------------------------------------------------
# Language-aware dispatcher
# ---------------------------------------------------------------------------

def normalize_text(
    text: str,
    *,
    language: str,
) -> NormalizationResult:
    """Dispatch to the appropriate normalizer by language code.

    Supported languages: ``th`` (Thai), ``ar`` (Arabic).
    For unsupported languages, returns NFC-normalized text with no
    language-specific transformations.
    """
    if language == "th":
        return normalize_thai(text)
    if language == "ar":
        return normalize_arabic(text)

    # Fallback: NFC only
    original = text
    result = unicodedata.normalize("NFC", text)
    steps = ["unicode_nfc"] if result != text else []

    return NormalizationResult(
        original=original,
        normalized=result,
        language=language,
        normalizer_version="generic-norm-v1",
        steps_applied=steps,
    )
