# Prompt: Run All Tasks with Sequential Subagents

ใช้ prompt นี้ส่งให้ main agent เพื่อให้แจกจ่ายงานใน `tasks/` ไปยัง custom subagents โดยทำทีละ task และเปิด subagent ทีละตัวเท่านั้น เพื่อลดการใช้ RAM และรักษา context ของ main agent

## ตั้งค่า Telegram ก่อนรัน Codex

ส่งค่า `TELEGRAM_BOT_TOKEN` และ `TELEGRAM_CHAT_ID` มาพร้อมคำสั่งเรียก prompt โดยตรง

ตัวอย่าง:

```text
run prompt docs\prompts\03_run_all_tasks_subagent.md TELEGRAM_BOT_TOKEN="xxxxxxx" TELEGRAM_CHAT_ID="xxxxx"
```

ถ้าไม่ส่งสองค่านี้มา ระบบจะถือว่า Telegram ถูกปิดสำหรับ run นั้น และยังทำงานต่อได้ตามปกติ

---

## Prompt to Run

```text
Act as the main orchestrator for this repository. Complete every numbered task file under tasks/ by delegating work to the project-scoped custom agents in .codex/agents/.

The user may invoke this prompt in a form like:
- run prompt docs\prompts\03_run_all_tasks_subagent.md TELEGRAM_BOT_TOKEN="xxxxxxx" TELEGRAM_CHAT_ID="xxxxx"

Interpret that invocation as:
- telegram_bot_token = the value provided in TELEGRAM_BOT_TOKEN="..."
- telegram_chat_id = the value provided in TELEGRAM_CHAT_ID="..."

Primary objective:
- Continue until every feasible task is fully implemented and verified.
- Work on exactly one task at a time.
- Run exactly one subagent at a time. Never run subagents in parallel.
- Wait for and close each subagent before starting another subagent to minimize RAM usage.
- Send a Telegram notification when each task attempt starts, when Telegram is enabled.
- Send a Telegram notification when each task reaches a terminal status or encounters an execution error.
- Do not stop after completing a single task.
- Do not ask the user for routine confirmation, implementation choices, or permission between tasks.

Available agent roles:
- task_explorer: read-only task analysis and prerequisite inspection.
- task_worker_b: Tier B implementation worker.
- task_worker_a: Tier A implementation worker.
- task_worker_s: Tier S implementation worker.
- health_security_reviewer: read-only correctness, security, privacy, accessibility, and test review.

## Orchestrator Responsibilities

The main agent owns:
- Task ordering and dependency resolution.
- Selecting the correct worker tier.
- Ensuring only one subagent is active at any time.
- Passing concise context and findings between subagents.
- Integrating results and preventing overlapping writers.
- Tracking completion and blockers in tasks-update.md.
- Confirming that verification evidence exists before marking a task complete.
- Sending privacy-safe Telegram notifications from the main agent only.
- Continuing automatically to the next task.

Do not delegate orchestration to another subagent. Do not ask a subagent to spawn additional agents.

## Initial Discovery

Before starting the first task:

1. Read repository instructions, including all applicable AGENTS.md files, README files, architecture/design rules, and project configuration.
2. Inspect every numbered file matching tasks/[0-9][0-9]_*.md.
3. Inspect all agent files under .codex/agents/.
4. Read tasks-update.md when it exists.
5. Build a dependency-aware task queue from each task's Prerequisites section.
6. Determine completion from repository evidence and verification results, not merely from task numbering or an old progress entry.
7. Skip a task only when its implementation and Definition of Done are already demonstrably complete; record why it was skipped.
8. Initialize Telegram notification state by checking whether TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID were provided in the user invocation and are non-empty, without printing, logging, persisting, or exposing their values. Initialize telegram_started_keys, telegram_terminal_keys, and the sent/disabled/failed counters.

Prefer dependency order over filename order. When multiple tasks are ready, choose the lowest numbered task first.

## Telegram Notifications

Telegram notification support is built into this prompt and must not depend on another repository document. Configuration comes only from the values passed in the user invocation:

- TELEGRAM_BOT_TOKEN
- TELEGRAM_CHAT_ID

At startup, check only whether both values are present and non-empty. Never print their values. Never read Telegram credentials from committed files. Never write their values to source files, tasks-update.md, command output, logs, commits, summaries, or subagent prompts. Never print the fully expanded API URL because it contains the bot token.

The main orchestrator owns all notifications. Subagents must not receive Telegram credentials and must not send Telegram messages.

### Notification state

Maintain these values in the main-agent context for the current run:

- telegram_enabled: true only when both invocation values exist and are non-empty.
- telegram_started_keys: a set of task-attempt start events for which delivery has already been attempted, used to prevent duplicate sends and repeated retries.
- telegram_terminal_keys: a set of terminal events for which delivery has already been attempted, used to prevent duplicate sends and repeated retries.
- telegram_sent_count.
- telegram_disabled_count.
- telegram_failed_count.

Use a unique start notification key in this form:

<task-number>:<attempt-number>:STARTED

Before sending a start notification, check telegram_started_keys. If the key is absent, add it immediately before the first HTTP attempt. The HTTP client may perform only the single configured retry. Do not attempt that start event again later, whether delivery succeeds or fails.

Use a unique terminal notification key in this form:

<task-number>:<attempt-number>:<terminal-status>

Before sending, check telegram_terminal_keys. If the key is absent, add it immediately before the first HTTP attempt. The HTTP client may perform only the single configured retry. Do not attempt that terminal event again later, whether delivery succeeds or fails.

### When to notify

Send exactly one start notification for each task attempt:

- 🚀STARTED: immediately before exploration of that task attempt begins.

Send exactly one terminal notification for each task attempt:

- ✅COMPLETED: after implementation, review, and verification succeed.
- ✳️ALREADY COMPLETE: after repository evidence and verification prove that no implementation is required.
- ⛔️BLOCKED: when a genuine external or dependency blocker prevents completion.
- ❌ERROR: when an unexpected command, test, worker, reviewer, or orchestration failure ends the current attempt.

Do not send ERROR for an individual command failure that is safely recovered within the same attempt. In that case, continue the task and send only its final terminal notification. Do not send both ERROR and BLOCKED for the same unchanged failure event.

Send the start notification before beginning the task attempt. Send the terminal notification before starting the next task. Telegram delivery is best-effort and must never change the implementation status of a task.

### Message format

Use concise plain-text messages:

[Mo-nut Task Runner]
Status: 🚀STARTED | ✅COMPLETED | ✳️ALREADY COMPLETE | ⛔️BLOCKED | ❌ERROR
Task: <task number> - <task title>
Agent: <worker agent or n/a>
Validation: <short pass/fail/blocked summary>
Time: <ISO-8601 timestamp with timezone>

For 🚀STARTED, Validation should be a short message such as:

Validation: starting task attempt

For ❌ERROR or ⛔️BLOCKED, add:

Reason: <one short sanitized reason>

Never include:

- Bot tokens, chat IDs, credentials, authorization headers, signed URLs, or environment values.
- PHI, patient/user-identifying data, document contents, transcript text, medication details, or production payloads.
- Raw stack traces, full command output, source code, diffs, or large test logs.

### Required send behavior

Send an HTTP POST to the Telegram Bot API with URL-encoded chat_id and text fields. Prefer curl or curl.exe. Keep output quiet, fail on HTTP errors, set finite timeouts, and retry no more than once.

POSIX shell pattern:

curl --silent --show-error --fail \
  --connect-timeout 10 \
  --max-time 20 \
  --retry 1 \
  --retry-delay 2 \
  --request POST \
  "https://api.telegram.org/bot${telegram_bot_token}/sendMessage" \
  --data-urlencode "chat_id=${telegram_chat_id}" \
  --data-urlencode "text=${TELEGRAM_MESSAGE}" \
  >/dev/null

PowerShell pattern when curl.exe is available:

curl.exe --silent --show-error --fail `
  --connect-timeout 10 `
  --max-time 20 `
  --retry 1 `
  --retry-delay 2 `
  --request POST `
  "https://api.telegram.org/bot<telegram_bot_token>/sendMessage" `
  --data-urlencode "chat_id=<telegram_chat_id>" `
  --data-urlencode "text=$env:TELEGRAM_MESSAGE" `
  *> $null

Construct TELEGRAM_MESSAGE in memory from the sanitized fields above. Do not echo the expanded endpoint or command. Do not expose the raw API response.

### Missing configuration or delivery failure

If Telegram configuration is absent from the invocation:

1. Set telegram_enabled to false.
2. Record once in tasks-update.md that Telegram notifications are disabled because required invocation values are unavailable.
3. Do not ask the user for credentials.
4. Continue all tasks normally.
5. Count each skipped terminal event as disabled for the final summary, without repeatedly writing the same warning.

If delivery fails because of network, API, authentication, rate limit, missing HTTP client, or runtime approval restrictions:

1. Do not expose credentials or the expanded endpoint.
2. Capture only a short sanitized reason, such as "HTTP request failed", "authentication rejected", or "network unavailable".
3. Do not retry more than the single retry configured above.
4. Record the notification as failed in tasks-update.md.
5. Increment telegram_failed_count.
6. Continue the task queue. Do not classify an otherwise successful task as failed solely because Telegram delivery failed.

## Worker Selection

For each task, read its Recommended Model section and select the worker from the GPT tier:

- Tier B -> task_worker_b
- Tier A -> task_worker_a
- Tier S -> task_worker_s

If no explicit tier exists, classify conservatively:

- Tier B: bounded implementation with clear requirements and verification.
- Tier A: complex cross-module logic, authentication, authorization, async workflows, concurrency, migrations, or sensitive data.
- Tier S: safety-critical, irreversible, emergency, destructive, compliance-critical, or high-impact data-loss work.

Use the model configured in the selected agent file. Do not downgrade a task below its documented tier merely to save resources.

## Sequential Workflow for Every Task

Perform these stages strictly in order. Never overlap stages or agents.

### Stage 1: Explore

1. Spawn one task_explorer for the current task only.
2. Ask it to inspect the complete task, context files, prerequisites, current implementation, likely affected files, risks, and verification commands.
3. Wait for its result.
4. Capture only its concise findings in the main context.
5. Close the explorer before continuing.

Before Stage 1 begins for a task attempt, send exactly one 🚀STARTED Telegram notification when telegram_enabled is true.

If a prerequisite is incomplete, return that prerequisite task to the front of the dependency queue. Do not implement multiple numbered tasks inside one worker run.

### Stage 2: Implement

1. Select task_worker_b, task_worker_a, or task_worker_s from the task tier.
2. Spawn exactly one worker and assign exactly one numbered task.
3. Include the explorer summary, relevant repository state, and explicit instruction that this worker is the sole writer for the task.
4. Require complete implementation, focused tests, all feasible Verify commands, and an explicit Definition of Done check.
5. Wait until the worker finishes.
6. Capture its changed-file summary, test results, risks, and blockers.
7. Close the worker before continuing.

Do not start another task while implementation or verification for the current task remains unfinished.

### Stage 3: Review

1. Spawn one health_security_reviewer for the completed task changes.
2. Give it the task file, worker summary, and changed-file scope.
3. Require findings ordered by severity with precise file references and missing-test analysis.
4. Wait for its result.
5. Capture the findings.
6. Close the reviewer before continuing.

### Stage 4: Fix Review Findings

If the reviewer reports actionable findings:

1. Re-spawn the same worker tier used for implementation.
2. Assign only the confirmed findings for the current task.
3. Require regression tests and rerun affected verification commands.
4. Wait for completion and close the worker.
5. Re-run the reviewer sequentially when fixes materially affect security, privacy, data integrity, accessibility, or task behavior.
6. Repeat sequentially until no actionable high- or medium-severity findings remain.

Never keep the reviewer and worker active at the same time.

### Stage 5: Verify and Record

Before marking the task complete, confirm:

- The implementation matches the task scope.
- Every feasible Verify command passed.
- Every Definition of Done item has repository evidence.
- No known high- or medium-severity review finding remains unresolved.
- No unrelated user changes were reverted.
- Secrets, credentials, PHI, or identifiable production data were not introduced.

For every terminal task result, perform these finalization steps in order:

1. Determine the final task status and prepare a sanitized notification message.
2. Send the terminal Telegram notification when telegram_enabled is true, before starting another task.
3. Capture notification status as sent, disabled, or failed with a sanitized reason.
4. Update tasks-update.md with the final task and notification result.
5. If the repository is a valid Git repository and local commits are allowed by the active runtime policy, create one focused commit for the completed task. Never combine unrelated tasks in one commit.
6. Immediately continue to the next dependency-ready task.

Update tasks-update.md after every task with:

- Timestamp.
- Task number, title, and attempt number.
- Status: completed, already-complete, blocked, or error.
- Explorer agent.
- Worker agent and configured model.
- Reviewer agent.
- Concise implementation summary.
- Changed files or modules.
- Verification commands and results.
- Review outcome.
- Telegram notification status: sent, disabled, or failed with a sanitized reason.
- Remaining risks, blockers, and owner-required actions.

If committing is unavailable or requires an approval that cannot be obtained non-interactively, record that fact and continue without claiming a commit was created. A Telegram delivery failure must not prevent progress recording or committing.

## Blocker Handling

Do not ask the user to make routine implementation decisions. Resolve ambiguity using, in order:

1. Existing repository code and tests.
2. Architecture, design, security, and coding documentation.
3. The task's explicit requirements and safest reversible assumption.
4. A documented placeholder, mock, feature flag, or disabled-by-default implementation when the task explicitly permits it.

Never fabricate credentials, legal approval, clinical approval, provider configuration, production access, or external-system success.

When a task has a genuine external blocker:

- Complete every safe and testable portion of the task.
- Record the exact blocker and required owner action in tasks-update.md.
- Mark the task blocked rather than completed.
- Send one ⛔️BLOCKED Telegram notification with a short sanitized reason.
- Continue with other dependency-ready tasks that do not depend on the blocker.
- Revisit blocked tasks after each full pass because another completed task may unblock them.

When an unexpected command, test, worker, reviewer, or orchestration error prevents the current task attempt from continuing safely:

- Capture a concise sanitized error summary without secrets, PHI, raw stack traces, or large logs.
- End the current attempt with status ERROR.
- Send exactly one ❌ERROR Telegram notification using the current task number and attempt number.
- Record the error, notification result, and recoverable next action in tasks-update.md.
- Apply safe local recovery in a new attempt when possible; increment the attempt number before retrying.
- If recovery is not possible, leave the task blocked for a later pass, but do not send an additional BLOCKED notification for the same unchanged failure event.
- Continue with another dependency-ready task when safe.

Do not loop forever. Stop only when either:

1. All numbered tasks are completed or already complete; or
2. A full pass makes no progress and every remaining task is blocked by external credentials, approval, unavailable infrastructure, or another recorded hard blocker.

In case 2, produce one consolidated blocker report after exhausting all feasible work. This is not a request for routine permission; it is an accurate account of work that cannot be completed locally.

## Resource Rules

- Maximum active subagents: 1.
- Never parallelize tasks, exploration, implementation, review, tests, or fixes across subagents.
- Close completed subagent threads promptly.
- Keep raw logs and large command output inside subagent threads; return concise summaries to the main context.
- Do not create one permanent agent per task.
- Do not load all task context into every worker; pass only the current task and its required context.
- Telegram notification calls are performed by the main agent between tasks and must never overlap a running subagent.

## Autonomy Rules

- Start work immediately after initial discovery.
- Do not pause after plans, analysis, individual tasks, commits, or review reports.
- Do not ask "Should I continue?" or request confirmation between tasks.
- Follow mandatory sandbox, approval, security, and external-access controls enforced by the runtime; never attempt to bypass them.
- When an enforced action cannot proceed without interactive approval, use the safest available local alternative, record the limitation, and continue with other feasible work.
- Continue until the completion or no-progress condition is reached.

## Final Response

After processing the complete queue, report:

- Completed tasks.
- Tasks that were already complete.
- Blocked tasks and exact owner actions required.
- Agents and models used.
- Verification summary.
- Review summary and residual risks.
- Commits created, when applicable.
- Telegram notification summary: sent, disabled, and failed counts.
- Path to tasks-update.md.

Do not claim all tasks are complete when any task remains blocked or unverified.
```

---

## Expected Execution Pattern

```text
Main agent
  -> task_explorer (Task 01) -> wait -> close
  -> task_worker_b (Task 01) -> wait -> close
  -> health_security_reviewer (Task 01) -> wait -> close
  -> task_worker_b fixes (only if needed) -> wait -> close
  -> send exactly one Task 01 terminal Telegram notification
  -> record Task 01 and notification result
  -> optional focused commit
  -> task_explorer (next dependency-ready task) -> wait -> close
  -> continue sequentially until the queue is exhausted
```
