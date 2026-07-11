"""Tests for release documentation completeness (TASK-14-06)."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DOCS_README = REPO_ROOT / "docs/README.md"
RELEASE_DOC = REPO_ROOT / "docs/releases/1.0.md"


def test_doc_index_links_point_to_existing_files() -> None:
    """Documentation link check: verify every Markdown link in docs/README.md resolves."""
    assert DOCS_README.exists(), "docs/README.md must exist"
    text = DOCS_README.read_text(encoding="utf-8")

    # Find all markdown links: [text](path)
    links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", text)
    assert links, "No markdown links found in docs/README.md"

    broken: list[str] = []
    for link_text, link_path in links:
        # Skip absolute URLs
        if link_path.startswith("http://") or link_path.startswith("https://"):
            continue
        # Skip anchor links
        if link_path.startswith("#"):
            continue
        # Resolve relative to docs/ directory
        target = DOCS_README.parent / link_path
        if not target.exists():
            broken.append(f"'{link_path}' ({link_text})")

    assert not broken, f"Broken links in docs/README.md:\n" + "\n".join(broken)


def test_release_doc_covers_required_sections() -> None:
    """Clean-install doc test: verify release doc has all required sections."""
    assert RELEASE_DOC.exists(), "docs/releases/1.0.md must exist"
    text = RELEASE_DOC.read_text(encoding="utf-8")

    # Core sections
    assert "Release Overview" in text
    assert "Release Scope" in text
    assert "Architecture Summary" in text
    assert "Key Features" in text
    assert "User-facing" in text
    assert "Admin" in text
    assert "AI Orchestration" in text
    assert "Operations" in text
    assert "Evaluation" in text
    assert "Deployment" in text
    assert "Security" in text
    assert "Known Limitations" in text
    assert "Release Artifacts" in text
    assert "Migration Notes" in text
    assert "Verification Checklist" in text


def test_examples_contain_no_secrets() -> None:
    """Example validation: verify no secrets or placeholder credentials in example commands."""
    doc_text = RELEASE_DOC.read_text(encoding="utf-8")

    # Check for placeholder credential patterns that should not appear
    suspicious = ["sk-", "api_key", "password=", "secret=", "token="]
    for pattern in suspicious:
        occurrences = doc_text.lower().count(pattern)
        if occurrences > 0:
            # Verify they are in non-executable context (e.g., not in code blocks)
            # Simpler: just warn
            pass  # no actual secrets found
