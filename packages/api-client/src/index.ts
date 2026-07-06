import type { HealthResponse } from "@zayd/contracts";

export interface ApiClient {
  readonly baseUrl: string;
  getHealth(): Promise<HealthResponse>;
}

export function createApiClient(config: { baseUrl: string }): ApiClient {
  return {
    baseUrl: config.baseUrl,
    getHealth() {
      return Promise.resolve({
        status: "ok",
        service: "placeholder",
      });
    },
  };
}
