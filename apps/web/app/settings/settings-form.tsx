"use client";

import type { ReactElement } from "react";

import {
  ANSWER_LENGTH_LABELS,
  DEFAULT_MADHHAB_DISCLOSURE_TH,
  MADHHAB_LABELS,
  type AnswerLengthPreference,
  type MadhhabPreference,
} from "@zayd/preferences";
import { resolveTheme, type ThemeMode } from "@zayd/ui";

import { usePreferences } from "../preferences/preferences-provider.js";

export function SettingsForm(): ReactElement {
  const { preferences, isSignedIn, isSyncing, syncError, updatePreferences } = usePreferences();
  const resolvedTheme = resolveTheme(preferences.themeMode);

  return (
    <form
      className="zayd-settings"
      aria-labelledby="settings-heading"
      onSubmit={(event) => {
        event.preventDefault();
      }}
    >
      <p className="zayd-settings__disclosure" role="note">
        {DEFAULT_MADHHAB_DISCLOSURE_TH}
      </p>

      <fieldset className="zayd-settings__group">
        <legend>มัซฮับ</legend>
        <label className="zayd-settings__field" htmlFor="settings-madhhab">
          มัซฮับที่ต้องการ
        </label>
        <select
          id="settings-madhhab"
          className="zayd-settings__control"
          value={preferences.madhhab}
          disabled={isSyncing}
          onChange={(event) => {
            void updatePreferences({ madhhab: event.target.value as MadhhabPreference });
          }}
        >
          {Object.entries(MADHHAB_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </fieldset>

      <fieldset className="zayd-settings__group">
        <legend>ความยาวคำตอบ</legend>
        <label className="zayd-settings__field" htmlFor="settings-answer-length">
          ระดับความละเอียด
        </label>
        <select
          id="settings-answer-length"
          className="zayd-settings__control"
          value={preferences.answerLength}
          disabled={isSyncing}
          onChange={(event) => {
            void updatePreferences({
              answerLength: event.target.value as AnswerLengthPreference,
            });
          }}
        >
          {Object.entries(ANSWER_LENGTH_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </fieldset>

      <fieldset className="zayd-settings__group">
        <legend>การแสดงผล</legend>
        <label className="zayd-settings__checkbox">
          <input
            type="checkbox"
            checked={preferences.showArabic}
            disabled={isSyncing}
            onChange={(event) => {
              void updatePreferences({ showArabic: event.target.checked });
            }}
          />
          แสดงข้อความอาหรับจากแหล่งอ้างอิง
        </label>

        <label className="zayd-settings__field" htmlFor="settings-theme">
          ธีม
        </label>
        <select
          id="settings-theme"
          className="zayd-settings__control"
          value={preferences.themeMode}
          disabled={isSyncing}
          onChange={(event) => {
            void updatePreferences({ themeMode: event.target.value as ThemeMode });
          }}
        >
          <option value="system">ตามระบบ ({resolvedTheme === "dark" ? "มืด" : "สว่าง"})</option>
          <option value="light">สว่าง</option>
          <option value="dark">มืด</option>
        </select>
      </fieldset>

      <fieldset className="zayd-settings__group">
        <legend>ประวัติการสนทนา</legend>
        <label className="zayd-settings__checkbox">
          <input
            type="radio"
            name="history-mode"
            checked={preferences.historyMode === "enabled"}
            disabled={isSyncing}
            onChange={() => {
              void updatePreferences({ historyMode: "enabled" });
            }}
          />
          ใช้ประวัติการสนทนาเพื่อความต่อเนื่อง
        </label>
        <label className="zayd-settings__checkbox">
          <input
            type="radio"
            name="history-mode"
            checked={preferences.historyMode === "disabled"}
            disabled={isSyncing}
            onChange={() => {
              void updatePreferences({ historyMode: "disabled" });
            }}
          />
          ไม่ใช้ประวัติ (โหมดคำถามใหม่)
        </label>
      </fieldset>

      <p className="zayd-settings__status" aria-live="polite">
        {isSignedIn
          ? isSyncing
            ? "กำลังซิงก์การตั้งค่ากับบัญชี…"
            : "การตั้งค่าถูกซิงก์กับบัญชีที่ลงชื่อเข้าใช้แล้ว"
          : "โหมดผู้เยี่ยมชม: การตั้งค่าถูกเก็บในเครื่องของคุณเท่านั้น"}
      </p>

      {syncError ? (
        <p className="zayd-settings__error" role="alert">
          {syncError}
        </p>
      ) : null}
    </form>
  );
}