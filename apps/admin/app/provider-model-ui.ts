import type {
  ModelCreatePayload,
  ModelRecord,
  ProviderCreatePayload,
  ProviderRecord,
} from "./admin-data.js";

export type ProviderDraft = {
  readonly name: string;
  readonly providerType: string;
  readonly status: string;
  readonly baseUrl: string;
  readonly secretRef: string;
  readonly termsUrl: string;
  readonly dataPolicyJson: string;
};

export type ModelDraft = {
  readonly providerId: string;
  readonly modelName: string;
  readonly modelType: string;
  readonly status: string;
  readonly configurationJson: string;
  readonly allowListed: boolean;
  readonly fallbackModelId: string;
  readonly costLimitDailyUsd: string;
  readonly isDefault: boolean;
};

export function validateProviderDraft(
  draft: ProviderDraft,
): readonly string[] {
  const errors: string[] = [];
  if (!draft.name.trim()) {
    errors.push("Provider name is required.");
  }
  if (!draft.providerType.trim()) {
    errors.push("Provider type is required.");
  }
  if (!draft.status.trim()) {
    errors.push("Provider status is required.");
  }
  if (draft.baseUrl.trim()) {
    try {
      const parsed = new URL(draft.baseUrl.trim());
      if (!["http:", "https:"].includes(parsed.protocol)) {
        errors.push("Provider base URL must use http or https.");
      }
    } catch {
      errors.push("Provider base URL must be a valid absolute URL.");
    }
  }
  if (draft.termsUrl.trim()) {
    try {
      const parsed = new URL(draft.termsUrl.trim());
      if (!["http:", "https:"].includes(parsed.protocol)) {
        errors.push("Terms URL must use http or https.");
      }
    } catch {
      errors.push("Terms URL must be a valid absolute URL.");
    }
  }
  if (draft.dataPolicyJson.trim()) {
    try {
      const parsed = JSON.parse(draft.dataPolicyJson);
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
        errors.push("Provider data policy must be a JSON object.");
      }
    } catch {
      errors.push("Provider data policy must be valid JSON.");
    }
  }
  return errors;
}

export function validateModelDraft(
  draft: ModelDraft,
): readonly string[] {
  const errors: string[] = [];
  if (!draft.providerId.trim()) {
    errors.push("Provider selection is required.");
  }
  if (!draft.modelName.trim()) {
    errors.push("Model name is required.");
  }
  if (!draft.modelType.trim()) {
    errors.push("Model type is required.");
  }
  if (!draft.status.trim()) {
    errors.push("Model status is required.");
  }
  if (draft.configurationJson.trim()) {
    try {
      const parsed = JSON.parse(draft.configurationJson);
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
        errors.push("Model configuration must be a JSON object.");
      }
    } catch {
      errors.push("Model configuration must be valid JSON.");
    }
  }
  if (draft.costLimitDailyUsd.trim()) {
    const parsed = Number(draft.costLimitDailyUsd);
    if (!Number.isFinite(parsed) || parsed < 0) {
      errors.push("Daily cost limit must be zero or greater.");
    }
  }
  return errors;
}

export function toProviderPayload(
  draft: ProviderDraft,
): ProviderCreatePayload {
  return {
    name: draft.name.trim(),
    provider_type: draft.providerType.trim(),
    status: draft.status.trim(),
    base_url: optionalString(draft.baseUrl),
    secret_ref: optionalString(draft.secretRef),
    terms_url: optionalString(draft.termsUrl),
    data_policy_json: parseJsonObject(draft.dataPolicyJson),
  };
}

export function toModelPayload(draft: ModelDraft): ModelCreatePayload {
  return {
    provider_id: draft.providerId.trim(),
    model_name: draft.modelName.trim(),
    model_type: draft.modelType.trim(),
    status: draft.status.trim(),
    configuration: parseJsonObject(draft.configurationJson),
    allow_listed: draft.allowListed,
    fallback_model_id: optionalString(draft.fallbackModelId),
    cost_limit_daily_usd: optionalNumber(draft.costLimitDailyUsd),
    is_default: draft.isDefault,
  };
}

export function providerToDraft(provider: ProviderRecord): ProviderDraft {
  return {
    name: provider.name,
    providerType: provider.provider_type,
    status: provider.status,
    baseUrl: provider.base_url ?? "",
    secretRef: "",
    termsUrl: provider.terms_url ?? "",
    dataPolicyJson: JSON.stringify(provider.data_policy_json, null, 2),
  };
}

export function modelToDraft(model: ModelRecord): ModelDraft {
  return {
    providerId: model.provider_id,
    modelName: model.model_name,
    modelType: model.model_type,
    status: model.status,
    configurationJson: JSON.stringify(model.configuration, null, 2),
    allowListed: model.allow_listed,
    fallbackModelId: model.fallback_model_id ?? "",
    costLimitDailyUsd:
      model.cost_limit_daily_usd === null
        ? ""
        : String(model.cost_limit_daily_usd),
    isDefault: model.is_default,
  };
}

export function summarizeDisableImpact(provider: ProviderRecord): string {
  if (provider.disable_impact.active_model_count === 0) {
    return "No enabled models depend on this provider.";
  }
  const impacted = provider.disable_impact.fallback_readiness.map((item) =>
    item.fallback_ready
      ? `${item.model_type}: fallback ready`
      : `${item.model_type}: no enabled fallback`,
  );
  return `${provider.disable_impact.active_model_count} enabled model(s) are affected. ${impacted.join(". ")}.`;
}

export function summarizeModelRouting(model: ModelRecord): string {
  const fallback = model.fallback_model_name
    ? `Fallback: ${model.fallback_model_name}.`
    : "No fallback configured.";
  const cost = model.cost_limit_daily_usd !== null
    ? ` Daily limit: $${model.cost_limit_daily_usd.toFixed(2)}.`
    : "";
  return `${model.is_default ? "Default route." : "Secondary route."} ${fallback}${cost}`;
}

function parseJsonObject(raw: string): Record<string, unknown> {
  const normalized = raw.trim();
  if (!normalized) {
    return {};
  }
  return JSON.parse(normalized) as Record<string, unknown>;
}

function optionalString(value: string): string | null {
  const normalized = value.trim();
  return normalized ? normalized : null;
}

function optionalNumber(value: string): number | null {
  const normalized = value.trim();
  if (!normalized) {
    return null;
  }
  return Number(normalized);
}
