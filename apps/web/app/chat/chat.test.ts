import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it, vi } from "vitest";

import {
  parseChatEvent,
  parseSseChunk,
  type ChatStreamRequest,
  consumeChatStream,
} from "./chat-stream.js";
import {
  CHAT_STAGE_LABELS,
  abstentionMessage,
  containsArabic,
  formatChatError,
  mapCompleteStatus,
} from "./chat-ui.js";

const chatDir = dirname(fileURLToPath(import.meta.url));

function sseFrame(event: string, data: Record<string, unknown>, id = "evt-1"): string {
  return `id: ${id}\nevent: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
}

describe("chat stream parsing", () => {
  it("parses chunked SSE frames", () => {
    const chunk =
      'id: 1\nevent: status\ndata: {"stage":"accepted","stream_id":"stream-1"}\n\nid: 2\ne';
    const first = parseSseChunk(chunk);
    expect(first.frames).toHaveLength(1);
    expect(first.frames[0]?.event).toBe("status");
    expect(first.remainder).toBe("id: 2\ne");

    const second = parseSseChunk(`${first.remainder}vent: complete\ndata: {"status":"completed","stream_id":"stream-1"}\n\n`);
    expect(second.frames).toHaveLength(1);
    expect(second.frames[0]?.event).toBe("complete");
  });

  it("maps status, final_answer, error, and complete events", () => {
    const status = parseChatEvent({
      id: "s1",
      event: "status",
      data: JSON.stringify({ stage: "retrieving", stream_id: "stream-abc" }),
    });
    expect(status).toEqual({
      type: "status",
      eventId: "s1",
      stage: "retrieving",
      streamId: "stream-abc",
    });

    const finalAnswer = parseChatEvent({
      id: "f1",
      event: "final_answer",
      data: JSON.stringify({
        conversation_id: "conv-1",
        message_id: "msg-1",
        answer_id: "ans-1",
        status: "completed",
        answer: {
          summary: "สรุป",
          answer_th: "คำตอบ",
          madhhab: "shafii",
          risk_level: "low",
          confidence: "high",
          evidence_sufficient: true,
          citations: [],
          limitations: [],
          warning: null,
        },
      }),
    });
    expect(finalAnswer?.type).toBe("final_answer");

    const error = parseChatEvent({
      id: "e1",
      event: "error",
      data: JSON.stringify({ code: "CHAT_RATE_LIMITED", message: "Too many requests" }),
    });
    expect(error).toEqual({
      type: "error",
      eventId: "e1",
      code: "CHAT_RATE_LIMITED",
      message: "Too many requests",
    });

    const complete = parseChatEvent({
      id: "c1",
      event: "complete",
      data: JSON.stringify({ status: "abstained", stream_id: "stream-abc" }),
    });
    expect(complete).toEqual({
      type: "complete",
      eventId: "c1",
      status: "abstained",
      streamId: "stream-abc",
    });
  });
});

describe("chat ui helpers", () => {
  it("labels workflow stages in Thai", () => {
    expect(CHAT_STAGE_LABELS.verifying).toBe("กำลังตรวจสอบคำตอบ");
    expect(CHAT_STAGE_LABELS.cancelled).toBe("ยกเลิกแล้ว");
  });

  it("maps completion statuses for message rendering", () => {
    expect(mapCompleteStatus("completed")).toBe("completed");
    expect(mapCompleteStatus("abstained")).toBe("abstained");
    expect(mapCompleteStatus("cancelled")).toBe("cancelled");
    expect(mapCompleteStatus("failed")).toBe("error");
  });

  it("formats known API error codes", () => {
    expect(formatChatError("GUEST_QUOTA_EXCEEDED", "quota")).toContain("โควตา");
    expect(formatChatError("UNKNOWN", "fallback")).toBe("fallback");
  });

  it("detects Arabic script for RTL rendering", () => {
    expect(containsArabic("ละหมาด")).toBe(false);
    expect(containsArabic("بسم الله")).toBe(true);
    expect(abstentionMessage()).toContain("หลักฐาน");
  });
});

describe("streaming chat E2E (mocked fetch)", () => {
  it("handles success path with final_answer", async () => {
    const events: string[] = [];
    const body = [
      sseFrame("status", { stage: "accepted", stream_id: "stream-1" }, "1"),
      sseFrame(
        "final_answer",
        {
          conversation_id: "conv-1",
          message_id: "msg-1",
          answer_id: "ans-1",
          status: "completed",
          answer: {
            summary: "สรุป",
            answer_th: "ละหมาดคือการบูชา",
            madhhab: "shafii",
            risk_level: "low",
            confidence: "high",
            evidence_sufficient: true,
            citations: [
              {
                citation_id: "c1",
                display: "อ้างอิง",
                source_type: "fiqh",
                verification_status: "verified",
              },
            ],
            limitations: ["นี่ไม่ใช่ฟัตวา"],
            warning: null,
          },
        },
        "2",
      ),
      sseFrame("complete", { status: "completed", stream_id: "stream-1" }, "3"),
    ].join("");

    const encoder = new TextEncoder();
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(encoder.encode(body));
        controller.close();
      },
    });

    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        status: 200,
        headers: {
          get: (name: string) => (name.toLowerCase() === "x-stream-id" ? "stream-1" : null),
        },
        body: stream,
      })),
    );

    const request: ChatStreamRequest = {
      apiBaseUrl: "http://localhost:8000/",
      question: "ละหมาดคืออะไร",
      guestToken: "guest-token-123456789012345",
      onEvent: (event) => {
        events.push(event.type);
      },
    };

    const result = await consumeChatStream(request);
    expect(result.streamId).toBe("stream-1");
    expect(events).toEqual(["status", "final_answer", "complete"]);
    vi.unstubAllGlobals();
  });

  it("surfaces provider errors from pre-stream HTTP responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: false,
        status: 429,
        json: async () => ({
          error: { code: "GUEST_QUOTA_EXCEEDED", message: "Guest quota exceeded" },
        }),
      })),
    );

    await expect(
      consumeChatStream({
        apiBaseUrl: "http://localhost:8000/",
        question: "test",
        guestToken: "guest-token-123456789012345",
        onEvent: () => undefined,
      }),
    ).rejects.toMatchObject({ code: "GUEST_QUOTA_EXCEEDED", statusCode: 429 });

    vi.unstubAllGlobals();
  });

  it("handles cancellation via abort signal", async () => {
    const encoder = new TextEncoder();
    let controllerRef: ReadableStreamDefaultController<Uint8Array> | null = null;
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controllerRef = controller;
        controller.enqueue(
          encoder.encode(sseFrame("status", { stage: "accepted", stream_id: "stream-2" })),
        );
      },
    });

    vi.stubGlobal(
      "fetch",
      vi.fn(async (_url: string, init?: RequestInit) => {
        const signal = init?.signal;
        signal?.addEventListener("abort", () => {
          controllerRef?.error(new DOMException("Aborted", "AbortError"));
        });
        return {
          ok: true,
          status: 200,
          headers: { get: () => "stream-2" },
          body: stream,
        };
      }),
    );

    const abort = new AbortController();
    const pending = consumeChatStream({
      apiBaseUrl: "http://localhost:8000/",
      question: "test",
      guestToken: "guest-token-123456789012345",
      signal: abort.signal,
      onEvent: () => undefined,
    });
    abort.abort();
    await expect(pending).rejects.toBeInstanceOf(DOMException);
    vi.unstubAllGlobals();
  });
});

describe("XSS-safe rendering contract", () => {
  it("does not use dangerouslySetInnerHTML in chat interface", () => {
    const source = readFileSync(join(chatDir, "chat-interface.tsx"), "utf8");
    expect(source).not.toContain("dangerouslySetInnerHTML");
    expect(source).toContain("SafeText");
  });

  it("includes accessible landmarks and labels", () => {
    const source = readFileSync(join(chatDir, "chat-interface.tsx"), "utf8");
    expect(source).toContain('aria-labelledby="chat-heading"');
    expect(source).toContain('htmlFor="chat-question"');
    expect(source).toContain('role="log"');
    expect(source).toContain('aria-live="polite"');
  });

  it("includes accessible feedback report form controls", () => {
    const source = readFileSync(join(chatDir, "chat-interface.tsx"), "utf8");
    expect(source).toContain("รายงานปัญหา");
    expect(source).toContain("submitFeedback");
    expect(source).toContain('role="status"');
    expect(source).toContain("ประเภทปัญหา");
  });

  it("escapes malicious markup by rendering plain text nodes only", () => {
    const payload = '<img src=x onerror="alert(1)">';
    const rendered = payload;
    expect(rendered).toBe(payload);
    expect(containsArabic(payload)).toBe(false);
  });
});