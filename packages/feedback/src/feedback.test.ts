import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import {
  FEEDBACK_CATEGORIES,
  FEEDBACK_CATEGORY_LABELS,
  validateFeedbackSubmission,
} from "./index.js";

const feedbackDir = dirname(fileURLToPath(import.meta.url));

describe("feedback categories", () => {
  it("labels all supported categories in Thai", () => {
    expect(FEEDBACK_CATEGORIES).toHaveLength(5);
    expect(FEEDBACK_CATEGORY_LABELS.incorrect_answer).toContain("ไม่ถูกต้อง");
    expect(FEEDBACK_CATEGORY_LABELS.citation_error).toContain("อ้างอิง");
  });
});

describe("feedback validation", () => {
  it("accepts valid submissions with optional notes", () => {
    expect(
      validateFeedbackSubmission({
        answerId: "ans-1",
        category: "other",
      }),
    ).toBeNull();
    expect(
      validateFeedbackSubmission({
        answerId: "ans-1",
        category: "citation_error",
        notes: "อ้างอิงไม่ตรง",
      }),
    ).toBeNull();
  });

  it("rejects missing answer id and unsupported categories", () => {
    expect(
      validateFeedbackSubmission({
        answerId: " ",
        category: "other",
      })?.field,
    ).toBe("answerId");
    expect(
      validateFeedbackSubmission({
        answerId: "ans-1",
        category: "invalid" as "other",
      })?.field,
    ).toBe("category");
  });

  it("rejects notes longer than 2000 characters", () => {
    expect(
      validateFeedbackSubmission({
        answerId: "ans-1",
        category: "other",
        notes: "x".repeat(2001),
      })?.field,
    ).toBe("notes");
  });
});

describe("feedback privacy contract", () => {
  it("submits answer references without internal trace fields", () => {
    const source = readFileSync(join(feedbackDir, "api.ts"), "utf8");
    expect(source).toContain("answer_id");
    expect(source).not.toContain("trace_id");
    expect(source).not.toContain("retrieval_run_id");
  });
});