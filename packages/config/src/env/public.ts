export type PublicEnv = {
  readonly NEXT_PUBLIC_API_BASE_URL: string;
};

function normalizeApiBaseUrl(value: string): string {
  const url = new URL(value);
  const pathname = url.pathname.endsWith("/") ? url.pathname : `${url.pathname}/`;
  return `${url.origin}${pathname}${url.search}${url.hash}`;
}

export function getPublicEnv(
  overrides?: Partial<Record<"NEXT_PUBLIC_API_BASE_URL", string>>,
): PublicEnv {
  const raw =
    overrides?.NEXT_PUBLIC_API_BASE_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    "http://localhost:8000";

  try {
    return {
      NEXT_PUBLIC_API_BASE_URL: normalizeApiBaseUrl(raw),
    };
  } catch {
    throw new Error("NEXT_PUBLIC_API_BASE_URL must be a valid absolute URL.");
  }
}