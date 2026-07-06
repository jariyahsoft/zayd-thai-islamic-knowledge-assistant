from pydantic import BaseModel
from zayd_common.enums import DocumentStatus, EvidenceStatus, ReviewTaskStatus


def test_enum_serialization() -> None:
    class DummyModel(BaseModel):
        status: DocumentStatus
        evidence: EvidenceStatus

    m = DummyModel(status=DocumentStatus.PUBLISHED, evidence=EvidenceStatus.SUFFICIENT)
    assert m.status == DocumentStatus.PUBLISHED
    assert m.evidence == EvidenceStatus.SUFFICIENT
    assert m.model_dump() == {"status": "published", "evidence": "SUFFICIENT"}


def test_enum_values() -> None:
    assert DocumentStatus.DRAFT.value == "draft"
    assert ReviewTaskStatus.OPEN.value == "open"
    assert EvidenceStatus.SUFFICIENT.value == "SUFFICIENT"
