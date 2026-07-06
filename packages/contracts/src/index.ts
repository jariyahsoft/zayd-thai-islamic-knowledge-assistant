export interface HealthResponse {
  readonly status: "ok";
  readonly service: string;
}

export * from "./enums.js";
export * from "./state-machines.js";
export * from "./retrievability.js";
