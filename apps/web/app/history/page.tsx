import type { ReactElement } from "react";

import { getPublicEnv } from "@zayd/config/env/public";

import { UserAppClient } from "../user-app-client.js";

export default function HistoryPage(): ReactElement {
  const apiBaseUrl = getPublicEnv().NEXT_PUBLIC_API_BASE_URL;

  return (
    <UserAppClient activeNav="history" apiBaseUrl={apiBaseUrl}>
      <section className="zayd-panel">
        <h2>ประวัติการสนทนา</h2>
        <p>ประวัติจะพร้อมใช้งานหลัง TASK-09-05 Conversation History</p>
      </section>
      <div className="zayd-screen-placeholder">ยังไม่มีประวัติที่บันทึก</div>
    </UserAppClient>
  );
}