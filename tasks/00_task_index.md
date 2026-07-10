# Zayd 1.0 — Task Index

## Document Information

| Field | Value |
|---|---|
| Project | Zayd — Thai Islamic Knowledge Assistant |
| Version | Task Plan 1.1 |
| Source | PRD 1.1 and SRS 1.1 |
| Development model | Greenfield Core + Selective Open-source Reuse |
| Repository model | Open-source monorepo |
| Primary platform | Mobile-first Web/PWA |
| Total tasks | 95 |

## Status Definitions

| Status | Meaning |
|---|---|
| `TODO` | Defined but dependencies are not complete |
| `READY` | All dependencies are complete and work may start |
| `IN_PROGRESS` | Actively being implemented |
| `BLOCKED` | Cannot continue due to a documented blocker |
| `IN_REVIEW` | Implementation is awaiting review |
| `CHANGES_REQUESTED` | Review found changes that must be made |
| `DONE` | Acceptance criteria and required checks are complete |
| `CANCELLED` | Task was intentionally removed from scope |

## Model Tier Definitions

| Tier | Intended use |
|---|---|
| Tier S | Architecture, security, migrations, RAG and critical cross-service reasoning |
| Tier A | Production implementation, APIs, integrations, Docker and CI |
| Tier B | Routine implementation, UI, documentation and clear-pattern tests |
| Tier C | Mechanical edits, templates, formatting and repetitive changes |

## Execution Rules

1. Read the PRD, SRS and this index before starting work.
2. Start only tasks with status `READY`.
3. Do not place secrets, production data or restricted religious datasets in the repository.
4. Every task must include tests appropriate to its risk level.
5. Update the task file completion report before marking it `DONE`.
6. Create one focused commit per completed task.
7. Record third-party code provenance in `CODE_PROVENANCE.md`.
8. Religious content and dataset changes require content and license review.
9. When a task becomes `DONE`, update dependent tasks to `READY` only when all dependencies are complete.

## Current Task Board

| Task ID | Task | Tier | Status | Dependencies | Path |
|---|---|---:|---|---|---|
| TASK-00-01 | Initialize Git Repository | B | DONE | None | `00_open_source/00-01_initialize_git_repository.md` |
| TASK-00-02 | Add Open-source License Files | A | DONE | TASK-00-01 | `00_open_source/00-02_add_open_source_license_files.md` |
| TASK-00-03 | Add Community Governance Files | B | DONE | TASK-00-02 | `00_open_source/00-03_add_community_governance_files.md` |
| TASK-00-04 | Configure GitHub Templates | C | DONE | TASK-00-03 | `00_open_source/00-04_configure_github_templates.md` |
| TASK-01-01 | Create Monorepo Structure | S | DONE | TASK-00-01 through TASK-00-04 must be `DONE`. | `01_foundation/01-01_create_monorepo_structure.md` |
| TASK-01-02 | Configure TypeScript Workspaces | A | DONE | TASK-01-01 | `01_foundation/01-02_configure_typescript_workspaces.md` |
| TASK-01-03 | Initialize Python Services | A | DONE | TASK-01-01 | `01_foundation/01-03_initialize_python_services.md` |
| TASK-01-04 | Create Development Docker Compose | A | DONE | TASK-01-02, TASK-01-03 | `01_foundation/01-04_create_development_docker_compose.md` |
| TASK-01-05 | Environment Configuration Validation | A | DONE | TASK-01-04 | `01_foundation/01-05_environment_configuration_validation.md` |
| TASK-01-06 | Add Makefile and Developer Commands | B | DONE | TASK-01-05 | `01_foundation/01-06_add_makefile_and_developer_commands.md` |
| TASK-02-01 | Design Core Database Schema | S | DONE | EPIC-01 complete | `02_database/02-01_design_core_database_schema.md` |
| TASK-02-02 | Create Initial Database Migration | S | DONE | TASK-02-01 | `02_database/02-02_create_initial_database_migration.md` |
| TASK-02-03 | Implement Domain Enums and State Machines | A | DONE | TASK-02-02 | `02_database/02-03_implement_domain_enums_and_state_machines.md` |
| TASK-02-04 | Add Repository and Unit-of-Work Layer | A | DONE | TASK-02-03 | `02_database/02-04_add_repository_and_unit_of_work_layer.md` |
| TASK-02-05 | Add Demo Seed Data | B | DONE | TASK-02-04 | `02_database/02-05_add_demo_seed_data.md` |
| TASK-03-01 | Implement User Authentication | S | DONE | EPIC-02 complete | `03_auth/03-01_implement_user_authentication.md` |
| TASK-03-02 | Implement Guest Sessions | A | DONE | TASK-03-01 | `03_auth/03-02_implement_guest_sessions.md` |
| TASK-03-03 | Implement RBAC | S | DONE | TASK-03-01 | `03_auth/03-03_implement_rbac.md` |
| TASK-03-04 | Implement MFA for Privileged Users | A | DONE | TASK-03-03 | `03_auth/03-04_implement_mfa_for_privileged_users.md` |
| TASK-03-05 | Implement Immutable Audit Log | S | DONE | TASK-03-03 | `03_auth/03-05_implement_immutable_audit_log.md` |
| TASK-04-01 | Source Registry API | A | DONE | EPIC-03 complete | `04_data_governance/04-01_source_registry_api.md` |
| TASK-04-02 | License Registry API | S | DONE | TASK-04-01 | `04_data_governance/04-02_license_registry_api.md` |
| TASK-04-03 | License Policy Engine | S | DONE | TASK-04-02 | `04_data_governance/04-03_license_policy_engine.md` |
| TASK-04-04 | Source and License Admin UI | A | DONE | TASK-04-03 | `04_data_governance/04-04_source_and_license_admin_ui.md` |
| TASK-05-01 | Document Upload API | A | DONE | EPIC-04 complete | `05_ingestion/05-01_document_upload_api.md` |
| TASK-05-02 | Object Storage Integration | A | DONE | TASK-05-01 | `05_ingestion/05-02_object_storage_integration.md` |
| TASK-05-03 | Malware Scan Pipeline | A | DONE | TASK-05-02 | `05_ingestion/05-03_malware_scan_pipeline.md` |
| TASK-05-04 | Document Parser Framework | S | DONE | TASK-05-03 | `05_ingestion/05-04_document_parser_framework.md` |
| TASK-05-05 | Thai and Arabic Text Normalization | S | DONE | TASK-05-04 | `05_ingestion/05-05_thai_and_arabic_text_normalization.md` |
| TASK-05-06 | Metadata Extraction Service | A | DONE | TASK-05-05 | `05_ingestion/05-06_metadata_extraction_service.md` |
| TASK-05-07 | Create Review Task Automatically | A | DONE | TASK-05-06 | `05_ingestion/05-07_create_review_task_automatically.md` |
| TASK-06-01 | Review Queue API | A | DONE | EPIC-05 complete | `06_review/06-01_review_queue_api.md` |
| TASK-06-02 | Document Review API | S | DONE | TASK-06-01 | `06_review/06-02_document_review_api.md` |
| TASK-06-03 | Scholar Approval Workflow | S | DONE | TASK-06-02 | `06_review/06-03_scholar_approval_workflow.md` |
| TASK-06-04 | Document Publishing Service | S | DONE | TASK-06-03 | `06_review/06-04_document_publishing_service.md` |
| TASK-06-05 | Suspend and Rollback Published Documents | S | DONE | TASK-06-04 | `06_review/06-05_suspend_and_rollback_published_documents.md` |
| TASK-07-01 | Chunking Framework | S | DONE | EPIC-06 complete | `07_retrieval/07-01_chunking_framework.md` |
| TASK-07-02 | Embedding Provider Interface | A | DONE | TASK-07-01 | `07_retrieval/07-02_embedding_provider_interface.md` |
| TASK-07-03 | Full-text Search | A | DONE | TASK-07-01 | `07_retrieval/07-03_full_text_search.md` |
| TASK-07-04 | Vector Search with pgvector | S | DONE | TASK-07-02 | `07_retrieval/07-04_vector_search_with_pgvector.md` |
| TASK-07-05 | Hybrid Search | S | DONE | TASK-07-03, TASK-07-04 | `07_retrieval/07-05_hybrid_search.md` |
| TASK-07-06 | Multilingual Query Expansion | S | DONE | TASK-07-05 | `07_retrieval/07-06_multilingual_query_expansion.md` |
| TASK-07-07 | Reranker Interface | A | DONE | TASK-07-05 | `07_retrieval/07-07_reranker_interface.md` |
| TASK-07-08 | Evidence Sufficiency Engine | S | DONE | TASK-07-06, TASK-07-07 | `07_retrieval/07-08_evidence_sufficiency_engine.md` |
| TASK-08-01 | Provider SDK | S | DONE | EPIC-07 complete | `08_orchestrator/08-01_provider_sdk.md` |
| TASK-08-02 | OpenAI-compatible LLM Adapter | A | DONE | TASK-08-01 | `08_orchestrator/08-02_openai_compatible_llm_adapter.md` |
| TASK-08-03 | Local Ollama and vLLM Adapter | A | DONE | TASK-08-01 | `08_orchestrator/08-03_local_ollama_and_vllm_adapter.md` |
| TASK-08-04 | Question Classification | S | DONE | TASK-08-02 or TASK-08-03 | `08_orchestrator/08-04_question_classification.md` |
| TASK-08-05 | Risk Policy Engine | S | DONE | TASK-08-04 | `08_orchestrator/08-05_risk_policy_engine.md` |
| TASK-08-06 | Answer Orchestration Workflow | S | DONE | TASK-07-08, TASK-08-05 | `08_orchestrator/08-06_answer_orchestration_workflow.md` |
| TASK-08-07 | Citation Registry | S | DONE | TASK-06-04 | `08_orchestrator/08-07_citation_registry.md` |
| TASK-08-08 | Citation Verification Engine | S | DONE | TASK-08-06, TASK-08-07 | `08_orchestrator/08-08_citation_verification_engine.md` |
| TASK-08-09 | Prompt Version Management | A | DONE | TASK-08-06 | `08_orchestrator/08-09_prompt_version_management.md` |
| TASK-08-10 | Streaming Chat API | A | DONE | TASK-08-08, TASK-08-09 | `08_orchestrator/08-10_streaming_chat_api.md` |
| TASK-09-01 | User Application Shell | A | DONE | EPIC-01 complete | `09_user_web/09-01_user_application_shell.md` |
| TASK-09-02 | Chat Interface | A | DONE | TASK-08-10, TASK-09-01 | `09_user_web/09-02_chat_interface.md` |
| TASK-09-03 | Citation Cards and Source Detail | A | DONE | TASK-08-07, TASK-09-02 | `09_user_web/09-03_citation_cards_and_source_detail.md` |
| TASK-09-04 | Madhhab and Answer Preferences | B | DONE | TASK-09-01 | `09_user_web/09-04_madhhab_and_answer_preferences.md` |
| TASK-09-05 | Conversation History | A | DONE | TASK-03-01, TASK-09-02 | `09_user_web/09-05_conversation_history.md` |
| TASK-09-06 | Saved Answers | B | DONE | TASK-09-03 | `09_user_web/09-06_saved_answers.md` |
| TASK-09-07 | User Feedback Form | B | DONE | TASK-11-01 | `09_user_web/09-07_user_feedback_form.md` |
| TASK-10-01 | Reviewer Dashboard | A | DONE | EPIC-06 complete | `10_admin_reviewer/10-01_reviewer_dashboard.md` |
| TASK-10-02 | Document Review Workspace | S | DONE | TASK-06-02, TASK-10-01 | `10_admin_reviewer/10-02_document_review_workspace.md` |
| TASK-10-03 | Scholar Approval Workspace | A | DONE | TASK-06-03, TASK-10-02 | `10_admin_reviewer/10-03_scholar_approval_workspace.md` |
| TASK-10-04 | Admin Dashboard | A | DONE | TASK-13-03 | `10_admin_reviewer/10-04_admin_dashboard.md` |
| TASK-10-05 | Provider and Model Management UI | A | DONE | TASK-08-01, TASK-03-05 | `10_admin_reviewer/10-05_provider_and_model_management_ui.md` |
| TASK-10-06 | User and Role Management UI | A | DONE | TASK-03-03 | `10_admin_reviewer/10-06_user_and_role_management_ui.md` |
| TASK-11-01 | Feedback API | A | DONE | EPIC-08 complete | `11_feedback/11-01_feedback_api.md` |
| TASK-11-02 | Feedback Review Queue | A | DONE | TASK-11-01 | `11_feedback/11-02_feedback_review_queue.md` |
| TASK-11-03 | Incident Management | S | DONE | TASK-11-02, TASK-06-05 | `11_feedback/11-03_incident_management.md` |
| TASK-11-04 | Answer Invalidation | S | DONE | TASK-11-03, TASK-08-07 | `11_feedback/11-04_answer_invalidation.md` |
| TASK-11-05 | Convert Incident to Regression Test | A | BLOCKED | TASK-11-03, EPIC-12 | `11_feedback/11-05_convert_incident_to_regression_test.md` |
| TASK-12-01 | Evaluation Data Schema | S | DONE | EPIC-02 complete | `12_evaluation/12-01_evaluation_data_schema.md` |
| TASK-12-02 | Benchmark Runner | S | DONE | TASK-12-01, EPIC-08 | `12_evaluation/12-02_benchmark_runner.md` |
| TASK-12-03 | Retrieval Metrics | A | DONE | TASK-12-02 | `12_evaluation/12-03_retrieval_metrics.md` |
| TASK-12-04 | Citation Metrics | S | DONE | TASK-12-02 | `12_evaluation/12-04_citation_metrics.md` |
| TASK-12-05 | Safety and Abstention Metrics | S | DONE | TASK-12-02 | `12_evaluation/12-05_safety_and_abstention_metrics.md` |
| TASK-12-06 | Create Zayd-IslamicQA-TH Starter Set | S + Human Scholar Review | DONE | TASK-12-01 | `12_evaluation/12-06_create_zayd_islamicqa_th_starter_set.md` |
| TASK-12-07 | Evaluation Dashboard | A | DONE | TASK-12-03, TASK-12-04, TASK-12-05 | `12_evaluation/12-07_evaluation_dashboard.md` |
| TASK-13-01 | Central Logging and Request IDs | A | DONE | EPIC-01 complete | `13_operations/13-01_central_logging_and_request_ids.md` |
| TASK-13-02 | OpenTelemetry Instrumentation | A | DONE | TASK-13-01 | `13_operations/13-02_opentelemetry_instrumentation.md` |
| TASK-13-03 | Metrics and Dashboards | A | DONE | TASK-13-02 | `13_operations/13-03_metrics_and_dashboards.md` |
| TASK-13-04 | Security Hardening | S | DONE | All core MVP epics | `13_operations/13-04_security_hardening.md` |
| TASK-13-05 | CI Pipeline | A | DONE | EPIC-01 complete | `13_operations/13-05_ci_pipeline.md` |
| TASK-13-06 | Software Bill of Materials | B | TODO | TASK-13-05 | `13_operations/13-06_software_bill_of_materials.md` |
| TASK-13-07 | Backup and Restore | S | TODO | EPIC-02, TASK-05-02 | `13_operations/13-07_backup_and_restore.md` |
| TASK-13-08 | Minimal Self-host Profile | A | TODO | All MVP epics | `13_operations/13-08_minimal_self_host_profile.md` |
| TASK-13-09 | Production Deployment Profile | S | TODO | TASK-13-08 | `13_operations/13-09_production_deployment_profile.md` |
| TASK-14-01 | Pilot Environment | A | TODO | EPIC-13 complete | `14_release/14-01_pilot_environment.md` |
| TASK-14-02 | Scholar Pilot Workflow | B | TODO | EPIC-12, TASK-14-01 | `14_release/14-02_scholar_pilot_workflow.md` |
| TASK-14-03 | User Pilot Workflow | B | TODO | TASK-14-01 | `14_release/14-03_user_pilot_workflow.md` |
| TASK-14-04 | Performance and Load Test | A | TODO | TASK-14-01 | `14_release/14-04_performance_and_load_test.md` |
| TASK-14-05 | Security Review and Penetration Test | S + Human Security Review | TODO | TASK-13-04, TASK-14-01 | `14_release/14-05_security_review_and_penetration_test.md` |
| TASK-14-06 | Release Documentation | B | TODO | All epics | `14_release/14-06_release_documentation.md` |
| TASK-14-07 | Zayd 1.0 Release | S | TODO | TASK-14-02, TASK-14-03, TASK-14-04, TASK-14-05, TASK-14-06 | `14_release/14-07_zayd_1_0_release.md` |

## Epic Summary

| Epic | Name | Tasks | Completion Gate |
|---|---|---:|---|
| EPIC-00 | Open-source Foundation | 4 | All task acceptance criteria, tests, security/license checks and documentation are complete. |
| EPIC-01 | Monorepo and Development Environment | 6 | All task acceptance criteria, tests, security/license checks and documentation are complete. |
| EPIC-02 | Database and Core Domain | 5 | All task acceptance criteria, tests, security/license checks and documentation are complete. |
| EPIC-03 | Authentication, RBAC and Audit | 5 | All task acceptance criteria, tests, security/license checks and documentation are complete. |
| EPIC-04 | Source and License Registry | 4 | All task acceptance criteria, tests, security/license checks and documentation are complete. |
| EPIC-05 | Document Ingestion | 7 | All task acceptance criteria, tests, security/license checks and documentation are complete. |
| EPIC-06 | Review and Publishing Workflow | 5 | All task acceptance criteria, tests, security/license checks and documentation are complete. |
| EPIC-07 | Retrieval Engine | 8 | All task acceptance criteria, tests, security/license checks and documentation are complete. |
| EPIC-08 | AI Orchestrator and Citation | 10 | All task acceptance criteria, tests, security/license checks and documentation are complete. |
| EPIC-09 | User PWA | 7 | All task acceptance criteria, tests, security/license checks and documentation are complete. |
| EPIC-10 | Reviewer and Admin Portals | 6 | All task acceptance criteria, tests, security/license checks and documentation are complete. |
| EPIC-11 | Feedback and Incident Management | 5 | All task acceptance criteria, tests, security/license checks and documentation are complete. |
| EPIC-12 | Evaluation and Benchmark | 7 | All task acceptance criteria, tests, security/license checks and documentation are complete. |
| EPIC-13 | Security, Monitoring and Operations | 9 | All task acceptance criteria, tests, security/license checks and documentation are complete. |
| EPIC-14 | Closed Pilot and Release | 7 | All task acceptance criteria, tests, security/license checks and documentation are complete. |

## Critical Path

```text
TASK-00-01 -> TASK-00-02 -> TASK-00-03 -> TASK-00-04
-> TASK-01-01 -> TASK-02-01 -> TASK-03-03 -> TASK-04-03
-> TASK-05-04 -> TASK-06-03 -> TASK-06-04 -> TASK-07-01
-> TASK-07-05 -> TASK-07-08 -> TASK-08-06 -> TASK-08-08
-> TASK-09-02 -> TASK-12-02 -> TASK-13-04 -> TASK-14-07
```

## Task Completion Checklist

- [ ] Scope is implemented.
- [ ] Acceptance criteria are met.
- [ ] Unit tests pass.
- [ ] Integration and end-to-end tests pass when required.
- [ ] Lint and type checks pass.
- [ ] Security, secret and dependency checks pass.
- [ ] License and provenance checks pass.
- [ ] Documentation is updated.
- [ ] Completion report is filled in.
- [ ] Focused commit is created.
