import { describe, expect, it } from "vitest";

import {
  AllowListedProviderRegistry,
  PROVIDER_SDK_VERSION,
  ProviderSdkError,
  type LLMProvider,
  type ProviderCapabilities,
  type ProviderConfig,
  type ProviderHealth,
  type ProviderIdentity,
  type ProviderValidationResult,
} from "./index.js";

const capabilities: ProviderCapabilities = {
  supportsStreaming: true,
  supportsStructuredOutput: true,
  supportsBatching: false,
  supportsMultilingual: true,
  supportsHealthCheck: true,
  capabilities: ["generate", "stream"],
};

class MockProvider implements LLMProvider {
  identity(): ProviderIdentity {
    return {
      name: "mock-llm",
      kind: "llm",
      version: "mock-provider-v1",
      apiVersion: PROVIDER_SDK_VERSION,
      modelId: "mock-model",
    };
  }

  capabilities(): ProviderCapabilities {
    return capabilities;
  }

  validateConfig(config: ProviderConfig): ProviderValidationResult {
    return {
      valid: config.enabled && config.kind === "llm" && config.providerName === "mock-llm",
      errors: config.enabled ? [] : ["provider config is disabled"],
      warnings: [],
    };
  }

  async healthCheck(): Promise<ProviderHealth> {
    return {
      status: "ok",
      checkedAt: new Date(0).toISOString(),
      providerName: "mock-llm",
      kind: "llm",
      sdkVersion: PROVIDER_SDK_VERSION,
      trace: {},
    };
  }

  async generate() {
    return {
      text: "mock",
      finishReason: "stop" as const,
      provider: this.identity(),
      usage: { inputTokens: 1, outputTokens: 1, totalTokens: 2 },
      trace: {},
    };
  }

  async *stream() {
    yield "mock";
  }
}

describe("provider sdk", () => {
  it("defines stable LLM provider contracts", async () => {
    const provider = new MockProvider();

    await expect(provider.healthCheck()).resolves.toMatchObject({
      providerName: "mock-llm",
      sdkVersion: PROVIDER_SDK_VERSION,
      status: "ok",
    });
    expect(provider.capabilities().supportsStructuredOutput).toBe(true);
    expect(await provider.generate()).toMatchObject({ text: "mock" });
  });

  it("loads providers only through an explicit allow-list", () => {
    const registry = new AllowListedProviderRegistry();
    registry.register(new MockProvider());
    registry.register(
      {
        ...new MockProvider(),
        identity: () => ({
          name: "disabled",
          kind: "llm",
          version: "mock-provider-v1",
          apiVersion: PROVIDER_SDK_VERSION,
        }),
      },
      false,
    );

    expect(registry.allowedProviderNames("llm")).toEqual(["mock-llm"]);
    expect(registry.load("llm", "mock-llm").identity().name).toBe("mock-llm");
    expect(() => registry.load("llm", "missing")).toThrow(ProviderSdkError);
    expect(() => registry.load("llm", "disabled")).toThrow(/disabled/);
  });

  it("validates configuration without exposing secrets", () => {
    const provider = new MockProvider();
    const result = provider.validateConfig({
      providerName: "mock-llm",
      kind: "llm",
      enabled: true,
      secretRef: "env:ZAYD_PROVIDER_KEY",
      timeoutMs: 1_000,
      maxRetries: 1,
    });

    expect(result.valid).toBe(true);
    expect(JSON.stringify(result)).not.toContain("ZAYD_PROVIDER_KEY");
  });
});
