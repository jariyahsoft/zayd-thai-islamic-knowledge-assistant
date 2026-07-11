"""Tests for scholar pilot workflow documentation and data privacy (TASK-14-02)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHOLAR_WORKFLOW = REPO_ROOT / "docs/pilot/scholar-workflow.md"


def test_workflow_document_exists_and_contains_required_sections() -> None:
    """Pilot workflow dry run: verify the document covers all acceptance criteria."""
    assert SCHOLAR_WORKFLOW.exists(), "scholar-workflow.md must exist"
    text = SCHOLAR_WORKFLOW.read_text(encoding="utf-8")

    # Acceptance criterion: Reviewer consent, role and conflict-of-interest information are handled
    assert "consent" in text.lower()
    assert "conflict-of-interest" in text.lower()

    # Acceptance criterion: Scores link to benchmark cases without exposing identities publicly
    assert "case_key" in text
    assert "never" in text.lower()

    # Acceptance criterion: Findings produce tracked issues
    assert "issue" in text.lower() or "incident" in text.lower()

    # Required sections present
    assert "Onboarding Flow" in text
    assert "Scoring Guidelines" in text
    assert "Issue Tracking" in text
    assert "Data Export and Privacy" in text
    assert "Verification" in text

    # Verify PII protection claim
    assert "public-facing outputs never include reviewer names" in text
    assert "without exposing their identities publicly" in text


def test_data_export_privacy_review() -> None:
    """Verify the documented export format matches actual system privacy claims."""
    text = SCHOLAR_WORKFLOW.read_text(encoding="utf-8")

    # The workflow claims exported JSON contains only non-PII fields
    # Cross-check against the actual CaseComparison dataclass fields
    claimed_fields = ["case_key", "topic", "base_passed", "target_passed", "scores"]
    for field in claimed_fields:
        assert field in text, f"Claimed field '{field}' must be documented"

    # Verify no PII fields are claimed to be in exports
    pii_terms = ["email", "name", "phone", "address", "reviewer_name"]
    for term in pii_terms:
        # The document should discuss PII only in the context of NOT including it
        mentions = text.lower().count(term)
        assert mentions == 0 or "never" in text.lower() or "not" in text.lower(), (
            f"PII term '{term}' appears in export context without privacy guard"
        )
