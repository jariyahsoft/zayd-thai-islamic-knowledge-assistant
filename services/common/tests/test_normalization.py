"""Unit tests for Thai and Arabic text normalization.

Covers:
- Golden normalization fixtures for Thai, Arabic, and mixed-script text
- Round-trip preservation (original text never mutated)
- Regression tests for known script edge cases
- Versioning and determinism
"""

from __future__ import annotations

from zayd_common.normalization import (
    ARABIC_NORMALIZER_VERSION,
    NORMALIZATION_FRAMEWORK_VERSION,
    THAI_NORMALIZER_VERSION,
    normalize_arabic,
    normalize_text,
    normalize_thai,
)

# ---------------------------------------------------------------------------
# Golden normalization fixtures — Thai
# ---------------------------------------------------------------------------


class TestThaiNormalization:
    """Golden fixtures for Thai text normalization."""

    def test_basic_thai_text(self):
        result = normalize_thai("สวัสดีครับ")
        assert result.original == "สวัสดีครับ"
        assert result.normalized == "สวัสดีครับ"
        assert result.language == "th"
        assert result.normalizer_version == THAI_NORMALIZER_VERSION

    def test_thai_basmala(self):
        """Thai transliteration of Bismillah."""
        text = "บิสมิลลาฮิรเราะห์มานิรเราะฮีม"
        result = normalize_thai(text)
        assert result.original == text
        assert result.normalized == text
        assert result.language == "th"

    def test_thai_with_zwsp(self):
        """Thai text often uses ZWSP for word boundaries."""
        # Thai with zero-width space between words
        text = "สวัสดี​ครับ"
        result = normalize_thai(text)
        assert result.original == text
        assert result.normalized == "สวัสดีครับ"
        assert "strip_zero_width" in result.steps_applied

    def test_thai_with_multiple_zero_width_chars(self):
        text = "ข้อ​ความ‌ทดสอบ‍นี้﻿"
        result = normalize_thai(text)
        assert result.original == text
        assert "​" not in result.normalized
        assert "‌" not in result.normalized
        assert "‍" not in result.normalized
        assert "﻿" not in result.normalized
        assert result.normalized == "ข้อความทดสอบนี้"

    def test_thai_whitespace_collapsing(self):
        text = "  สวัสดี   ครับ  "
        result = normalize_thai(text)
        assert result.original == text
        assert result.normalized == "สวัสดี ครับ"
        assert "collapse_whitespace" in result.steps_applied

    def test_thai_nfc_normalization(self):
        """Thai text with decomposed Unicode should be NFC-composed."""
        # สำ as decomposed (SARA AM separate) vs composed
        decomposed = "สำ"  # ส + SARA AM
        composed = "สำ"
        result = normalize_thai(decomposed)
        assert result.normalized == composed
        assert result.original == decomposed

    def test_thai_soft_hyphen_removal(self):
        text = "ทด­สอบ"
        result = normalize_thai(text)
        assert "­" not in result.normalized
        assert result.normalized == "ทดสอบ"

    def test_thai_islamic_terminology(self):
        """Thai Islamic terms should be preserved."""
        terms = [
            "อัลกุรอาน",       # Al-Quran
            "ฮะดีษ",          # Hadith
            "ซอลาต",          # Salat
            "วุฎูอ์",          # Wudu
            "อิสลาม",          # Islam
            "มุสลิม",          # Muslim
            "มัสยิด",          # Masjid
            "จุมอะฮ์",         # Jum'ah
            "ซะกาต",          # Zakat
            "เราะมะฎอน",       # Ramadan
        ]
        for term in terms:
            result = normalize_thai(term)
            assert result.original == term
            # Basic text should pass through unchanged
            assert result.normalized == term

    def test_thai_empty_string(self):
        result = normalize_thai("")
        assert result.original == ""
        assert result.normalized == ""
        assert result.steps_applied == []


# ---------------------------------------------------------------------------
# Golden normalization fixtures — Arabic
# ---------------------------------------------------------------------------


class TestArabicNormalization:
    """Golden fixtures for Arabic text normalization."""

    def test_basmala_with_diacritics(self):
        """Basmala with full tashkeel."""
        text = "بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ"
        result = normalize_arabic(text)
        assert result.original == text
        # Diacritics stripped, alef preserved
        assert "بسم الله الرحمن الرحيم" == result.normalized
        assert "strip_diacritics" in result.steps_applied
        assert result.language == "ar"
        assert result.normalizer_version == ARABIC_NORMALIZER_VERSION

    def test_arabic_without_diacritics(self):
        text = "بسم الله الرحمن الرحيم"
        result = normalize_arabic(text)
        assert result.original == text
        assert result.normalized == text

    def test_alef_variant_normalization(self):
        """All alef variants should normalize to bare alef."""
        text = "أحمد إبراهيم آمنة"
        result = normalize_arabic(text)
        assert "ا" in result.normalized
        assert "أ" not in result.normalized
        assert "إ" not in result.normalized
        assert "آ" not in result.normalized
        assert "normalize_alef" in result.steps_applied
        assert result.normalized == "احمد ابراهيم امنه"

    def test_tatweel_removal(self):
        """Tatweel (kashida) used for stretching should be removed."""
        text = "الرحمـــن"
        result = normalize_arabic(text)
        assert "ـ" not in result.normalized
        assert result.normalized == "الرحمن"
        assert "strip_tatweel" in result.steps_applied

    def test_teh_marbuta_to_heh(self):
        text = "مكة المكرمة"
        result = normalize_arabic(text)
        assert "ة" not in result.normalized
        assert result.normalized == "مكه المكرمه"
        assert "teh_marbuta_to_heh" in result.steps_applied

    def test_alef_maksura_to_yeh(self):
        text = "موسى"
        result = normalize_arabic(text)
        assert "ى" not in result.normalized
        assert result.normalized == "موسي"
        assert "alef_maksura_to_yeh" in result.steps_applied

    def test_arabic_whitespace_collapsing(self):
        text = "  بسم   الله  "
        result = normalize_arabic(text)
        assert result.normalized == "بسم الله"
        assert "collapse_whitespace" in result.steps_applied

    def test_arabic_islamic_terminology(self):
        """Core Islamic terms with diacritics."""
        terms = {
            "القُرْآنُ": "القران",         # Al-Quran
            "الحَدِيثُ": "الحديث",        # Hadith
            "الصَّلَاةُ": "الصلاه",        # Salat
            "الزَّكَاةُ": "الزكاه",        # Zakat
            "الصَّوْمُ": "الصوم",          # Sawm/Fasting
        }
        for original, expected in terms.items():
            result = normalize_arabic(original)
            assert result.original == original
            assert result.normalized == expected, (
                f"Failed for {original!r}: "
                f"expected {expected!r}, got {result.normalized!r}"
            )

    def test_arabic_empty_string(self):
        result = normalize_arabic("")
        assert result.original == ""
        assert result.normalized == ""
        assert result.steps_applied == []

    def test_arabic_combined_normalization(self):
        """Multiple normalization steps in a single pass."""
        text = "بِسْمِ اللَّـــهِ الرَّحْمَنِ الرَّحِيمِ"
        result = normalize_arabic(text)
        assert result.original == text
        assert "strip_diacritics" in result.steps_applied
        assert "strip_tatweel" in result.steps_applied
        assert result.normalized == "بسم الله الرحمن الرحيم"


# ---------------------------------------------------------------------------
# Round-trip preservation tests
# ---------------------------------------------------------------------------


class TestRoundTripPreservation:
    """Verify original text is never mutated."""

    def test_thai_original_preserved(self):
        original = "สวัสดี​ครับ ท่าน‌ทุกคน"
        result = normalize_thai(original)
        assert result.original == original
        assert "​" in result.original
        assert "‌" in result.original

    def test_arabic_original_preserved(self):
        original = "بِسْمِ اللَّهِ"
        result = normalize_arabic(original)
        assert result.original == original
        assert "ِ" in result.original  # kasrah in original
        assert "ّ" in result.original  # shaddah in original

    def test_normalization_does_not_modify_input_string(self):
        """The input Python string object is not modified."""
        thai_text = "ทดสอบ​ข้อความ"
        thai_copy = str(thai_text)
        normalize_thai(thai_text)
        assert thai_text == thai_copy

        arabic_text = "بِسْمِ اللَّهِ"
        arabic_copy = str(arabic_text)
        normalize_arabic(arabic_text)
        assert arabic_text == arabic_copy


# ---------------------------------------------------------------------------
# Regression tests for known script edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Regression tests for known script edge cases."""

    def test_thai_with_arabic_loanwords(self):
        """Thai text containing transliterated Arabic terms."""
        text = "การละหมาดซุบฮิ (صلاة الصبح)"
        result = normalize_thai(text)
        assert result.original == text
        # Thai normalizer should not strip Arabic diacritics
        assert result.normalized == text

    def test_arabic_with_latin_numerals(self):
        """Arabic text mixed with Latin digits."""
        text = "سورة البقرة - 255"
        result = normalize_arabic(text)
        assert "255" in result.normalized
        assert result.normalized == "سوره البقره - 255"

    def test_mixed_thai_arabic_via_dispatcher(self):
        """Dispatcher selects correct normalizer by language."""
        thai = normalize_text("สวัสดี​ครับ", language="th")
        arabic = normalize_text("بِسْمِ اللَّهِ", language="ar")
        assert thai.language == "th"
        assert thai.normalizer_version == THAI_NORMALIZER_VERSION
        assert arabic.language == "ar"
        assert arabic.normalizer_version == ARABIC_NORMALIZER_VERSION

    def test_unsupported_language_gets_nfc(self):
        """Unsupported language code returns NFC-only normalization."""
        result = normalize_text("hello world", language="en")
        assert result.original == "hello world"
        assert result.normalized == "hello world"
        assert result.language == "en"
        assert result.normalizer_version == "generic-norm-v1"

    def test_arabic_hamza_variations(self):
        """Different hamza positions should be handled correctly."""
        text = "إسلام أمة ٱلله"
        result = normalize_arabic(text)
        assert "إ" not in result.normalized
        assert "أ" not in result.normalized
        assert "ٱ" not in result.normalized
        assert result.normalized == "اسلام امه الله"

    def test_thai_combining_marks_preserved(self):
        """Thai combining marks (tone marks, vowels) should be preserved."""
        # สวัสดี has combining marks: sara-am, mai-ek, etc.
        text = "ก้า"  # ko kai + mai ek + sara aa
        result = normalize_thai(text)
        assert result.normalized == text

    def test_arabic_all_diacritics_strip(self):
        """Every Arabic diacritic should be removed."""
        base = "ك"
        diacritical = "كً"  # kaf + fathatan
        result = normalize_arabic(diacritical)
        assert result.normalized == base

    def test_consecutive_tatweels(self):
        text = "كـــتـــاب"
        result = normalize_arabic(text)
        assert "ـ" not in result.normalized
        assert result.normalized == "كتاب"

    def test_arabic_surah_fatiha_opening(self):
        """Full opening of Al-Fatiha with tashkeel."""
        text = (
            "الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ "
            "الرَّحْمَنِ الرَّحِيمِ "
            "مَالِكِ يَوْمِ الدِّينِ"
        )
        result = normalize_arabic(text)
        assert result.original == text
        expected = "الحمد لله رب العالمين الرحمن الرحيم مالك يوم الدين"
        assert result.normalized == expected

    def test_thai_quran_verse_reference(self):
        """Thai Quran verse reference with numbers."""
        text = "อัล-บะเกาะเราะฮ์ อายะฮ์ที่ 255"
        result = normalize_thai(text)
        assert result.normalized == text

    def test_only_whitespace_text(self):
        thai = normalize_thai("   ")
        assert thai.normalized == ""
        arabic = normalize_arabic("   ")
        assert arabic.normalized == ""


# ---------------------------------------------------------------------------
# Determinism and versioning
# ---------------------------------------------------------------------------


class TestDeterminismAndVersioning:
    """Normalization must be deterministic and versioned."""

    def test_thai_idempotent(self):
        """Normalizing already-normalized Thai text returns same result."""
        text = "สวัสดี​ครับ"
        first = normalize_thai(text)
        second = normalize_thai(first.normalized)
        assert second.normalized == first.normalized

    def test_arabic_idempotent(self):
        """Normalizing already-normalized Arabic text returns same result."""
        text = "بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ"
        first = normalize_arabic(text)
        second = normalize_arabic(first.normalized)
        assert second.normalized == first.normalized

    def test_deterministic_thai(self):
        """Same input always produces same output."""
        text = "ทดสอบ​ข้อ‌ความ"
        results = [normalize_thai(text) for _ in range(3)]
        assert all(r.normalized == results[0].normalized for r in results)

    def test_deterministic_arabic(self):
        """Same input always produces same output."""
        text = "بِسْمِ اللَّهِ"
        results = [normalize_arabic(text) for _ in range(3)]
        assert all(r.normalized == results[0].normalized for r in results)

    def test_version_included_in_result(self):
        thai = normalize_thai("ทดสอบ")
        assert thai.normalizer_version == THAI_NORMALIZER_VERSION
        assert thai.framework_version == NORMALIZATION_FRAMEWORK_VERSION

        arabic = normalize_arabic("بسم")
        assert arabic.normalizer_version == ARABIC_NORMALIZER_VERSION
        assert arabic.framework_version == NORMALIZATION_FRAMEWORK_VERSION

    def test_dispatcher_version(self):
        result = normalize_text("test", language="en")
        assert result.framework_version == NORMALIZATION_FRAMEWORK_VERSION
