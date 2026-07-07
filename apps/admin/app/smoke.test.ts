import { describe, expect, it } from "vitest";
import {
  buildLicenseWarnings,
  buildSourceWarnings,
  summarizePolicyDecision,
  summarizeSuspensionImpact,
  toSourcePayload,
  validateLicenseDraft,
  validateSourceDraft,
} from "./admin-ui.js";

describe("admin source and license UI helpers", () => {
  it("validates source and license drafts", () => {
    expect(
      validateSourceDraft({
        name: "",
        sourceType: "",
        owner: "",
        website: "",
        language: "",
        country: "",
        reliabilityLevel: "9",
        isActive: true,
      }),
    ).toEqual([
      "Source name is required.",
      "Source type is required.",
      "Language is required.",
      "Reliability level must be an integer from 1 to 5.",
    ]);

    expect(
      validateLicenseDraft({
        licenseName: "",
        licenseVersion: "",
        status: "",
        storagePermission: "",
        embeddingPermission: "",
        commercialUse: "",
        redistribution: "",
        attributionRequired: true,
        attributionTemplate: "",
        permissionDocumentKey: "",
        validFrom: "2026-07-10",
        validUntil: "2026-07-01",
        notes: "",
      }),
    ).toEqual([
      "License name is required.",
      "License status is required.",
      "Storage permission is required.",
      "Embedding permission is required.",
      "Commercial use permission is required.",
      "Redistribution permission is required.",
      "Attribution template is required when attribution is mandatory.",
      "Valid until must be on or after valid from.",
    ]);
  });

  it("builds warnings and summaries for incomplete records", () => {
    const source = {
      id: "source-1",
      name: "Thai Library",
      source_type: "fiqh",
      owner: "Publisher",
      website: null,
      language: "th",
      country: "TH",
      reliability_level: 4,
      is_active: false,
      created_by: "user-1",
      updated_by: null,
      created_at: "2026-07-07T00:00:00Z",
      updated_at: "2026-07-07T00:00:00Z",
    };
    const license = {
      id: "license-1",
      source_id: "source-1",
      license_name: "Agreement",
      license_version: "2026-01",
      status: "unknown",
      storage_permission: "unknown",
      embedding_permission: "unknown",
      commercial_use: "conditional",
      redistribution: "unknown",
      attribution_required: true,
      attribution_template: null,
      permission_document_key: null,
      valid_from: "2026-01-01",
      valid_until: "2026-12-31",
      notes: null,
      created_by: "user-1",
      updated_by: null,
      created_at: "2026-07-07T00:00:00Z",
      updated_at: "2026-07-07T00:00:00Z",
      row_version: 1,
    };
    const policy = {
      license_id: "license-1",
      source_id: "source-1",
      workflow: "retrieval",
      policy_version: "license-policy-engine-v1",
      evaluated_on: "2026-07-07",
      source_license_version: "2026-01",
      workflow_allowed: false,
      llm_override_allowed: false,
      reason_codes: ["WORKFLOW_RETRIEVAL_DENIED", "LICENSE_STATUS_UNKNOWN"],
      actions: [],
    };

    expect(
      buildSourceWarnings(source, [license]).length,
    ).toBeGreaterThanOrEqual(2);
    expect(buildLicenseWarnings(license, policy)[0]?.title).toBe(
      "Incomplete permissions",
    );
    expect(summarizeSuspensionImpact(source, [license])).toContain(
      "will stop accepting new content",
    );
    expect(summarizePolicyDecision(policy)).toContain("Retrieval");
  });

  it("maps a valid source draft into an API payload", () => {
    expect(
      toSourcePayload({
        name: " Thai Library ",
        sourceType: "fiqh",
        owner: "",
        website: "https://example.com",
        language: "th",
        country: "TH",
        reliabilityLevel: "4",
        isActive: true,
      }),
    ).toEqual({
      name: "Thai Library",
      source_type: "fiqh",
      owner: null,
      website: "https://example.com",
      language: "th",
      country: "TH",
      reliability_level: 4,
      is_active: true,
    });
  });
});
