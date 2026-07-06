from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

SCHEMA_PATH = Path(__file__).parents[1] / "schemas" / "core-domain.schema.json"

SRS_CORE_ENTITIES = {
    "User",
    "Role",
    "Permission",
    "Session",
    "Source",
    "SourceLicense",
    "Document",
    "DocumentVersion",
    "DocumentPage",
    "DocumentChunk",
    "EmbeddingRecord",
    "ReviewTask",
    "Review",
    "Approval",
    "ReviewComment",
    "Conversation",
    "Message",
    "Answer",
    "RetrievalRun",
    "RetrievalResult",
    "Citation",
    "Feedback",
    "Incident",
    "AuditLog",
    "Provider",
    "ModelConfiguration",
    "PromptVersion",
    "PolicyVersion",
    "EvaluationDataset",
    "EvaluationCase",
    "EvaluationRun",
    "EvaluationResult",
}

REQUIRED_ACCESS_PATTERNS = {
    "review_queue",
    "production_retrieval_full_text",
    "production_retrieval_vector",
    "citation_lookup",
    "conversation_history",
    "audit_resource_trace",
    "evaluation_run_results",
}

REQUIRED_SECURITY_RISKS = {
    "license",
    "embeddings",
    "audit logs",
    "provider secrets",
    "document state",
}


JsonObject = dict[str, Any]


def load_schema() -> JsonObject:
    return cast(JsonObject, json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))


def entity_field_names(entity: JsonObject) -> set[str]:
    return {cast(str, field["name"]) for field in entity["fields"]}


def reference_target(foreign_key: JsonObject) -> str:
    reference = cast(str, foreign_key["references"])
    return reference.split(".", maxsplit=1)[0]


def all_foreign_keys(schema: JsonObject) -> list[JsonObject]:
    keys: list[JsonObject] = []
    for entity in schema["entities"].values():
        keys.extend(entity.get("foreign_keys", []))
    for join_table in schema.get("join_tables", {}).values():
        keys.extend(join_table.get("foreign_keys", []))
    return keys


def all_index_names(schema: JsonObject) -> set[str]:
    indexes: set[str] = set()
    for entity in schema["entities"].values():
        indexes.update(index["name"] for index in entity.get("indexes", []))
    for join_table in schema.get("join_tables", {}).values():
        indexes.update(index["name"] for index in join_table.get("indexes", []))
    return indexes


def test_schema_covers_every_srs_core_entity() -> None:
    schema = load_schema()

    assert set(schema["entities"]) == SRS_CORE_ENTITIES


def test_every_entity_has_primary_key_timestamps_and_integrity_metadata() -> None:
    schema = load_schema()

    for entity_name, entity in schema["entities"].items():
        fields = entity_field_names(entity)

        assert entity["primary_key"], f"{entity_name} is missing a primary key"
        assert "created_at" in fields, f"{entity_name} is missing created_at"
        assert "updated_at" in fields, f"{entity_name} is missing updated_at"
        assert "unique_constraints" in entity, f"{entity_name} must document uniqueness rules"
        assert "indexes" in entity, f"{entity_name} must document indexes"
        assert "foreign_keys" in entity, f"{entity_name} must document foreign keys"
        assert "soft_delete" in entity, f"{entity_name} must document soft-delete behavior"
        assert "versioning" in entity, f"{entity_name} must document versioning behavior"


def test_foreign_keys_reference_known_entities_and_existing_columns() -> None:
    schema = load_schema()
    known_entities = set(schema["entities"])
    known_entities.update(schema.get("join_tables", {}))

    for foreign_key in all_foreign_keys(schema):
        assert reference_target(foreign_key) in known_entities, foreign_key
        assert foreign_key["columns"], foreign_key
        assert foreign_key.get("on_delete"), foreign_key

    for entity_name, entity in schema["entities"].items():
        fields = entity_field_names(entity)
        for foreign_key in entity.get("foreign_keys", []):
            for column in foreign_key["columns"]:
                assert column in fields, f"{entity_name}.{column} missing for FK {foreign_key}"


def test_license_and_document_content_are_separate_entities() -> None:
    schema = load_schema()
    document_fields = entity_field_names(schema["entities"]["Document"])
    license_fields = entity_field_names(schema["entities"]["SourceLicense"])
    version_fields = entity_field_names(schema["entities"]["DocumentVersion"])
    chunk_fields = entity_field_names(schema["entities"]["DocumentChunk"])

    assert "source_license_id" in document_fields
    assert {
        "license_name",
        "storage_permission",
        "embedding_permission",
        "redistribution",
    }.issubset(
        license_fields,
    )
    assert "extracted_text" not in document_fields
    assert "extracted_text" in version_fields
    assert "content_normalized" in chunk_fields
    assert "embedding" not in chunk_fields


def test_embedding_records_require_published_document_version_and_chunk_invariants() -> None:
    schema = load_schema()
    embedding = schema["entities"]["EmbeddingRecord"]
    fields = entity_field_names(embedding)
    invariants = "\n".join(embedding.get("invariants", [])).lower()

    assert {"document_version_id", "chunk_id", "model_configuration_id", "provider_id"}.issubset(
        fields
    )
    assert "published_document_version_required" in invariants
    assert "published_chunk_required" in invariants
    assert "license_embedding_permission_required" in invariants
    assert "chunk_version_match_required" in invariants


def test_citations_and_retrieval_results_are_traceable_to_versions_and_chunks() -> None:
    schema = load_schema()

    citation_fields = entity_field_names(schema["entities"]["Citation"])
    retrieval_result_fields = entity_field_names(schema["entities"]["RetrievalResult"])
    answer_fields = entity_field_names(schema["entities"]["Answer"])

    assert {"document_version_id", "chunk_id", "canonical_reference"}.issubset(citation_fields)
    assert {"retrieval_run_id", "document_version_id", "chunk_id", "rank"}.issubset(
        retrieval_result_fields,
    )
    assert {
        "model_configuration_id",
        "prompt_version_id",
        "policy_version_id",
        "retrieval_run_id",
    }.issubset(
        answer_fields,
    )


def test_primary_access_patterns_have_required_indexes() -> None:
    schema = load_schema()
    indexes = all_index_names(schema)
    patterns = {pattern["name"]: pattern for pattern in schema["primary_access_patterns"]}

    assert REQUIRED_ACCESS_PATTERNS.issubset(patterns)
    for pattern in patterns.values():
        missing = set(pattern["required_indexes"]) - indexes
        assert not missing, f"{pattern['name']} references missing indexes: {sorted(missing)}"


def test_schema_review_documents_security_privacy_and_migration_risks() -> None:
    schema = load_schema()
    risk_text = "\n".join(risk["risk"].lower() for risk in schema["security_and_privacy_risks"])
    mitigation_text = "\n".join(
        risk["mitigation"].lower() for risk in schema["security_and_privacy_risks"]
    )

    for keyword in REQUIRED_SECURITY_RISKS:
        assert keyword in risk_text or keyword in mitigation_text

    assert schema["migration_risks"], "migration risks must be documented"
    assert any("pgvector" in risk.lower() for risk in schema["migration_risks"])
    assert any("citext" in risk.lower() for risk in schema["migration_risks"])


def test_sensitive_fields_are_marked_and_audit_log_avoids_raw_content() -> None:
    schema = load_schema()
    sensitive_fields = [
        (entity_name, field["name"])
        for entity_name, entity in schema["entities"].items()
        for field in entity["fields"]
        if field.get("sensitive")
    ]
    audit_fields = entity_field_names(schema["entities"]["AuditLog"])

    assert sensitive_fields, "schema should mark sensitive fields explicitly"
    assert "before_summary" in audit_fields
    assert "after_summary" in audit_fields
    assert "body" not in audit_fields
    assert "password" not in audit_fields
