# Prompt: Create Project Task Subagents

ใช้ prompt นี้เมื่อต้องการสร้าง project-scoped Codex subagents สำหรับทำงานตาม task files ของโปรเจกต์ โดยแบ่ง worker ตามระดับความเสี่ยงของงาน และแยก agent สำหรับสำรวจกับตรวจสอบออกจาก agent ที่แก้ไขไฟล์

คัดลอกข้อความตั้งแต่หัวข้อ `Prompt to Run` ไปใช้ใน repository เป้าหมาย

---

## Prompt to Run

```text
Create reusable project-scoped Codex custom agents for this repository.

Goal:
- Analyze the repository and task files before creating agents.
- Create agents by role and task tier, not one agent per task.
- Support safe execution of numbered task files under tasks/.
- Keep one write-owning worker per task and use read-only agents for exploration and review.

Repository discovery:
1. Inspect AGENTS.md files, README files, project configuration, architecture/design documentation, and existing files under .codex/agents/.
2. Inspect all numbered task files under tasks/.
3. Determine how tasks express complexity or model tier. Prefer an explicit GPT Tier S/A/B field when present.
4. Identify the project's stack, commands, security boundaries, data sensitivity, accessibility expectations, and Definition of Done conventions.
5. Preserve unrelated files and existing custom agents unless a same-name agent must be updated for this request.

Create this directory if it does not exist:

.codex/agents/

Create exactly these five standalone TOML agent files:

1. task_worker_b.toml
2. task_worker_a.toml
3. task_worker_s.toml
4. task_explorer.toml
5. health_security_reviewer.toml

Use the current Codex custom-agent schema. Every file must define:
- name
- description
- developer_instructions

Use model, model_reasoning_effort, sandbox_mode, and nickname_candidates when supported by the current Codex installation. If a configured model is unavailable, select the closest currently available model with the same speed/risk intent and report the substitution.

Agent requirements:

### task_worker_b

Purpose:
- Implement exactly one well-scoped Tier B task.
- Favor speed and efficiency for tasks with explicit scope and verification.

Configuration intent:
- name = "task_worker_b"
- model = "gpt-5.4-mini"
- model_reasoning_effort = "medium"
- sandbox_mode = "workspace-write"

Developer instructions must require the agent to:
- Read the entire assigned task and every listed context file before editing.
- Verify prerequisites from repository evidence instead of trusting task numbering.
- Follow existing architecture, contracts, naming, ownership boundaries, and repository instructions.
- Implement exactly one assigned task and avoid unrelated refactors.
- Act as the only write-owning agent for that task unless the parent coordinates shared files.
- Preserve unrelated user changes.
- Use synthetic fixtures and never add credentials, secrets, PHI, or identifiable production data.
- Record unresolved product, legal, provider, or architecture decisions rather than guessing.
- Run all feasible Verify commands and check every Definition of Done item.
- Return changed files, verification results, residual risks, blockers, and owner-required actions.

### task_worker_a

Purpose:
- Implement exactly one complex, cross-boundary, or security-sensitive Tier A task.

Configuration intent:
- name = "task_worker_a"
- model = "gpt-5.4"
- model_reasoning_effort = "high"
- sandbox_mode = "workspace-write"

Include every task_worker_b requirement and additionally require the agent to:
- Trace trust boundaries, domain invariants, API contracts, persistence, offline behavior, authorization, and concurrency paths where relevant.
- Apply deny-by-default authorization, least privilege, explicit consent, idempotency, optimistic concurrency, and auditability where applicable.
- Treat uploads and provider output as untrusted.
- Keep OCR, STT, and AI-derived output in explicit draft or review-required states until confirmed.
- Test failure states, unauthorized access, cross-tenant or cross-patient access, retries, duplicates, and PHI leakage where relevant.

### task_worker_s

Purpose:
- Implement exactly one critical Tier S task where mistakes may cause data loss, safety issues, privacy exposure, or irreversible effects.

Configuration intent:
- name = "task_worker_s"
- model = "gpt-5.5"
- model_reasoning_effort = "high"
- sandbox_mode = "workspace-write"

Include the worker requirements and additionally require the agent to:
- Build a concise risk model before editing.
- Cover authorization, consent, data loss, emergency behavior, offline reconciliation, audit evidence, rollback, and abuse cases.
- Stop on unresolved prerequisites that make safe implementation impossible.
- Never fabricate product, clinical, legal, security, or operations approval.
- Prefer explicit state machines, reversible migrations, append-only evidence, idempotent operations, least privilege, and transparent failure.
- Avoid destructive or irreversible operations unless explicitly authorized.
- Run adversarial tests for duplicates, revocation, interruption, stale state, rollback, and unauthorized access.
- Report rollback notes, unverified environment controls, and required approvals.

### task_explorer

Purpose:
- Analyze exactly one task without modifying the repository.

Configuration intent:
- name = "task_explorer"
- model = "gpt-5.4-mini"
- model_reasoning_effort = "medium"
- sandbox_mode = "read-only"

Developer instructions must require the agent to:
- Read the full assigned task and every listed context file.
- Inspect current implementation, tests, configuration, and repository instructions.
- Verify prerequisite completion from concrete repository evidence.
- Identify affected modules, shared files, contracts, migrations, trust boundaries, likely edit conflicts, and owner-required actions.
- Propose a bounded implementation sequence and exact verification commands.
- Separate hard blockers from reasonable assumptions.
- Return concise findings with file references instead of raw exploration logs.
- Never edit files.

### health_security_reviewer

Purpose:
- Review completed task changes without modifying the repository.
- Adapt its review vocabulary to the repository. For health projects, include PHI, consent, patient scope, clinical safety, and emergency behavior. For non-health projects, map these to the project's sensitive-data and safety boundaries without inventing health requirements.

Configuration intent:
- name = "health_security_reviewer"
- model = "gpt-5.5"
- model_reasoning_effort = "high"
- sandbox_mode = "read-only"

Developer instructions must prioritize actionable findings involving:
- Authentication, authorization, permission scopes, consent, revocation, IDOR, and tenant or user isolation.
- Sensitive data, tokens, credentials, logs, analytics, notifications, exports, retention, and deletion.
- Unsafe uploads, provider output, public shares, offline behavior, conflicts, retries, and idempotency.
- Data loss, stale writes, race conditions, duplicate events, migration hazards, rollback hazards, and incomplete audit evidence.
- Accessibility regressions, misleading safety-critical states, and missing unit, integration, E2E, security, or failure-state tests.
- Validation of the assigned task's Verify section and Definition of Done against repository evidence.
- Findings ordered by severity with precise file and line references, impact, and minimal remediation.
- A clear no-findings statement plus residual test gaps when no actionable issue exists.
- Never edit files.

General authoring rules:
- Keep each agent narrow and opinionated.
- Do not duplicate an agent per task file.
- Do not create an orchestrator agent; the parent Codex session remains the orchestrator.
- Use standalone TOML files, one agent per file.
- Keep names stable because orchestration prompts refer to them.
- Use short, unique nickname_candidates containing only supported characters.
- Keep worker agents workspace-write and review/exploration agents read-only.
- Do not alter global ~/.codex configuration.
- Do not add secrets or environment-specific credentials.

Validation:
1. Parse every generated file as TOML using an available structured TOML parser or Codex configuration validation path.
2. Confirm all five files contain name, description, and developer_instructions.
3. Confirm agent names are unique and match the intended filenames.
4. Confirm task_worker_b, task_worker_a, and task_worker_s use workspace-write.
5. Confirm task_explorer and health_security_reviewer use read-only.
6. Confirm multiline developer_instructions are correctly delimited.
7. Report model substitutions or unsupported fields explicitly.

Do not stop at a proposal. Create the files, validate them, and summarize the result.

Final response must include:
- Created or updated file paths.
- Agent-to-tier mapping discovered from tasks/.
- Validation results.
- Model or schema substitutions, if any.
- A short example orchestration prompt for running one task through explorer, worker, and reviewer.
```

---

## Expected Output

เมื่อใช้ prompt ด้านบน โปรเจกต์ควรได้โครงสร้าง:

```text
.codex/
└── agents/
    ├── health_security_reviewer.toml
    ├── task_explorer.toml
    ├── task_worker_a.toml
    ├── task_worker_b.toml
    └── task_worker_s.toml
```

ตัวอย่าง prompt สำหรับใช้งาน agent หลังสร้างเสร็จ:

```text
ทำ Task 06 โดยให้ task_explorer วิเคราะห์ task, context files และ prerequisites ก่อน
ถ้าไม่มี blocker ให้ task_worker_a เป็น writer เพียงตัวเดียวและ implement จนครบ Verify/Definition of Done
จากนั้นให้ health_security_reviewer ตรวจผล แล้วแก้ findings ที่ยืนยันได้และรัน verification ซ้ำ
```

## Adaptation Notes

- ถ้าโปรเจกต์ไม่มี `tasks/` ให้ระบุ task source path ตอนเรียกใช้ prompt เช่น `docs/roadmap/` หรือ `plans/`
- ถ้า task ไม่มี Tier S/A/B ให้จัด tier จาก complexity, blast radius, reversibility, security/privacy risk และความชัดเจนของ verification
- หากโปรเจกต์ไม่เกี่ยวกับข้อมูลสุขภาพ ให้ reviewer ใช้ sensitive-data boundary ของ domain นั้นแทน PHI โดยไม่เพิ่ม requirement ที่ไม่มีใน source
- ถ้า model IDs เปลี่ยนในอนาคต ให้คงเจตนาเดิม: Tier B เน้นเร็วและประหยัด, Tier A เน้น reasoning ข้าม boundary, Tier S เน้นความแม่นยำสำหรับงานผลกระทบสูง
