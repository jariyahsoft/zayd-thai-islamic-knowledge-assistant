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
import {
  modelToDraft,
  providerToDraft,
  summarizeDisableImpact,
  summarizeModelRouting,
  toModelPayload,
  toProviderPayload,
  validateModelDraft,
  validateProviderDraft,
} from "./provider-model-ui.js";
import { sortRoles, summarizeUserRisk } from "./user-admin-ui.js";

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

  it("validates provider and model drafts and maps payloads", () => {
    expect(
      validateProviderDraft({
        name: "",
        providerType: "",
        status: "",
        baseUrl: "notaurl",
        secretRef: "",
        termsUrl: "https://example.com",
        dataPolicyJson: "[]",
      }),
    ).toEqual([
      "Provider name is required.",
      "Provider type is required.",
      "Provider status is required.",
      "Provider base URL must be a valid absolute URL.",
      "Provider data policy must be a JSON object.",
    ]);

    expect(
      validateModelDraft({
        providerId: "",
        modelName: "",
        modelType: "",
        status: "",
        configurationJson: "[]",
        allowListed: true,
        fallbackModelId: "",
        costLimitDailyUsd: "-1",
        isDefault: false,
      }),
    ).toEqual([
      "Provider selection is required.",
      "Model name is required.",
      "Model type is required.",
      "Model status is required.",
      "Model configuration must be a JSON object.",
      "Daily cost limit must be zero or greater.",
    ]);

    expect(
      toProviderPayload({
        name: " OpenAI ",
        providerType: "llm",
        status: "enabled",
        baseUrl: "https://api.example.com",
        secretRef: " vault://provider/openai ",
        termsUrl: "",
        dataPolicyJson: '{"classification":"restricted"}',
      }),
    ).toEqual({
      name: "OpenAI",
      provider_type: "llm",
      status: "enabled",
      base_url: "https://api.example.com",
      secret_ref: "vault://provider/openai",
      terms_url: null,
      data_policy_json: { classification: "restricted" },
    });

    expect(
      toModelPayload({
        providerId: "provider-1",
        modelName: " GPT-4 ",
        modelType: "llm",
        status: "enabled",
        configurationJson: '{"temperature":0}',
        allowListed: true,
        fallbackModelId: "",
        costLimitDailyUsd: "5.5",
        isDefault: true,
      }),
    ).toEqual({
      provider_id: "provider-1",
      model_name: "GPT-4",
      model_type: "llm",
      status: "enabled",
      configuration: { temperature: 0 },
      allow_listed: true,
      fallback_model_id: null,
      cost_limit_daily_usd: 5.5,
      is_default: true,
    });
  });

  it("summarizes provider/model impact and user-admin state", () => {
    const provider = {
      id: "provider-1",
      name: "OpenAI",
      provider_type: "llm",
      status: "enabled",
      base_url: "https://api.example.com",
      terms_url: null,
      data_policy_json: {},
      secret_configured: true,
      secret_mask: "configured",
      created_by: "user-1",
      updated_by: null,
      created_at: "2026-07-10T00:00:00Z",
      updated_at: "2026-07-10T00:00:00Z",
      row_version: 2,
      model_count: 2,
      active_model_count: 1,
      disable_impact: {
        provider_id: "provider-1",
        provider_name: "OpenAI",
        active_model_count: 1,
        impacted_model_types: ["llm"],
        fallback_readiness: [
          {
            model_type: "llm",
            active_model_count: 1,
            alternative_model_count: 0,
            fallback_ready: false,
          },
        ],
        safe_to_disable: false,
      },
    };
    const model = {
      id: "model-1",
      provider_id: "provider-1",
      provider_name: "OpenAI",
      provider_status: "enabled",
      model_name: "gpt-4",
      model_type: "llm",
      configuration: { temperature: 0 },
      allow_listed: true,
      fallback_model_id: null,
      fallback_model_name: null,
      cost_limit_daily_usd: 3,
      is_default: true,
      status: "enabled",
      created_by: "user-1",
      created_at: "2026-07-10T00:00:00Z",
      updated_at: "2026-07-10T00:00:00Z",
      row_version: 1,
    };
    const adminUser = {
      id: "user-1",
      email: "admin@example.com",
      display_name: "Admin",
      status: "active",
      roles: ["admin", "user"],
      active_session_count: 2,
      last_login_at: "2026-07-10T00:00:00Z",
      created_at: "2026-07-10T00:00:00Z",
      updated_at: "2026-07-10T00:00:00Z",
      row_version: 1,
      last_admin_guarded: true,
    };

    expect(providerToDraft(provider).secretRef).toBe("");
    expect(modelToDraft(model).costLimitDailyUsd).toBe("3");
    expect(summarizeDisableImpact(provider)).toContain("no enabled fallback");
    expect(summarizeModelRouting(model)).toContain("Default route.");
    expect(sortRoles(adminUser.roles)).toEqual(["admin", "user"]);
    expect(summarizeUserRisk(adminUser)).toContain("final active admin");
  });
});
