"""Tests for retrieval chunking strategies."""

from __future__ import annotations

from uuid import uuid4

import pytest
from zayd_common.chunking import (
    CHUNKING_FRAMEWORK_VERSION,
    FIQH_ISSUE_STRATEGY_VERSION,
    FIXED_WINDOW_STRATEGY_VERSION,
    HADITH_STRATEGY_VERSION,
    HEADING_SECTION_STRATEGY_VERSION,
    PARAGRAPH_STRATEGY_VERSION,
    QURAN_VERSE_STRATEGY_VERSION,
    TABLE_STRATEGY_VERSION,
    ChunkingError,
    ChunkSourceSection,
    chunk_sections_for_retrieval,
    chunk_text_for_retrieval,
    chunking_strategy_versions,
)


def test_quran_verse_strategy_preserves_references_context_and_versions():
    version_id = uuid4()

    result = chunk_text_for_retrieval(
        document_version_id=version_id,
        canonical_id="quran-doc",
        version_number=3,
        text="Quran 2:255 Ayat al-Kursi line.\nQuran 2:256 No compulsion line.",
        language="en",
        document_type="quran",
    )

    assert result.framework_version == CHUNKING_FRAMEWORK_VERSION
    assert result.strategy_name == "quran_verse"
    assert result.strategy_version == QURAN_VERSE_STRATEGY_VERSION
    assert [chunk.reference for chunk in result.chunks] == [
        "quran-doc:v3:quran-2-255",
        "quran-doc:v3:quran-2-256",
    ]
    assert all(chunk.document_version_id == version_id for chunk in result.chunks)
    assert all(chunk.strategy_version == QURAN_VERSE_STRATEGY_VERSION for chunk in result.chunks)
    assert result.chunks[0].metadata["context_after"] == result.chunks[1].content
    assert result.chunks[1].metadata["context_before"] == result.chunks[0].content


def test_hadith_strategy_splits_by_hadith_record_boundary():
    result = chunk_text_for_retrieval(
        document_version_id=uuid4(),
        canonical_id="hadith-doc",
        version_number=1,
        text=(
            "Hadith 42\n"
            "Actions are by intentions.\n"
            "\n"
            "Hadith 43\n"
            "Religion is sincere counsel."
        ),
        language="en",
        document_type="book",
    )

    assert result.strategy_name == "hadith_record"
    assert result.strategy_version == HADITH_STRATEGY_VERSION
    assert len(result.chunks) == 2
    assert result.chunks[0].reference == "hadith-doc:v1:42"
    assert result.chunks[1].reference == "hadith-doc:v1:43"
    assert result.chunks[0].metadata["semantic_unit"] == "hadith"


def test_fiqh_issue_strategy_splits_by_issue_heading():
    result = chunk_text_for_retrieval(
        document_version_id=uuid4(),
        canonical_id="fiqh-doc",
        version_number=2,
        text=(
            "Issue: Ablution before prayer\n"
            "Discussion of the first issue.\n"
            "Issue: Travel prayer\n"
            "Discussion of the second issue."
        ),
        language="en",
        document_type="fiqh",
    )

    assert result.strategy_name == "fiqh_issue"
    assert result.strategy_version == FIQH_ISSUE_STRATEGY_VERSION
    assert len(result.chunks) == 2
    assert result.chunks[0].reference == "fiqh-doc:v2:ablution-before-prayer"
    assert result.chunks[1].reference == "fiqh-doc:v2:travel-prayer"


def test_heading_section_strategy_preserves_section_and_page():
    result = chunk_sections_for_retrieval(
        document_version_id=uuid4(),
        canonical_id="heading-doc",
        version_number=1,
        sections=(
            ChunkSourceSection(
                content="# Purification\nRules for water.",
                page_start=4,
                page_end=5,
            ),
            ChunkSourceSection(
                content="## Prayer\nRules for standing.",
                page_start=6,
                page_end=7,
            ),
        ),
        language="en",
        document_type="book",
    )

    assert result.strategy_name == "heading_section"
    assert result.strategy_version == HEADING_SECTION_STRATEGY_VERSION
    assert [chunk.section for chunk in result.chunks] == ["Purification", "Prayer"]
    assert [chunk.page_start for chunk in result.chunks] == [4, 6]
    assert result.chunks[0].reference == "heading-doc:v1:purification"


def test_table_strategy_uses_parser_table_blocks():
    result = chunk_sections_for_retrieval(
        document_version_id=uuid4(),
        canonical_id="table-doc",
        version_number=1,
        sections=(
            ChunkSourceSection(
                content="| Topic | Rule |\n| --- | --- |\n| Water | Pure |",
                heading="Rulings",
                page_start=8,
                page_end=8,
                content_type="table",
            ),
        ),
        language="en",
        document_type="book",
    )

    assert result.strategy_name == "table"
    assert result.strategy_version == TABLE_STRATEGY_VERSION
    assert len(result.chunks) == 1
    assert result.chunks[0].section == "Rulings"
    assert result.chunks[0].reference == "table-doc:v1:table-1"
    assert result.chunks[0].metadata["semantic_unit"] == "table"


def test_paragraph_strategy_preserves_paragraph_boundaries():
    result = chunk_text_for_retrieval(
        document_version_id=uuid4(),
        canonical_id="para-doc",
        version_number=1,
        text="First paragraph with a ruling.\n\nSecond paragraph with evidence.",
        language="en",
        document_type="book",
    )

    assert result.strategy_name == "paragraph"
    assert result.strategy_version == PARAGRAPH_STRATEGY_VERSION
    assert [chunk.reference for chunk in result.chunks] == [
        "para-doc:v1:paragraph-1",
        "para-doc:v1:paragraph-2",
    ]
    assert result.chunks[0].metadata["context_after"] == "Second paragraph with evidence."


def test_fixed_window_fallback_uses_overlap_for_large_unstructured_block():
    words = [f"w{index}" for index in range(75)]

    result = chunk_text_for_retrieval(
        document_version_id=uuid4(),
        canonical_id="window-doc",
        version_number=1,
        text=" ".join(words),
        language="en",
        document_type="book",
        max_tokens=30,
        overlap_tokens=5,
    )

    assert result.strategy_name == "fixed_window"
    assert result.strategy_version == FIXED_WINDOW_STRATEGY_VERSION
    assert len(result.chunks) == 3
    assert result.chunks[0].metadata["window_start_token"] == 0
    assert result.chunks[1].metadata["window_start_token"] == 25
    assert result.chunks[0].content.split()[-5:] == result.chunks[1].content.split()[:5]
    assert all(chunk.token_count <= 30 for chunk in result.chunks)


def test_invalid_input_returns_stable_chunking_errors():
    with pytest.raises(ChunkingError) as empty_exc:
        chunk_text_for_retrieval(
            document_version_id=uuid4(),
            canonical_id="empty-doc",
            version_number=1,
            text="  ",
            language="en",
            document_type="book",
        )
    assert empty_exc.value.code == "CHUNKING_EMPTY_CONTENT"
    assert empty_exc.value.status_code == 422

    with pytest.raises(ChunkingError) as window_exc:
        chunk_text_for_retrieval(
            document_version_id=uuid4(),
            canonical_id="bad-doc",
            version_number=1,
            text="valid text",
            language="en",
            document_type="book",
            max_tokens=10,
        )
    assert window_exc.value.code == "CHUNKING_INVALID_WINDOW"

    with pytest.raises(ChunkingError) as overlap_exc:
        chunk_text_for_retrieval(
            document_version_id=uuid4(),
            canonical_id="bad-doc",
            version_number=1,
            text="valid text",
            language="en",
            document_type="book",
            max_tokens=20,
            overlap_tokens=20,
        )
    assert overlap_exc.value.code == "CHUNKING_INVALID_OVERLAP"


def test_chunking_strategy_versions_are_selection_ordered():
    assert chunking_strategy_versions() == (
        QURAN_VERSE_STRATEGY_VERSION,
        HADITH_STRATEGY_VERSION,
        FIQH_ISSUE_STRATEGY_VERSION,
        HEADING_SECTION_STRATEGY_VERSION,
        TABLE_STRATEGY_VERSION,
        PARAGRAPH_STRATEGY_VERSION,
        FIXED_WINDOW_STRATEGY_VERSION,
    )
