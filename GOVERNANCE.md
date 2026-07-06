# Governance

## Purpose

This document explains how Zayd makes project decisions for source code, data, review policy, and public-facing documentation.

## Roles

- Contributor: proposes changes and supplies required evidence.
- Reviewer: checks correctness, tests, and task-specific requirements.
- Maintainer: owns merge decisions and release coordination.
- Security Maintainer: receives private security reports and coordinates remediation.
- Islamic Content Board: reviews madhhab-sensitive, religious-content, and product-positioning changes.
- Data Steward: reviews source, license, permission, and retention evidence for datasets.

## Decision Process

Routine changes may be approved by the relevant maintainer or reviewer.
Major changes require an RFC and the applicable domain review before merge.

RFC-triggering changes include:

- changing license structure or rights statements
- changing database or vector-store assumptions
- changing API contracts or public task workflows
- changing madhhab policy or answer safety policy
- adding contentious datasets or new content classes
- changing governance or contribution rules

## RFC Guidance

Create RFCs under [`docs/rfcs/`](docs/rfcs/) using a lightweight structure that includes:

- title
- motivation
- proposal
- alternatives
- security impact
- religious-content impact
- data-license impact
- migration plan

## Review Expectations

- Pull requests should reference the affected task or requirement.
- Reviewers should confirm source, license, and review evidence when content or data changes are involved.
- Maintainers should not merge a change that lacks the required policy review.

## Escalation

Escalate security incidents through [`SECURITY.md`](SECURITY.md).
Escalate community conduct issues through the maintainer path documented in [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

