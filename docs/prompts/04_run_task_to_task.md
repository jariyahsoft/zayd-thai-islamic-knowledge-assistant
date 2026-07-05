# Prompt: Run Tasks from Range

ใช้ prompt นี้ส่งให้ main agent เพื่อให้ทำงานเฉพาะช่วง task ที่ระบุใน `tasks/` โดย main agent ทำงานเองทั้งหมด ไม่ใช้ subagent

รองรับการสั่งงานลักษณะนี้:

```text
run prompt docs\prompts\04_run_task_to_task.md task 01 - 05 TELEGRAM_BOT_TOKEN="xxxxxxx" TELEGRAM_CHAT_ID="xxxxx"
```

ความหมายคือให้ main agent ทำงานเฉพาะ task หมายเลข `01` ถึง `05` แบบรวมปลายทั้งสองฝั่ง และยังต้องเคารพ dependency ภายในช่วงนั้นเสมอ

## วิธีส่งค่า Telegram

ส่งค่า `TELEGRAM_BOT_TOKEN` และ `TELEGRAM_CHAT_ID` มาพร้อมคำสั่งเรียก prompt โดยตรง

ตัวอย่าง:

```text
run prompt docs\prompts\04_run_task_to_task.md task 01 - 05 TELEGRAM_BOT_TOKEN="xxxxxxx" TELEGRAM_CHAT_ID="xxxxx"
```

ถ้าไม่ส่งสองค่านี้มา ระบบจะถือว่า Telegram ถูกปิดสำหรับ run นั้น และยังทำงานต่อได้ตามปกติ

---

## Prompt to Run

```text
Act as the main implementation agent for this repository. Complete only the numbered task files under tasks/ that fall within the user-requested inclusive range, and do all work yourself without spawning or delegating to subagents.

The user will invoke this prompt in a form like:
- run prompt docs\prompts\04_run_task_to_task.md task 01 - 05 TELEGRAM_BOT_TOKEN="xxxxxxx" TELEGRAM_CHAT_ID="xxxxx"

Interpret that invocation as:
- start_task = 01
- end_task = 05
- include every numbered task file whose two-digit prefix is between start_task and end_task, inclusive
- telegram_bot_token = the value provided in TELEGRAM_BOT_TOKEN="..."
- telegram_chat_id = the value provided in TELEGRAM_CHAT_ID="..."

Primary objective:
- Continue until every feasible task in the requested range is fully implemented and verified.
- Work on exactly one task at a time.
- Do all exploration, implementation, review, and verification in the main agent.
- Send a Telegram notification when each task attempt starts, when Telegram is enabled.
- Send a Telegram notification when each task reaches a terminal status or encounters an execution error.
- Do not stop after completing a single task in the range.
- Do not ask the user for routine confirmation, implementation choices, or permission between tasks in the range.

## Range Rules

The active workset is only the tasks whose numeric prefixes are within the requested inclusive range.

Examples:
- `task 01 - 05` means tasks `01`, `02`, `03`, `04`, and `05`
- `task 24 - 24` means only task `24`

Do not implement tasks outside the requested range unless the repository already contains completed evidence for them and you only need to inspect that evidence to determine whether an in-range task is blocked by an unmet prerequisite.

If an in-range task depends on an out-of-range task that is not already complete, mark the in-range task as BLOCKED with the out-of-range prerequisite as the reason. Do not automatically execute that out-of-range task.

Prefer dependency order over filename order. When multiple in-range tasks are ready, choose the lowest numbered task first.

## Main-Agent Responsibilities

The main agent owns:
- Task ordering and dependency resolution within the requested range.
- Selecting the implementation approach from each task's Recommended Model and task content.
- Reading context files, inspecting current implementation, and identifying affected files.
- Implementing changes directly.
- Running focused verification and reviewing its own work critically before marking a task complete.
- Tracking completion and blockers in tasks-update.md.
- Confirming that verification evidence exists before marking a task complete.
- Sending privacy-safe Telegram notifications.
- Continuing automatically to the next dependency-ready task in range.

Do not spawn, delegate to, or rely on subagents for any part of this workflow.

## Initial Discovery

Before starting the first task:

1. Read repository instructions, including all applicable AGENTS.md files, README files, architecture/design rules, and project configuration.
2. Inspect every numbered file matching tasks/[0-9][0-9]_*.md, but build the active queue only from the tasks inside the requested range.
3. Read tasks-update.md when it exists.
4. Build a dependency-aware task queue from each in-range task's Prerequisites section.
5. Determine completion from repository evidence and verification results, not merely from task numbering or an old progress entry.
6. Skip an in-range task only when its implementation and Definition of Done are already demonstrably complete; record why it was skipped.
7. Initialize Telegram notification state by checking whether TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID were provided in the user invocation and are non-empty, without printing, logging, persisting, or exposing their values. Initialize telegram_started_keys, telegram_terminal_keys, and the sent/disabled/failed counters.

## Telegram Notifications

Telegram notification support is built into this prompt and must not depend on another repository document. Configuration comes only from the values passed in the user invocation:

- TELEGRAM_BOT_TOKEN
- TELEGRAM_CHAT_ID

At startup, check only whether both values are present and non-empty. Never print their values. Never read Telegram credentials from committed files. Never write their values to source files, tasks-update.md, command output, logs, commits, or summaries. Never print the fully expanded API URL because it contains the bot token.

### Notification state

Maintain these values in the main-agent context for the current run:

- telegram_enabled: true only when both invocation values exist and are non-empty.
- telegram_started_keys: a set of task-attempt start events for which delivery has already been attempted, used to prevent duplicate sends and repeated retries.
- telegram_terminal_keys: a set of terminal events for which delivery has already been attempted, used to prevent duplicate sends and repeated retries.
- telegram_sent_count
- telegram_disabled_count
- telegram_failed_count

Use a unique start notification key in this form:

<task-number>:<attempt-number>:STARTED

Before sending a start notification, check telegram_started_keys. If the key is absent, add it immediately before the first HTTP attempt. The HTTP client may perform only the single configured retry. Do not attempt that start event again later, whether delivery succeeds or fails.

Use a unique terminal notification key in this form:

<task-number>:<attempt-number>:<terminal-status>

Before sending, check telegram_terminal_keys. If the key is absent, add it immediately before the first HTTP attempt. The HTTP client may perform only the single configured retry. Do not attempt that terminal event again later, whether delivery succeeds or fails.

### When to notify

Send exactly one start notification for each task attempt:

- 🚀STARTED: immediately before exploration or implementation of that task attempt begins.

Send exactly one terminal notification for each task attempt:

- ✅COMPLETED: after implementation and verification succeed.
- ✳️ALREADY COMPLETE: after repository evidence and verification prove that no implementation is required.
- ⛔️BLOCKED: when a genuine external or dependency blocker prevents completion.
- ❌ERROR: when an unexpected command, test, or execution failure ends the current attempt.

Do not send ERROR for an individual command failure that is safely recovered within the same attempt. In that case, continue the task and send only its final terminal notification. Do not send both ERROR and BLOCKED for the same unchanged failure event.

Send the start notification before beginning the task attempt. Send the terminal notification before starting the next task. Telegram delivery is best-effort and must never change the implementation status of a task.

### Message format

Use concise plain-text messages:

[<project> Task Runner]
Status: 🚀STARTED | ✅COMPLETED | ✳️ALREADY COMPLETE | ⛔️BLOCKED | ❌ERROR
Task: <task number> - <task title>
Agent: main
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
4. Continue all in-range tasks normally.
5. Count each skipped terminal event as disabled for the final summary, without repeatedly writing the same warning.

If delivery fails because of network, API, authentication, rate limit, missing HTTP client, or runtime approval restrictions:

1. Do not expose credentials or the expanded endpoint.
2. Capture only a short sanitized reason, such as "HTTP request failed", "authentication rejected", or "network unavailable".
3. Do not retry more than the single retry configured above.
4. Record the notification as failed in tasks-update.md.
5. Increment telegram_failed_count.
6. Continue the task queue. Do not classify an otherwise successful task as failed solely because Telegram delivery failed.

## Recommended Model Handling

For each task, read its Recommended Model section and use the GPT recommendation as a complexity signal for how much effort and verification depth to apply.

Guidance:

- Tier B or GPT mini: use a lighter implementation pass, but still complete verification.
- Tier A or GPT high: use a more careful pass across design, security, and tests.
- Tier S: treat as safety-critical or high-impact work and apply the strictest review and verification.

Do not downgrade a task below its documented tier merely to save resources.

## Sequential Workflow for Every In-Range Task

Perform these stages strictly in order.

### Stage 1: Explore

1. Read the current task file completely.
2. Read its context files and prerequisites.
3. Inspect current implementation, likely affected files, risks, and verification commands.
4. Capture concise findings in your working context before editing.

Before Stage 1 begins for a task attempt, send exactly one 🚀STARTED Telegram notification when telegram_enabled is true.

If an in-range prerequisite is incomplete, return that prerequisite task to the front of the dependency queue. If the prerequisite is out of range and not already complete, mark the current task BLOCKED.

Do not implement multiple numbered tasks inside one pass.

### Stage 2: Implement

1. Edit only what is needed for the current task.
2. Keep the current task as the only active implementation target.
3. Complete all feasible implementation work for the task.
4. Run focused tests and all feasible Verify commands.
5. Capture changed-file summary, test results, risks, and blockers.

Do not start another task while implementation or verification for the current task remains unfinished.

### Stage 3: Self-Review

Review the completed task changes critically before marking the task complete.

Required review areas:
- correctness against the task instructions
- security and privacy impact
- accessibility impact when UI is affected
- data integrity and migration risk when persistence is affected
- missing-test analysis

If you find actionable issues, fix them and rerun affected verification before continuing.

### Stage 4: Verify and Record

Before marking the task complete, confirm:

- The implementation matches the task scope.
- Every feasible Verify command passed.
- Every Definition of Done item has repository evidence.
- No known high- or medium-severity issue remains unresolved.
- No unrelated user changes were reverted.
- Secrets, credentials, PHI, or identifiable production data were not introduced.

For every terminal task result, perform these finalization steps in order:

1. Determine the final task status and prepare a sanitized notification message.
2. Send the terminal Telegram notification when telegram_enabled is true, before starting another task.
3. Capture notification status as sent, disabled, or failed with a sanitized reason.
4. Update tasks-update.md with the final task and notification result.
5. If the repository is a valid Git repository and local commits are allowed by the active runtime policy, create one focused commit for the completed task. Never combine unrelated tasks in one commit.
6. Immediately continue to the next dependency-ready task in range.

Update tasks-update.md after every task with:

- Timestamp
- Task number, title, and attempt number
- Status: completed, already-complete, blocked, or error
- Recommended model summary used for planning
- Concise implementation summary
- Changed files or modules
- Verification commands and results
- Self-review outcome
- Telegram notification status: sent, disabled, or failed with a sanitized reason
- Remaining risks, blockers, and owner-required actions

If committing is unavailable or requires an approval that cannot be obtained non-interactively, record that fact and continue without claiming a commit was created. A Telegram delivery failure must not prevent progress recording or committing.

## Blocker Handling

Do not ask the user to make routine implementation decisions. Resolve ambiguity using, in order:

1. Existing repository code and tests
2. Architecture, design, security, and coding documentation
3. The task's explicit requirements and safest reversible assumption
4. A documented placeholder, mock, feature flag, or disabled-by-default implementation when the task explicitly permits it

Never fabricate credentials, legal approval, clinical approval, provider configuration, production access, or external-system success.

When a task has a genuine external blocker:

- Complete every safe and testable portion of the task.
- Record the exact blocker and required owner action in tasks-update.md.
- Mark the task blocked rather than completed.
- Send one ⛔️BLOCKED Telegram notification with a short sanitized reason.
- Continue with other dependency-ready tasks in range that do not depend on the blocker.
- Revisit blocked in-range tasks after each full pass because another completed in-range task may unblock them.

When an unexpected command, test, or execution error prevents the current task attempt from continuing safely:

- Capture a concise sanitized error summary without secrets, PHI, raw stack traces, or large logs.
- End the current attempt with status ERROR.
- Send exactly one ❌ERROR Telegram notification using the current task number and attempt number.
- Record the error, notification result, and recoverable next action in tasks-update.md.
- Apply safe local recovery in a new attempt when possible; increment the attempt number before retrying.
- If recovery is not possible, leave the task blocked for a later pass, but do not send an additional BLOCKED notification for the same unchanged failure event.
- Continue with another dependency-ready in-range task when safe.

Do not loop forever. Stop only when either:

1. All in-range numbered tasks are completed or already complete
2. A full pass makes no progress and every remaining in-range task is blocked by external credentials, approval, unavailable infrastructure, or another recorded hard blocker
3. Every remaining in-range task is blocked by an out-of-range prerequisite that is incomplete

In case 2 or 3, produce one consolidated blocker report after exhausting all feasible in-range work. This is not a request for routine permission; it is an accurate account of work that cannot be completed locally.

## Resource Rules

- Work on one numbered task at a time.
- Do not use subagents.
- Keep raw logs concise in the main context and summarize key results.
- Do not load unnecessary context; read only the current task and required supporting files.
- Telegram notification calls are performed between tasks only.

## Autonomy Rules

- Start work immediately after initial discovery.
- Do not pause after plans, analysis, individual tasks, commits, or reviews.
- Do not ask "Should I continue?" or request confirmation between tasks.
- Follow mandatory sandbox, approval, security, and external-access controls enforced by the runtime; never attempt to bypass them.
- When an enforced action cannot proceed without interactive approval, use the safest available local alternative, record the limitation, and continue with other feasible in-range work.
- Continue until the completion or no-progress condition is reached.

## Final Response

After processing the in-range queue, report:

- Requested range
- Completed tasks
- Tasks that were already complete
- Blocked tasks and exact owner actions required
- Out-of-range prerequisite blockers, if any
- Recommended models referenced
- Verification summary
- Self-review summary and residual risks
- Commits created, when applicable
- Telegram notification summary: sent, disabled, and failed counts
- Path to tasks-update.md

Do not claim the requested range is complete when any in-range task remains blocked or unverified.
```

---

## Expected Execution Pattern

```text
Main agent
  -> parse requested range, for example Task 01 to Task 05
  -> inspect Task 01
  -> implement Task 01
  -> self-review Task 01
  -> verify Task 01
  -> send exactly one Task 01 terminal Telegram notification
  -> record Task 01 and notification result
  -> optional focused commit
  -> inspect next dependency-ready in-range task
  -> continue sequentially until the requested range is exhausted
```

## Usage Example

```text
run prompt docs\prompts\04_run_task_to_task.md task 01 - 05 TELEGRAM_BOT_TOKEN="xxxxxxx" TELEGRAM_CHAT_ID="xxxxx"
```
