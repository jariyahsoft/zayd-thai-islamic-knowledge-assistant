# TASK-00-03 — Add Community Governance Files

## Status

`TODO`

## Model Tier

Tier B

## Related Requirements

- SRS §39 Open-source Governance
- SRS §40 Community Files
- SRS §41 Contribution Workflow
- SRS §42 Data Contribution Workflow
- SRS §30 Security Requirements

## Objective

Create the community, governance, support and security documents needed for transparent and safe open-source collaboration.

## Scope

### In Scope

Create or complete:

```text
README.md
CONTRIBUTING.md
CODE_OF_CONDUCT.md
GOVERNANCE.md
SECURITY.md
SUPPORT.md
ROADMAP.md
CHANGELOG.md
```

The documents must define:

- Contributor, reviewer, maintainer, security maintainer, Islamic Content Board and Data Steward roles.
- Pull request and review expectations.
- RFC requirements for major changes.
- Private security reporting.
- Religious-content and dataset contribution requirements.
- Support boundaries and non-emergency response expectations.

### Out of Scope

- Creating issue templates.
- Configuring GitHub permissions.
- Naming individual maintainers.
- Defining the complete product roadmap beyond current approved milestones.

## Dependencies

- TASK-00-02

## Expected Files

```text
README.md
CONTRIBUTING.md
CODE_OF_CONDUCT.md
GOVERNANCE.md
SECURITY.md
SUPPORT.md
ROADMAP.md
CHANGELOG.md
```

## Functional Requirements

1. `README.md` must explain the product purpose, limitations and open-source structure.
2. `CONTRIBUTING.md` must describe local setup at a high level, branch naming, commits, tests and pull requests.
3. `SECURITY.md` must direct vulnerability reports to a private channel and prohibit public disclosure before remediation.
4. `GOVERNANCE.md` must describe decision roles and RFC-triggering changes.
5. Data contributions must require source, owner, license, permission evidence, checksum and validation report.
6. Religious-content changes must require source citation, madhhab metadata and content review.
7. `CHANGELOG.md` must follow a versioned changelog format.

## Technical Requirements

- Use clear Markdown headings.
- Avoid claiming response-time guarantees that the project cannot maintain.
- Include links between community documents.
- Include a lightweight RFC template path recommendation such as `docs/rfcs/`.

## Security Requirements

- Security reports must not be filed through public issues.
- Documentation must warn contributors not to include private user conversations, secrets or restricted datasets in bug reports.
- Define redaction requirements for logs and screenshots.

## Acceptance Criteria

- [ ] All eight files exist and are internally consistent.
- [ ] Governance roles and decision flow are documented.
- [ ] Security reporting has a private path placeholder.
- [ ] Dataset and religious-content contributions require license and review evidence.
- [ ] Project limitations state that Zayd is not an automated fatwa authority.
- [ ] Documentation does not contain real personal data or credentials.

## Required Tests

### Documentation Checks

- Markdown lint passes.
- Internal file links resolve.
- A new contributor can identify setup, contribution, security and support instructions from the README.

### Human Review

- Maintainer review.
- Islamic Content Board or designated content-policy review for product-positioning statements.

## Documentation Updates

This task creates the documentation listed above.

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- Pending

### Commands and Tests Executed

- Pending

### Acceptance Criteria Result

- Pending

### Security and License Review

- Pending

### Known Limitations

- Pending

### Follow-up Tasks

- Pending

### Commit

- Pending
