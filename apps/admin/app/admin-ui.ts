import type {
  LicenseCreatePayload,
  LicensePolicyDecision,
  LicenseRecord,
  SourceCreatePayload,
  SourceRecord,
} from "./admin-data.js";

export type WarningTone = "critical" | "warning" | "info";

export type WarningCard = {
  readonly tone: WarningTone;
  readonly title: string;
  readonly detail: string;
};

export type SourceDraft = {
  readonly name: string;
  readonly sourceType: string;
  readonly owner: string;
  readonly website: string;
  readonly language: string;
  readonly country: string;
  readonly reliabilityLevel: string;
  readonly isActive: boolean;
};

export type LicenseDraft = {
  readonly licenseName: string;
  readonly licenseVersion: string;
  readonly status: string;
  readonly storagePermission: string;
  readonly embeddingPermission: string;
  readonly commercialUse: string;
  readonly redistribution: string;
  readonly attributionRequired: boolean;
  readonly attributionTemplate: string;
  readonly permissionDocumentKey: string;
  readonly validFrom: string;
  readonly validUntil: string;
  readonly notes: string;
};

export function validateSourceDraft(draft: SourceDraft): readonly string[] {
  const errors: string[] = [];
  if (!draft.name.trim()) {
    errors.push("Source name is required.");
  }
  if (!draft.sourceType.trim()) {
    errors.push("Source type is required.");
  }
  if (!draft.language.trim()) {
    errors.push("Language is required.");
  }
  const reliability = Number(draft.reliabilityLevel);
  if (!Number.isInteger(reliability) || reliability < 1 || reliability > 5) {
    errors.push("Reliability level must be an integer from 1 to 5.");
  }
  return errors;
}

export function validateLicenseDraft(draft: LicenseDraft): readonly string[] {
  const errors: string[] = [];
  if (!draft.licenseName.trim()) {
    errors.push("License name is required.");
  }
  if (!draft.status.trim()) {
    errors.push("License status is required.");
  }
  if (!draft.storagePermission.trim()) {
    errors.push("Storage permission is required.");
  }
  if (!draft.embeddingPermission.trim()) {
    errors.push("Embedding permission is required.");
  }
  if (!draft.commercialUse.trim()) {
    errors.push("Commercial use permission is required.");
  }
  if (!draft.redistribution.trim()) {
    errors.push("Redistribution permission is required.");
  }
  if (draft.attributionRequired && !draft.attributionTemplate.trim()) {
    errors.push(
      "Attribution template is required when attribution is mandatory.",
    );
  }
  if (
    draft.validFrom &&
    draft.validUntil &&
    draft.validUntil < draft.validFrom
  ) {
    errors.push("Valid until must be on or after valid from.");
  }
  return errors;
}

export function toSourcePayload(draft: SourceDraft): SourceCreatePayload {
  return {
    name: draft.name.trim(),
    source_type: draft.sourceType.trim(),
    owner: optionalString(draft.owner),
    website: optionalString(draft.website),
    language: draft.language.trim(),
    country: optionalString(draft.country),
    reliability_level: Number(draft.reliabilityLevel),
    is_active: draft.isActive,
  };
}

export function toLicensePayload(
  draft: LicenseDraft,
): LicenseCreatePayload | never {
  const errors = validateLicenseDraft(draft);
  if (errors.length > 0) {
    throw new Error(errors.join(" "));
  }
  return {
    license_name: draft.licenseName.trim(),
    license_version: optionalString(draft.licenseVersion),
    status: draft.status.trim(),
    storage_permission: draft.storagePermission.trim(),
    embedding_permission: draft.embeddingPermission.trim(),
    commercial_use: draft.commercialUse.trim(),
    redistribution: draft.redistribution.trim(),
    attribution_required: draft.attributionRequired,
    attribution_template: draft.attributionRequired
      ? draft.attributionTemplate.trim()
      : optionalString(draft.attributionTemplate),
    permission_document_key: optionalString(draft.permissionDocumentKey),
    valid_from: optionalString(draft.validFrom),
    valid_until: optionalString(draft.validUntil),
    notes: optionalString(draft.notes),
  };
}

export function buildSourceWarnings(
  source: SourceRecord,
  licenses: readonly LicenseRecord[],
): readonly WarningCard[] {
  const warnings: WarningCard[] = [];
  const activeLicenses = licenses.filter(
    (license) => license.status !== "expired",
  );
  if (activeLicenses.length === 0) {
    warnings.push({
      tone: "critical",
      title: "No active license coverage",
      detail:
        "New ingestion and publication should be blocked until a valid license is attached.",
    });
  }
  if (!source.is_active) {
    warnings.push({
      tone: "warning",
      title: "Source suspended",
      detail:
        "Suspended sources should not receive new documents and may affect downstream review queues.",
    });
  }
  if (licenses.some(isIncompleteLicense)) {
    warnings.push({
      tone: "critical",
      title: "Incomplete license metadata",
      detail:
        "Unknown rights or missing attribution details must be resolved before restricted operations continue.",
    });
  }
  return warnings;
}

export function buildLicenseWarnings(
  license: LicenseRecord,
  policy: LicensePolicyDecision | null,
): readonly WarningCard[] {
  const warnings: WarningCard[] = [];
  if (isIncompleteLicense(license)) {
    warnings.push({
      tone: "critical",
      title: "Incomplete permissions",
      detail: "This license has unknown, missing, or fail-closed fields.",
    });
  }
  if (!license.permission_document_key) {
    warnings.push({
      tone: "warning",
      title: "Permission evidence missing",
      detail:
        "No private permission document key is registered for this license.",
    });
  }
  if (license.valid_until) {
    warnings.push({
      tone: "info",
      title: "Expiry date recorded",
      detail: `This license expires on ${license.valid_until}. Review downstream impact before changing it.`,
    });
  }
  if (policy && !policy.workflow_allowed) {
    warnings.push({
      tone: "critical",
      title: `${capitalize(policy.workflow)} blocked`,
      detail: policy.reason_codes.join(", "),
    });
  }
  return warnings;
}

export function summarizeSuspensionImpact(
  source: SourceRecord,
  licenses: readonly LicenseRecord[],
): string {
  const incompleteCount = licenses.filter(isIncompleteLicense).length;
  const expiringCount = licenses.filter(
    (license) => license.valid_until !== null,
  ).length;
  return [
    `${source.name} will stop accepting new content when suspended.`,
    `${licenses.length} license version(s) remain attached for audit history.`,
    incompleteCount > 0
      ? `${incompleteCount} license record(s) already contain unknown or incomplete permissions.`
      : "No current license records are flagged as incomplete.",
    expiringCount > 0
      ? `${expiringCount} license record(s) carry expiry dates that may affect downstream retrieval or export.`
      : "No expiry dates are recorded on the attached licenses.",
  ].join(" ");
}

export function summarizePolicyDecision(policy: LicensePolicyDecision): string {
  const status = policy.workflow_allowed ? "allowed" : "blocked";
  return `${capitalize(policy.workflow)} is ${status} under ${policy.policy_version}. Reasons: ${policy.reason_codes.join(", ")}.`;
}

function isIncompleteLicense(license: LicenseRecord): boolean {
  return (
    license.status === "unknown" ||
    license.storage_permission === "unknown" ||
    license.embedding_permission === "unknown" ||
    license.commercial_use === "unknown" ||
    license.redistribution === "unknown" ||
    (license.attribution_required && !license.attribution_template)
  );
}

function optionalString(value: string): string | null {
  const normalized = value.trim();
  return normalized ? normalized : null;
}

function capitalize(value: string): string {
  return value ? `${value[0].toUpperCase()}${value.slice(1)}` : value;
}
