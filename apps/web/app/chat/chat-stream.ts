import type {
  ChatAnswerStatus,
  ChatFinalAnswerPayload,
  ChatStreamStage,
  GuestSession,
  ParsedChatEvent,
} from "./chat-types.js";

const GUEST_TOKEN_STORAGE_KEY = "zayd.guest_token";
const GUEST_EXPIRES_STORAGE_KEY = "zayd.guest_expires_at";

type SseFrame = {
  readonly id?: string;
  readonly event?: string;
  readonly data?: string;
};

export type ChatStreamRequest = {
  readonly apiBaseUrl: string;
  readonly question: string;
  readonly guestToken?: string | null;
  readonly accessToken?: string | null;
  readonly conversationId?: string | null;
  readonly signal?: AbortSignal;
  readonly onEvent: (event: ParsedChatEvent) => void;
};

export type ChatStreamResult = {
  readonly streamId: string | null;
};

export type ApiErrorBody = {
  readonly error?: {
    readonly code?: string;
    readonly message?: string;
  };
};

export function parseSseChunk(buffer: string): {
  readonly frames: readonly SseFrame[];
  readonly remainder: string;
} {
  const parts = buffer.split("\n\n");
  const remainder = parts.pop() ?? "";
  const frames = parts
    .map((part) => part.trim())
    .filter((part) => part.length > 0)
    .map(parseSseFrame);
  return { frames, remainder };
}

function parseSseFrame(raw: string): SseFrame {
  const frame: { id?: string; event?: string; data?: string } = {};
  for (const line of raw.split("\n")) {
    if (line.startsWith("id:")) {
      frame.id = line.slice(3).trim();
      continue;
    }
    if (line.startsWith("event:")) {
      frame.event = line.slice(6).trim();
      continue;
    }
    if (line.startsWith("data:")) {
      const chunk = line.slice(5).trim();
      frame.data = frame.data ? `${frame.data}\n${chunk}` : chunk;
    }
  }
  return frame;
}

export function parseChatEvent(frame: SseFrame): ParsedChatEvent | null {
  if (!frame.event || !frame.data) {
    return null;
  }
  const eventId = frame.id ?? "unknown";
  let payload: Record<string, unknown>;
  try {
    payload = JSON.parse(frame.data) as Record<string, unknown>;
  } catch {
    return null;
  }

  if (frame.event === "status") {
    const stage = payload.stage;
    if (typeof stage !== "string") {
      return null;
    }
    return {
      type: "status",
      eventId,
      stage: stage as ChatStreamStage,
      streamId: typeof payload.stream_id === "string" ? payload.stream_id : undefined,
      status: typeof payload.status === "string" ? payload.status : undefined,
    };
  }

  if (frame.event === "final_answer") {
    return {
      type: "final_answer",
      eventId,
      payload: payload as unknown as ChatFinalAnswerPayload,
    };
  }

  if (frame.event === "error") {
    return {
      type: "error",
      eventId,
      code: typeof payload.code === "string" ? payload.code : "CHAT_STREAM_ERROR",
      message: typeof payload.message === "string" ? payload.message : "เกิดข้อผิดพลาด",
    };
  }

  if (frame.event === "complete") {
    const status = payload.status;
    const streamId = payload.stream_id;
    if (typeof status !== "string" || typeof streamId !== "string") {
      return null;
    }
    return {
      type: "complete",
      eventId,
      status: status as ChatAnswerStatus,
      streamId,
    };
  }

  return null;
}

export async function consumeChatStream(request: ChatStreamRequest): Promise<ChatStreamResult> {
  const headers: Record<string, string> = {
    Accept: "text/event-stream",
    "Content-Type": "application/json",
  };
  if (request.accessToken) {
    headers.Authorization = `Bearer ${request.accessToken}`;
  }

  const body: Record<string, unknown> = {
    question: request.question,
    conversation_id: request.conversationId ?? null,
  };
  if (request.guestToken) {
    body.guest_token = request.guestToken;
  }

  const response = await fetch(new URL("chat/stream", request.apiBaseUrl), {
    method: "POST",
    headers,
    body: JSON.stringify(body),
    signal: request.signal,
  });

  if (!response.ok) {
    const error = await readApiError(response);
    throw new ChatClientError(error.code, error.message, response.status);
  }

  const streamId = response.headers.get("X-Stream-Id");
  const reader = response.body?.getReader();
  if (!reader) {
    throw new ChatClientError("CHAT_STREAM_ERROR", "ไม่สามารถอ่านสตรีมได้", 500);
  }

  const decoder = new TextDecoder();
  let buffer = "";
  let resolvedStreamId = streamId;

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const parsed = parseSseChunk(buffer);
    buffer = parsed.remainder;
    for (const frame of parsed.frames) {
      const event = parseChatEvent(frame);
      if (!event) {
        continue;
      }
      if (event.type === "status" && event.streamId) {
        resolvedStreamId = event.streamId;
      }
      request.onEvent(event);
    }
  }

  if (buffer.trim().length > 0) {
    const trailing = parseSseChunk(`${buffer}\n\n`);
    for (const frame of trailing.frames) {
      const event = parseChatEvent(frame);
      if (event) {
        request.onEvent(event);
      }
    }
  }

  return { streamId: resolvedStreamId };
}

export async function cancelChatStream(options: {
  readonly apiBaseUrl: string;
  readonly streamId: string;
  readonly accessToken: string;
}): Promise<void> {
  const response = await fetch(
    new URL(`chat/streams/${encodeURIComponent(options.streamId)}`, options.apiBaseUrl),
    {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${options.accessToken}`,
      },
    },
  );
  if (!response.ok) {
    const error = await readApiError(response);
    throw new ChatClientError(error.code, error.message, response.status);
  }
}

export async function ensureGuestSession(apiBaseUrl: string): Promise<GuestSession> {
  const storedToken = readStoredGuestToken();
  if (storedToken) {
    return storedToken;
  }
  const response = await fetch(new URL("auth/guest/start", apiBaseUrl), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    const error = await readApiError(response);
    throw new ChatClientError(error.code, error.message, response.status);
  }
  const payload = (await response.json()) as {
    guest_token: string;
    expires_at: string;
    message_quota: number;
    messages_used: number;
  };
  const session: GuestSession = {
    guestToken: payload.guest_token,
    expiresAt: payload.expires_at,
    messageQuota: payload.message_quota,
    messagesUsed: payload.messages_used,
  };
  persistGuestSession(session);
  return session;
}

export function readStoredGuestToken(): GuestSession | null {
  if (typeof window === "undefined") {
    return null;
  }
  const guestToken = window.localStorage.getItem(GUEST_TOKEN_STORAGE_KEY);
  const expiresAt = window.localStorage.getItem(GUEST_EXPIRES_STORAGE_KEY);
  if (!guestToken || !expiresAt) {
    return null;
  }
  if (new Date(expiresAt).getTime() <= Date.now()) {
    clearGuestSession();
    return null;
  }
  return {
    guestToken,
    expiresAt,
    messageQuota: 0,
    messagesUsed: 0,
  };
}

export function persistGuestSession(session: GuestSession): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(GUEST_TOKEN_STORAGE_KEY, session.guestToken);
  window.localStorage.setItem(GUEST_EXPIRES_STORAGE_KEY, session.expiresAt);
}

export function clearGuestSession(): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.removeItem(GUEST_TOKEN_STORAGE_KEY);
  window.localStorage.removeItem(GUEST_EXPIRES_STORAGE_KEY);
}

export function readStoredAccessToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem("zayd.access_token");
}

async function readApiError(response: Response): Promise<{ code: string; message: string }> {
  try {
    const payload = (await response.json()) as ApiErrorBody;
    return {
      code: payload.error?.code ?? "CHAT_STREAM_ERROR",
      message: payload.error?.message ?? "เกิดข้อผิดพลาดจากเซิร์ฟเวอร์",
    };
  } catch {
    return {
      code: "CHAT_STREAM_ERROR",
      message: "เกิดข้อผิดพลาดจากเซิร์ฟเวอร์",
    };
  }
}

export class ChatClientError extends Error {
  readonly code: string;
  readonly statusCode: number;

  constructor(code: string, message: string, statusCode: number) {
    super(message);
    this.name = "ChatClientError";
    this.code = code;
    this.statusCode = statusCode;
  }
}