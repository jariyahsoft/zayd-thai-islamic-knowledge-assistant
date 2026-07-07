"""Decision-table tests for the deterministic license policy engine."""

from datetime import date
from itertools import product
from uuid import uuid4

import pytest
from zayd_common.license_policy import (
    EPHEMERAL_CACHE_TTL_SECONDS,
    LICENSE_POLICY_ENGINE_VERSION,
    LicensePolicyInput,
    evaluate_license_policy,
)


def _policy_input(**overrides: object) -> LicensePolicyInput:
    values = {
        "license_id": uuid4(),
        "source_id": uuid4(),
        "license_version": "2026-01",
        "status": "persistent_redistributable",
        "storage_permission": "allowed",
        "embedding_permission": "allowed",
        "commercial_use": "allowed",
        "redistribution": "allowed",
        "attribution_required": True,
        "attribution_template": "Required attribution.",
        "valid_from": date(2026, 1, 1),
        "valid_until": date(2027, 1, 1),
    }
    values.update(overrides)
    return LicensePolicyInput(**values)


@pytest.mark.parametrize(
    ("workflow", "expected_allowed"),
    [
        ("ingestion", True),
        ("retrieval", True),
        ("export", True),
    ],
)
def test_permissive_license_allows_supported_workflows(
    workflow: str,
    expected_allowed: bool,
) -> None:
    decision = evaluate_license_policy(
        _policy_input(),
        workflow=workflow,
        today=date(2026, 7, 1),
    )

    assert decision.workflow_allowed is expected_allowed
    assert decision.policy_version == LICENSE_POLICY_ENGINE_VERSION
    assert decision.source_license_version == "2026-01"
    assert decision.llm_override_allowed is False
    assert "WORKFLOW_ALLOWED" in decision.reason_codes
    assert all(action.source_license_version == "2026-01" for action in decision.actions)


@pytest.mark.parametrize("status", ["unknown", "prohibited", "expired"])
def test_blocking_statuses_deny_all_operational_workflows(status: str) -> None:
    for workflow in ("ingestion", "retrieval", "export"):
        decision = evaluate_license_policy(
            _policy_input(status=status),
            workflow=workflow,
            today=date(2026, 7, 1),
        )

        assert decision.workflow_allowed is False
        assert f"LICENSE_STATUS_{status.upper()}" in decision.reason_codes


def test_cache_only_content_allows_bounded_cache_but_denies_persistent_workflows() -> None:
    decision = evaluate_license_policy(
        _policy_input(
            status="ephemeral_cache_only",
            storage_permission="prohibited",
            embedding_permission="prohibited",
            redistribution="prohibited",
        ),
        workflow="retrieval",
        today=date(2026, 7, 1),
    )

    actions = {action.action: action for action in decision.actions}
    assert decision.workflow_allowed is False
    assert actions["cache"].allowed is True
    assert actions["cache"].max_cache_ttl_seconds == EPHEMERAL_CACHE_TTL_SECONDS
    assert actions["persistent_storage"].allowed is False
    assert actions["embedding"].allowed is False
    assert "STATUS_DOES_NOT_ALLOW_PERSISTENT_STORAGE" in decision.reason_codes


def test_expiry_and_not_yet_valid_dates_fail_closed() -> None:
    expired = evaluate_license_policy(
        _policy_input(valid_until=date(2026, 6, 30)),
        workflow="retrieval",
        today=date(2026, 7, 1),
    )
    not_yet_valid = evaluate_license_policy(
        _policy_input(valid_from=date(2026, 7, 2)),
        workflow="retrieval",
        today=date(2026, 7, 1),
    )

    assert expired.workflow_allowed is False
    assert "LICENSE_DATE_EXPIRED" in expired.reason_codes
    assert not_yet_valid.workflow_allowed is False
    assert "LICENSE_NOT_YET_VALID" in not_yet_valid.reason_codes


def test_private_persistent_license_allows_retrieval_but_denies_export() -> None:
    retrieval = evaluate_license_policy(
        _policy_input(status="persistent_private", redistribution="prohibited"),
        workflow="retrieval",
        today=date(2026, 7, 1),
    )
    export = evaluate_license_policy(
        _policy_input(status="persistent_private", redistribution="prohibited"),
        workflow="export",
        today=date(2026, 7, 1),
    )

    assert retrieval.workflow_allowed is True
    assert export.workflow_allowed is False
    assert "STATUS_DOES_NOT_ALLOW_REDISTRIBUTION" in export.reason_codes


def test_attribution_required_without_template_denies_workflow() -> None:
    decision = evaluate_license_policy(
        _policy_input(attribution_required=True, attribution_template=None),
        workflow="ingestion",
        today=date(2026, 7, 1),
    )

    assert decision.workflow_allowed is False
    assert "ATTRIBUTION_TEMPLATE_MISSING" in decision.reason_codes


def test_invalid_workflow_is_denied_with_reason_code() -> None:
    decision = evaluate_license_policy(
        _policy_input(),
        workflow="llm_override",
        today=date(2026, 7, 1),
    )

    assert decision.workflow_allowed is False
    assert decision.llm_override_allowed is False
    assert decision.reason_codes[0] == "WORKFLOW_INVALID"


def test_forbidden_permission_combinations_never_allow_retrieval() -> None:
    statuses = ("unknown", "review_required", "ephemeral_cache_only", "prohibited", "expired")
    permission_states = ("unknown", "allowed", "conditional", "prohibited")

    for status, storage_permission, embedding_permission in product(
        statuses,
        permission_states,
        permission_states,
    ):
        decision = evaluate_license_policy(
            _policy_input(
                status=status,
                storage_permission=storage_permission,
                embedding_permission=embedding_permission,
            ),
            workflow="retrieval",
            today=date(2026, 7, 1),
        )

        assert decision.workflow_allowed is False


def test_retrieval_requires_storage_and_embedding_permissions_for_persistent_statuses() -> None:
    permission_states = ("unknown", "prohibited")

    for status, denied_state in product(
        ("persistent_private", "persistent_redistributable"),
        permission_states,
    ):
        denied_storage = evaluate_license_policy(
            _policy_input(status=status, storage_permission=denied_state),
            workflow="retrieval",
            today=date(2026, 7, 1),
        )
        denied_embedding = evaluate_license_policy(
            _policy_input(status=status, embedding_permission=denied_state),
            workflow="retrieval",
            today=date(2026, 7, 1),
        )

        assert denied_storage.workflow_allowed is False
        assert "STORAGE_PERMISSION_DENIED" in denied_storage.reason_codes
        assert denied_embedding.workflow_allowed is False
        assert "EMBEDDING_PERMISSION_DENIED" in denied_embedding.reason_codes
