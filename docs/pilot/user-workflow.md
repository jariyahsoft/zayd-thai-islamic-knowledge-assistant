# User Pilot Workflow

## Objective

Recruit and onboard representative Thai Muslim users to evaluate the Zayd Islamic Knowledge Assistant under real usage conditions. Collect usability feedback, answer quality assessments, and safety observations — triaged into product, content, and security categories.

## Prerequisites

- Pilot environment operational with invite-only registration (see `environment.md`)
- `PILOT_MODE=true`, `ENABLE_GUEST_MODE=false`
- Participant email hashes configured in the invite allowlist
- Monitoring, backup, and incident alerting confirmed operational

## Onboarding Flow

### 1. Participant Briefing

Each participant receives a consent and briefing document covering:

- **Purpose**: helping improve an AI Islamic knowledge assistant for the Thai Muslim community
- **AI limitations**: the system may make mistakes — answers should be verified with a qualified scholar for important religious rulings
- **Privacy policy**: questions and conversation history are recorded for quality improvement; personally identifiable information (name, email) is stored as hashed references only
- **Sensitive topics**: the system will refuse to answer certain high-risk questions (e.g., takfir, divorce, inheritance rulings); this is a safety feature, not a defect
- **Feedback**: users can report problematic answers at any time via the feedback form

After briefing, the participant signs a consent form (recorded by the operations team outside the repo).

### 2. Account Registration

The participant's email hash is added to the pilot allowlist:

```bash
echo -n "user@example.test" | sha256sum | awk '{print $1}'
# Add hash to PILOT_INVITE_EMAIL_HASHES in secrets manager
```

The participant registers at the pilot URL using their email:
- If the email hash matches the allowlist → registration succeeds (201)
- If the email hash does NOT match → registration is denied (403)
- Both outcomes produce audit records (`action: pilot.invite.consume`)
- Audit logs record `allowlist_version` and outcome — never the email or hash

### 3. Using the Application

Participants access the **mobile-first PWA** (or web app) at the pilot URL:

- **Ask questions** via the chat interface on topics such as taharah, salah, fasting, zakat, hajj, family, and daily life
- **Review answers** displayed with citations, source references, and madhhab context
- **Provide feedback** using the feedback form on any answer (categories: incorrect_answer, citation_error, incomplete_answer, inappropriate_content, other)
- **View conversation history** and saved answers

### 4. Sensitive Question Handling

High-risk and unanswerable questions are handled according to the pilot policy:

| Question Type | System Behavior | User Sees |
|---------------|----------------|-----------|
| Normal (taharah, salah, fasting) | Full answer with citations | Answer with sources |
| Madhhab difference | Answer noting differing views | Answer with school-specific guidance |
| Insufficient evidence | Abstention with explanation | "ไม่สามารถตอบได้เนื่องจาก..." |
| High-risk (takfir, divorce, inheritance) | Immediate route to safety flow | Refusal + escalation notice |
| Speculative creed | Abstention | Refusal with theological boundary notice |

### 5. Feedback Triage

User feedback is routed into categories for appropriate response:

| Feedback Category | Triage Path | Owner |
|------------------|-------------|-------|
| `incorrect_answer` | → Content review → possible incident | Scholar reviewer |
| `citation_error` | → Citation verification → registry update | Data operator |
| `incomplete_answer` | → Prompt/retrieval review → model update | ML engineer |
| `inappropriate_content` | → Safety policy review → possible escalation | Scholar + security |
| `other` | → General triage → product backlog | Product owner |

Feedback is triaged through the existing **feedback review queue** (`/admin/feedback`) in the admin console. Each item can be assigned, classified (root cause, priority, severity), and resolved with a corrective-action record. Audit logs track reviewer actions without exposing user identity.

## Quality Metrics

User pilot success is measured by:

- **Answer accuracy**: % of feedback items resolved as "user misunderstanding" vs. genuine errors
- **Abstention appropriateness**: % of high-risk queries correctly refused vs. incorrectly answered
- **Usability**: conversation completion rate, re-ask rate, session duration
- **Safety compliance**: zero unsafe answers detected in post-pilot audit

These metrics are derived from the **evaluation dashboard** and **admin dashboard** — no user-identifying data is stored in the metric aggregates.

## Privacy and Data Handling

- Conversation bodies are stored and audited; user email is stored only as a hashed session reference
- Audit logs for feedback submissions record `actor_user_id` (UUID) — never the email or name in the log body
- Feedback notes are redacted from audit summaries (length-only metrics)
- Saved answers and conversation history belong to the user and are deletable
- The raw invite list is stored in secrets manager, never in the repository or database
- No production data is cloned into the pilot environment

## Verification Checklist

Before concluding the user pilot, confirm:

- [ ] At least one participant has completed the onboarding briefing and signed consent
- [ ] The participant has successfully registered with an invited email
- [ ] A registration attempt with a non-invited email correctly returns 403
- [ ] The participant has asked at least one question and received an answer
- [ ] The participant has submitted at least one feedback report
- [ ] Feedback is visible in the admin feedback review queue
- [ ] An audit log confirms registration, questions, and feedback without exposing PII
- [ ] A denied registration audit record exists without leaking the email hash
