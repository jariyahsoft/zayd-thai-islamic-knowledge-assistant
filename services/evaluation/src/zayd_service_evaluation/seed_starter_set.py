"""Seed the Zayd-IslamicQA-TH starter evaluation set."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from zayd_common.database.models import EvaluationCase, EvaluationDataset
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.rbac import Permission

from .case_store import DatasetCreate, EvaluationCaseStore, EvaluationCaseStoreError
from .schema import EvaluationCaseContract, EvaluationVisibility

STARTER_SET_SEED_VERSION = "zayd-islamicqa-th-starter-v1"


class StarterSetSeedError(Exception):
    def __init__(self, code: str, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.code, self.message, self.status_code = code, message, status_code


@dataclass(frozen=True)
class StarterSetSeedResult:
    dataset_id: UUID
    dataset_created: bool
    created_cases: int
    skipped_cases: int
    total_cases: int


def load_starter_set_files(
    dataset_dir: Path,
    *,
    reviewed_by: UUID,
) -> tuple[DatasetCreate, tuple[EvaluationCaseContract, ...]]:
    """Load and validate starter-set JSON files.

    `reviewed_by` is injected at load time so repository JSON does not hard-code
    a production user ID. All cases must be scholar-approved before seeding.
    """
    manifest = _read_json(dataset_dir / "starter_set_manifest.json")
    public_cases = _read_json(dataset_dir / "public_cases.json")
    private_cases = _read_json(dataset_dir / "private_cases.json")

    if not isinstance(manifest, dict):
        raise StarterSetSeedError("STARTER_SET_MANIFEST_INVALID", "Manifest must be an object.")
    if not isinstance(public_cases, list) or not isinstance(private_cases, list):
        raise StarterSetSeedError("STARTER_SET_CASES_INVALID", "Case files must be arrays.")

    dataset_request = DatasetCreate(
        name=str(manifest["name"]),
        version=str(manifest["version"]),
        visibility=EvaluationVisibility(str(manifest["visibility"])),
        license_status=str(manifest["license_status"]),
        manifest=dict(manifest.get("manifest", {})),
    )

    contracts: list[EvaluationCaseContract] = []
    for raw in [*public_cases, *private_cases]:
        if not isinstance(raw, dict):
            raise StarterSetSeedError("STARTER_SET_CASE_INVALID", "Each case must be an object.")
        payload = dict(raw)
        payload["reviewed_by"] = reviewed_by
        case = EvaluationCaseContract.model_validate(payload)
        _require_reviewed(case)
        contracts.append(case)
    return dataset_request, tuple(contracts)


def seed_starter_set(
    uow: SQLAlchemyUnitOfWork,
    *,
    dataset_dir: Path,
    actor_user_id: UUID,
    reviewed_by: UUID,
    permissions: frozenset[str],
    trace_id: str | None = None,
) -> StarterSetSeedResult:
    if Permission.EVALUATIONS_MANAGE.value not in permissions:
        raise StarterSetSeedError("STARTER_SET_FORBIDDEN", "Forbidden.", status_code=403)

    dataset_request, contracts = load_starter_set_files(dataset_dir, reviewed_by=reviewed_by)
    store = EvaluationCaseStore(uow)

    dataset_created = False
    try:
        store.create_dataset(
            dataset_request,
            actor_user_id=actor_user_id,
            permissions=permissions,
            trace_id=trace_id,
        )
        dataset_created = True
    except EvaluationCaseStoreError as exc:
        if exc.code != "EVALUATION_DATASET_EXISTS":
            raise

    dataset_id = _get_dataset_id(uow, dataset_request.name, dataset_request.version)

    created = 0
    skipped = 0
    for case in contracts:
        if _case_exists(uow, dataset_id, case.case_key):
            skipped += 1
            continue
        store.create_case(
            dataset_id,
            case,
            actor_user_id=actor_user_id,
            permissions=permissions,
            trace_id=trace_id,
        )
        created += 1

    return StarterSetSeedResult(
        dataset_id=dataset_id,
        dataset_created=dataset_created,
        created_cases=created,
        skipped_cases=skipped,
        total_cases=len(contracts),
    )


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise StarterSetSeedError(
            "STARTER_SET_FILE_MISSING", f"Starter set file missing: {path.name}.", status_code=404
        ) from exc
    except json.JSONDecodeError as exc:
        raise StarterSetSeedError(
            "STARTER_SET_JSON_INVALID", f"Starter set JSON invalid: {path.name}."
        ) from exc


def _require_reviewed(case: EvaluationCaseContract) -> None:
    if case.reviewer_status.value != "approved" or case.reviewed_by is None:
        raise StarterSetSeedError(
            "STARTER_SET_REVIEW_REQUIRED",
            "Starter-set cases must be approved by a human scholar reviewer.",
        )
    for source in case.sources:
        if not source.license_name.strip() or not source.license_status.strip():
            raise StarterSetSeedError(
                "STARTER_SET_LICENSE_INVALID",
                "Every case source must include license name and status.",
            )
        if not source.canonical_reference.strip():
            raise StarterSetSeedError(
                "STARTER_SET_SOURCE_INVALID",
                "Every case source must include a canonical reference.",
            )


def _get_dataset_id(uow: SQLAlchemyUnitOfWork, name: str, version: str) -> UUID:
    with uow:
        session = uow.session
        if session is None:
            raise RuntimeError("Database session not initialised in UoW.")
        dataset = session.scalar(
            select(EvaluationDataset).where(
                EvaluationDataset.name == name,
                EvaluationDataset.version == version,
            )
        )
        if dataset is None:
            raise StarterSetSeedError(
                "STARTER_SET_DATASET_NOT_FOUND",
                "Dataset was not found after duplicate detection.",
                status_code=404,
            )
        dataset_id = dataset.id
        uow.commit()
        return dataset_id


def _case_exists(uow: SQLAlchemyUnitOfWork, dataset_id: UUID, case_key: str) -> bool:
    with uow:
        session = uow.session
        if session is None:
            raise RuntimeError("Database session not initialised in UoW.")
        exists = session.scalar(
            select(EvaluationCase.id).where(
                EvaluationCase.dataset_id == dataset_id,
                EvaluationCase.case_key == case_key,
            )
        )
        uow.commit()
        return exists is not None
