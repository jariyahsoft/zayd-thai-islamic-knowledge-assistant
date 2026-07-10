"use client";

import type { CSSProperties, ReactElement } from "react";
import { startTransition, useState } from "react";
import type {
  LicensePolicyDecision,
  LicenseRecord,
  SourceRecord,
} from "./admin-data.js";
import {
  createLicense,
  createSource,
  getPermissionDocumentMetadata,
  getPolicyDecision,
  listLicenses,
  listSources,
  replaceLicense,
  suspendSource,
  updateSource,
} from "./admin-data.js";
import {
  buildLicenseWarnings,
  buildSourceWarnings,
  summarizePolicyDecision,
  summarizeSuspensionImpact,
  toLicensePayload,
  toSourcePayload,
  validateLicenseDraft,
  validateSourceDraft,
  type LicenseDraft,
  type SourceDraft,
} from "./admin-ui.js";

const SOURCE_INITIAL_DRAFT: SourceDraft = {
  name: "",
  sourceType: "",
  owner: "",
  website: "",
  language: "th",
  country: "",
  reliabilityLevel: "4",
  isActive: true,
};

const LICENSE_INITIAL_DRAFT: LicenseDraft = {
  licenseName: "",
  licenseVersion: "",
  status: "persistent_private",
  storagePermission: "allowed",
  embeddingPermission: "allowed",
  commercialUse: "conditional",
  redistribution: "prohibited",
  attributionRequired: true,
  attributionTemplate: "",
  permissionDocumentKey: "",
  validFrom: "",
  validUntil: "",
  notes: "",
};

type Notice = {
  readonly tone: "success" | "error" | "info";
  readonly message: string;
};

type DerivedState = {
  readonly licenses: readonly LicenseRecord[];
  readonly policy: LicensePolicyDecision | null;
  readonly permissionDocumentKey: string | null;
};

export function SourceLicenseAdminConsole(props: {
  readonly apiBaseUrl: string;
}): ReactElement {
  const [token, setToken] = useState("");
  const [query, setQuery] = useState("");
  const [workflow, setWorkflow] = useState("retrieval");
  const [busyMessage, setBusyMessage] = useState<string | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [sources, setSources] = useState<readonly SourceRecord[]>([]);
  const [selectedSourceId, setSelectedSourceId] = useState<string | null>(null);
  const [derivedBySource, setDerivedBySource] = useState<
    Record<string, DerivedState>
  >({});
  const [sourceDraft, setSourceDraft] =
    useState<SourceDraft>(SOURCE_INITIAL_DRAFT);
  const [sourceEditDrafts, setSourceEditDrafts] = useState<
    Record<string, SourceDraft>
  >({});
  const [licenseDraft, setLicenseDraft] = useState<LicenseDraft>(
    LICENSE_INITIAL_DRAFT,
  );
  const [replacementDrafts, setReplacementDrafts] = useState<
    Record<string, LicenseDraft>
  >({});

  const selectedSource =
    sources.find((source) => source.id === selectedSourceId) ?? null;
  const selectedDerived = selectedSource
    ? derivedBySource[selectedSource.id]
    : undefined;
  const licenses = selectedDerived?.licenses ?? [];
  const selectedLicense = licenses[0] ?? null;
  const policy = selectedDerived?.policy ?? null;
  const permissionDocumentKey = selectedDerived?.permissionDocumentKey ?? null;
  const sourceEditDraft = selectedSource
    ? (sourceEditDrafts[selectedSource.id] ?? sourceToDraft(selectedSource))
    : SOURCE_INITIAL_DRAFT;

  async function refreshSources(): Promise<void> {
    setBusyMessage("Loading sources...");
    try {
      const nextSources = await listSources(
        props.apiBaseUrl,
        token.trim(),
        query.trim(),
      );
      setSources(nextSources);
      setSourceEditDrafts((current) => {
        const next: Record<string, SourceDraft> = {};
        for (const source of nextSources) {
          next[source.id] = current[source.id] ?? sourceToDraft(source);
        }
        return next;
      });
      setSelectedSourceId((current) =>
        current && nextSources.some((source) => source.id === current)
          ? current
          : (nextSources[0]?.id ?? null),
      );
      setNotice(null);
    } catch (error) {
      setNotice({ tone: "error", message: errorMessage(error) });
      setSources([]);
    } finally {
      setBusyMessage(null);
    }
  }

  async function refreshLicenses(sourceId: string): Promise<void> {
    setBusyMessage("Loading licenses...");
    try {
      const nextLicenses = await listLicenses(
        props.apiBaseUrl,
        token.trim(),
        sourceId,
      );
      setDerivedBySource((current) => ({
        ...current,
        [sourceId]: {
          licenses: nextLicenses,
          policy: current[sourceId]?.policy ?? null,
          permissionDocumentKey:
            current[sourceId]?.permissionDocumentKey ?? null,
        },
      }));
      setReplacementDrafts((current) => {
        const drafts = { ...current };
        for (const license of nextLicenses) {
          drafts[license.id] = licenseToDraft(license);
        }
        return drafts;
      });
      if (nextLicenses[0]) {
        await refreshDerived(sourceId, nextLicenses[0].id);
      } else {
        setDerivedBySource((current) => ({
          ...current,
          [sourceId]: {
            licenses: [],
            policy: null,
            permissionDocumentKey: null,
          },
        }));
      }
      setNotice(null);
    } catch (error) {
      setNotice({ tone: "error", message: errorMessage(error) });
      setDerivedBySource((current) => ({
        ...current,
        [sourceId]: {
          licenses: [],
          policy: null,
          permissionDocumentKey: null,
        },
      }));
    } finally {
      setBusyMessage(null);
    }
  }

  async function refreshDerived(
    sourceId: string,
    licenseId: string,
  ): Promise<void> {
    try {
      const [decision, permission] = await Promise.all([
        getPolicyDecision(props.apiBaseUrl, token.trim(), licenseId, workflow),
        getPermissionDocumentMetadata(
          props.apiBaseUrl,
          token.trim(),
          licenseId,
        ).catch(() => null),
      ]);
      setDerivedBySource((current) => ({
        ...current,
        [sourceId]: {
          licenses: current[sourceId]?.licenses ?? [],
          policy: decision,
          permissionDocumentKey: permission
            ? permission.permission_document_key
            : null,
        },
      }));
    } catch (error) {
      setDerivedBySource((current) => ({
        ...current,
        [sourceId]: {
          licenses: current[sourceId]?.licenses ?? [],
          policy: null,
          permissionDocumentKey: null,
        },
      }));
      setNotice({ tone: "error", message: errorMessage(error) });
    }
  }

  async function submitCreateSource(): Promise<void> {
    const errors = validateSourceDraft(sourceDraft);
    if (errors.length > 0) {
      setNotice({ tone: "error", message: errors.join(" ") });
      return;
    }
    setBusyMessage("Creating source...");
    try {
      const source = await createSource(
        props.apiBaseUrl,
        token.trim(),
        toSourcePayload(sourceDraft),
      );
      setSourceDraft(SOURCE_INITIAL_DRAFT);
      setSelectedSourceId(source.id);
      setNotice({ tone: "success", message: `Source ${source.name} created.` });
      await refreshSources();
      await refreshLicenses(source.id);
    } catch (error) {
      setNotice({ tone: "error", message: errorMessage(error) });
    } finally {
      setBusyMessage(null);
    }
  }

  async function submitUpdateSource(): Promise<void> {
    if (!selectedSource) {
      return;
    }
    const errors = validateSourceDraft(sourceEditDraft);
    if (errors.length > 0) {
      setNotice({ tone: "error", message: errors.join(" ") });
      return;
    }
    setBusyMessage("Saving source...");
    try {
      await updateSource(
        props.apiBaseUrl,
        token.trim(),
        selectedSource.id,
        toSourcePayload(sourceEditDraft),
      );
      setNotice({
        tone: "success",
        message: `Source ${selectedSource.name} updated.`,
      });
      await refreshSources();
    } catch (error) {
      setNotice({ tone: "error", message: errorMessage(error) });
    } finally {
      setBusyMessage(null);
    }
  }

  async function submitSuspendSource(): Promise<void> {
    if (!selectedSource) {
      return;
    }
    setBusyMessage("Suspending source...");
    try {
      await suspendSource(props.apiBaseUrl, token.trim(), selectedSource.id);
      setNotice({
        tone: "success",
        message: `Source ${selectedSource.name} suspended.`,
      });
      await refreshSources();
    } catch (error) {
      setNotice({ tone: "error", message: errorMessage(error) });
    } finally {
      setBusyMessage(null);
    }
  }

  async function submitCreateLicense(): Promise<void> {
    if (!selectedSource) {
      setNotice({
        tone: "error",
        message: "Select a source before creating a license.",
      });
      return;
    }
    const errors = validateLicenseDraft(licenseDraft);
    if (errors.length > 0) {
      setNotice({ tone: "error", message: errors.join(" ") });
      return;
    }
    setBusyMessage("Creating license...");
    try {
      await createLicense(
        props.apiBaseUrl,
        token.trim(),
        selectedSource.id,
        toLicensePayload(licenseDraft),
      );
      setLicenseDraft(LICENSE_INITIAL_DRAFT);
      setNotice({ tone: "success", message: "License version created." });
      await refreshLicenses(selectedSource.id);
    } catch (error) {
      setNotice({ tone: "error", message: errorMessage(error) });
    } finally {
      setBusyMessage(null);
    }
  }

  async function submitReplaceLicense(licenseId: string): Promise<void> {
    const draft = replacementDrafts[licenseId];
    if (!selectedSource || !draft) {
      return;
    }
    const errors = validateLicenseDraft(draft);
    if (errors.length > 0) {
      setNotice({ tone: "error", message: errors.join(" ") });
      return;
    }
    setBusyMessage("Replacing license...");
    try {
      await replaceLicense(
        props.apiBaseUrl,
        token.trim(),
        licenseId,
        toLicensePayload(draft),
      );
      setNotice({ tone: "success", message: "License replacement created." });
      await refreshLicenses(selectedSource.id);
    } catch (error) {
      setNotice({ tone: "error", message: errorMessage(error) });
    } finally {
      setBusyMessage(null);
    }
  }

  const sourceWarnings = selectedSource
    ? buildSourceWarnings(selectedSource, licenses)
    : [];
  const licenseWarnings =
    selectedLicense && policy
      ? buildLicenseWarnings(selectedLicense, policy)
      : [];

  return (
    <main style={shellStyle}>
      <section style={containerStyle}>
        <header style={heroStyle}>
          <p style={eyebrowStyle}>Zayd Governance Console</p>
          <h1 style={titleStyle}>Source and license operations</h1>
          <p style={subtitleStyle}>
            Manage sources, license versions, permission evidence metadata, and
            workflow policy decisions. Unknown or incomplete permissions remain
            visible before mutations.
          </p>
          <p style={{ margin: 0, color: "#52625a" }}>
            API base URL: <code>{props.apiBaseUrl}</code>
          </p>
        </header>

        {notice ? (
          <div style={bannerStyle(notice.tone)}>{notice.message}</div>
        ) : null}
        {busyMessage ? (
          <div style={bannerStyle("info")}>{busyMessage}</div>
        ) : null}

        <section style={layoutStyle}>
          <aside style={sidebarStyle}>
            <div style={tokenPanelStyle}>
              <label htmlFor="access-token" style={smallLabelStyle}>
                Bearer token
              </label>
              <textarea
                id="access-token"
                rows={4}
                value={token}
                onChange={(event) => {
                  const next = event.target.value;
                  startTransition(() => {
                    setToken(next);
                    if (!next.trim()) {
                      setSources([]);
                      setDerivedBySource({});
                      setSelectedSourceId(null);
                      setNotice(null);
                      setBusyMessage(null);
                    }
                  });
                }}
                placeholder="Paste a temporary admin access token. The UI keeps it in memory only."
                style={textAreaStyle("#132019", "#f4f0ea")}
              />
            </div>

            <div style={tokenPanelStyle}>
              <label htmlFor="search-query" style={smallLabelStyle}>
                Search sources
              </label>
              <div
                style={{
                  display: "grid",
                  gap: 10,
                  gridTemplateColumns: "1fr auto",
                }}
              >
                <input
                  id="search-query"
                  value={query}
                  onChange={(event) => {
                    const next = event.target.value;
                    startTransition(() => {
                      setQuery(next);
                    });
                  }}
                  placeholder="Bukhari, publisher, fiqh..."
                  style={inputStyle("#132019", "#f4f0ea")}
                />
                <button
                  type="button"
                  onClick={() => void refreshSources()}
                  style={darkButtonStyle}
                >
                  Load
                </button>
              </div>
            </div>

            <div style={{ display: "grid", gap: 10 }}>
              {sources.length === 0 ? (
                <p style={{ margin: 0, color: "#c6d0cb" }}>
                  {token.trim()
                    ? "No sources returned. Verify RBAC access or create a source."
                    : "Add a bearer token to load protected admin records."}
                </p>
              ) : (
                sources.map((source) => (
                  <button
                    key={source.id}
                    type="button"
                    onClick={() => {
                      setSelectedSourceId(source.id);
                      void refreshLicenses(source.id);
                    }}
                    style={sourceCardStyle(
                      selectedSourceId === source.id,
                      source.is_active,
                    )}
                  >
                    <strong>{source.name}</strong>
                    <span style={{ color: "#d6ddd9", fontSize: 14 }}>
                      {source.source_type} · {source.language} · reliability{" "}
                      {source.reliability_level}
                    </span>
                    <span
                      style={{
                        color: source.is_active ? "#a6d1af" : "#ffbc9f",
                        fontSize: 13,
                      }}
                    >
                      {source.is_active ? "Active" : "Suspended"}
                    </span>
                  </button>
                ))
              )}
            </div>

            <section style={formCardDarkStyle}>
              <h2 style={{ marginTop: 0, fontSize: 22 }}>Create source</h2>
              <SourceFields
                draft={sourceDraft}
                onChange={setSourceDraft}
                dark
              />
              <button
                type="button"
                onClick={() => void submitCreateSource()}
                style={darkButtonStyle}
              >
                Create source record
              </button>
            </section>
          </aside>

          <section style={{ display: "grid", gap: 24 }}>
            {selectedSource ? (
              <>
                <article style={cardStyle}>
                  <div style={headerGridStyle}>
                    <div>
                      <p style={eyebrowMutedStyle}>Source registry</p>
                      <h2 style={{ margin: 0, fontSize: 34 }}>
                        {selectedSource.name}
                      </h2>
                      <p style={{ margin: "10px 0 0", color: "#495a52" }}>
                        {selectedSource.source_type} · {selectedSource.language}
                        {selectedSource.owner
                          ? ` · ${selectedSource.owner}`
                          : ""}
                        {selectedSource.country
                          ? ` · ${selectedSource.country}`
                          : ""}
                      </p>
                    </div>
                    <span style={statusPillStyle(selectedSource.is_active)}>
                      {selectedSource.is_active ? "Active" : "Suspended"}
                    </span>
                  </div>

                  <div style={metricGridStyle}>
                    <Metric
                      label="Reliability"
                      value={String(selectedSource.reliability_level)}
                    />
                    <Metric
                      label="License versions"
                      value={String(licenses.length)}
                    />
                    <Metric
                      label="Unknown or incomplete"
                      value={String(
                        licenses.filter(
                          (license) =>
                            license.status === "unknown" ||
                            license.storage_permission === "unknown" ||
                            license.embedding_permission === "unknown" ||
                            license.redistribution === "unknown",
                        ).length,
                      )}
                    />
                    <Metric
                      label="Website"
                      value={selectedSource.website ?? "Not set"}
                    />
                  </div>

                  <div style={twoColumnStyle}>
                    <section style={formCardLightStyle}>
                      <h3 style={{ marginTop: 0 }}>Edit source</h3>
                      <SourceFields
                        draft={sourceEditDraft}
                        onChange={(draft) => {
                          if (!selectedSource) {
                            return;
                          }
                          setSourceEditDrafts((current) => ({
                            ...current,
                            [selectedSource.id]: draft,
                          }));
                        }}
                      />
                      <button
                        type="button"
                        onClick={() => void submitUpdateSource()}
                        style={secondaryButtonStyle}
                      >
                        Save source changes
                      </button>
                    </section>

                    <section style={formCardLightStyle}>
                      <h3 style={{ marginTop: 0 }}>Suspend source</h3>
                      <p>
                        {summarizeSuspensionImpact(selectedSource, licenses)}
                      </p>
                      <button
                        type="button"
                        onClick={() => void submitSuspendSource()}
                        style={dangerButtonStyle}
                      >
                        Suspend record
                      </button>
                    </section>
                  </div>
                </article>

                <section style={detailLayoutStyle}>
                  <section style={cardStyle}>
                    <div style={headerGridStyle}>
                      <div>
                        <h2 style={{ margin: 0, fontSize: 28 }}>
                          License versions
                        </h2>
                        <p style={{ margin: 0, color: "#495a52" }}>
                          Newest first. Replacement creates a new row and
                          preserves history.
                        </p>
                      </div>
                      <select
                        value={workflow}
                        onChange={(event) => {
                          const nextWorkflow = event.target.value;
                          setWorkflow(nextWorkflow);
                          if (selectedSource && selectedLicense) {
                            startTransition(() => {
                              void refreshDerived(
                                selectedSource.id,
                                selectedLicense.id,
                              );
                            });
                          }
                        }}
                        style={selectStyle}
                      >
                        <option value="retrieval">Retrieval</option>
                        <option value="ingestion">Ingestion</option>
                        <option value="export">Export</option>
                      </select>
                    </div>

                    {policy ? (
                      <div style={infoPanelStyle}>
                        <strong>Selected workflow</strong>
                        <p style={{ marginBottom: 0 }}>
                          {summarizePolicyDecision(policy)}
                        </p>
                      </div>
                    ) : null}

                    {permissionDocumentKey ? (
                      <div style={infoPanelStyle}>
                        <strong>Permission evidence metadata</strong>
                        <p style={{ marginBottom: 0 }}>
                          Private object key:{" "}
                          <code>{permissionDocumentKey}</code>
                        </p>
                      </div>
                    ) : null}

                    <div style={{ display: "grid", gap: 14 }}>
                      {licenses.map((license) => (
                        <article key={license.id} style={licenseCardStyle}>
                          <div style={headerGridStyle}>
                            <div>
                              <strong>{license.license_name}</strong>
                              <p
                                style={{ margin: "4px 0 0", color: "#56665e" }}
                              >
                                Version{" "}
                                {license.license_version ?? "unversioned"} ·
                                status {license.status}
                              </p>
                            </div>
                            <span style={licenseStatusStyle(license.status)}>
                              {license.status}
                            </span>
                          </div>

                          <div style={metricGridCompactStyle}>
                            <Metric
                              label="Storage"
                              value={license.storage_permission}
                              compact
                            />
                            <Metric
                              label="Embedding"
                              value={license.embedding_permission}
                              compact
                            />
                            <Metric
                              label="Commercial"
                              value={license.commercial_use}
                              compact
                            />
                            <Metric
                              label="Redistribution"
                              value={license.redistribution}
                              compact
                            />
                          </div>

                          <details>
                            <summary
                              style={{ cursor: "pointer", fontWeight: 700 }}
                            >
                              Replace with new version
                            </summary>
                            <div
                              style={{
                                marginTop: 12,
                                display: "grid",
                                gap: 10,
                              }}
                            >
                              <LicenseFields
                                draft={
                                  replacementDrafts[license.id] ??
                                  licenseToDraft(license)
                                }
                                onChange={(draft) =>
                                  setReplacementDrafts((current) => ({
                                    ...current,
                                    [license.id]: draft,
                                  }))
                                }
                              />
                              <button
                                type="button"
                                onClick={() =>
                                  void submitReplaceLicense(license.id)
                                }
                                style={secondaryButtonStyle}
                              >
                                Create replacement row
                              </button>
                            </div>
                          </details>
                        </article>
                      ))}
                    </div>

                    <section style={formCardLightStyle}>
                      <h3 style={{ marginTop: 0 }}>Create license version</h3>
                      <LicenseFields
                        draft={licenseDraft}
                        onChange={setLicenseDraft}
                      />
                      <button
                        type="button"
                        onClick={() => void submitCreateLicense()}
                        style={secondaryButtonStyle}
                      >
                        Create license
                      </button>
                    </section>
                  </section>

                  <section style={cardStyle}>
                    <h2 style={{ marginTop: 0, fontSize: 28 }}>
                      Warnings and impact
                    </h2>
                    <WarningList warnings={sourceWarnings} />
                    <WarningList
                      warnings={licenseWarnings}
                      title={selectedLicense?.license_name}
                    />
                    <div style={infoPanelStyle}>
                      <h3 style={{ marginTop: 0 }}>Mutation expectations</h3>
                      <p style={{ marginBottom: 0 }}>
                        Every source and license mutation goes through the
                        RBAC-protected API and should emit immutable audit
                        events. Unknown, incomplete, and expiring rights stay
                        highlighted before action.
                      </p>
                    </div>
                  </section>
                </section>
              </>
            ) : (
              <div style={cardStyle}>
                Select a source after loading records.
              </div>
            )}
          </section>
        </section>
      </section>
    </main>
  );
}

function SourceFields(props: {
  readonly draft: SourceDraft;
  readonly onChange: (draft: SourceDraft) => void;
  readonly dark?: boolean;
}): ReactElement {
  const style = props.dark ? inputStyle("#203126", "#f4f0ea") : inputStyle();
  return (
    <>
      <input
        value={props.draft.name}
        onChange={(event) =>
          props.onChange({ ...props.draft, name: event.target.value })
        }
        placeholder="Source name"
        style={style}
      />
      <input
        value={props.draft.sourceType}
        onChange={(event) =>
          props.onChange({ ...props.draft, sourceType: event.target.value })
        }
        placeholder="Source type"
        style={style}
      />
      <input
        value={props.draft.owner}
        onChange={(event) =>
          props.onChange({ ...props.draft, owner: event.target.value })
        }
        placeholder="Owner"
        style={style}
      />
      <input
        value={props.draft.website}
        onChange={(event) =>
          props.onChange({ ...props.draft, website: event.target.value })
        }
        placeholder="Website"
        style={style}
      />
      <div style={fieldGridStyle}>
        <input
          value={props.draft.language}
          onChange={(event) =>
            props.onChange({ ...props.draft, language: event.target.value })
          }
          placeholder="Language"
          style={style}
        />
        <input
          value={props.draft.country}
          onChange={(event) =>
            props.onChange({ ...props.draft, country: event.target.value })
          }
          placeholder="Country"
          style={style}
        />
        <input
          value={props.draft.reliabilityLevel}
          onChange={(event) =>
            props.onChange({
              ...props.draft,
              reliabilityLevel: event.target.value,
            })
          }
          placeholder="Reliability 1-5"
          style={style}
        />
      </div>
      <label style={checkboxRowStyle}>
        <input
          type="checkbox"
          checked={props.draft.isActive}
          onChange={(event) =>
            props.onChange({ ...props.draft, isActive: event.target.checked })
          }
        />
        Active for new ingestion
      </label>
    </>
  );
}

function LicenseFields(props: {
  readonly draft: LicenseDraft;
  readonly onChange: (draft: LicenseDraft) => void;
}): ReactElement {
  return (
    <>
      <input
        value={props.draft.licenseName}
        onChange={(event) =>
          props.onChange({ ...props.draft, licenseName: event.target.value })
        }
        placeholder="License name"
        style={inputStyle()}
      />
      <div style={fieldGridStyleTwo}>
        <input
          value={props.draft.licenseVersion}
          onChange={(event) =>
            props.onChange({
              ...props.draft,
              licenseVersion: event.target.value,
            })
          }
          placeholder="License version"
          style={inputStyle()}
        />
        <input
          value={props.draft.status}
          onChange={(event) =>
            props.onChange({ ...props.draft, status: event.target.value })
          }
          placeholder="Status"
          style={inputStyle()}
        />
      </div>
      <div style={fieldGridStyleTwo}>
        <input
          value={props.draft.storagePermission}
          onChange={(event) =>
            props.onChange({
              ...props.draft,
              storagePermission: event.target.value,
            })
          }
          placeholder="Storage permission"
          style={inputStyle()}
        />
        <input
          value={props.draft.embeddingPermission}
          onChange={(event) =>
            props.onChange({
              ...props.draft,
              embeddingPermission: event.target.value,
            })
          }
          placeholder="Embedding permission"
          style={inputStyle()}
        />
      </div>
      <div style={fieldGridStyleTwo}>
        <input
          value={props.draft.commercialUse}
          onChange={(event) =>
            props.onChange({
              ...props.draft,
              commercialUse: event.target.value,
            })
          }
          placeholder="Commercial use"
          style={inputStyle()}
        />
        <input
          value={props.draft.redistribution}
          onChange={(event) =>
            props.onChange({
              ...props.draft,
              redistribution: event.target.value,
            })
          }
          placeholder="Redistribution"
          style={inputStyle()}
        />
      </div>
      <label style={checkboxRowStyle}>
        <input
          type="checkbox"
          checked={props.draft.attributionRequired}
          onChange={(event) =>
            props.onChange({
              ...props.draft,
              attributionRequired: event.target.checked,
            })
          }
        />
        Attribution required
      </label>
      <input
        value={props.draft.attributionTemplate}
        onChange={(event) =>
          props.onChange({
            ...props.draft,
            attributionTemplate: event.target.value,
          })
        }
        placeholder="Attribution template"
        style={inputStyle()}
      />
      <input
        value={props.draft.permissionDocumentKey}
        onChange={(event) =>
          props.onChange({
            ...props.draft,
            permissionDocumentKey: event.target.value,
          })
        }
        placeholder="Private permission document key"
        style={inputStyle()}
      />
      <div style={fieldGridStyleTwo}>
        <input
          value={props.draft.validFrom}
          onChange={(event) =>
            props.onChange({ ...props.draft, validFrom: event.target.value })
          }
          placeholder="YYYY-MM-DD"
          style={inputStyle()}
        />
        <input
          value={props.draft.validUntil}
          onChange={(event) =>
            props.onChange({ ...props.draft, validUntil: event.target.value })
          }
          placeholder="YYYY-MM-DD"
          style={inputStyle()}
        />
      </div>
      <textarea
        rows={3}
        value={props.draft.notes}
        onChange={(event) =>
          props.onChange({ ...props.draft, notes: event.target.value })
        }
        placeholder="Operational notes"
        style={textAreaStyle()}
      />
    </>
  );
}

function WarningList(props: {
  readonly warnings: readonly {
    readonly tone: "critical" | "warning" | "info";
    readonly title: string;
    readonly detail: string;
  }[];
  readonly title?: string;
}): ReactElement | null {
  if (props.warnings.length === 0) {
    return null;
  }
  return (
    <div style={{ display: "grid", gap: 12 }}>
      {props.title ? <strong>{props.title}</strong> : null}
      {props.warnings.map((warning) => (
        <div
          key={`${warning.title}-${warning.detail}`}
          style={warningStyle(warning.tone)}
        >
          <strong>{warning.title}</strong>
          <p style={{ marginBottom: 0 }}>{warning.detail}</p>
        </div>
      ))}
    </div>
  );
}

function Metric(props: {
  readonly label: string;
  readonly value: string;
  readonly compact?: boolean;
}): ReactElement {
  return (
    <div
      style={{
        padding: props.compact ? 0 : 14,
        borderRadius: props.compact ? 0 : 18,
        background: props.compact ? "transparent" : "rgba(244,240,234,0.9)",
        border: props.compact ? "none" : "1px solid rgba(24,33,28,0.08)",
      }}
    >
      <div
        style={{
          fontSize: 12,
          letterSpacing: "0.1em",
          textTransform: "uppercase",
        }}
      >
        {props.label}
      </div>
      <div style={{ marginTop: 4, fontWeight: 700 }}>{props.value}</div>
    </div>
  );
}

function licenseToDraft(license: LicenseRecord): LicenseDraft {
  return {
    licenseName: license.license_name,
    licenseVersion: license.license_version ?? "",
    status: license.status,
    storagePermission: license.storage_permission,
    embeddingPermission: license.embedding_permission,
    commercialUse: license.commercial_use,
    redistribution: license.redistribution,
    attributionRequired: license.attribution_required,
    attributionTemplate: license.attribution_template ?? "",
    permissionDocumentKey: license.permission_document_key ?? "",
    validFrom: license.valid_from ?? "",
    validUntil: license.valid_until ?? "",
    notes: license.notes ?? "",
  };
}

function sourceToDraft(source: SourceRecord): SourceDraft {
  return {
    name: source.name,
    sourceType: source.source_type,
    owner: source.owner ?? "",
    website: source.website ?? "",
    language: source.language,
    country: source.country ?? "",
    reliabilityLevel: String(source.reliability_level),
    isActive: source.is_active,
  };
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Request failed.";
}

function inputStyle(background = "#fffaf4", color = "#18211c"): CSSProperties {
  return {
    width: "100%",
    padding: "12px 14px",
    borderRadius: 14,
    border: "1px solid rgba(24,33,28,0.12)",
    background,
    color,
  };
}

function textAreaStyle(
  background = "#fffaf4",
  color = "#18211c",
): CSSProperties {
  return {
    ...inputStyle(background, color),
    resize: "vertical",
  };
}

function bannerStyle(tone: Notice["tone"]): CSSProperties {
  return {
    borderRadius: 18,
    padding: "14px 18px",
    background:
      tone === "success" ? "#e6f5ea" : tone === "error" ? "#f8e3df" : "#eef2f3",
    border:
      tone === "success"
        ? "1px solid #86b591"
        : tone === "error"
          ? "1px solid #c48374"
          : "1px solid #99aab1",
  };
}

function warningStyle(tone: "critical" | "warning" | "info"): CSSProperties {
  return {
    borderRadius: 18,
    padding: 14,
    background:
      tone === "critical"
        ? "#fae0d9"
        : tone === "warning"
          ? "#fff0d8"
          : "#eef2f3",
    border:
      tone === "critical"
        ? "1px solid #d08877"
        : tone === "warning"
          ? "1px solid #d5ab55"
          : "1px solid #aab8bf",
  };
}

function statusPillStyle(active: boolean): CSSProperties {
  return {
    padding: "8px 12px",
    borderRadius: 999,
    background: active ? "#dff1e2" : "#ffe4d6",
    color: active ? "#1d5c31" : "#8a3c1d",
    fontWeight: 700,
  };
}

function licenseStatusStyle(status: string): CSSProperties {
  return {
    padding: "6px 10px",
    borderRadius: 999,
    background:
      status === "persistent_redistributable"
        ? "#d9f2df"
        : status === "persistent_private"
          ? "#e6ecff"
          : "#fde3d8",
    color:
      status === "persistent_redistributable"
        ? "#1c6132"
        : status === "persistent_private"
          ? "#294782"
          : "#94461f",
    fontWeight: 700,
  };
}

function sourceCardStyle(selected: boolean, active: boolean): CSSProperties {
  return {
    display: "grid",
    gap: 4,
    padding: 14,
    borderRadius: 18,
    textAlign: "left",
    background: selected
      ? "linear-gradient(135deg, #9c6c40, #6d4a28)"
      : "rgba(255,255,255,0.06)",
    border: active
      ? "1px solid rgba(255,255,255,0.08)"
      : "1px solid rgba(255,179,145,0.45)",
    color: "#f4f0ea",
    cursor: "pointer",
  };
}

const shellStyle: CSSProperties = {
  minHeight: "100vh",
  padding: "32px 20px 60px",
  background:
    "radial-gradient(circle at top left, #ffe6cf 0%, #f6f1e8 42%, #dfe9e2 100%)",
  color: "#18211c",
  fontFamily: "Georgia, 'Times New Roman', serif",
};

const containerStyle: CSSProperties = {
  maxWidth: 1280,
  margin: "0 auto",
  display: "grid",
  gap: 24,
};

const heroStyle: CSSProperties = {
  display: "grid",
  gap: 12,
  padding: 24,
  borderRadius: 28,
  background: "rgba(255,255,255,0.72)",
  border: "1px solid rgba(24,33,28,0.08)",
  boxShadow: "0 22px 48px rgba(24,33,28,0.12)",
};

const eyebrowStyle: CSSProperties = {
  margin: 0,
  letterSpacing: "0.18em",
  textTransform: "uppercase",
  fontSize: 12,
  color: "#8b5e3c",
};

const eyebrowMutedStyle: CSSProperties = {
  ...eyebrowStyle,
  color: "#7b5f49",
};

const titleStyle: CSSProperties = {
  margin: 0,
  fontSize: "clamp(2.3rem, 4vw, 4.4rem)",
  lineHeight: 1,
};

const subtitleStyle: CSSProperties = {
  margin: 0,
  maxWidth: 900,
  fontSize: 18,
  lineHeight: 1.55,
};

const layoutStyle: CSSProperties = {
  display: "grid",
  gap: 24,
  gridTemplateColumns: "minmax(280px, 360px) minmax(0, 1fr)",
  alignItems: "start",
};

const sidebarStyle: CSSProperties = {
  display: "grid",
  gap: 18,
  padding: 20,
  borderRadius: 28,
  background: "rgba(15, 24, 20, 0.92)",
  color: "#f4f0ea",
};

const tokenPanelStyle: CSSProperties = {
  display: "grid",
  gap: 10,
};

const smallLabelStyle: CSSProperties = {
  fontSize: 13,
  letterSpacing: "0.08em",
};

const formCardDarkStyle: CSSProperties = {
  display: "grid",
  gap: 12,
  padding: 18,
  borderRadius: 22,
  background: "rgba(255,255,255,0.07)",
};

const cardStyle: CSSProperties = {
  display: "grid",
  gap: 20,
  padding: 24,
  borderRadius: 30,
  background: "rgba(255,255,255,0.76)",
  border: "1px solid rgba(24,33,28,0.08)",
};

const headerGridStyle: CSSProperties = {
  display: "grid",
  gap: 8,
  gridTemplateColumns: "minmax(0, 1fr) auto",
  alignItems: "start",
};

const metricGridStyle: CSSProperties = {
  display: "grid",
  gap: 14,
  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
};

const metricGridCompactStyle: CSSProperties = {
  display: "grid",
  gap: 8,
  gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
  fontSize: 14,
};

const twoColumnStyle: CSSProperties = {
  display: "grid",
  gap: 20,
  gridTemplateColumns: "minmax(0, 1fr) minmax(260px, 320px)",
};

const detailLayoutStyle: CSSProperties = {
  display: "grid",
  gap: 24,
  gridTemplateColumns: "minmax(0, 1.2fr) minmax(320px, 0.8fr)",
};

const formCardLightStyle: CSSProperties = {
  display: "grid",
  gap: 12,
  padding: 18,
  borderRadius: 22,
  background: "rgba(250,247,242,0.92)",
  border: "1px solid rgba(24,33,28,0.08)",
};

const licenseCardStyle: CSSProperties = {
  display: "grid",
  gap: 12,
  padding: 16,
  borderRadius: 20,
  background: "rgba(245,239,232,0.85)",
  border: "1px solid rgba(24,33,28,0.08)",
};

const infoPanelStyle: CSSProperties = {
  padding: 16,
  borderRadius: 18,
  background: "rgba(244,240,234,0.9)",
  border: "1px solid rgba(24,33,28,0.08)",
};

const fieldGridStyle: CSSProperties = {
  display: "grid",
  gap: 10,
  gridTemplateColumns: "1fr 1fr 1fr",
};

const fieldGridStyleTwo: CSSProperties = {
  display: "grid",
  gap: 10,
  gridTemplateColumns: "1fr 1fr",
};

const checkboxRowStyle: CSSProperties = {
  display: "flex",
  gap: 10,
  alignItems: "center",
};

const darkButtonStyle: CSSProperties = {
  padding: "12px 16px",
  borderRadius: 14,
  border: "none",
  background: "linear-gradient(135deg, #b07439, #6f4d2f)",
  color: "#fff8f2",
  fontWeight: 700,
  cursor: "pointer",
};

const secondaryButtonStyle: CSSProperties = {
  padding: "12px 16px",
  borderRadius: 14,
  border: "1px solid rgba(24,33,28,0.18)",
  background: "#f4efe8",
  color: "#18211c",
  fontWeight: 700,
  cursor: "pointer",
};

const dangerButtonStyle: CSSProperties = {
  ...secondaryButtonStyle,
  background: "#5c2011",
  color: "#fff4ef",
  border: "1px solid #79311f",
};

const selectStyle: CSSProperties = {
  ...inputStyle(),
  minWidth: 150,
};
