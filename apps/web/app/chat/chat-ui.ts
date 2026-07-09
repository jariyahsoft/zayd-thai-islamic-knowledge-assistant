import type { ChatAnswerStatus, ChatMessage, ChatStreamStage } from "./chat-types.js";

const ARABIC_PATTERN = /[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]/u;

export const CHAT_STAGE_LABELS: Record<ChatStreamStage, string> = {
  accepted: "รับคำถามแล้ว",
  classifying: "กำลังจัดประเภทคำถาม",
  retrieving: "กำลังค้นหาหลักฐาน",
  verifying: "กำลังตรวจสอบคำตอบ",
  completed: "เสร็จสิ้น",
  cancelled: "ยกเลิกแล้ว",
};

export const CHAT_ERROR_LABELS: Record<string, string> = {
  CHAT_AUTH_REQUIRED: "ต้องเข้าสู่ระบบหรือเริ่มเซสชันผู้เยี่ยมชม",
  CHAT_INPUT_INVALID: "คำถามไม่ถูกต้อง",
  CHAT_RATE_LIMITED: "ส่งคำถามบ่อยเกินไป กรุณารอสักครู่",
  GUEST_QUOTA_EXCEEDED: "โควตาผู้เยี่ยมชมหมดแล้ว",
  RBAC_FORBIDDEN: "ไม่มีสิทธิ์ใช้งานแชท",
};

export function containsArabic(value: string): boolean {
  return ARABIC_PATTERN.test(value);
}

export function formatChatError(code: string, fallbackMessage: string): string {
  return CHAT_ERROR_LABELS[code] ?? fallbackMessage;
}

export function mapCompleteStatus(status: ChatAnswerStatus): ChatMessage["status"] {
  if (status === "completed") {
    return "completed";
  }
  if (status === "abstained") {
    return "abstained";
  }
  if (status === "cancelled") {
    return "cancelled";
  }
  return "error";
}

export function abstentionMessage(): string {
  return "ยังไม่พบหลักฐานที่เพียงพอสำหรับตอบคำถามนี้อย่างน่าเชื่อถือ ระบบจึงเลือกที่จะไม่ตอบ";
}

export function cancellationMessage(): string {
  return "ยกเลิกการสร้างคำตอบแล้ว";
}

export function createMessageId(prefix: string): string {
  return `${prefix}-${crypto.randomUUID()}`;
}