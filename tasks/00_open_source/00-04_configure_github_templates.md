# TASK-00-04 — Configure GitHub Templates

## Status

`DONE`

## Model Tier

Tier C

## Related Requirements

- SRS §40 Community Files
- SRS §41 Contribution Workflow
- SRS §42 Data Contribution Workflow
- SRS §37 CI/CD Requirements

## Objective

Add structured GitHub issue, pull-request and ownership templates so contributions arrive with the information needed for engineering, security, data-license and religious-content review.

## Scope

### In Scope

Create:

```text
.github/ISSUE_TEMPLATE/bug_report.yml
.github/ISSUE_TEMPLATE/feature_request.yml
.github/ISSUE_TEMPLATE/data_source_proposal.yml
.github/ISSUE_TEMPLATE/citation_error.yml
.github/ISSUE_TEMPLATE/translation_issue.yml
.github/ISSUE_TEMPLATE/religious_content_issue.yml
.github/ISSUE_TEMPLATE/config.yml
.github/PULL_REQUEST_TEMPLATE.md
.github/CODEOWNERS
```

### Out of Scope

- GitHub Actions.
- Branch protection implementation.
- Assigning real usernames without project-owner input.
- Public security-vulnerability issue forms.

## Dependencies

- TASK-00-03

## Expected Files

All files listed in scope.

## Functional Requirements

1. Bug reports must request reproduction steps, expected result, actual result, version and sanitized logs.
2. Feature requests must request motivation, scope and alternatives.
3. Data-source proposals must request owner, source URL, license, permission evidence, language, madhhab, content type and checksum.
4. Citation-error reports must request answer reference, citation shown, expected source and problem category.
5. Translation issues must distinguish original text, displayed translation and suggested correction.
6. Religious-content issues must avoid collecting unnecessary personal details and must allow private escalation instructions.
7. Pull requests must include requirement/task ID, tests, security impact, data-license impact and content-review impact.
8. CODEOWNERS must use placeholder teams or documented paths until real owners are provided.

## Technical Requirements

- Issue forms must use valid GitHub issue-form YAML.
- Pull request and CODEOWNERS templates must use repository-relative paths.
- Template labels and names must be stable enough for later automation.

## Security Requirements

- Disable public security issue submission and link to `SECURITY.md`.
- Tell reporters to redact secrets, tokens, private conversations and personal data.
- Do not ask users to post sensitive religious or family disputes publicly.

## Acceptance Criteria

- [ ] All issue forms render as valid YAML.
- [ ] Pull-request template includes task ID and test evidence.
- [ ] Data and religious-content templates include source and license review fields.
- [ ] Security issues are redirected to the private process.
- [ ] CODEOWNERS syntax is valid and contains no invented personal accounts.

## Required Tests

- Validate issue-form YAML syntax.
- Review templates through GitHub's preview if available.
- Confirm repository issue configuration links to `SECURITY.md`.

## Documentation Updates

- Link issue types from `CONTRIBUTING.md`.

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `.github/ISSUE_TEMPLATE/bug_report.yml`
- `.github/ISSUE_TEMPLATE/feature_request.yml`
- `.github/ISSUE_TEMPLATE/data_source_proposal.yml`
- `.github/ISSUE_TEMPLATE/citation_error.yml`
- `.github/ISSUE_TEMPLATE/translation_issue.yml`
- `.github/ISSUE_TEMPLATE/religious_content_issue.yml`
- `.github/ISSUE_TEMPLATE/config.yml`
- `.github/PULL_REQUEST_TEMPLATE.md`
- `.github/CODEOWNERS`
- `CONTRIBUTING.md`
- `tasks/00_open_source/00-04_configure_github_templates.md`
- `tasks/00_task_index.md`
- `tasks-update.md`

### Commands and Tests Executed

- `sed -n '1,260p' tasks/00_open_source/00-04_configure_github_templates.md`
- `rg --files .github .`
- `sed -n '1,220p' CONTRIBUTING.md`
- `sed -n '1,240p' SECURITY.md`
- `sed -n '1,260p' GOVERNANCE.md`
- `sed -n '1,220p' tasks/00_task_index.md`
- `sed -n '1,220p' tasks-update.md`
- `sed -n '1,220p' docs/09_development/ai_coding_agent_policy.md`
- `test -f .github/ISSUE_TEMPLATE/bug_report.yml -a -f .github/ISSUE_TEMPLATE/feature_request.yml -a -f .github/ISSUE_TEMPLATE/data_source_proposal.yml -a -f .github/ISSUE_TEMPLATE/citation_error.yml -a -f .github/ISSUE_TEMPLATE/translation_issue.yml -a -f .github/ISSUE_TEMPLATE/religious_content_issue.yml -a -f .github/ISSUE_TEMPLATE/config.yml -a -f .github/PULL_REQUEST_TEMPLATE.md -a -f .github/CODEOWNERS`
- `python - <<'PY' ... yaml.safe_load(...) ... PY`
- `rg -n "blank_issues_enabled|security@zayd.example|Task ID|source URL|license|permission evidence|madhhab|content review|reproduction|sanitized logs|redact|docs/rfcs|CODEOWNERS" .github README.md CONTRIBUTING.md SECURITY.md GOVERNANCE.md SUPPORT.md`

### Acceptance Criteria Result

- Passed: all issue forms render as valid YAML.
- Passed: pull-request template includes task ID and test evidence.
- Passed: data and religious-content templates include source and license review fields.
- Passed: security issues are redirected to the private process in `SECURITY.md`.
- Passed: CODEOWNERS uses placeholder teams and repository-relative paths.

### Security and License Review

- Public security issue submission is disabled through `.github/ISSUE_TEMPLATE/config.yml`.
- Sensitive data redaction guidance is included in the templates and `SECURITY.md`.
- No secrets or restricted datasets were introduced.

### Known Limitations

- CODEOWNERS uses placeholder teams until the project owner assigns real owners.

### Follow-up Tasks

- Replace placeholder CODEOWNERS teams with real project ownership when available.

### Commit

- Pending focused commit creation
