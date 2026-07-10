"use client";

import type { CSSProperties, ReactElement } from "react";
import { startTransition, useState } from "react";
import type { ModelRecord, ProviderRecord } from "./admin-data.js";
import {
  createModel,
  createProvider,
  listModels,
  listProviders,
  testProviderConnection,
  updateModel,
  updateProvider,
} from "./admin-data.js";
import {
  modelToDraft,
  providerToDraft,
  summarizeDisableImpact,
  summarizeModelRouting,
  toModelPayload,
  toProviderPayload,
  validateModelDraft,
  validateProviderDraft,
  type ModelDraft,
  type ProviderDraft,
} from "./provider-model-ui.js";

const PROVIDER_INITIAL_DRAFT: ProviderDraft = {
  name: "",
  providerType: "llm",
  status: "disabled",
  baseUrl: "",
  secretRef: "",
  termsUrl: "",
  dataPolicyJson: "{}",
};

const MODEL_INITIAL_DRAFT: ModelDraft = {
  providerId: "",
  modelName: "",
  modelType: "llm",
  status: "disabled",
  configurationJson: "{}",
  allowListed: true,
  fallbackModelId: "",
  costLimitDailyUsd: "",
  isDefault: false,
};

type Notice = {
  readonly tone: "success" | "error" | "info";
  readonly message: string;
};

export function ProviderModelConsole(props: {
  readonly apiBaseUrl: string;
}): ReactElement {
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [providers, setProviders] = useState<readonly ProviderRecord[]>([]);
  const [models, setModels] = useState<readonly ModelRecord[]>([]);
  const [providerDraft, setProviderDraft] = useState<ProviderDraft>(
    PROVIDER_INITIAL_DRAFT,
  );
  const [providerEditDrafts, setProviderEditDrafts] = useState<
    Record<string, ProviderDraft>
  >({});
  const [modelDraft, setModelDraft] = useState<ModelDraft>(MODEL_INITIAL_DRAFT);
  const [modelEditDrafts, setModelEditDrafts] = useState<
    Record<string, ModelDraft>
  >({});

  async function refresh(): Promise<void> {
    setBusy("Loading providers and models...");
    try {
      const [nextProviders, nextModels] = await Promise.all([
        listProviders(props.apiBaseUrl, token.trim()),
        listModels(props.apiBaseUrl, token.trim()),
      ]);
      setProviders(nextProviders);
      setModels(nextModels);
      setProviderEditDrafts((current) => {
        const next: Record<string, ProviderDraft> = {};
        for (const provider of nextProviders) {
          next[provider.id] = current[provider.id] ?? providerToDraft(provider);
        }
        return next;
      });
      setModelEditDrafts((current) => {
        const next: Record<string, ModelDraft> = {};
        for (const model of nextModels) {
          next[model.id] = current[model.id] ?? modelToDraft(model);
        }
        return next;
      });
      setModelDraft((current) => ({
        ...current,
        providerId: current.providerId || nextProviders[0]?.id || "",
      }));
      setNotice(null);
    } catch (error) {
      setNotice({ tone: "error", message: errorMessage(error) });
      setProviders([]);
      setModels([]);
    } finally {
      setBusy(null);
    }
  }

  async function submitCreateProvider(): Promise<void> {
    const errors = validateProviderDraft(providerDraft);
    if (errors.length > 0) {
      setNotice({ tone: "error", message: errors.join(" ") });
      return;
    }
    setBusy("Creating provider...");
    try {
      await createProvider(
        props.apiBaseUrl,
        token.trim(),
        toProviderPayload(providerDraft),
      );
      setProviderDraft(PROVIDER_INITIAL_DRAFT);
      setNotice({ tone: "success", message: "Provider record created." });
      await refresh();
    } catch (error) {
      setNotice({ tone: "error", message: errorMessage(error) });
    } finally {
      setBusy(null);
    }
  }

  async function submitUpdateProvider(providerId: string): Promise<void> {
    const draft = providerEditDrafts[providerId];
    if (!draft) {
      return;
    }
    const errors = validateProviderDraft(draft);
    if (errors.length > 0) {
      setNotice({ tone: "error", message: errors.join(" ") });
      return;
    }
    setBusy("Saving provider...");
    try {
      await updateProvider(
        props.apiBaseUrl,
        token.trim(),
        providerId,
        toProviderPayload(draft),
      );
      setNotice({ tone: "success", message: "Provider updated." });
      await refresh();
    } catch (error) {
      setNotice({ tone: "error", message: errorMessage(error) });
    } finally {
      setBusy(null);
    }
  }

  async function submitTestConnection(providerId: string): Promise<void> {
    setBusy("Testing provider connection...");
    try {
      const result = await testProviderConnection(
        props.apiBaseUrl,
        token.trim(),
        providerId,
      );
      setNotice({
        tone: result.status === "ok" ? "success" : "info",
        message: `${result.provider_name}: ${result.message}`,
      });
    } catch (error) {
      setNotice({ tone: "error", message: errorMessage(error) });
    } finally {
      setBusy(null);
    }
  }

  async function submitCreateModel(): Promise<void> {
    const errors = validateModelDraft(modelDraft);
    if (errors.length > 0) {
      setNotice({ tone: "error", message: errors.join(" ") });
      return;
    }
    setBusy("Creating model route...");
    try {
      await createModel(props.apiBaseUrl, token.trim(), toModelPayload(modelDraft));
      setModelDraft({
        ...MODEL_INITIAL_DRAFT,
        providerId: providers[0]?.id ?? "",
      });
      setNotice({ tone: "success", message: "Model configuration created." });
      await refresh();
    } catch (error) {
      setNotice({ tone: "error", message: errorMessage(error) });
    } finally {
      setBusy(null);
    }
  }

  async function submitUpdateModel(modelId: string): Promise<void> {
    const draft = modelEditDrafts[modelId];
    if (!draft) {
      return;
    }
    const errors = validateModelDraft(draft);
    if (errors.length > 0) {
      setNotice({ tone: "error", message: errors.join(" ") });
      return;
    }
    setBusy("Saving model route...");
    try {
      await updateModel(
        props.apiBaseUrl,
        token.trim(),
        modelId,
        toModelPayload(draft),
      );
      setNotice({ tone: "success", message: "Model configuration updated." });
      await refresh();
    } catch (error) {
      setNotice({ tone: "error", message: errorMessage(error) });
    } finally {
      setBusy(null);
    }
  }

  return (
    <section style={sectionStyle}>
      <div style={heroStyle}>
        <div>
          <p style={eyebrowStyle}>TASK-10-05</p>
          <h2 style={titleStyle}>Provider and model management</h2>
          <p style={copyStyle}>
            Configure providers, manage primary and fallback model routing,
            update write-only secret references, and run audited connection
            checks with rate limiting.
          </p>
        </div>
        <div style={tokenCardStyle}>
          <label htmlFor="provider-admin-token" style={labelStyle}>
            Bearer token
          </label>
          <textarea
            id="provider-admin-token"
            rows={4}
            value={token}
            onChange={(event) => {
              const next = event.target.value;
              startTransition(() => {
                setToken(next);
                if (!next.trim()) {
                  setProviders([]);
                  setModels([]);
                  setNotice(null);
                }
              });
            }}
            placeholder="Paste a temporary admin token. It stays in memory only."
            style={textAreaStyle}
          />
          <button type="button" onClick={() => void refresh()} style={primaryButtonStyle}>
            Load protected records
          </button>
        </div>
      </div>

      {notice ? <div style={bannerStyle(notice.tone)}>{notice.message}</div> : null}
      {busy ? <div style={bannerStyle("info")}>{busy}</div> : null}

      <div style={gridStyle}>
        <section style={cardStyle}>
          <h3 style={sectionTitleStyle}>Create provider</h3>
          <ProviderFields draft={providerDraft} onChange={setProviderDraft} />
          <button type="button" onClick={() => void submitCreateProvider()} style={primaryButtonStyle}>
            Create provider
          </button>
        </section>

        <section style={cardStyle}>
          <h3 style={sectionTitleStyle}>Create model route</h3>
          <ModelFields
            draft={modelDraft}
            providers={providers}
            models={models}
            onChange={setModelDraft}
          />
          <button type="button" onClick={() => void submitCreateModel()} style={primaryButtonStyle}>
            Create model
          </button>
        </section>
      </div>

      <section style={stackStyle}>
        <div style={cardStyle}>
          <div style={headerRowStyle}>
            <div>
              <h3 style={sectionTitleStyle}>Providers</h3>
              <p style={mutedStyle}>
                Secrets stay write-only. Existing values are represented only as
                configuration status.
              </p>
            </div>
            <span style={countPillStyle}>{providers.length} provider(s)</span>
          </div>
          <div style={stackStyle}>
            {providers.map((provider) => (
              <article key={provider.id} style={subCardStyle}>
                <div style={headerRowStyle}>
                  <div>
                    <strong style={{ fontSize: 20 }}>{provider.name}</strong>
                    <p style={mutedStyle}>
                      {provider.provider_type} · status {provider.status} · secret{" "}
                      {provider.secret_mask}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => void submitTestConnection(provider.id)}
                    style={secondaryButtonStyle}
                  >
                    Test connection
                  </button>
                </div>
                <p style={mutedStyle}>{summarizeDisableImpact(provider)}</p>
                <ProviderFields
                  draft={providerEditDrafts[provider.id] ?? providerToDraft(provider)}
                  onChange={(draft) =>
                    setProviderEditDrafts((current) => ({
                      ...current,
                      [provider.id]: draft,
                    }))
                  }
                />
                <button
                  type="button"
                  onClick={() => void submitUpdateProvider(provider.id)}
                  style={secondaryButtonStyle}
                >
                  Save provider changes
                </button>
              </article>
            ))}
            {providers.length === 0 ? (
              <p style={mutedStyle}>Load providers with an admin token to manage routing.</p>
            ) : null}
          </div>
        </div>

        <div style={cardStyle}>
          <div style={headerRowStyle}>
            <div>
              <h3 style={sectionTitleStyle}>Models</h3>
              <p style={mutedStyle}>
                Configure allow-listing, default routing, fallback readiness,
                and daily cost limits.
              </p>
            </div>
            <span style={countPillStyle}>{models.length} model(s)</span>
          </div>
          <div style={stackStyle}>
            {models.map((model) => (
              <article key={model.id} style={subCardStyle}>
                <div style={headerRowStyle}>
                  <div>
                    <strong style={{ fontSize: 20 }}>{model.model_name}</strong>
                    <p style={mutedStyle}>
                      {model.model_type} · {model.provider_name} · status {model.status}
                    </p>
                  </div>
                  <span style={routeBadgeStyle(model.is_default)}>
                    {model.is_default ? "Default" : "Secondary"}
                  </span>
                </div>
                <p style={mutedStyle}>{summarizeModelRouting(model)}</p>
                <ModelFields
                  draft={modelEditDrafts[model.id] ?? modelToDraft(model)}
                  providers={providers}
                  models={models}
                  onChange={(draft) =>
                    setModelEditDrafts((current) => ({
                      ...current,
                      [model.id]: draft,
                    }))
                  }
                />
                <button
                  type="button"
                  onClick={() => void submitUpdateModel(model.id)}
                  style={secondaryButtonStyle}
                >
                  Save model changes
                </button>
              </article>
            ))}
            {models.length === 0 ? (
              <p style={mutedStyle}>Load models with an admin token to manage routing.</p>
            ) : null}
          </div>
        </div>
      </section>
    </section>
  );
}

function ProviderFields(props: {
  readonly draft: ProviderDraft;
  readonly onChange: (draft: ProviderDraft) => void;
}): ReactElement {
  return (
    <div style={fieldStackStyle}>
      <div style={fieldGridStyle}>
        <input
          value={props.draft.name}
          onChange={(event) =>
            props.onChange({ ...props.draft, name: event.target.value })
          }
          placeholder="Provider name"
          style={inputStyle}
        />
        <input
          value={props.draft.providerType}
          onChange={(event) =>
            props.onChange({ ...props.draft, providerType: event.target.value })
          }
          placeholder="Provider type"
          style={inputStyle}
        />
      </div>
      <div style={fieldGridStyle}>
        <input
          value={props.draft.status}
          onChange={(event) =>
            props.onChange({ ...props.draft, status: event.target.value })
          }
          placeholder="Status"
          style={inputStyle}
        />
        <input
          value={props.draft.baseUrl}
          onChange={(event) =>
            props.onChange({ ...props.draft, baseUrl: event.target.value })
          }
          placeholder="Base URL"
          style={inputStyle}
        />
      </div>
      <input
        value={props.draft.secretRef}
        onChange={(event) =>
          props.onChange({ ...props.draft, secretRef: event.target.value })
        }
        placeholder="Secret reference (write-only)"
        style={inputStyle}
      />
      <input
        value={props.draft.termsUrl}
        onChange={(event) =>
          props.onChange({ ...props.draft, termsUrl: event.target.value })
        }
        placeholder="Terms URL"
        style={inputStyle}
      />
      <textarea
        rows={4}
        value={props.draft.dataPolicyJson}
        onChange={(event) =>
          props.onChange({ ...props.draft, dataPolicyJson: event.target.value })
        }
        placeholder='{"classification":"internal"}'
        style={textAreaLightStyle}
      />
    </div>
  );
}

function ModelFields(props: {
  readonly draft: ModelDraft;
  readonly providers: readonly ProviderRecord[];
  readonly models: readonly ModelRecord[];
  readonly onChange: (draft: ModelDraft) => void;
}): ReactElement {
  return (
    <div style={fieldStackStyle}>
      <div style={fieldGridStyle}>
        <select
          value={props.draft.providerId}
          onChange={(event) =>
            props.onChange({ ...props.draft, providerId: event.target.value })
          }
          style={inputStyle}
        >
          <option value="">Select provider</option>
          {props.providers.map((provider) => (
            <option key={provider.id} value={provider.id}>
              {provider.name}
            </option>
          ))}
        </select>
        <input
          value={props.draft.modelType}
          onChange={(event) =>
            props.onChange({ ...props.draft, modelType: event.target.value })
          }
          placeholder="Model type"
          style={inputStyle}
        />
      </div>
      <div style={fieldGridStyle}>
        <input
          value={props.draft.modelName}
          onChange={(event) =>
            props.onChange({ ...props.draft, modelName: event.target.value })
          }
          placeholder="Model name"
          style={inputStyle}
        />
        <input
          value={props.draft.status}
          onChange={(event) =>
            props.onChange({ ...props.draft, status: event.target.value })
          }
          placeholder="Status"
          style={inputStyle}
        />
      </div>
      <div style={fieldGridStyle}>
        <select
          value={props.draft.fallbackModelId}
          onChange={(event) =>
            props.onChange({
              ...props.draft,
              fallbackModelId: event.target.value,
            })
          }
          style={inputStyle}
        >
          <option value="">No fallback</option>
          {props.models
            .filter((model) => model.model_type === props.draft.modelType)
            .map((model) => (
              <option key={model.id} value={model.id}>
                {model.model_name}
              </option>
            ))}
        </select>
        <input
          value={props.draft.costLimitDailyUsd}
          onChange={(event) =>
            props.onChange({
              ...props.draft,
              costLimitDailyUsd: event.target.value,
            })
          }
          placeholder="Daily cost limit USD"
          style={inputStyle}
        />
      </div>
      <label style={checkboxStyle}>
        <input
          type="checkbox"
          checked={props.draft.allowListed}
          onChange={(event) =>
            props.onChange({
              ...props.draft,
              allowListed: event.target.checked,
            })
          }
        />
        Allow-listed for orchestration
      </label>
      <label style={checkboxStyle}>
        <input
          type="checkbox"
          checked={props.draft.isDefault}
          onChange={(event) =>
            props.onChange({
              ...props.draft,
              isDefault: event.target.checked,
            })
          }
        />
        Default route for this model type
      </label>
      <textarea
        rows={4}
        value={props.draft.configurationJson}
        onChange={(event) =>
          props.onChange({
            ...props.draft,
            configurationJson: event.target.value,
          })
        }
        placeholder='{"temperature":0,"max_output_tokens":512}'
        style={textAreaLightStyle}
      />
    </div>
  );
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Request failed.";
}

const sectionStyle: CSSProperties = {
  display: "grid",
  gap: 20,
};

const heroStyle: CSSProperties = {
  display: "grid",
  gap: 18,
  gridTemplateColumns: "1.4fr 1fr",
  alignItems: "start",
};

const eyebrowStyle: CSSProperties = {
  margin: 0,
  textTransform: "uppercase",
  letterSpacing: "0.14em",
  fontSize: 12,
  color: "#456050",
};

const titleStyle: CSSProperties = {
  margin: "8px 0 0",
  fontSize: "clamp(1.9rem, 4vw, 3rem)",
};

const copyStyle: CSSProperties = {
  margin: "12px 0 0",
  color: "#486054",
  maxWidth: 720,
};

const tokenCardStyle: CSSProperties = {
  borderRadius: 28,
  padding: 20,
  background: "#173127",
  color: "#eff6ef",
  display: "grid",
  gap: 12,
};

const labelStyle: CSSProperties = {
  fontSize: 12,
  textTransform: "uppercase",
  letterSpacing: "0.12em",
};

const textAreaStyle: CSSProperties = {
  width: "100%",
  borderRadius: 18,
  border: "1px solid rgba(255,255,255,0.14)",
  padding: "12px 14px",
  background: "#10231b",
  color: "#eff6ef",
  resize: "vertical",
};

const gridStyle: CSSProperties = {
  display: "grid",
  gap: 20,
  gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
};

const stackStyle: CSSProperties = {
  display: "grid",
  gap: 20,
};

const cardStyle: CSSProperties = {
  borderRadius: 30,
  padding: 24,
  background: "rgba(255,252,248,0.92)",
  border: "1px solid rgba(24,54,41,0.08)",
  boxShadow: "0 22px 48px rgba(41,54,46,0.08)",
};

const subCardStyle: CSSProperties = {
  borderRadius: 22,
  padding: 18,
  background: "#f7f0e6",
  border: "1px solid rgba(24,54,41,0.08)",
  display: "grid",
  gap: 12,
};

const sectionTitleStyle: CSSProperties = {
  margin: 0,
  fontSize: 24,
};

const headerRowStyle: CSSProperties = {
  display: "flex",
  gap: 12,
  justifyContent: "space-between",
  alignItems: "start",
  flexWrap: "wrap",
};

const mutedStyle: CSSProperties = {
  margin: "6px 0 0",
  color: "#5c7066",
};

const countPillStyle: CSSProperties = {
  borderRadius: 999,
  background: "#dbe9dc",
  color: "#1b3a2d",
  padding: "8px 12px",
  fontSize: 13,
  fontWeight: 700,
};

const primaryButtonStyle: CSSProperties = {
  borderRadius: 16,
  border: "1px solid #183629",
  background: "#183629",
  color: "#f5efe6",
  padding: "12px 16px",
  fontWeight: 700,
};

const secondaryButtonStyle: CSSProperties = {
  borderRadius: 16,
  border: "1px solid rgba(24,54,41,0.18)",
  background: "#f8f3eb",
  color: "#183629",
  padding: "12px 16px",
  fontWeight: 700,
};

const fieldStackStyle: CSSProperties = {
  display: "grid",
  gap: 10,
};

const fieldGridStyle: CSSProperties = {
  display: "grid",
  gap: 10,
  gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
};

const inputStyle: CSSProperties = {
  width: "100%",
  borderRadius: 16,
  border: "1px solid rgba(24,54,41,0.12)",
  padding: "12px 14px",
  background: "#fffaf4",
  color: "#18211c",
};

const textAreaLightStyle: CSSProperties = {
  ...inputStyle,
  resize: "vertical",
};

const checkboxStyle: CSSProperties = {
  display: "flex",
  gap: 10,
  alignItems: "center",
};

const bannerStyle = (tone: "success" | "error" | "info"): CSSProperties => ({
  borderRadius: 18,
  padding: "14px 18px",
  background:
    tone === "success" ? "#e7f4e9" : tone === "error" ? "#f8e2dd" : "#eef3f5",
  border:
    tone === "success"
      ? "1px solid #8eb698"
      : tone === "error"
        ? "1px solid #d18c7f"
        : "1px solid #9eb3bc",
});

const routeBadgeStyle = (isDefault: boolean): CSSProperties => ({
  borderRadius: 999,
  padding: "8px 12px",
  background: isDefault ? "#173127" : "#dce7de",
  color: isDefault ? "#eef5ef" : "#183629",
  fontWeight: 700,
  fontSize: 13,
});
