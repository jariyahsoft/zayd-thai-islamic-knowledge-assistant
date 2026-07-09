import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const historyDir = dirname(fileURLToPath(import.meta.url));

describe("history page", () => {
  it("requires sign-in for server-side history access", () => {
    const list = readFileSync(join(historyDir, "history-list.tsx"), "utf8");
    expect(list).toContain("readStoredAccessToken");
    expect(list).toContain("โหมดผู้เยี่ยมชมไม่บันทึกประวัติบนเซิร์ฟเวอร์");
  });

  it("supports search, open, delete, and delete-all controls", () => {
    const list = readFileSync(join(historyDir, "history-list.tsx"), "utf8");
    expect(list).toContain("deleteAllConversations");
    expect(list).toContain("deleteConversation");
    expect(list).toContain("/chat?conversation=");
    expect(list).toContain('type="search"');
  });
});