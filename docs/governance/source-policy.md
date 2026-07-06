# Source Policy

## Overview

This document defines the governance rules for knowledge source management in the Zayd platform. These policies ensure that only reliable, properly licensed, and verified Islamic knowledge sources are ingested and made available for retrieval.

## Source Reliability Levels

Every source must be assigned a reliability level from 1 (lowest) to 5 (highest) based on scholarly consensus, verification methodology, and historical reputation.

### Level 5 — Canonical and Universally Accepted

**Criteria:**
- Canonical Islamic texts with established authenticity
- Translations by recognized scholarly bodies
- Material that has undergone rigorous peer review by multiple qualified scholars

**Examples:**
- Sahih Bukhari and Sahih Muslim (primary hadith collections)
- Authenticated Quran translations by established Islamic centers
- Works by recognized classical scholars (e.g., Al-Nawawi, Ibn Kathir)

**Usage:** Can be used without additional review for retrieval and citation

### Level 4 — High Quality with Minor Variations

**Criteria:**
- Well-regarded hadith collections beyond the two Sahih
- Translations by recognized individual scholars with formal credentials
- Contemporary scholarly works published by established institutions

**Examples:**
- Sunan Abu Dawud, Sunan An-Nasa'i, Jami' At-Tirmidhi
- Fiqh references from established madhahib authorities
- Modern scholarly works with peer review

**Usage:** Suitable for general retrieval with standard citation

### Level 3 — Accepted with Caveats

**Criteria:**
- Secondary sources that compile from primary references
- Educational materials from recognized institutions
- Historical works that require contextual interpretation

**Examples:**
- Compiled fiqh encyclopedias
- Educational curricula from Islamic universities
- Historical commentary works

**Usage:** Requires explicit citation of original sources where possible

### Level 2 — Supplementary and Opinion-Based

**Criteria:**
- Contemporary interpretations and personal scholarly opinions
- Regional fatwa collections without broader consensus
- Educational materials for general audiences

**Examples:**
- Individual contemporary fatwa websites
- Regional Islamic council rulings
- General Islamic education books

**Usage:** Must be clearly labeled as supplementary; not used for high-risk queries

### Level 1 — Under Review or Unverified

**Criteria:**
- Newly submitted sources pending scholarly verification
- Community-contributed content awaiting review
- Sources with known accuracy concerns

**Examples:**
- Crowd-sourced translations
- Personal blog posts
- Unverified community submissions

**Usage:** Not used for public retrieval until elevated to Level 2 or higher

## Source Active Status

### Active Sources (`is_active: true`)

- Can be assigned to new documents during ingestion
- Appear in admin source selection interfaces
- Documents from active sources flow through normal review and publishing workflows

### Suspended Sources (`is_active: false`)

**Suspension Triggers:**
- License status changed to "revoked" or "uncertain"
- Scholarly review identified accuracy concerns
- Publisher requested removal
- Copyright or permission issues discovered
- Source reliability downgraded below operational threshold

**Impact of Suspension:**

1. **Immediate Effects:**
   - Source cannot be assigned to new document uploads
   - Source appears with warning badge in admin interfaces
   - Suspension event recorded in audit log with actor and timestamp

2. **Existing Documents:**
   - Already published documents remain retrievable unless explicitly archived
   - Documents in review queue are flagged for re-evaluation
   - Admin UI displays suspension notice when viewing affected documents

3. **Required Actions:**
   - Admin must decide: archive existing documents, maintain with warning, or replace with alternative source
   - Incident management workflow may be triggered for high-impact sources
   - Affected users may be notified if suspension affects published content

## Source Type Classification

Sources must be classified by type to enable proper filtering and madhhab alignment:

- **hadith** — Hadith collections and authentication
- **quran** — Quran text and translations
- **tafsir** — Quranic exegesis and commentary
- **fiqh** — Islamic jurisprudence and legal rulings
- **aqeedah** — Islamic creed and theology
- **sirah** — Biography of the Prophet (PBUH)
- **history** — Islamic history and scholarly biographies
- **contemporary** — Modern scholarly works and fatwa
- **educational** — Teaching materials and curricula

Accurate classification enables:
- Madhhab-specific filtering (e.g., Shafi'i fiqh sources for Thai users)
- Query routing to appropriate source types
- Reliability weighting by domain

## Language and Regional Policy

### Language Requirements

- **Primary Language:** Each source must declare its primary language (ISO 639-1 code)
- **Thai Language Priority:** Thai translations from canonical sources receive priority for retrieval
- **Arabic Originals:** Arabic source texts are preserved as authoritative references
- **Multi-language Support:** Sources may reference original language when providing translations

### Regional Adaptation

- **Country Field:** Optional ISO 3166-1 country code indicating regional context
- **Thai Context:** Sources adapted for Thai Muslim community receive special consideration
- **Madhhab Alignment:** Sources explicitly state madhhab affiliation when applicable

## License and Permission Compliance

Every source must have an associated license record (managed via TASK-04-02) that specifies:

- **Storage Permission:** Whether the source text can be stored in the system
- **Embedding Permission:** Whether the source can be used to create vector embeddings
- **Commercial Use:** Whether the source permits commercial deployment
- **Attribution Requirements:** How the source must be cited in answers

**Policy Rules:**

1. **No document ingestion** without a valid, non-expired license record
2. **Embedding creation blocked** if license prohibits it
3. **Published citations** must include attribution per license terms
4. **License changes trigger review** of all affected published documents

See [License Registry Documentation](./license-policy.md) for full license governance rules (TASK-04-03).

## Ownership and Provenance

### Owner Field

The optional `owner` field records:
- Publisher name for printed works
- Organization name for institutional sources
- Translator or author for original works
- "Unknown" or "Public Domain" when provenance is unclear

**Usage:**
- Displayed in citations
- Used for copyright compliance
- Helps trace source lineage

### Website Field

Optional URL to the source's authoritative online location:
- Official publisher website
- Institutional repository
- Digital library catalog entry

**Purpose:**
- Verification reference
- User access to original material
- Provenance tracking

## Source Creation Workflow

1. **Admin Submission:**
   - Admin with `licenses.manage` permission creates source record
   - Minimum required: name, source_type, language, reliability_level
   - Owner, website, country, and active status are optional

2. **License Association:**
   - Before ingesting documents, admin must create associated license record (TASK-04-02)
   - License must permit storage and embedding if documents will be indexed

3. **Scholarly Review (for Levels 3-5):**
   - High-reliability sources should undergo verification by qualified reviewer
   - Verification confirms authenticity, reliability rating, and proper attribution

4. **Activation:**
   - Source marked `is_active: true` after license and verification complete
   - Source available for document ingestion

## Source Suspension Workflow

1. **Trigger Identification:**
   - License status changed
   - Scholarly review found concerns
   - Publisher request
   - Community feedback escalation

2. **Suspension Execution:**
   - Admin with `licenses.manage` permission calls suspend endpoint
   - System sets `is_active: false` and records audit entry
   - Downstream services notified (via future event system)

3. **Impact Assessment:**
   - Admin identifies all documents from suspended source
   - Reviews published documents for continued accuracy
   - Determines retention vs. archival policy

4. **Resolution:**
   - If concerns addressed: reactivate source via update endpoint
   - If unresolved: archive affected documents and notify users
   - Incident report created for high-impact suspensions

## RBAC and Audit Requirements

### Required Permissions

- **Read Sources:** `licenses.read` permission
  - View source details
  - Search and filter sources
  - Export source lists

- **Manage Sources:** `licenses.manage` permission
  - Create new sources
  - Update source metadata
  - Suspend sources
  - All read operations

### MFA Requirement

Source management operations require MFA enrollment and verification for users with privileged roles (`admin`, `senior_scholar`, `reviewer`).

### Audit Trail

All source mutations are recorded in the immutable audit log:

- **Create:** Logs new source with name, type, language, reliability, active status
- **Update:** Logs before/after values for name and reliability level
- **Suspend:** Logs source name, active status change, and suspension reason

Audit records include:
- Actor user ID
- Action name
- Resource ID (source UUID)
- Request ID and trace ID
- Timestamp
- Sanitized metadata (no secrets)

## Compliance and Best Practices

### Scholarly Verification

- High-reliability sources (Levels 4-5) should be verified by a qualified Islamic scholar
- Verification confirms authenticity, proper attribution, and accuracy of metadata
- Verification results stored in internal review records (future enhancement)

### License Compliance

- Never ingest documents without valid license record
- Respect embedding and commercial use restrictions
- Provide required attribution in all citations
- Monitor license expiration dates and renew as needed

### Privacy and Security

- Source metadata is not considered sensitive but should not include:
  - Personal contact information of submitters
  - Internal cost or contract terms
  - Unpublished negotiation details
- Permission document storage keys are kept private (managed via license records)

### Community Feedback

- User reports of source accuracy concerns trigger review workflow
- Feedback routed through incident management (TASK-11-03)
- High-severity incidents may result in immediate suspension

## Future Enhancements

Planned for later milestones:

- **Source Reputation Scoring:** Aggregate citation accuracy and user feedback
- **Automated License Monitoring:** Alert on upcoming license expirations
- **Source Versioning:** Track source edition changes over time
- **Madhhab Tagging:** Explicit source-to-madhhab associations for better filtering
- **Scholar Endorsements:** Record which scholars have verified each source

## Related Documentation

- [Sources API](../api/sources.md) — API reference for source management
- [License Policy](./license-policy.md) — License governance rules (TASK-04-03)
- [RBAC Documentation](../security/rbac.md) — Permission model
- [Audit Logging](../security/audit-logging.md) — Audit trail details
- [SRS §23.2](../02_requirements/SRS.md#232-source) — Source schema specification
