from __future__ import annotations

import pytest
from zayd_service_retrieval.query_expansion import (
    QUERY_EXPANSION_VERSION,
    QueryExpansionError,
    QueryExpansionPolicy,
    QueryExpansionRequest,
    QueryExpansionService,
)


def test_query_expansion_thai_arabic_english_golden_terms() -> None:
    service = QueryExpansionService()

    response = service.expand(QueryExpansionRequest(text="ละหมาดเดินทาง", language="th"))
    texts = {item.text for item in response.expansions}

    assert response.expansion_version == QUERY_EXPANSION_VERSION
    assert "ละหมาดเดินทาง" in texts
    assert "ซอลาต" in texts
    assert "الصلاة" in texts
    assert "prayer" in texts
    assert response.trace["expansion_version"] == QUERY_EXPANSION_VERSION
    assert response.trace["detected_language"] == "th"


def test_query_expansion_preserves_named_reference_intent() -> None:
    service = QueryExpansionService()

    response = service.expand(
        QueryExpansionRequest(text="hybrid-book:v1:travel-prayer ละหมาด", language="th")
    )

    assert response.named_reference_preserved is True
    assert len(response.expansions) == 1
    assert response.expansions[0].text == "hybrid-book:v1:travel-prayer ละหมาด"
    assert response.trace["named_reference_preserved"] is True


def test_query_expansion_can_be_disabled_or_limited_by_policy() -> None:
    service = QueryExpansionService()

    disabled = service.expand(
        QueryExpansionRequest(
            text="hadith prayer",
            language="en",
            policy=QueryExpansionPolicy(enabled=False, version="disabled-test"),
        )
    )
    assert disabled.disabled is True
    assert disabled.policy_version == "disabled-test"
    assert [item.kind for item in disabled.expansions] == ["original"]

    limited = service.expand(
        QueryExpansionRequest(
            text="hadith prayer",
            language="en",
            policy=QueryExpansionPolicy(max_expansions=2, version="limited-test"),
        )
    )
    assert limited.limited is True
    assert len(limited.expansions) == 2
    assert limited.trace["max_expansions"] == 2


def test_query_expansion_local_provider_fallback_is_deterministic() -> None:
    service = QueryExpansionService()

    first = service.expand(QueryExpansionRequest(text="zakat quran", language="en"))
    second = service.expand(QueryExpansionRequest(text="zakat quran", language="en"))

    assert first.expansions == second.expansions
    assert first.trace == second.trace
    assert {item.concept_id for item in first.expansions if item.concept_id} == {
        "zakat",
        "quran",
    }


def test_query_expansion_rejects_invalid_input() -> None:
    service = QueryExpansionService()

    with pytest.raises(QueryExpansionError) as empty_error:
        service.expand(QueryExpansionRequest(text=" ", language="th"))
    assert empty_error.value.code == "QUERY_EXPANSION_TEXT_REQUIRED"

    with pytest.raises(QueryExpansionError) as limit_error:
        service.expand(
            QueryExpansionRequest(
                text="ละหมาด",
                language="th",
                policy=QueryExpansionPolicy(max_expansions=0),
            )
        )
    assert limit_error.value.code == "QUERY_EXPANSION_INVALID_LIMIT"
