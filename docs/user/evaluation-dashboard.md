# Evaluation Dashboard

The Evaluation Dashboard allows administrators and scholar reviewers to analyze, compare, and trace benchmark runs. It assists in detecting accuracy regressions, performance degradation, and safety compliance drifts.

## Permissions and Access Controls

- **Access Level**: Accessing evaluation dashboards, run lists, and reports requires `evaluations.read` clearance (held by roles such as `admin`, `senior_scholar`, or `auditor`).
- **Private Case Masking**: In alignment with the Zayd data governance policy, any private case details (such as restricted question text, reference texts, or evaluator notes) are hidden from the dashboard when accessed by users lacking `evaluations.read` permissions. Public reports exclude private benchmark runs and cases completely.

## Core Capabilities

1. **Dashboard Controls**: Enters temporary Bearer Token in memory, fetching run config and listings directly from the backend.
2. **Side-by-Side Metadata**: Displays reproducing configurations (git commit, random seed, dataset metadata, embedding and reranker versions) for comparable runs.
3. **Difference Highlighting**:
   - **Regressions**: Highlights cases that successfully passed on the base run but failed on the target run.
   - **Improvements**: Highlights cases that failed on the base run but passed on the target run.
4. **Overall Pass Rates**: Visualizes raw differences in accuracy between the selected model versions.
5. **Interactive Search and Filtering**: Filter results by topic, case type (e.g. `abstention`, `risk_routing`), status (passed, failed), or search for specific case keys.
6. **Downloadable Reports**: Exports complete comparison schemas as JSON reports.
