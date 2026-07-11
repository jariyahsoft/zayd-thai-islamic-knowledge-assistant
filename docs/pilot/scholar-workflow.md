# Scholar Pilot Workflow

## Objective

Recruit and onboard Islamic scholar reviewers for the closed pilot. Scholars evaluate answer accuracy, citation correctness, and thematic compliance under real usage scenarios, producing scored feedback linked to benchmark cases without exposing their identities publicly.

## Prerequisites

Before onboarding begins, the pilot environment (see `environment.md`) must be operational, including:

- Docker Swarm stack with pilot overlay (`pilot.yml`)
- Invite hashes configured for all scholar email addresses
- `senior_scholar` or `reviewer` RBAC roles activated for pilot accounts
- Evaluation starter set (`Zayd-IslamicQA-TH` v1.0.0) seeded into the pilot database
- Monitoring and backup confirmed operational

## Onboarding Flow

### 1. Consent and Conflict-of-Interest Declaration

Each scholar receives a participant briefing covering:

- **Purpose**: evaluating an AI Islamic knowledge assistant (Zayd) during closed pilot
- **AI limitations**: the system is an assistive tool, not a substitute for qualified scholarly judgment
- **Data handling**: their identity, email, and personal details are stored as password hashes or audit UUIDs; public-facing outputs never include reviewer names
- **Confidentiality**: benchmark questions and internal system answers are not to be shared externally

After briefing, the scholar must return a signed consent and conflict-of-interest declaration. The pilot coordinator records the declaration reference ID in the operations log (outside the repo).

### 2. Platform Registration

An allowlist hash of the scholar's email is added to the pilot invite list by the operations team.

```bash
# email normalised: lowercase, trimmed
echo -n "scholar@example.test" | sha256sum | awk '{print $1}'
# Add hash to PILOT_INVITE_EMAIL_HASHES in secrets manager
```

After registration, the scholar's RBAC roles are assigned via the admin console:

- `reviewer` — can view review queue, feedback items, and the evaluation dashboard
- `senior_scholar` (optional, for high-risk content) — can approve documents, invalidate answers, and publish

### 3. Task Assignment

Scholars access the **Reviewer Dashboard** (`/reviews`) and **Evaluation Dashboard** (`/admin/evaluation`) in the pilot environment:

- **Review tasks**: document review queue items assigned by the data operator team
- **Benchmark evaluations**: run comparisons in the Evaluation Dashboard to assess answer quality
- **Feedback triage**: open feedback items requiring root-cause classification and resolution

### 4. Scoring Guidelines

Scores link to benchmark cases but never expose the reviewer's identity publicly. When evaluating a benchmark run, the scholar:

1. Selects a **base run** (e.g. a known-good configuration) and a **target run** (the pilot candidate)
2. Reviews each **case comparison** in the dashboard, noting:
   - Whether the answer is theologically sound
   - Whether citations are correct and support the answer
   - Whether abstention or risk-routing was triggered correctly for sensitive queries
3. **Scores** each case as:
   - **Pass** — correct, supported, safe
   - **Fail** — incorrect, unsupported, unsafe, or missed abstention/routing
4. Downloads the comparison report as JSON for offline record-keeping

The `comparisons` array in the exported JSON contains `case_key`, `topic`, `base_passed`, `target_passed`, and `scores` fields — never reviewer names or email addresses.

### 5. Issue Tracking

Findings discovered during evaluation produce tracked remediation items:

| Finding | Tracked As | Priority |
|---------|-----------|----------|
| Configuration drift | Benchmark run config diff | Medium |
| Incorrect answer | Incident (via feedback or admin) | High |
| Citation error | Incident with citation ID | High |
| Safety policy bypass | Incident + escalated | Critical |
| Usability issue | Feedback report | Low |

Incidents and feedback are created through the existing API endpoints (`POST /admin/incidents`, `POST /feedback`) and visible on the admin dashboard.

## Data Export and Privacy

- Benchmark comparison reports (JSON) contain only `case_key`, `case_type`, `risk_level`, `topic`, `language`, `madhhab`, and score flags — no personal data.
- Audit logs for review decisions record `actor_user_id` (UUID) and action — never the reviewer's email or name in the log body.
- The raw invite list is stored in secrets manager, not in the repository or database.
- Public-facing evaluation exports (without `evaluations.read` permission) exclude private cases and all reviewer metadata.

## Verification

Before concluding the scholar pilot, confirm:

- [ ] At least one scholar has completed an onboarding briefing and signed consent
- [ ] At least one benchmark comparison run has been reviewed and scored
- [ ] Exported comparison JSON contains no reviewer identity fields
- [ ] At least one incident has been created from a finding
- [ ] Audit logs confirm the scholar's actions are recorded without PII exposure
