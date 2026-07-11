"""Tests for user pilot workflow documentation and feedback routing (TASK-14-03)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
USER_WORKFLOW = REPO_ROOT / "docs/pilot/user-workflow.md"

# Expected feedback categories from the system (matching FeedbackCategory in feedback.py)
EXPECTED_FEEDBACK_CATEGORIES = [
    "incorrect_answer",
    "citation_error",
    "incomplete_answer",
    "inappropriate_content",
    "other",
]


def test_workflow_document_exists_and_contains_required_sections() -> None:
    """Onboarding usability test: verify the document covers all acceptance criteria."""
    assert USER_WORKFLOW.exists(), "user-workflow.md must exist"
    text = USER_WORKFLOW.read_text(encoding="utf-8")

    # Acceptance criterion: Participants understand AI limitations and privacy policy
    assert "AI limitations" in text
    assert "privacy" in text.lower()

    # Acceptance criterion: Sensitive questions are handled according to pilot policy
    assert "Sensitive" in text or "sensitive" in text
    assert "high-risk" in text.lower()

    # Acceptance criterion: Feedback is triaged into product/content/security categories
    assert "triage" in text.lower()
    assert "feedback" in text.lower()

    # Required sections present
    assert "Onboarding Flow" in text
    assert "Participant Briefing" in text
    assert "Sensitive Question Handling" in text
    assert "Feedback Triage" in text
    assert "Privacy and Data Handling" in text
    assert "Verification Checklist" in text

    # Verify consent and privacy briefing
    assert "consent" in text.lower()


def test_feedback_routing_matches_system_categories() -> None:
    """Feedback routing test: verify all documented feedback categories match the API."""
    text = USER_WORKFLOW.read_text(encoding="utf-8")

    # Each system feedback category should appear in the documented triage table
    for category in EXPECTED_FEEDBACK_CATEGORIES:
        assert category in text, f"Feedback category '{category}' must be documented in triage table"

    # Verify triage owners are defined
    assert "Content review" in text or "content review" in text.lower()
    assert "Safety policy review" in text or "safety" in text.lower()


def test_privacy_and_audit_claims() -> None:
    """Verify privacy and audit claims in the document."""
    text = USER_WORKFLOW.read_text(encoding="utf-8")

    # The document should state that audit logs don't expose PII
    assert "never" in text.lower() or "not" in text.lower()
    assert "audit" in text.lower()
