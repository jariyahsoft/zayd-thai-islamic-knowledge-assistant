import type { CitationDetail, PublicSourceDetail } from "./types.js";

type ApiErrorBody = {
  readonly error?: {
    readonly code?: string;
    readonly message?: string;
  };
};

export class CitationClientError extends Error {
  readonly code: string;
  readonly statusCode: number;

  constructor(code: string, message: string, statusCode: number) {
    super(message);
    this.name = "CitationClientError";
    this.code = code;
    this.statusCode = statusCode;
  }
}

export async function fetchCitationDetail(
  apiBaseUrl: string,
  citationRef: string,
): Promise<CitationDetail> {
  const response = await fetch(
    new URL(`citations/${encodeURIComponent(citationRef)}`, apiBaseUrl),
    {
      headers: { Accept: "application/json" },
    },
  );
  if (!response.ok) {
    throw await toClientError(response);
  }
  return (await response.json()) as CitationDetail;
}

export async function fetchSourceDetail(
  apiBaseUrl: string,
  sourceId: string,
): Promise<PublicSourceDetail> {
  const response = await fetch(new URL(`sources/${encodeURIComponent(sourceId)}`, apiBaseUrl), {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw await toClientError(response);
  }
  return (await response.json()) as PublicSourceDetail;
}

async function toClientError(response: Response): Promise<CitationClientError> {
  try {
    const payload = (await response.json()) as ApiErrorBody;
    return new CitationClientError(
      payload.error?.code ?? "CITATION_CLIENT_ERROR",
      payload.error?.message ?? "ไม่สามารถโหลดข้อมูลอ้างอิงได้",
      response.status,
    );
  } catch {
    return new CitationClientError(
      "CITATION_CLIENT_ERROR",
      "ไม่สามารถโหลดข้อมูลอ้างอิงได้",
      response.status,
    );
  }
}