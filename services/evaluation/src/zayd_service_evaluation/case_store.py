"""Persistence and visibility enforcement for evaluation case contracts."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session
from zayd_common.database.models import AuditLog, EvaluationCase, EvaluationDataset
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.rbac import Permission

from .schema import EvaluationCaseContract, EvaluationVisibility


class EvaluationCaseStoreError(Exception):
    def __init__(self, code: str, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.code, self.message, self.status_code = code, message, status_code


@dataclass(frozen=True)
class DatasetCreate:
    name: str
    version: str
    visibility: EvaluationVisibility
    license_status: str
    manifest: dict[str, object]


class EvaluationCaseStore:
    def __init__(self, uow: SQLAlchemyUnitOfWork) -> None:
        self.uow = uow

    def create_dataset(
        self,
        request: DatasetCreate,
        *,
        actor_user_id: UUID,
        permissions: frozenset[str],
        trace_id: str | None = None,
    ) -> EvaluationDataset:
        _require(permissions, Permission.EVALUATIONS_MANAGE)
        name, version = request.name.strip(), request.version.strip()
        if not name or not version:
            raise EvaluationCaseStoreError(
                "EVALUATION_INPUT_INVALID", "Dataset name and version are required."
            )
        with self.uow:
            session = self._session()
            if session.scalar(
                select(EvaluationDataset).where(
                    EvaluationDataset.name == name, EvaluationDataset.version == version
                )
            ):
                raise EvaluationCaseStoreError(
                    "EVALUATION_DATASET_EXISTS", "Dataset version already exists.", status_code=409
                )
            dataset = EvaluationDataset(
                name=name,
                version=version,
                visibility=request.visibility.value,
                license_status=request.license_status,
                manifest_json=dict(request.manifest),
                created_by=actor_user_id,
            )
            session.add(dataset)
            session.flush()
            _audit(
                session,
                actor_user_id,
                "evaluation.dataset.create",
                dataset.id,
                trace_id,
                {"name": name, "version": version, "visibility": request.visibility.value},
            )
            self.uow.commit()
            return dataset

    def create_case(
        self,
        dataset_id: UUID,
        contract: EvaluationCaseContract,
        *,
        actor_user_id: UUID,
        permissions: frozenset[str],
        trace_id: str | None = None,
    ) -> EvaluationCase:
        _require(permissions, Permission.EVALUATIONS_MANAGE)
        with self.uow:
            session = self._session()
            dataset = session.get(EvaluationDataset, dataset_id)
            if dataset is None:
                raise EvaluationCaseStoreError(
                    "EVALUATION_DATASET_NOT_FOUND", "Dataset was not found.", status_code=404
                )
            if (
                dataset.visibility == "public"
                and contract.visibility != EvaluationVisibility.PUBLIC
            ):
                raise EvaluationCaseStoreError(
                    "EVALUATION_VISIBILITY_INVALID",
                    "Public datasets may contain only public cases.",
                )
            existing = session.scalar(
                select(EvaluationCase).where(
                    EvaluationCase.dataset_id == dataset_id,
                    EvaluationCase.case_key == contract.case_key,
                )
            )
            if existing:
                raise EvaluationCaseStoreError(
                    "EVALUATION_CASE_EXISTS", "Case key already exists in dataset.", status_code=409
                )
            sources = [source.model_dump(mode="json") for source in contract.sources]
            row = EvaluationCase(
                dataset_id=dataset_id,
                case_key=contract.case_key,
                schema_version=contract.schema_version,
                case_type=contract.case_type.value,
                visibility=contract.visibility.value,
                reviewer_status=contract.reviewer_status.value,
                reviewed_by=contract.reviewed_by,
                question=contract.question,
                choices_json=[choice.model_dump() for choice in contract.choices],
                expected_citations=[
                    {"citation_id": str(value)}
                    for value in contract.expected_behavior.required_citation_ids
                ],
                expected_behavior=contract.expected_behavior.model_dump(mode="json"),
                source_references=sources,
                license_metadata={
                    "sources": [
                        {
                            "source_id": item["source_id"],
                            "license_name": item["license_name"],
                            "license_status": item["license_status"],
                            "redistributable": item["redistributable"],
                        }
                        for item in sources
                    ]
                },
                provenance_json=dict(contract.provenance),
                risk_level=contract.risk_level,
            )
            session.add(row)
            session.flush()
            _audit(
                session,
                actor_user_id,
                "evaluation.case.create",
                row.id,
                trace_id,
                {
                    "dataset_id": str(dataset_id),
                    "case_key": row.case_key,
                    "case_type": row.case_type,
                    "visibility": row.visibility,
                    "schema_version": row.schema_version,
                },
            )
            self.uow.commit()
            return row

    def list_cases(self, dataset_id: UUID, *, permissions: frozenset[str]) -> list[EvaluationCase]:
        can_read_private = Permission.EVALUATIONS_READ.value in permissions
        with self.uow:
            stmt = select(EvaluationCase).where(EvaluationCase.dataset_id == dataset_id)
            if not can_read_private:
                stmt = stmt.where(
                    EvaluationCase.visibility == "public",
                    EvaluationCase.reviewer_status == "approved",
                )
            rows = list(self._session().scalars(stmt.order_by(EvaluationCase.case_key)).all())
            self.uow.commit()
            return rows

    def _session(self) -> Session:
        if self.uow.session is None:
            raise RuntimeError("Database session not initialised in UoW.")
        return self.uow.session


def _require(permissions: frozenset[str], permission: Permission) -> None:
    if permission.value not in permissions:
        raise EvaluationCaseStoreError("EVALUATION_FORBIDDEN", "Forbidden.", status_code=403)


def _audit(
    session: Session,
    actor: UUID,
    action: str,
    resource_id: UUID,
    trace_id: str | None,
    after: dict[str, object],
) -> None:
    session.add(
        AuditLog(
            id=uuid4(),
            actor_user_id=actor,
            action=action,
            resource_type="evaluation",
            resource_id=resource_id,
            outcome="success",
            request_id=trace_id,
            trace_id=trace_id,
            before_summary={},
            after_summary=after,
            source_context={},
        )
    )
