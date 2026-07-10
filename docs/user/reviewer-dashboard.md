# Reviewer Dashboard

## Purpose

The reviewer dashboard gives back-office reviewers a mobile-safe summary of their current document-review workload without exposing full document content by default.

## What It Shows

The dashboard pulls authorized data from `GET /reviews/dashboard` and presents:

- Visible queue count
- Pending unassigned work
- Work assigned to the current reviewer
- Overdue active work
- Documents in `changes_requested`
- Open feedback count and triage items for roles that can read feedback

The queue preview shows only compact metadata:

- document title
- review level
- status
- priority
- language
- madhhab
- due date
- whether a reviewer is assigned

## Filters

Reviewers can switch between:

- All visible work
- My assigned work
- Overdue work

They can also filter by queue status. The dashboard keeps the page size small for fast mobile use and links to the full queue for deeper review workflows.

## Authorization

Server-side RBAC remains authoritative.

- `documents.review` is required to open the dashboard API.
- Queue visibility still follows the review-queue specialization rules.
- Feedback triage data is returned only for roles that have `feedback.read`.

This means a role such as `translator` may still see document-review counts and tasks it is allowed to review, but it must not receive feedback queue data.

## Privacy and Safety

- The dashboard does not expose full feedback notes in the summary view.
- It does not expose raw extracted document text in queue cards.
- It uses only minimal metadata needed for triage and prioritization.
- Full review actions remain in later task workspaces.

## Main API

- `GET /reviews/dashboard`

Supported query parameters mirror the review queue:

- `language`
- `madhhab`
- `content_type`
- `status`
- `priority`
- `assigned_to`
- `review_level`
- `due_before`
- `due_after`
- `limit`
- `offset`
- `feedback_limit`
