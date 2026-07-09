export const PROVIDER_SDK_VERSION = "provider-sdk-v1" as const;

export type ProviderKind = "llm" | "embedding" | "knowledge" | "reranker" | "vector_store";
export type ProviderHealthStatus = "ok" | "degraded" | "unavailable";

export interface ProviderIdentity {
  readonly name: string;
  readonly kind: ProviderKind;
  readonly version: string;
  readonly apiVersion: typeof PROVIDER_SDK_VERSION;
  readonly modelId?: string;
  readonly modelRevision?: string;
}

export interface ProviderCapabilities {
  readonly supportsStreaming: boolean;
  readonly supportsStructuredOutput: boolean;
  readonly supportsBatching: boolean;
  readonly supportsMultilingual: boolean;
  readonly supportsHealthCheck: boolean;
  readonly maxInputTokens?: number;
  readonly maxOutputTokens?: number;
  readonly dimensions?: number;
  readonly capabilities: readonly string[];
}

export interface ProviderStoragePolicy {
  readonly persistentStorage: boolean;
  readonly maxCacheTtlSeconds: number;
  readonly dataSharingAllowed: boolean;
  readonly storesUserContent: boolean;
}

export interface ProviderConfig {
  readonly providerName: string;
  readonly kind: ProviderKind;
  readonly enabled: boolean;
  readonly baseUrl?: string;
  readonly secretRef?: string;
  readonly timeoutMs: number;
  readonly maxRetries: number;
  readonly extra?: Readonly<Record<string, unknown>>;
}

export interface ProviderValidationResult {
  readonly valid: boolean;
  readonly errors: readonly string[];
  readonly warnings: readonly string[];
}

export interface ProviderHealth {
  readonly status: ProviderHealthStatus;
  readonly checkedAt: string;
  readonly providerName: string;
  readonly kind: ProviderKind;
  readonly sdkVersion: typeof PROVIDER_SDK_VERSION;
  readonly message?: string;
  readonly latencyMs?: number;
  readonly trace: Readonly<Record<string, unknown>>;
}

export interface Provider {
  identity(): ProviderIdentity;
  capabilities(): ProviderCapabilities;
  validateConfig(config: ProviderConfig): ProviderValidationResult;
  healthCheck(): Promise<ProviderHealth>;
}

export interface LLMMessage {
  readonly role: "system" | "user" | "assistant" | "tool";
  readonly content: string;
}

export interface LLMRequest {
  readonly messages: readonly LLMMessage[];
  readonly traceId?: string;
  readonly temperature: number;
  readonly maxOutputTokens: number;
  readonly responseFormat: "text" | "json";
  readonly safetyContext?: Readonly<Record<string, unknown>>;
}

export interface LLMUsage {
  readonly inputTokens: number;
  readonly outputTokens: number;
  readonly totalTokens: number;
}

export interface LLMResponse {
  readonly text: string;
  readonly finishReason: "stop" | "length" | "tool_call" | "error";
  readonly provider: ProviderIdentity;
  readonly usage: LLMUsage;
  readonly trace: Readonly<Record<string, unknown>>;
}

export interface LLMProvider extends Provider {
  generate(request: LLMRequest): Promise<LLMResponse>;
  stream(request: LLMRequest, signal?: AbortSignal): AsyncIterable<string>;
}

export interface EmbeddingRequest {
  readonly texts: readonly string[];
  readonly language: string;
  readonly normalize: boolean;
  readonly traceId?: string;
}

export interface EmbeddingResult {
  readonly vectors: readonly (readonly number[])[];
  readonly dimensions: number;
  readonly provider: ProviderIdentity;
  readonly trace: Readonly<Record<string, unknown>>;
}

export interface EmbeddingProvider extends Provider {
  embed(request: EmbeddingRequest): Promise<EmbeddingResult>;
  dimensions(): number;
}

export interface KnowledgeSearchRequest {
  readonly query: string;
  readonly filters?: Readonly<Record<string, unknown>>;
  readonly limit: number;
  readonly traceId?: string;
}

export interface KnowledgeSearchResult {
  readonly providerDocumentId: string;
  readonly title: string;
  readonly snippet: string;
  readonly score: number;
  readonly metadata: Readonly<Record<string, unknown>>;
}

export interface KnowledgeSearchResponse {
  readonly results: readonly KnowledgeSearchResult[];
  readonly provider: ProviderIdentity;
  readonly storagePolicy: ProviderStoragePolicy;
  readonly trace: Readonly<Record<string, unknown>>;
}

export interface KnowledgeDocument {
  readonly providerDocumentId: string;
  readonly title: string;
  readonly content: string;
  readonly metadata: Readonly<Record<string, unknown>>;
}

export interface KnowledgeProvider extends Provider {
  search(request: KnowledgeSearchRequest): Promise<KnowledgeSearchResponse>;
  fetchDocument(providerDocumentId: string): Promise<KnowledgeDocument>;
  storagePolicy(): ProviderStoragePolicy;
}

export interface RerankRequest {
  readonly query: string;
  readonly documents: readonly KnowledgeSearchResult[];
  readonly traceId?: string;
}

export interface RerankResult {
  readonly providerDocumentId: string;
  readonly score: number;
  readonly rank: number;
  readonly metadata: Readonly<Record<string, unknown>>;
}

export interface RerankResponse {
  readonly results: readonly RerankResult[];
  readonly provider: ProviderIdentity;
  readonly trace: Readonly<Record<string, unknown>>;
}

export interface RerankerProvider extends Provider {
  rerank(request: RerankRequest): Promise<RerankResponse>;
}

export interface VectorRecord {
  readonly recordId: string;
  readonly vector: readonly number[];
  readonly metadata: Readonly<Record<string, unknown>>;
}

export interface VectorSearchRequest {
  readonly vector: readonly number[];
  readonly filters?: Readonly<Record<string, unknown>>;
  readonly limit: number;
  readonly traceId?: string;
}

export interface VectorSearchResult {
  readonly record: VectorRecord;
  readonly score: number;
  readonly rank: number;
}

export interface VectorStoreProvider extends Provider {
  search(request: VectorSearchRequest): Promise<readonly VectorSearchResult[]>;
  upsert(records: readonly VectorRecord[]): Promise<number>;
  delete(recordIds: readonly string[]): Promise<number>;
}

export class ProviderSdkError extends Error {
  readonly code: string;
  readonly statusCode: number;

  constructor(code: string, message: string, statusCode = 400) {
    super(message);
    this.name = "ProviderSdkError";
    this.code = code;
    this.statusCode = statusCode;
  }
}

export class AllowListedProviderRegistry {
  private readonly providers = new Map<string, { readonly provider: Provider; readonly enabled: boolean }>();

  register(provider: Provider, enabled = true): void {
    const identity = provider.identity();
    this.providers.set(this.key(identity.kind, identity.name), { provider, enabled });
  }

  allowedProviderNames(kind?: ProviderKind): readonly string[] {
    const names: string[] = [];
    for (const [key, registration] of this.providers.entries()) {
      const [providerKind, providerName] = key.split(":", 2);
      if (registration.enabled && (kind === undefined || providerKind === kind)) {
        names.push(providerName);
      }
    }
    return names.sort();
  }

  load(kind: ProviderKind, providerName: string): Provider {
    const registration = this.providers.get(this.key(kind, providerName));
    if (registration === undefined) {
      throw new ProviderSdkError("PROVIDER_NOT_ALLOWED", "Provider is not in the explicit allow-list.", 403);
    }
    if (!registration.enabled) {
      throw new ProviderSdkError("PROVIDER_DISABLED", "Provider is registered but disabled.", 403);
    }
    return registration.provider;
  }

  private key(kind: ProviderKind, providerName: string): string {
    return `${kind}:${providerName}`;
  }
}
